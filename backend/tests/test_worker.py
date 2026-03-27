"""Tests for task worker functions and new task endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch


def _tasks_url(workspace):
    """Build the nested tasks URL for a workspace."""
    return f"/api/v1/workspaces/{workspace['slug']}/tasks"


# ---------------------------------------------------------------------------
# Tests for new task route endpoints (delete, enqueue, status, filtering)
# ---------------------------------------------------------------------------


def test_delete_task(test_client, auth_headers, create_workspace):
    """Test deleting a task."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    # Create a task
    resp = test_client.post(f"{url}/", json={"title": "To Delete"}, headers=headers)
    assert resp.status_code == 200
    task_id = resp.json()["id"]

    # Delete it
    resp = test_client.delete(f"{url}/{task_id}", headers=headers)
    assert resp.status_code == 204

    # Confirm it's gone
    resp = test_client.get(f"{url}/{task_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_nonexistent_task(test_client, auth_headers, create_workspace):
    """Test deleting a task that doesn't exist."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp = test_client.delete(f"{url}/99999", headers=headers)
    assert resp.status_code == 404


def test_list_tasks_filter_by_status(test_client, auth_headers, create_workspace):
    """Test filtering tasks by status."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    # Create tasks and update one to in_progress
    test_client.post(f"{url}/", json={"title": "Pending Task"}, headers=headers)
    resp2 = test_client.post(f"{url}/", json={"title": "Active Task"}, headers=headers)
    task_id = resp2.json()["id"]
    test_client.put(f"{url}/{task_id}", json={"status": "in_progress"}, headers=headers)

    # Filter by pending
    resp = test_client.get(f"{url}/", params={"status": "pending"}, headers=headers)
    assert resp.status_code == 200
    tasks = resp.json()
    assert all(t["status"] == "pending" for t in tasks)
    assert len(tasks) == 1

    # Filter by in_progress
    resp = test_client.get(f"{url}/", params={"status": "in_progress"}, headers=headers)
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Active Task"


def test_list_tasks_filter_by_assigned_to(test_client, auth_headers, create_workspace):
    """Test filtering tasks by assigned_to."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp1 = test_client.post(f"{url}/", json={"title": "Task A"}, headers=headers)
    resp2 = test_client.post(f"{url}/", json={"title": "Task B"}, headers=headers)
    test_client.put(f"{url}/{resp1.json()['id']}", json={"assigned_to": "agent-1"}, headers=headers)
    test_client.put(f"{url}/{resp2.json()['id']}", json={"assigned_to": "agent-2"}, headers=headers)

    resp = test_client.get(f"{url}/", params={"assigned_to": "agent-1"}, headers=headers)
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task A"


def test_list_tasks_filter_combined(test_client, auth_headers, create_workspace):
    """Test filtering tasks by both status and assigned_to."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp1 = test_client.post(f"{url}/", json={"title": "Task 1"}, headers=headers)
    resp2 = test_client.post(f"{url}/", json={"title": "Task 2"}, headers=headers)
    test_client.put(f"{url}/{resp1.json()['id']}", json={"assigned_to": "agent-x", "status": "in_progress"}, headers=headers)
    test_client.put(f"{url}/{resp2.json()['id']}", json={"assigned_to": "agent-x"}, headers=headers)

    # Both assigned to agent-x, but only one is in_progress
    resp = test_client.get(f"{url}/", params={"assigned_to": "agent-x", "status": "in_progress"}, headers=headers)
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task 1"


def test_create_task_with_job_type(test_client, auth_headers, create_workspace):
    """Test creating a task with a custom job_type."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp = test_client.post(
        f"{url}/",
        json={"title": "Export Job", "job_type": "export"},
        headers=headers,
    )
    assert resp.status_code == 200
    task = resp.json()
    assert task["job_type"] == "export"


def test_enqueue_task_no_redis(test_client, auth_headers, create_workspace):
    """Test enqueue returns 503 when Redis is not available."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp = test_client.post(f"{url}/", json={"title": "Background Task"}, headers=headers)
    task_id = resp.json()["id"]

    # arq_pool is None in test environment (no Redis)
    resp = test_client.post(f"{url}/{task_id}/enqueue", headers=headers)
    assert resp.status_code == 503
    assert "not available" in resp.json()["detail"]


def test_enqueue_task_with_mock_redis(test_client, auth_headers, create_workspace):
    """Test enqueue succeeds when ARQ pool is available."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp = test_client.post(f"{url}/", json={"title": "Background Task"}, headers=headers)
    task_id = resp.json()["id"]

    # Mock the ARQ pool on the app state
    mock_job = MagicMock()
    mock_job.job_id = "test-job-123"
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

    from codex.main import app

    app.state.arq_pool = mock_pool
    try:
        resp = test_client.post(f"{url}/{task_id}/enqueue", headers=headers)
        assert resp.status_code == 200
        task = resp.json()
        assert task["job_id"] == "test-job-123"
        mock_pool.enqueue_job.assert_called_once_with("run_job", task_id)
    finally:
        app.state.arq_pool = None


def test_enqueue_task_wrong_status(test_client, auth_headers, create_workspace):
    """Test enqueue rejects tasks that are already in_progress."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp = test_client.post(f"{url}/", json={"title": "Running Task"}, headers=headers)
    task_id = resp.json()["id"]
    test_client.put(f"{url}/{task_id}", json={"status": "in_progress"}, headers=headers)

    # Mock ARQ pool so we don't get 503
    mock_pool = AsyncMock()
    from codex.main import app

    app.state.arq_pool = mock_pool
    try:
        resp = test_client.post(f"{url}/{task_id}/enqueue", headers=headers)
        assert resp.status_code == 409
    finally:
        app.state.arq_pool = None


def test_task_status_endpoint(test_client, auth_headers, create_workspace):
    """Test the task status endpoint returns DB status."""
    headers = auth_headers[0]
    workspace = create_workspace()
    url = _tasks_url(workspace)

    resp = test_client.post(f"{url}/", json={"title": "Status Check"}, headers=headers)
    task_id = resp.json()["id"]

    resp = test_client.get(f"{url}/{task_id}/status", headers=headers)
    assert resp.status_code == 200
    status = resp.json()
    assert status["task_id"] == task_id
    assert status["status"] == "pending"
    assert status["job_id"] is None


def test_delete_requires_authentication(test_client):
    """Test that delete and enqueue endpoints require authentication."""
    resp = test_client.delete("/api/v1/workspaces/no-such-ws/tasks/1")
    assert resp.status_code == 401

    resp = test_client.post("/api/v1/workspaces/no-such-ws/tasks/1/enqueue")
    assert resp.status_code == 401

    resp = test_client.get("/api/v1/workspaces/no-such-ws/tasks/1/status")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests for worker task functions (unit tests with mocked DB)
# ---------------------------------------------------------------------------


def _make_session_maker(mock_session=None):
    """Create a mock async session maker compatible with `async with maker() as session`."""
    if mock_session is None:
        mock_session = AsyncMock()

    class _FakeCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            pass

    return MagicMock(side_effect=lambda: _FakeCtx())


@patch("codex.worker.tasks._load_task")
async def test_run_job_task_not_found(mock_load):
    """Test run_job handles missing tasks."""
    from codex.worker.tasks import run_job

    mock_load.return_value = None
    ctx = {"session_maker": _make_session_maker()}

    result = await run_job(ctx, task_id=999)
    assert result["status"] == "error"
    assert "not found" in result["detail"]


@patch("codex.worker.tasks._load_task")
async def test_run_job_unknown_job_type(mock_load):
    """Test run_job handles unknown job types."""
    from codex.worker.tasks import run_job

    mock_task = MagicMock()
    mock_task.id = 1
    mock_task.job_type = "unknown_type"
    mock_load.return_value = mock_task

    mock_session = AsyncMock()
    ctx = {"session_maker": _make_session_maker(mock_session)}

    result = await run_job(ctx, task_id=1)
    assert result["status"] == "error"
    assert "Unknown job_type" in result["detail"]

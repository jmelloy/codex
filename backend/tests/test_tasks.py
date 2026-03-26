"""Tests for task endpoints."""


def test_create_task(test_client, auth_headers, create_workspace):
    """Test creating a task."""
    headers = auth_headers[0]
    workspace = create_workspace()
    workspace_id = workspace["id"]

    # Create a task
    response = test_client.post(
        "/api/v1/tasks/",
        json={"workspace_id": workspace_id, "title": "Test Task", "description": "This is a test task"},
        headers=headers,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["title"] == "Test Task"
    assert task["description"] == "This is a test task"
    assert task["status"] == "pending"
    assert task["workspace_id"] == workspace_id


def test_list_tasks(test_client, auth_headers, create_workspace):
    """Test listing tasks for a workspace."""
    headers = auth_headers[0]
    workspace = create_workspace()
    workspace_id = workspace["id"]

    # Initially should be empty
    response = test_client.get("/api/v1/tasks/", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Create some tasks
    for i in range(3):
        test_client.post(
            "/api/v1/tasks/", json={"workspace_id": workspace_id, "title": f"Task {i+1}"}, headers=headers
        )

    # List tasks
    response = test_client.get("/api/v1/tasks/", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 3


def test_get_task(test_client, auth_headers, create_workspace):
    """Test getting a specific task."""
    headers = auth_headers[0]
    workspace = create_workspace()
    workspace_id = workspace["id"]

    # Create a task
    create_response = test_client.post(
        "/api/v1/tasks/",
        json={"workspace_id": workspace_id, "title": "Specific Task", "description": "Task to retrieve"},
        headers=headers,
    )
    task_id = create_response.json()["id"]

    # Get the task
    response = test_client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    task = response.json()
    assert task["id"] == task_id
    assert task["title"] == "Specific Task"
    assert task["description"] == "Task to retrieve"


def test_get_nonexistent_task(test_client, auth_headers):
    """Test getting a task that doesn't exist."""
    headers = auth_headers[0]

    response = test_client.get("/api/v1/tasks/99999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_status(test_client, auth_headers, create_workspace):
    """Test updating a task's status."""
    headers = auth_headers[0]
    workspace = create_workspace()
    workspace_id = workspace["id"]

    # Create a task
    create_response = test_client.post(
        "/api/v1/tasks/", json={"workspace_id": workspace_id, "title": "Task to Update"}, headers=headers
    )
    task_id = create_response.json()["id"]
    assert create_response.json()["status"] == "pending"

    # Update status to in_progress
    response = test_client.put(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # Update status to completed
    response = test_client.put(f"/api/v1/tasks/{task_id}", json={"status": "completed"}, headers=headers)
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"
    assert task["completed_at"] is not None


def test_update_task_assignment(test_client, auth_headers, create_workspace):
    """Test assigning a task to an agent."""
    headers = auth_headers[0]
    workspace = create_workspace()
    workspace_id = workspace["id"]

    # Create a task
    create_response = test_client.post(
        "/api/v1/tasks/", json={"workspace_id": workspace_id, "title": "Task to Assign"}, headers=headers
    )
    task_id = create_response.json()["id"]

    # Assign to an agent
    response = test_client.put(f"/api/v1/tasks/{task_id}", json={"assigned_to": "agent-123"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["assigned_to"] == "agent-123"


def test_update_nonexistent_task(test_client, auth_headers):
    """Test updating a task that doesn't exist."""
    headers = auth_headers[0]

    response = test_client.put("/api/v1/tasks/99999", json={"status": "completed"}, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_task_requires_authentication(test_client):
    """Test that task endpoints require authentication."""
    # No auth header
    response = test_client.get("/api/v1/tasks/", params={"workspace_id": 1})
    assert response.status_code == 401

    response = test_client.post("/api/v1/tasks/", json={"workspace_id": 1, "title": "Test"})
    assert response.status_code == 401

    response = test_client.get("/api/v1/tasks/1")
    assert response.status_code == 401

    response = test_client.put("/api/v1/tasks/1", json={"status": "completed"})
    assert response.status_code == 401


# --- Nested router tests ---


def test_nested_create_task(test_client, auth_headers, create_workspace):
    """Test creating a task via nested workspace route."""
    headers = auth_headers[0]
    workspace = create_workspace()

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/tasks/",
        json={"title": "Nested Task", "description": "Created via nested route"},
        headers=headers,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["title"] == "Nested Task"
    assert task["description"] == "Created via nested route"
    assert task["workspace_id"] == workspace["id"]


def test_nested_list_tasks(test_client, auth_headers, create_workspace):
    """Test listing tasks via nested workspace route."""
    headers = auth_headers[0]
    workspace = create_workspace()

    # Create tasks via nested route
    for i in range(2):
        test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/tasks/",
            json={"title": f"Nested Task {i+1}"},
            headers=headers,
        )

    response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/tasks/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_nested_get_task(test_client, auth_headers, create_workspace):
    """Test getting a task via nested workspace route."""
    headers = auth_headers[0]
    workspace = create_workspace()

    create_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/tasks/",
        json={"title": "Get Me"},
        headers=headers,
    )
    task_id = create_resp.json()["id"]

    response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Get Me"


def test_nested_update_task(test_client, auth_headers, create_workspace):
    """Test updating a task via nested workspace route."""
    headers = auth_headers[0]
    workspace = create_workspace()

    create_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/tasks/",
        json={"title": "Update Me"},
        headers=headers,
    )
    task_id = create_resp.json()["id"]

    response = test_client.put(
        f"/api/v1/workspaces/{workspace['slug']}/tasks/{task_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None


def test_nested_workspace_by_id(test_client, auth_headers, create_workspace):
    """Test nested route works with workspace ID too."""
    headers = auth_headers[0]
    workspace = create_workspace()

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/tasks/",
        json={"title": "By ID"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "By ID"

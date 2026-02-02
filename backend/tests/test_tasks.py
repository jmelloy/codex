"""Tests for task endpoints."""

import time
from pathlib import Path


def get_workspace_slug_from_response(workspace_response: dict) -> str:
    """Extract workspace slug from API response path."""
    return Path(workspace_response["path"]).name


def setup_test_user(test_client):
    """Register and login a test user for task tests."""
    username = f"test_task_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    # Register
    test_client.post("/api/register", json={"username": username, "email": email, "password": password})

    # Login
    login_response = test_client.post("/api/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_task(test_client, temp_workspace_dir):
    """Test creating a task."""
    headers = setup_test_user(test_client)

    # Create a workspace first
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Task Test Workspace", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # Create a task
    response = test_client.post(
        f"/api/v1/{workspace_slug}/tasks",
        params={"title": "Test Task", "description": "This is a test task"},
        headers=headers,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["title"] == "Test Task"
    assert task["description"] == "This is a test task"
    assert task["status"] == "pending"

    # Cleanup handled by fixture


def test_list_tasks(test_client, temp_workspace_dir):
    """Test listing tasks for a workspace."""
    headers = setup_test_user(test_client)

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Task List Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # Initially should be empty
    response = test_client.get(f"/api/v1/{workspace_slug}/tasks", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Create some tasks
    for i in range(3):
        test_client.post(
            f"/api/v1/{workspace_slug}/tasks", params={"title": f"Task {i+1}"}, headers=headers
        )

    # List tasks
    response = test_client.get(f"/api/v1/{workspace_slug}/tasks", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 3

    # Cleanup handled by fixture


def test_get_task(test_client, temp_workspace_dir):
    """Test getting a specific task."""
    headers = setup_test_user(test_client)

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Get Task Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # Create a task
    create_response = test_client.post(
        f"/api/v1/{workspace_slug}/tasks",
        params={"title": "Specific Task", "description": "Task to retrieve"},
        headers=headers,
    )
    task_id = create_response.json()["id"]

    # Get the task
    response = test_client.get(f"/api/v1/{workspace_slug}/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    task = response.json()
    assert task["id"] == task_id
    assert task["title"] == "Specific Task"
    assert task["description"] == "Task to retrieve"

    # Cleanup handled by fixture


def test_get_nonexistent_task(test_client, temp_workspace_dir):
    """Test getting a task that doesn't exist."""
    headers = setup_test_user(test_client)

    # Create a workspace first (needed to have a valid slug)
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Nonexistent Task Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    response = test_client.get(f"/api/v1/{workspace_slug}/tasks/99999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_status(test_client, temp_workspace_dir):
    """Test updating a task's status."""
    headers = setup_test_user(test_client)

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Update Task Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # Create a task
    create_response = test_client.post(
        f"/api/v1/{workspace_slug}/tasks", params={"title": "Task to Update"}, headers=headers
    )
    task_id = create_response.json()["id"]
    assert create_response.json()["status"] == "pending"

    # Update status to in_progress
    response = test_client.put(f"/api/v1/{workspace_slug}/tasks/{task_id}", params={"status": "in_progress"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # Update status to completed
    response = test_client.put(f"/api/v1/{workspace_slug}/tasks/{task_id}", params={"status": "completed"}, headers=headers)
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"
    assert task["completed_at"] is not None

    # Cleanup handled by fixture


def test_update_task_assignment(test_client, temp_workspace_dir):
    """Test assigning a task to an agent."""
    headers = setup_test_user(test_client)

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Assign Task Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # Create a task
    create_response = test_client.post(
        f"/api/v1/{workspace_slug}/tasks", params={"title": "Task to Assign"}, headers=headers
    )
    task_id = create_response.json()["id"]

    # Assign to an agent
    response = test_client.put(f"/api/v1/{workspace_slug}/tasks/{task_id}", params={"assigned_to": "agent-123"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["assigned_to"] == "agent-123"

    # Cleanup handled by fixture


def test_update_nonexistent_task(test_client, temp_workspace_dir):
    """Test updating a task that doesn't exist."""
    headers = setup_test_user(test_client)

    # Create a workspace first (needed to have a valid slug)
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Update Nonexistent Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    response = test_client.put(f"/api/v1/{workspace_slug}/tasks/99999", params={"status": "completed"}, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_task_requires_authentication(test_client, temp_workspace_dir):
    """Test that task endpoints require authentication."""
    headers = setup_test_user(test_client)

    # Create a workspace to get a valid slug
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Auth Test Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # No auth header - list tasks
    response = test_client.get(f"/api/v1/{workspace_slug}/tasks")
    assert response.status_code == 401

    # No auth header - create task
    response = test_client.post(f"/api/v1/{workspace_slug}/tasks", params={"title": "Test"})
    assert response.status_code == 401

    # No auth header - get task
    response = test_client.get(f"/api/v1/{workspace_slug}/tasks/1")
    assert response.status_code == 401

    # No auth header - update task
    response = test_client.put(f"/api/v1/{workspace_slug}/tasks/1", params={"status": "completed"})
    assert response.status_code == 401

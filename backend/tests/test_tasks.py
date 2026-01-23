"""Tests for task endpoints."""

import tempfile
import shutil
import time
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


def setup_test_user():
    """Register and login a test user for task tests."""
    username = f"test_task_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    # Register
    client.post("/register", json={"username": username, "email": email, "password": password})

    # Login
    login_response = client.post("/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_task(temp_workspace_dir):
    """Test creating a task."""
    headers = setup_test_user()

    # Create a workspace first
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Task Test Workspace", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]

    # Create a task
    response = client.post(
        "/api/v1/tasks/",
        params={"workspace_id": workspace_id, "title": "Test Task", "description": "This is a test task"},
        headers=headers,
    )
    assert response.status_code == 200
    task = response.json()
    assert task["title"] == "Test Task"
    assert task["description"] == "This is a test task"
    assert task["status"] == "pending"
    assert task["workspace_id"] == workspace_id

    # Cleanup handled by fixture


def test_list_tasks(temp_workspace_dir):
    """Test listing tasks for a workspace."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Task List Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = workspace_response.json()["id"]

    # Initially should be empty
    response = client.get("/api/v1/tasks/", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Create some tasks
    for i in range(3):
        client.post("/api/v1/tasks/", params={"workspace_id": workspace_id, "title": f"Task {i+1}"}, headers=headers)

    # List tasks
    response = client.get("/api/v1/tasks/", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 3

    # Cleanup handled by fixture


def test_get_task(temp_workspace_dir):
    """Test getting a specific task."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Get Task Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = workspace_response.json()["id"]

    # Create a task
    create_response = client.post(
        "/api/v1/tasks/",
        params={"workspace_id": workspace_id, "title": "Specific Task", "description": "Task to retrieve"},
        headers=headers,
    )
    task_id = create_response.json()["id"]

    # Get the task
    response = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    task = response.json()
    assert task["id"] == task_id
    assert task["title"] == "Specific Task"
    assert task["description"] == "Task to retrieve"

    # Cleanup handled by fixture


def test_get_nonexistent_task():
    """Test getting a task that doesn't exist."""
    headers = setup_test_user()

    response = client.get("/api/v1/tasks/99999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_status(temp_workspace_dir):
    """Test updating a task's status."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Update Task Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = workspace_response.json()["id"]

    # Create a task
    create_response = client.post(
        "/api/v1/tasks/", params={"workspace_id": workspace_id, "title": "Task to Update"}, headers=headers
    )
    task_id = create_response.json()["id"]
    assert create_response.json()["status"] == "pending"

    # Update status to in_progress
    response = client.put(f"/api/v1/tasks/{task_id}", params={"status": "in_progress"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # Update status to completed
    response = client.put(f"/api/v1/tasks/{task_id}", params={"status": "completed"}, headers=headers)
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"
    assert task["completed_at"] is not None

    # Cleanup handled by fixture


def test_update_task_assignment(temp_workspace_dir):
    """Test assigning a task to an agent."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Assign Task Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = workspace_response.json()["id"]

    # Create a task
    create_response = client.post(
        "/api/v1/tasks/", params={"workspace_id": workspace_id, "title": "Task to Assign"}, headers=headers
    )
    task_id = create_response.json()["id"]

    # Assign to an agent
    response = client.put(f"/api/v1/tasks/{task_id}", params={"assigned_to": "agent-123"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["assigned_to"] == "agent-123"

    # Cleanup handled by fixture

def test_update_nonexistent_task():
    """Test updating a task that doesn't exist."""
    headers = setup_test_user()

    response = client.put("/api/v1/tasks/99999", params={"status": "completed"}, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_task_requires_authentication():
    """Test that task endpoints require authentication."""
    # No auth header
    response = client.get("/api/v1/tasks/", params={"workspace_id": 1})
    assert response.status_code == 401

    response = client.post("/api/v1/tasks/", params={"workspace_id": 1, "title": "Test"})
    assert response.status_code == 401

    response = client.get("/api/v1/tasks/1")
    assert response.status_code == 401

    response = client.put("/api/v1/tasks/1", params={"status": "completed"})
    assert response.status_code == 401

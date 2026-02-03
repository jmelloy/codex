"""Tests for the implemented TODO endpoints."""

from fastapi.testclient import TestClient

from codex.main import app

client = TestClient(app)


def setup_test_user():
    """Register and login a test user."""
    username = "test_todo_user"
    email = "todo@example.com"
    password = "testpass123"

    # Try to register (may already exist from previous test runs)
    client.post("/api/register", json={"username": username, "email": email, "password": password})

    # Login
    login_response = client.post("/api/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_search_endpoints(temp_workspace_dir):
    """Test search endpoints."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Search Test", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]

    # Test search endpoint
    response = client.get("/api/v1/search/", params={"q": "test query", "workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "test query"
    assert "results" in data

    # Test tag search
    response = client.get(
        "/api/v1/search/tags", params={"tags": "tag1,tag2", "workspace_id": workspace_id}, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    assert len(data["tags"]) == 2

    # Cleanup handled by fixture


def test_notebook_endpoints(temp_workspace_dir):
    """Test notebook endpoints."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Notebook Test", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]

    # List notebooks (should be empty)
    response = client.get("/api/v1/notebooks/", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Create a notebook
    response = client.post(
        "/api/v1/notebooks/",
        json={"workspace_id": workspace_id, "name": "Test Notebook", "description": "A test notebook"},
        headers=headers,
    )
    if response.status_code != 200:
        print(f"ERROR: {response.status_code} - {response.text}")
    assert response.status_code == 200
    notebook = response.json()
    assert notebook["name"] == "Test Notebook"
    assert notebook["path"] == "test-notebook"
    notebook_id = notebook["id"]

    # List notebooks (should have one)
    response = client.get("/api/v1/notebooks/", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    notebooks = response.json()
    assert len(notebooks) == 1

    # Get notebook by ID
    response = client.get(f"/api/v1/notebooks/{notebook_id}", params={"workspace_id": workspace_id}, headers=headers)
    assert response.status_code == 200
    notebook_data = response.json()
    assert notebook_data["id"] == notebook_id
    assert notebook_data["name"] == "Test Notebook"

    # Cleanup handled by fixture


def test_file_endpoints(temp_workspace_dir):
    """Test file endpoints."""
    headers = setup_test_user()

    # Create a workspace and notebook
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "File Test", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = workspace_response.json()["id"]

    notebook_response = client.post(
        "/api/v1/notebooks/", json={"workspace_id": workspace_id, "name": "File Notebook"}, headers=headers
    )
    notebook_id = notebook_response.json()["id"]

    # List files (should be empty)
    response = client.get(
        "/api/v1/files/", params={"notebook_id": notebook_id, "workspace_id": workspace_id}, headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()["files"]) == 0

    # Create a file
    response = client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook_id,
            "workspace_id": workspace_id,
            "path": "test.md",
            "content": "# Test File\n\nThis is a test.",
        },
        headers=headers,
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["filename"] == "test.md"
    file_id = file_data["id"]

    # List files (should have one)
    response = client.get(
        "/api/v1/files/", params={"notebook_id": notebook_id, "workspace_id": workspace_id}, headers=headers
    )
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 1

    # Get file by ID
    response = client.get(
        f"/api/v1/files/{file_id}", params={"workspace_id": workspace_id, "notebook_id": notebook_id}, headers=headers
    )
    assert response.status_code == 200
    file_content = response.json()
    assert file_content["id"] == file_id

    # Update file
    response = client.put(
        f"/api/v1/files/{file_id}",
        params={"workspace_id": workspace_id, "notebook_id": notebook_id},
        json={"content": "# Updated Test File\n\nThis is updated."},
        headers=headers,
    )
    assert response.status_code == 200

    # Verify update
    response = client.get(
        f"/api/v1/files/{file_id}/text", params={"workspace_id": workspace_id, "notebook_id": notebook_id}, headers=headers
    )
    assert response.status_code == 200
    updated_content = response.json()
    assert updated_content["content"] == "# Updated Test File\n\nThis is updated."

    # Cleanup handled by fixture


    # Cleanup handled by fixture


# test_markdown_file_operations was removed because all markdown endpoints
# have been deleted from markdown.py as they were unused and redundant
# with the files.py router which handles all file operations.

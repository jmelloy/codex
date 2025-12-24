"""Tests for the implemented TODO endpoints."""

import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from backend.api.main import app


client = TestClient(app)


def setup_test_user():
    """Register and login a test user."""
    username = "test_todo_user"
    email = "todo@example.com"
    password = "testpass123"
    
    # Try to register (may already exist from previous test runs)
    client.post("/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    
    # Login
    login_response = client.post("/token", data={
        "username": username,
        "password": password
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_search_endpoints():
    """Test search endpoints."""
    headers = setup_test_user()
    
    # Create a workspace
    temp_dir = tempfile.mkdtemp()
    workspace_response = client.post(
        "/api/v1/workspaces/",
        params={"name": "Search Test", "path": temp_dir},
        headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]
    
    # Test search endpoint
    response = client.get(
        "/api/v1/search/",
        params={"q": "test query", "workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "test query"
    assert "results" in data
    
    # Test tag search
    response = client.get(
        "/api/v1/search/tags",
        params={"tags": "tag1,tag2", "workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    assert len(data["tags"]) == 2
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_notebook_endpoints():
    """Test notebook endpoints."""
    headers = setup_test_user()
    
    # Create a workspace
    temp_dir = tempfile.mkdtemp()
    workspace_response = client.post(
        "/api/v1/workspaces/",
        params={"name": "Notebook Test", "path": temp_dir},
        headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]
    
    # List notebooks (should be empty)
    response = client.get(
        "/api/v1/notebooks/",
        params={"workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # Create a notebook
    response = client.post(
        "/api/v1/notebooks/",
        params={
            "workspace_id": workspace_id,
            "name": "Test Notebook",
            "path": "test-notebook",
            "description": "A test notebook"
        },
        headers=headers
    )
    assert response.status_code == 200
    notebook = response.json()
    assert notebook["name"] == "Test Notebook"
    assert notebook["path"] == "test-notebook"
    notebook_id = notebook["id"]
    
    # List notebooks (should have one)
    response = client.get(
        "/api/v1/notebooks/",
        params={"workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    notebooks = response.json()
    assert len(notebooks) == 1
    
    # Get notebook by ID
    response = client.get(
        f"/api/v1/notebooks/{notebook_id}",
        params={"workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    notebook_data = response.json()
    assert notebook_data["id"] == notebook_id
    assert notebook_data["name"] == "Test Notebook"
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_file_endpoints():
    """Test file endpoints."""
    headers = setup_test_user()
    
    # Create a workspace and notebook
    temp_dir = tempfile.mkdtemp()
    workspace_response = client.post(
        "/api/v1/workspaces/",
        params={"name": "File Test", "path": temp_dir},
        headers=headers
    )
    workspace_id = workspace_response.json()["id"]
    
    notebook_response = client.post(
        "/api/v1/notebooks/",
        params={
            "workspace_id": workspace_id,
            "name": "File Notebook",
            "path": "file-notebook"
        },
        headers=headers
    )
    notebook_id = notebook_response.json()["id"]
    
    # List files (should be empty)
    response = client.get(
        "/api/v1/files/",
        params={"notebook_id": notebook_id, "workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # Create a file
    response = client.post(
        "/api/v1/files/",
        params={
            "notebook_id": notebook_id,
            "workspace_id": workspace_id,
            "path": "test.md",
            "content": "# Test File\n\nThis is a test."
        },
        headers=headers
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["filename"] == "test.md"
    file_id = file_data["id"]
    
    # List files (should have one)
    response = client.get(
        "/api/v1/files/",
        params={"notebook_id": notebook_id, "workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    files = response.json()
    assert len(files) == 1
    
    # Get file by ID
    response = client.get(
        f"/api/v1/files/{file_id}",
        params={"workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    file_content = response.json()
    assert file_content["id"] == file_id
    assert file_content["content"] == "# Test File\n\nThis is a test."
    
    # Update file
    response = client.put(
        f"/api/v1/files/{file_id}",
        params={
            "workspace_id": workspace_id,
            "content": "# Updated Test File\n\nThis is updated."
        },
        headers=headers
    )
    assert response.status_code == 200
    
    # Verify update
    response = client.get(
        f"/api/v1/files/{file_id}",
        params={"workspace_id": workspace_id},
        headers=headers
    )
    assert response.status_code == 200
    updated_content = response.json()
    assert updated_content["content"] == "# Updated Test File\n\nThis is updated."
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_markdown_file_operations():
    """Test markdown file operations."""
    headers = setup_test_user()
    
    # Create a workspace
    temp_dir = tempfile.mkdtemp()
    workspace_response = client.post(
        "/api/v1/workspaces/",
        params={"name": "Markdown Test", "path": temp_dir},
        headers=headers
    )
    workspace_id = workspace_response.json()["id"]
    
    # Create a markdown file
    response = client.post(
        f"/api/v1/markdown/{workspace_id}/file",
        json={
            "path": "test.md",
            "content": "# Test Content",
            "frontmatter": {"title": "Test", "author": "TestUser"}
        },
        headers=headers
    )
    assert response.status_code == 201
    
    # List markdown files
    response = client.get(
        f"/api/v1/markdown/{workspace_id}/files",
        headers=headers
    )
    assert response.status_code == 200
    files = response.json()
    assert len(files) == 1
    assert "test.md" in files[0]
    
    # Get markdown file
    response = client.get(
        f"/api/v1/markdown/{workspace_id}/file",
        params={"file_path": "test.md"},
        headers=headers
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["path"] == "test.md"
    assert file_data["frontmatter"]["title"] == "Test"
    
    # Update markdown file
    response = client.put(
        f"/api/v1/markdown/{workspace_id}/file",
        json={
            "path": "test.md",
            "content": "# Updated Content",
            "frontmatter": {"title": "Updated", "author": "TestUser"}
        },
        headers=headers
    )
    assert response.status_code == 200
    
    # Delete markdown file
    response = client.delete(
        f"/api/v1/markdown/{workspace_id}/file",
        params={"file_path": "test.md"},
        headers=headers
    )
    assert response.status_code == 200
    
    # Verify deletion
    response = client.get(
        f"/api/v1/markdown/{workspace_id}/files",
        headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

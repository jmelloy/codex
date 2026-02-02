"""Tests for the implemented TODO endpoints."""

import os
from pathlib import Path

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


def get_workspace_slug_from_response(workspace_response: dict) -> str:
    """Extract workspace slug from API response path."""
    return Path(workspace_response["path"]).name


def test_search_endpoints(temp_workspace_dir):
    """Test search endpoints."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Search Test", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # Test search endpoint
    response = client.get(f"/api/v1/{workspace_slug}/search", params={"q": "test query"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "test query"
    assert "results" in data

    # Test tag search
    response = client.get(
        f"/api/v1/{workspace_slug}/search/tags", params={"tags": "tag1,tag2"}, headers=headers
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
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    # List notebooks (should be empty)
    response = client.get(f"/api/v1/{workspace_slug}/notebooks", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Create a notebook
    response = client.post(
        f"/api/v1/{workspace_slug}/notebooks",
        json={"name": "Test Notebook", "description": "A test notebook"},
        headers=headers,
    )
    if response.status_code != 200:
        print(f"ERROR: {response.status_code} - {response.text}")
    assert response.status_code == 200
    notebook = response.json()
    assert notebook["name"] == "Test Notebook"
    assert notebook["path"] == "test-notebook"
    notebook_slug = notebook["path"]

    # List notebooks (should have one)
    response = client.get(f"/api/v1/{workspace_slug}/notebooks", headers=headers)
    assert response.status_code == 200
    notebooks = response.json()
    assert len(notebooks) == 1

    # Get notebook by slug
    response = client.get(f"/api/v1/{workspace_slug}/{notebook_slug}", headers=headers)
    assert response.status_code == 200
    notebook_data = response.json()
    assert notebook_data["name"] == "Test Notebook"

    # Cleanup handled by fixture


def test_file_endpoints(temp_workspace_dir):
    """Test file endpoints."""
    headers = setup_test_user()

    # Create a workspace and notebook
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "File Test", "path": temp_workspace_dir}, headers=headers
    )
    workspace_slug = get_workspace_slug_from_response(workspace_response.json())

    notebook_response = client.post(
        f"/api/v1/{workspace_slug}/notebooks", json={"name": "File Notebook"}, headers=headers
    )
    notebook_slug = notebook_response.json()["path"]

    # List files (should be empty)
    response = client.get(f"/api/v1/{workspace_slug}/{notebook_slug}/files", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["files"]) == 0

    # Create a file
    response = client.post(
        f"/api/v1/{workspace_slug}/{notebook_slug}/files",
        json={
            "path": "test.md",
            "content": "# Test File\n\nThis is a test.",
        },
        headers=headers,
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["filename"] == "test.md"
    file_path = file_data["path"]

    # List files (should have one)
    response = client.get(f"/api/v1/{workspace_slug}/{notebook_slug}/files", headers=headers)
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 1

    # Get file by path
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe="")
    response = client.get(f"/api/v1/{workspace_slug}/{notebook_slug}/files/{encoded_path}", headers=headers)
    assert response.status_code == 200
    file_content = response.json()
    assert file_content["path"] == file_path

    # Update file
    response = client.put(
        f"/api/v1/{workspace_slug}/{notebook_slug}/files/{encoded_path}",
        json={"content": "# Updated Test File\n\nThis is updated."},
        headers=headers,
    )
    assert response.status_code == 200

    # Verify update
    response = client.get(f"/api/v1/{workspace_slug}/{notebook_slug}/files/{encoded_path}/text", headers=headers)
    assert response.status_code == 200
    updated_content = response.json()
    assert updated_content["content"] == "# Updated Test File\n\nThis is updated."

    # Cleanup handled by fixture


def test_markdown_file_operations(temp_workspace_dir):
    """Test markdown file operations."""
    headers = setup_test_user()

    # Create a workspace
    workspace_response = client.post(
        "/api/v1/workspaces/", json={"name": "Markdown Test", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = workspace_response.json()["id"]

    # Create a markdown file
    response = client.post(
        f"/api/v1/markdown/{workspace_id}/file",
        json={"path": "test.md", "content": "# Test Content", "frontmatter": {"title": "Test", "author": "TestUser"}},
        headers=headers,
    )
    assert response.status_code == 201

    # List markdown files
    response = client.get(f"/api/v1/markdown/{workspace_id}/files", headers=headers)
    assert response.status_code == 200
    files = response.json()
    assert len(files) == 1
    assert "test.md" in files[0]

    # Get markdown file
    response = client.get(f"/api/v1/markdown/{workspace_id}/file", params={"file_path": "test.md"}, headers=headers)
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
            "frontmatter": {"title": "Updated", "author": "TestUser"},
        },
        headers=headers,
    )
    assert response.status_code == 200

    # Delete markdown file
    response = client.delete(f"/api/v1/markdown/{workspace_id}/file", params={"file_path": "test.md"}, headers=headers)
    assert response.status_code == 200

    # Verify deletion
    response = client.get(f"/api/v1/markdown/{workspace_id}/files", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Cleanup handled by fixture

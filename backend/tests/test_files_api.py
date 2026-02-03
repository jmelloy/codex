"""Integration tests for file API endpoints."""

import os
import time
from pathlib import Path


def setup_test_user(test_client):
    """Register and login a test user."""
    username = f"test_files_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def setup_workspace_and_notebook(test_client, headers, temp_workspace_dir):
    """Create a workspace and notebook for testing."""
    # Create workspace
    ws_response = test_client.post(
        "/api/v1/workspaces/",
        json={"name": "Test Files Workspace", "path": temp_workspace_dir},
        headers=headers,
    )
    assert ws_response.status_code == 200
    workspace = ws_response.json()

    # Create notebook
    nb_response = test_client.post(
        "/api/v1/notebooks/",
        json={"workspace_id": workspace["id"], "name": "Test Notebook"},
        headers=headers,
    )
    assert nb_response.status_code == 200
    notebook = nb_response.json()

    return workspace, notebook


def test_create_file(test_client, temp_workspace_dir):
    """Test creating a new file."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "test_file.md",
            "content": "# Test Content\n\nThis is a test file.",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "test_file.md"
    assert data["filename"] == "test_file.md"
    assert data["content_type"] == "text/markdown"
    assert data["message"] == "File created successfully"


def test_create_file_with_frontmatter(test_client, temp_workspace_dir):
    """Test creating a file with YAML frontmatter."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    content = """---
title: My Document
tags:
  - test
  - documentation
---

# Document Content

This is the body of the document.
"""
    response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "frontmatter_test.md",
            "content": content,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "frontmatter_test.md"


def test_create_file_in_subdirectory(test_client, temp_workspace_dir):
    """Test creating a file in a subdirectory (auto-creates parent dirs)."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "subdir/nested/file.md",
            "content": "# Nested File",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "subdir/nested/file.md"
    assert data["filename"] == "file.md"


def test_create_duplicate_file_fails(test_client, temp_workspace_dir):
    """Test that creating a duplicate file returns an error."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create first file
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "duplicate.md",
            "content": "First file",
        },
        headers=headers,
    )

    # Try to create duplicate
    response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "duplicate.md",
            "content": "Second file",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_files(test_client, temp_workspace_dir):
    """Test listing files in a notebook."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create multiple files
    for i in range(3):
        test_client.post(
            "/api/v1/files/",
            json={
                "notebook_id": notebook["id"],
                "workspace_id": workspace["id"],
                "path": f"file_{i}.md",
                "content": f"Content {i}",
            },
            headers=headers,
        )

    # List files
    response = test_client.get(
        f"/api/v1/files/?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert "pagination" in data
    assert len(data["files"]) >= 3
    assert data["pagination"]["total"] >= 3


def test_list_files_with_pagination(test_client, temp_workspace_dir):
    """Test listing files with pagination."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create multiple files
    for i in range(5):
        test_client.post(
            "/api/v1/files/",
            json={
                "notebook_id": notebook["id"],
                "workspace_id": workspace["id"],
                "path": f"paginated_{i}.md",
                "content": f"Content {i}",
            },
            headers=headers,
        )

    # List with limit
    response = test_client.get(
        f"/api/v1/files/?notebook_id={notebook['id']}&workspace_id={workspace['id']}&skip=0&limit=2",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 2
    assert data["pagination"]["has_more"] is True


def test_get_file_by_id(test_client, temp_workspace_dir):
    """Test getting file metadata by ID."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "get_by_id.md",
            "content": "# Test Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Get file by ID
    response = test_client.get(
        f"/api/v1/files/{file_id}?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == file_id
    assert data["path"] == "get_by_id.md"


def test_get_file_text(test_client, temp_workspace_dir):
    """Test getting file text content."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    content = "# Test Content\n\nThis is the body."
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "text_test.md",
            "content": content,
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Get file text
    response = test_client.get(
        f"/api/v1/files/{file_id}/text?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "Test Content" in data["content"]


def test_get_file_by_path(test_client, temp_workspace_dir):
    """Test getting file by path."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "by_path_test.md",
            "content": "# Content",
        },
        headers=headers,
    )

    # Get by path
    response = test_client.get(
        f"/api/v1/files/by-path?path=by_path_test.md&notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "by_path_test.md"


def test_get_file_text_by_path(test_client, temp_workspace_dir):
    """Test getting file text content by path."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    content = "# By Path Content"
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "text_by_path.md",
            "content": content,
        },
        headers=headers,
    )

    # Get text by path
    response = test_client.get(
        f"/api/v1/files/by-path/text?path=text_by_path.md&notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "By Path Content" in data["content"]


def test_update_file(test_client, temp_workspace_dir):
    """Test updating file content."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "update_test.md",
            "content": "# Original Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Update file
    response = test_client.put(
        f"/api/v1/files/{file_id}?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        json={"content": "# Updated Content"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "File updated successfully"

    # Verify update
    text_response = test_client.get(
        f"/api/v1/files/{file_id}/text?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert "Updated Content" in text_response.json()["content"]


def test_update_file_with_properties(test_client, temp_workspace_dir):
    """Test updating file with properties (frontmatter)."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "props_test.md",
            "content": "# Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Update with properties
    response = test_client.put(
        f"/api/v1/files/{file_id}?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        json={
            "content": "# Updated Content",
            "properties": {"title": "My Title", "tags": ["test"]},
        },
        headers=headers,
    )
    assert response.status_code == 200


def test_move_file(test_client, temp_workspace_dir):
    """Test moving/renaming a file."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "original_name.md",
            "content": "# Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Move file
    response = test_client.patch(
        f"/api/v1/files/{file_id}/move?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        json={"new_path": "renamed_file.md"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "renamed_file.md"
    assert data["filename"] == "renamed_file.md"


def test_move_file_to_subdirectory(test_client, temp_workspace_dir):
    """Test moving a file to a subdirectory."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "root_file.md",
            "content": "# Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Move to subdirectory
    response = test_client.patch(
        f"/api/v1/files/{file_id}/move?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        json={"new_path": "subdir/moved_file.md"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "subdir/moved_file.md"


def test_delete_file(test_client, temp_workspace_dir):
    """Test deleting a file."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "to_delete.md",
            "content": "# Delete Me",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Delete file
    response = test_client.delete(
        f"/api/v1/files/{file_id}?workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "File deleted successfully"

    # Verify deletion
    get_response = test_client.get(
        f"/api/v1/files/{file_id}?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert get_response.status_code == 404


def test_get_file_history(test_client, temp_workspace_dir):
    """Test getting git history for a file."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create file (creates initial commit)
    create_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "history_test.md",
            "content": "# Version 1",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Get history
    response = test_client.get(
        f"/api/v1/files/{file_id}/history?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert len(data["history"]) >= 1
    # Each history entry should have hash, author, date, message
    if data["history"]:
        entry = data["history"][0]
        assert "hash" in entry
        assert "date" in entry
        assert "message" in entry


def test_get_nonexistent_file(test_client, temp_workspace_dir):
    """Test getting a file that doesn't exist."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.get(
        f"/api/v1/files/99999?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 404


def test_file_requires_authentication(test_client, temp_workspace_dir):
    """Test that file endpoints require authentication."""
    # No auth header
    response = test_client.get("/api/v1/files/?notebook_id=1&workspace_id=1")
    assert response.status_code == 401

    response = test_client.post("/api/v1/files/", json={"notebook_id": 1, "workspace_id": 1, "path": "test.md", "content": "test"})
    assert response.status_code == 401


def test_list_templates(test_client, temp_workspace_dir):
    """Test listing available templates."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.get(
        f"/api/v1/files/templates?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    # Templates should be a list
    assert isinstance(data["templates"], list)


def test_resolve_link(test_client, temp_workspace_dir):
    """Test resolving a link to a file."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create target file
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "target.md",
            "content": "# Target File",
        },
        headers=headers,
    )

    # Resolve link
    response = test_client.post(
        f"/api/v1/files/resolve-link?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        json={"link": "target.md"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "target.md"


def test_resolve_nonexistent_link(test_client, temp_workspace_dir):
    """Test resolving a link to a nonexistent file."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.post(
        f"/api/v1/files/resolve-link?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        json={"link": "nonexistent.md"},
        headers=headers,
    )
    assert response.status_code == 404

"""Integration tests for file API endpoints."""


def test_create_file(test_client, auth_headers, workspace_and_notebook):
    """Test creating a new file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
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


def test_create_file_with_frontmatter(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file with YAML frontmatter."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

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
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "frontmatter_test.md",
            "content": content,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "frontmatter_test.md"


def test_create_file_in_subdirectory(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file in a subdirectory (auto-creates parent dirs)."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "subdir/nested/file.md",
            "content": "# Nested File",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "subdir/nested/file.md"
    assert data["filename"] == "file.md"


def test_create_duplicate_file_appends_suffix(test_client, auth_headers, workspace_and_notebook):
    """Test that creating a duplicate file auto-appends a numeric suffix."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create first file
    resp1 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "duplicate.md",
            "content": "First file",
        },
        headers=headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["path"] == "duplicate.md"

    # Create duplicate — should succeed with suffix -1
    resp2 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "duplicate.md",
            "content": "Second file",
        },
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["path"] == "duplicate-1.md"
    assert resp2.json()["filename"] == "duplicate-1.md"

    # Create another duplicate — should succeed with suffix -2
    resp3 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "duplicate.md",
            "content": "Third file",
        },
        headers=headers,
    )
    assert resp3.status_code == 200
    assert resp3.json()["path"] == "duplicate-2.md"


def test_list_files(test_client, auth_headers, workspace_and_notebook):
    """Test listing files in a notebook."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create multiple files
    for i in range(3):
        test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
            json={
                "path": f"file_{i}.md",
                "content": f"Content {i}",
            },
            headers=headers,
        )

    # List files
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert "pagination" in data
    assert len(data["files"]) >= 3
    assert data["pagination"]["total"] >= 3


def test_list_files_with_pagination(test_client, auth_headers, workspace_and_notebook):
    """Test listing files with pagination."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create multiple files
    for i in range(5):
        test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
            json={
                "path": f"paginated_{i}.md",
                "content": f"Content {i}",
            },
            headers=headers,
        )

    # List with limit
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/?skip=0&limit=2",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 2
    assert data["pagination"]["has_more"] is True


def test_get_file_by_id(test_client, auth_headers, workspace_and_notebook):
    """Test getting file metadata by ID."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "get_by_id.md",
            "content": "# Test Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Get file by ID
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == file_id
    assert data["path"] == "get_by_id.md"


def test_get_file_text(test_client, auth_headers, workspace_and_notebook):
    """Test getting file text content."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    content = "# Test Content\n\nThis is the body."
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "text_test.md",
            "content": content,
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Get file text
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}/text",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "Test Content" in data["content"]


def test_get_file_by_path(test_client, auth_headers, workspace_and_notebook):
    """Test getting file by path."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "by_path_test.md",
            "content": "# Content",
        },
        headers=headers,
    )

    # Get by path
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/path/by_path_test.md",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "by_path_test.md"


def test_get_file_text_by_path(test_client, auth_headers, workspace_and_notebook):
    """Test getting file text content by path."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    content = "# By Path Content"
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "text_by_path.md",
            "content": content,
        },
        headers=headers,
    )

    # Get text by path
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/path/text_by_path.md/text",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "By Path Content" in data["content"]


def test_update_file(test_client, auth_headers, workspace_and_notebook):
    """Test updating file content."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "update_test.md",
            "content": "# Original Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Update file
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}",
        json={"content": "# Updated Content"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "File updated successfully"

    # Verify update
    text_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}/text",
        headers=headers,
    )
    assert "Updated Content" in text_response.json()["content"]


def test_update_file_with_properties(test_client, auth_headers, workspace_and_notebook):
    """Test updating file with properties (frontmatter)."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "props_test.md",
            "content": "# Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Update with properties
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}",
        json={
            "content": "# Updated Content",
            "properties": {"title": "My Title", "tags": ["test"]},
        },
        headers=headers,
    )
    assert response.status_code == 200


def test_move_file(test_client, auth_headers, workspace_and_notebook):
    """Test moving/renaming a file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "original_name.md",
            "content": "# Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Move file
    response = test_client.patch(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}/move",
        json={"new_path": "renamed_file.md"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "renamed_file.md"
    assert data["filename"] == "renamed_file.md"


def test_move_file_to_subdirectory(test_client, auth_headers, workspace_and_notebook):
    """Test moving a file to a subdirectory."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "root_file.md",
            "content": "# Content",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Move to subdirectory
    response = test_client.patch(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}/move",
        json={"new_path": "subdir/moved_file.md"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "subdir/moved_file.md"


def test_delete_file(test_client, auth_headers, workspace_and_notebook):
    """Test deleting a file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "to_delete.md",
            "content": "# Delete Me",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Delete file
    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "File deleted successfully"

    # Verify deletion
    get_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}",
        headers=headers,
    )
    assert get_response.status_code == 404


def test_get_file_history(test_client, auth_headers, workspace_and_notebook):
    """Test getting git history for a file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create file (creates initial commit)
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "history_test.md",
            "content": "# Version 1",
        },
        headers=headers,
    )
    file_id = create_response.json()["id"]

    # Get history
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}/history",
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


def test_get_nonexistent_file(test_client, auth_headers, workspace_and_notebook):
    """Test getting a file that doesn't exist."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/99999",
        headers=headers,
    )
    assert response.status_code == 404


def test_file_requires_authentication(test_client):
    """Test that file endpoints require authentication."""
    # No auth header
    response = test_client.get("/api/v1/workspaces/1/notebooks/1/files/")
    assert response.status_code == 401

    response = test_client.post("/api/v1/workspaces/1/notebooks/1/files/", json={"path": "test.md", "content": "test"})
    assert response.status_code == 401


def test_list_templates(test_client, auth_headers, workspace_and_notebook):
    """Test listing available templates."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/templates",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    # Templates should be a list
    assert isinstance(data["templates"], list)


def test_resolve_link(test_client, auth_headers, workspace_and_notebook):
    """Test resolving a link to a file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create target file
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "target.md",
            "content": "# Target File",
        },
        headers=headers,
    )

    # Resolve link
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/resolve-link",
        json={"link": "target.md"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "target.md"


def test_create_duplicate_file_in_subdirectory(test_client, auth_headers, workspace_and_notebook):
    """Test that duplicate suffix works for files in subdirectories."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create first file in subdir
    resp1 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "subdir/page.md",
            "content": "First",
        },
        headers=headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["path"] == "subdir/page.md"

    # Create duplicate in same subdir
    resp2 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "subdir/page.md",
            "content": "Second",
        },
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["path"] == "subdir/page-1.md"


def test_create_duplicate_file_no_extension(test_client, auth_headers, workspace_and_notebook):
    """Test that duplicate suffix works for files without an extension."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    resp1 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "README",
            "content": "First",
        },
        headers=headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["path"] == "README"

    resp2 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "README",
            "content": "Second",
        },
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["path"] == "README-1"


def test_resolve_nonexistent_link(test_client, auth_headers, workspace_and_notebook):
    """Test resolving a link to a nonexistent file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/resolve-link",
        json={"link": "nonexistent.md"},
        headers=headers,
    )
    assert response.status_code == 404

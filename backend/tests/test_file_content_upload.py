"""Tests for file content serving and file upload endpoints."""

import io


def test_get_file_content_by_id(test_client, auth_headers, workspace_and_notebook):
    """Test getting file content (binary serving) by ID."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    content = "# Content Served\n\nThis is the body."
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={"path": "serve_test.md", "content": content},
        headers=headers,
    )
    assert create_response.status_code == 200
    file_id = create_response.json()["id"]

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}/content",
        headers=headers,
    )
    assert response.status_code == 200
    assert "Content Served" in response.text


def test_get_file_content_by_path(test_client, auth_headers, workspace_and_notebook):
    """Test getting file content by path."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    content = "# By Path Content"
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={"path": "content_by_path.md", "content": content},
        headers=headers,
    )

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/path/content_by_path.md/content",
        headers=headers,
    )
    assert response.status_code == 200
    assert "By Path Content" in response.text


def test_get_content_nonexistent_file(test_client, auth_headers, workspace_and_notebook):
    """Test getting content of a nonexistent file returns 404."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/99999/content",
        headers=headers,
    )
    assert response.status_code == 404


def test_upload_file(test_client, auth_headers, workspace_and_notebook):
    """Test uploading a binary file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    file_content = b"Hello, this is a text file uploaded via multipart."
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/upload",
        files={"file": ("uploaded.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "uploaded.txt"
    assert data["message"] == "File uploaded successfully"
    assert data["size"] > 0


def test_upload_file_with_custom_path(test_client, auth_headers, workspace_and_notebook):
    """Test uploading a file with a custom path."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    file_content = b"Custom path upload."
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/upload",
        files={"file": ("original.txt", io.BytesIO(file_content), "text/plain")},
        data={"path": "uploads/custom_name.txt"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "uploads/custom_name.txt"
    assert data["filename"] == "custom_name.txt"


def test_upload_duplicate_file_generates_unique_name(test_client, auth_headers, workspace_and_notebook):
    """Test that uploading a duplicate file auto-generates a unique name."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    url = f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/upload"

    # Upload first file
    resp1 = test_client.post(
        url,
        files={"file": ("dup_upload.txt", io.BytesIO(b"First"), "text/plain")},
        headers=headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["path"] == "dup_upload.txt"

    # Upload duplicate — should get a unique name
    resp2 = test_client.post(
        url,
        files={"file": ("dup_upload.txt", io.BytesIO(b"Second"), "text/plain")},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["path"] != "dup_upload.txt"


def test_upload_requires_auth(test_client):
    """Test that upload requires authentication."""
    response = test_client.post(
        "/api/v1/workspaces/any-ws/notebooks/any-nb/files/upload",
        files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")},
    )
    assert response.status_code == 401

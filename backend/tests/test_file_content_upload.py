"""Tests for block content serving and file upload via block API."""

import io


def test_get_block_content(test_client, auth_headers, workspace_and_notebook):
    """Test getting block content by block_id."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a page and block
    page_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/pages",
        json={"title": "Content Test"},
        headers=headers,
    )
    assert page_resp.status_code == 200
    page = page_resp.json()

    block_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/",
        json={"parent_block_id": page["block_id"], "block_type": "text", "content": "# Content Served\n\nBody."},
        headers=headers,
    )
    assert block_resp.status_code == 200
    block_id = block_resp.json()["block_id"]

    # Get text content
    text_resp = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/{block_id}/text",
        headers=headers,
    )
    assert text_resp.status_code == 200
    assert "Content Served" in text_resp.json()["content"]


def test_get_content_by_path(test_client, auth_headers, workspace_and_notebook):
    """Test getting content by path."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a page with content
    page_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/pages",
        json={"title": "Path Content Test"},
        headers=headers,
    )
    assert page_resp.status_code == 200
    page = page_resp.json()

    block_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/",
        json={"parent_block_id": page["block_id"], "content": "Path test content"},
        headers=headers,
    )
    assert block_resp.status_code == 200
    block_path = block_resp.json()["path"]

    # Get content by path
    from urllib.parse import quote

    encoded = quote(block_path, safe="")
    path_resp = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/path/{encoded}/content",
        headers=headers,
    )
    assert path_resp.status_code == 200


def test_upload_block(test_client, auth_headers, workspace_and_notebook):
    """Test uploading a file as a block."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    file_content = b"Hello, this is an uploaded file."
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/upload",
        files={"file": ("uploaded.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "block_id" in data
    assert data["path"].endswith("uploaded.txt")


def test_upload_block_with_parent(test_client, auth_headers, workspace_and_notebook):
    """Test uploading a file into a specific page."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a page first
    page_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/pages",
        json={"title": "Upload Target"},
        headers=headers,
    )
    assert page_resp.status_code == 200
    page = page_resp.json()

    file_content = b"Uploaded into page."
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/upload",
        files={"file": ("page_file.txt", io.BytesIO(file_content), "text/plain")},
        data={"parent_block_id": page["block_id"]},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["parent_block_id"] == page["block_id"]


def test_upload_requires_auth(test_client):
    """Test that upload requires authentication."""
    response = test_client.post(
        "/api/v1/workspaces/any-ws/notebooks/any-nb/blocks/upload",
        files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")},
    )
    assert response.status_code == 401


def test_upload_folder_stages_files_and_creates_task(test_client, auth_headers, workspace_and_notebook):
    """Uploading a folder stages files under their relative paths and kicks off an import task."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/upload-folder",
        files=[
            ("files", ("a.md", io.BytesIO(b"# A"), "text/markdown")),
            ("files", ("b.md", io.BytesIO(b"# B"), "text/markdown")),
            ("paths", (None, "myfolder/a.md")),
            ("paths", (None, "myfolder/nested/b.md")),
        ],
        headers=headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "pending"
    assert isinstance(payload["task_id"], int)


def test_upload_folder_rejects_traversal(test_client, auth_headers, workspace_and_notebook):
    """Paths that escape the staging dir must be rejected."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/upload-folder",
        files=[
            ("files", ("x.md", io.BytesIO(b"x"), "text/markdown")),
            ("paths", (None, "../escape.md")),
        ],
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_folder_rejects_length_mismatch(test_client, auth_headers, workspace_and_notebook):
    """files and paths must have matching lengths."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/upload-folder",
        files=[
            ("files", ("a.md", io.BytesIO(b"a"), "text/markdown")),
            ("files", ("b.md", io.BytesIO(b"b"), "text/markdown")),
            ("paths", (None, "only/one.md")),
        ],
        headers=headers,
    )
    assert response.status_code == 400

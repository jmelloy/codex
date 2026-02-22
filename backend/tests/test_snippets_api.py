"""Tests for the snippets API endpoint."""


def test_post_snippet(test_client, auth_headers, workspace_and_notebook):
    """Test posting a snippet creates a file."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": workspace["slug"],
            "notebook": notebook["slug"],
            "content": "This is a quick note captured via snippet.",
            "title": "Quick Note",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "Snippet created" in data["message"]
    assert data["title"] == "Quick Note"
    assert data["size"] > 0
    assert data["content_type"] == "text/markdown"


def test_post_snippet_with_tags(test_client, auth_headers, workspace_and_notebook):
    """Test posting a snippet with tags."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": workspace["slug"],
            "notebook": notebook["slug"],
            "content": "Tagged snippet content.",
            "title": "Tagged Snippet",
            "tags": ["important", "review"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "quick-note" in data["filename"].lower() or "tagged" in data["filename"].lower()


def test_post_snippet_with_folder(test_client, auth_headers, workspace_and_notebook):
    """Test posting a snippet to a specific folder."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": workspace["slug"],
            "notebook": notebook["slug"],
            "content": "Snippet in subfolder.",
            "title": "Subfolder Snippet",
            "folder": "snippets/daily",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["path"].startswith("snippets/daily/")


def test_post_snippet_with_custom_filename(test_client, auth_headers, workspace_and_notebook):
    """Test posting a snippet with a custom filename."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": workspace["slug"],
            "notebook": notebook["slug"],
            "content": "Custom filename snippet.",
            "filename": "my-custom-snippet.md",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "my-custom-snippet.md"


def test_post_snippet_auto_generates_filename(test_client, auth_headers, workspace_and_notebook):
    """Test that snippets auto-generate a filename when none is provided."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": workspace["slug"],
            "notebook": notebook["slug"],
            "content": "Auto-named snippet.",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"].endswith(".md")
    assert len(data["filename"]) > 5  # Not empty


def test_post_snippet_requires_auth(test_client):
    """Test that posting snippets requires authentication."""
    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": "any-ws",
            "notebook": "any-nb",
            "content": "Unauthorized snippet.",
        },
    )
    assert response.status_code == 401


def test_post_snippet_nonexistent_workspace(test_client, auth_headers):
    """Test posting a snippet to a nonexistent workspace."""
    headers = auth_headers[0]

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": "nonexistent-workspace",
            "notebook": "some-notebook",
            "content": "This should fail.",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_post_snippet_nonexistent_notebook(test_client, auth_headers, workspace_and_notebook):
    """Test posting a snippet to a nonexistent notebook."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": workspace["slug"],
            "notebook": "nonexistent-notebook",
            "content": "This should fail.",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_post_snippet_with_properties(test_client, auth_headers, workspace_and_notebook):
    """Test posting a snippet with extra properties."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        "/api/v1/snippets/",
        json={
            "workspace": workspace["slug"],
            "notebook": notebook["slug"],
            "content": "Snippet with properties.",
            "title": "Props Snippet",
            "file_type": "log",
            "properties": {"source": "test", "priority": "high"},
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Props Snippet"

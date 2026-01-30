"""Tests for markdown API endpoints."""


def test_render_markdown_simple(test_client):
    """Test basic markdown rendering."""
    # First register and login
    test_client.post(
        "/api/register", json={"username": "testuser_md", "email": "testmd@example.com", "password": "testpass123"}
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_md", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test markdown rendering
    response = test_client.post(
        "/api/v1/markdown/render", json={"content": "# Hello World\n\nThis is **bold** text."}, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "html" in data
    assert data["html"] is not None
    # Should not have custom blocks for plain markdown
    assert data.get("custom_blocks") is None or data.get("custom_blocks") == []


def test_render_markdown_with_frontmatter(test_client):
    """Test markdown rendering with frontmatter."""
    # Login
    test_client.post(
        "/api/register", json={"username": "testuser_fm", "email": "testfm@example.com", "password": "testpass123"}
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_fm", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test markdown with frontmatter
    content = """---
title: Test Document
author: Test User
tags:
  - test
  - markdown
---

# Test Content

This is a test document."""

    response = test_client.post("/api/v1/markdown/render", json={"content": content}, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "html" in data
    assert "frontmatter" in data
    assert data["frontmatter"] is not None
    assert data["frontmatter"]["title"] == "Test Document"
    assert data["frontmatter"]["author"] == "Test User"
    assert "test" in data["frontmatter"]["tags"]
    assert "markdown" in data["frontmatter"]["tags"]


def test_list_markdown_files_empty(test_client, temp_workspace_dir):
    """Test listing markdown files returns empty list."""
    # Login
    test_client.post(
        "/api/register", json={"username": "testuser_list", "email": "testlist@example.com", "password": "testpass123"}
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_list", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a workspace first
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Test Workspace", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]

    # Test listing files
    response = test_client.get(f"/api/v1/markdown/{workspace_id}/files", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

    # Cleanup handled by fixture


def test_markdown_endpoints_require_auth(test_client):
    """Test that markdown endpoints require authentication."""
    # Try to render without auth
    response = test_client.post("/api/v1/markdown/render", json={"content": "# Test"})
    assert response.status_code == 401

    # Try to list files without auth
    response = test_client.get("/api/v1/markdown/1/files")
    assert response.status_code == 401


def test_render_markdown_empty_content(test_client):
    """Test rendering empty markdown content."""
    # Login
    test_client.post(
        "/api/register",
        json={"username": "testuser_empty", "email": "testempty@example.com", "password": "testpass123"},
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_empty", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test empty content
    response = test_client.post("/api/v1/markdown/render", json={"content": ""}, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "html" in data
    assert data["html"] == ""


def test_render_markdown_with_datetime_frontmatter(test_client):
    """Test that datetime values in frontmatter are serialized correctly."""
    # Login
    test_client.post(
        "/api/register", json={"username": "testuser_dt", "email": "testdt@example.com", "password": "testpass123"}
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_dt", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test markdown with datetime in frontmatter (YAML parses this as datetime object)
    content = """---
id: 01K2QB949G
created: 2025-08-15 10:08:46-07:00
modified: 2025-08-15
tags:
- test
---

# Test Content"""

    response = test_client.post("/api/v1/markdown/render", json={"content": content}, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "frontmatter" in data
    assert data["frontmatter"] is not None
    # Datetime should be serialized as ISO string
    assert data["frontmatter"]["created"] == "2025-08-15T10:08:46-07:00"
    # Date should also be serialized as ISO string
    assert data["frontmatter"]["modified"] == "2025-08-15"


def test_render_markdown_with_custom_blocks(test_client):
    """Test that custom blocks are detected and returned."""
    # Login
    test_client.post(
        "/api/register", json={"username": "testuser_cb", "email": "testcb@example.com", "password": "testpass123"}
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_cb", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test markdown with custom blocks
    content = """# Weather Report

Here's the current weather:

```weather
location: San Francisco
units: imperial
```

And a link preview:

```link-preview
url: https://github.com
```

Some regular code:

```python
print("hello")
```
"""

    response = test_client.post("/api/v1/markdown/render", json={"content": content}, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "html" in data
    assert "custom_blocks" in data
    assert data["custom_blocks"] is not None
    assert len(data["custom_blocks"]) == 2  # weather and link-preview, not python

    # Check weather block
    weather_block = next(b for b in data["custom_blocks"] if b["block_type"] == "weather")
    assert weather_block["config"]["location"] == "San Francisco"
    assert weather_block["config"]["units"] == "imperial"

    # Check link-preview block
    link_block = next(b for b in data["custom_blocks"] if b["block_type"] == "link-preview")
    assert link_block["config"]["url"] == "https://github.com"


def test_render_markdown_with_multiple_same_blocks(test_client):
    """Test rendering markdown with multiple blocks of the same type."""
    # Login
    test_client.post(
        "/api/register", json={"username": "testuser_mb", "email": "testmb@example.com", "password": "testpass123"}
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_mb", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    content = """
```weather
location: New York
```

```weather
location: London
units: metric
```

```weather
location: Tokyo
units: metric
```
"""

    response = test_client.post("/api/v1/markdown/render", json={"content": content}, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["custom_blocks"] is not None
    assert len(data["custom_blocks"]) == 3
    assert all(b["block_type"] == "weather" for b in data["custom_blocks"])

    # Verify each location
    locations = [b["config"]["location"] for b in data["custom_blocks"]]
    assert "New York" in locations
    assert "London" in locations
    assert "Tokyo" in locations

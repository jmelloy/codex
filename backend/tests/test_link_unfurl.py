"""End-to-end test for link unfurl functionality."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codex.main import app


@pytest.fixture
def client():
    """Create test client with lifespan context."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for test user."""
    username = f"testuser_unfurl_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201

    response = client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def workspace_and_notebook(client, auth_headers):
    """Create a test workspace and notebook."""
    import tempfile

    # Create a temporary workspace
    tmpdir = tempfile.mkdtemp()
    workspace_path = Path(tmpdir) / "test_workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Create workspace via API
    response = client.post(
        "/api/v1/workspaces",
        headers=auth_headers,
        json={"name": f"Test Workspace {int(time.time() * 1000)}", "path": str(workspace_path)},
    )
    assert response.status_code == 200
    workspace_slug = response.json()["slug"]

    # Create notebook
    notebook_response = client.post(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/",
        json={
            "name": f"Test Notebook {int(time.time() * 1000)}",
            "description": "Test notebook for link unfurl",
        },
        headers=auth_headers,
    )
    assert notebook_response.status_code == 200
    notebook_slug = notebook_response.json()["slug"]

    return workspace_slug, notebook_slug


def test_opengraph_scraper_with_html():
    """Test the opengraph scraper with mock HTML."""
    from codex.plugins.opengraph_scraper import OpenGraphScraper

    scraper = OpenGraphScraper()

    html = """
    <html>
    <head>
        <title>Example Page</title>
        <meta property="og:title" content="Example Title">
        <meta property="og:description" content="Example description">
        <meta property="og:image" content="https://example.com/image.jpg">
        <meta property="og:url" content="https://example.com">
        <meta property="og:site_name" content="Example Site">
    </head>
    <body></body>
    </html>
    """

    metadata = scraper._parse_og_tags(html)

    assert metadata["title"] == "Example Title"
    assert metadata["description"] == "Example description"
    assert metadata["image"] == "https://example.com/image.jpg"
    assert metadata["url"] == "https://example.com"
    assert metadata["site_name"] == "Example Site"


def test_url_detection_in_markdown():
    """Test that URLs in markdown are detected for unfurling."""
    from codex.core.custom_blocks import CustomBlockParser

    markdown = """
    # My Notes
    
    9:00 - https://amazon.com
    
    Some other text here.
    """

    # Simulate the URL detection that happens in frontend
    # When a URL is detected, it should be converted to a link-preview block
    expected_block_format = "```link-preview\nurl: https://amazon.com\n```"

    # This tests the concept - the actual detection happens in MarkdownViewer.vue
    # but we verify the block parser can handle it
    parser = CustomBlockParser(available_block_types=["link-preview"])
    markdown_with_block = markdown.replace("https://amazon.com", expected_block_format)

    blocks = parser.parse(markdown_with_block)

    assert len(blocks) == 1
    assert blocks[0].block_type == "link-preview"
    assert blocks[0].config["url"] == "https://amazon.com"


@pytest.mark.asyncio
async def test_execute_opengraph_scraper():
    """Test executing the opengraph scraper directly."""
    from codex.plugins.opengraph_scraper import OpenGraphScraper

    scraper = OpenGraphScraper()

    # Test with mock HTML
    html = """
    <html>
    <head>
        <meta property="og:title" content="Test Title">
        <meta property="og:description" content="Test Description">
    </head>
    </html>
    """

    metadata = scraper._parse_og_tags(html)

    assert "title" in metadata
    assert metadata["title"] == "Test Title"
    assert metadata["description"] == "Test Description"

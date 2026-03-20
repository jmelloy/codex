"""Tests for block creation with page hierarchy."""

from pathlib import Path


def test_create_page_and_block(test_client, auth_headers, workspace_and_notebook):
    """Test creating a page and adding a block to it."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a page using block API
    page_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/pages",
        json={
            "title": "Test Page",
            "description": "A test page",
        },
        headers=headers,
    )

    assert page_response.status_code == 200, f"Failed to create page: {page_response.json()}"
    page_data = page_response.json()
    assert page_data["title"] == "Test Page"
    assert "block_id" in page_data

    # Create a text block within the page
    block_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/",
        json={
            "parent_block_id": page_data["block_id"],
            "block_type": "text",
            "content": "Hello, world!",
        },
        headers=headers,
    )

    assert block_response.status_code == 200, f"Failed to create block: {block_response.json()}"
    block_data = block_response.json()
    assert block_data["type"] == "text"


def test_create_nested_pages(test_client, auth_headers, workspace_and_notebook):
    """Test creating nested pages."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a parent page
    parent_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/pages",
        json={"title": "Parent Page"},
        headers=headers,
    )
    assert parent_response.status_code == 200
    parent_data = parent_response.json()

    # Create a child page under the parent
    child_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/pages",
        json={"title": "Child Page", "parent_path": parent_data["path"]},
        headers=headers,
    )
    assert child_response.status_code == 200
    child_data = child_response.json()
    assert child_data["title"] == "Child Page"


def test_block_tree(test_client, auth_headers, workspace_and_notebook):
    """Test that the block tree returns created pages and blocks."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a page
    page_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/pages",
        json={"title": "Tree Test Page"},
        headers=headers,
    )
    assert page_response.status_code == 200

    # Fetch the tree
    tree_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/tree",
        headers=headers,
    )
    assert tree_response.status_code == 200
    tree_data = tree_response.json()
    assert "tree" in tree_data
    # Should have at least the page we created
    assert len(tree_data["tree"]) > 0

"""Tests for pages API endpoints."""

import json
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codex.main import app


@pytest.fixture
def test_user_and_workspace(test_client):
    """Create a test user and workspace."""
    # Create unique username to avoid conflicts
    username = f"pagetest_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    
    # Register a test user
    register_response = test_client.post(
        "/api/register",
        json={
            "username": username,
            "email": email,
            "password": "pagetest123",
        },
    )
    assert register_response.status_code == 201

    # Login to get token
    login_response = test_client.post(
        "/api/token",
        data={
            "username": username,
            "password": "pagetest123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Create a workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_response = test_client.post(
            "/api/v1/workspaces/",
            json={
                "name": "Page Test Workspace",
                "path": temp_dir,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert workspace_response.status_code in [200, 201]
        workspace = workspace_response.json()

        # Create a notebook
        notebook_response = test_client.post(
            "/api/v1/notebooks/",
            json={
                "workspace_id": workspace["id"],
                "name": "Test Notebook",
                "description": "Notebook for page testing",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert notebook_response.status_code in [200, 201]
        notebook = notebook_response.json()

        yield token, workspace, notebook, temp_dir


def test_create_page(test_client, test_user_and_workspace):
    """Test creating a page."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create a page
    response = test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={
            "title": "Test Page",
            "description": "A test page",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    page = response.json()
    assert page["title"] == "Test Page"
    assert page["description"] == "A test page"
    assert page["directory_path"] == "pages/test-page"
    assert page["notebook_id"] == notebook["id"]

    # Verify directory was created (use actual workspace path from response)
    notebook_path = Path(workspace["path"]) / notebook["path"]
    page_dir = notebook_path / page["directory_path"]
    assert page_dir.exists()
    assert page_dir.is_dir()

    # Verify .page.json was created
    metadata_file = page_dir / ".page.json"
    assert metadata_file.exists()
    metadata = json.loads(metadata_file.read_text())
    assert metadata["title"] == "Test Page"
    assert metadata["description"] == "A test page"


def test_list_pages(test_client, test_user_and_workspace):
    """Test listing pages."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create multiple pages
    test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "Page 1", "description": "First page"},
        headers={"Authorization": f"Bearer {token}"},
    )
    test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "Page 2", "description": "Second page"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # List pages
    response = test_client.get(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    pages = response.json()
    assert len(pages) == 2
    assert pages[0]["title"] in ["Page 1", "Page 2"]
    assert pages[1]["title"] in ["Page 1", "Page 2"]


def test_get_page(test_client, test_user_and_workspace):
    """Test getting page details."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create a page
    create_response = test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "Detail Test", "description": "Testing details"},
        headers={"Authorization": f"Bearer {token}"},
    )
    page = create_response.json()

    # Get page details
    response = test_client.get(
        f"/api/v1/pages/{page['id']}",
        params={"workspace_id": workspace["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    page_detail = response.json()
    assert page_detail["title"] == "Detail Test"
    assert page_detail["description"] == "Testing details"
    assert page_detail["blocks"] == []


def test_update_page(test_client, test_user_and_workspace):
    """Test updating page metadata."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create a page
    create_response = test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "Original Title", "description": "Original description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    page = create_response.json()

    # Update the page
    response = test_client.put(
        f"/api/v1/pages/{page['id']}",
        params={"workspace_id": workspace["id"]},
        json={"title": "Updated Title", "description": "Updated description"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    updated_page = response.json()
    assert updated_page["title"] == "Updated Title"
    assert updated_page["description"] == "Updated description"


def test_delete_page(test_client, test_user_and_workspace):
    """Test deleting a page."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create a page
    create_response = test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "To Delete", "description": "Will be deleted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    page = create_response.json()

    notebook_path = Path(workspace["path"]) / notebook["path"]
    page_dir = notebook_path / page["directory_path"]
    assert page_dir.exists()

    # Delete the page
    response = test_client.delete(
        f"/api/v1/pages/{page['id']}",
        params={"workspace_id": workspace["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify directory was deleted
    assert not page_dir.exists()


def test_create_block(test_client, test_user_and_workspace):
    """Test creating a block in a page."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create a page
    create_response = test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "Block Test", "description": "Testing blocks"},
        headers={"Authorization": f"Bearer {token}"},
    )
    page = create_response.json()

    # Create a block
    response = test_client.post(
        f"/api/v1/pages/{page['id']}/blocks",
        params={"workspace_id": workspace["id"]},
        json={"filename": "test.md"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    block = response.json()
    assert block["position"] == 1
    assert block["file"] == "001-test.md"

    # Verify file was created
    notebook_path = Path(workspace["path"]) / notebook["path"]
    block_file = notebook_path / page["directory_path"] / block["file"]
    assert block_file.exists()


def test_reorder_blocks(test_client, test_user_and_workspace):
    """Test reordering blocks in a page."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create a page
    create_response = test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "Reorder Test", "description": "Testing reordering"},
        headers={"Authorization": f"Bearer {token}"},
    )
    page = create_response.json()

    # Create multiple blocks
    test_client.post(
        f"/api/v1/pages/{page['id']}/blocks",
        params={"workspace_id": workspace["id"]},
        json={"filename": "first.md"},
        headers={"Authorization": f"Bearer {token}"},
    )
    test_client.post(
        f"/api/v1/pages/{page['id']}/blocks",
        params={"workspace_id": workspace["id"]},
        json={"filename": "second.md"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Reorder blocks
    response = test_client.put(
        f"/api/v1/pages/{page['id']}/blocks/reorder",
        params={"workspace_id": workspace["id"]},
        json=[
            {"file": "001-first.md", "new_position": 2},
            {"file": "002-second.md", "new_position": 1},
        ],
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    # Verify files were renamed
    notebook_path = Path(workspace["path"]) / notebook["path"]
    page_dir = notebook_path / page["directory_path"]
    assert (page_dir / "001-second.md").exists()
    assert (page_dir / "002-first.md").exists()


def test_delete_block(test_client, test_user_and_workspace):
    """Test deleting a block from a page."""
    token, workspace, notebook, temp_dir = test_user_and_workspace

    # Create a page
    create_response = test_client.post(
        f"/api/v1/notebooks/{notebook['id']}/pages",
        params={"workspace_id": workspace["id"]},
        json={"title": "Block Delete Test", "description": "Testing block deletion"},
        headers={"Authorization": f"Bearer {token}"},
    )
    page = create_response.json()

    # Create a block
    block_response = test_client.post(
        f"/api/v1/pages/{page['id']}/blocks",
        params={"workspace_id": workspace["id"]},
        json={"filename": "to-delete.md"},
        headers={"Authorization": f"Bearer {token}"},
    )
    block = block_response.json()

    notebook_path = Path(workspace["path"]) / notebook["path"]
    block_file = notebook_path / page["directory_path"] / block["file"]
    assert block_file.exists()

    # Delete the block
    response = test_client.delete(
        f"/api/v1/pages/{page['id']}/blocks/{block['file']}",
        params={"workspace_id": workspace["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify file was deleted
    assert not block_file.exists()

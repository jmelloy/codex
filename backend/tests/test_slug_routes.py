"""Test slug-based URL routing for workspaces and notebooks."""

import tempfile
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from codex.main import app


def create_test_user(client: TestClient):
    """Helper to create and login a test user."""
    # Generate unique username and email
    unique_id = str(uuid.uuid4())[:8]
    username = f"sluguser_{unique_id}"
    email = f"slug_{unique_id}@example.com"
    
    # Register
    client.post(
        "/api/register",
        json={"username": username, "email": email, "password": "testpass123"}
    )
    
    # Login
    login_response = client.post(
        "/api/token",
        data={"username": username, "password": "testpass123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_workspace_slug_creation():
    """Test that creating a workspace generates a slug."""
    with TestClient(app) as client:
        headers = create_test_user(client)
        
        # Create workspace
        workspace_response = client.post(
            "/api/v1/workspaces/",
            headers=headers,
            json={"name": "My Test Workspace"}
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()
        
        # Verify slug was generated
        assert "slug" in workspace
        assert workspace["slug"] == "my-test-workspace"
        assert workspace["name"] == "My Test Workspace"


def test_workspace_get_by_slug():
    """Test getting a workspace by slug."""
    with TestClient(app) as client:
        headers = create_test_user(client)
        
        # Create workspace
        workspace_response = client.post(
            "/api/v1/workspaces/",
            headers=headers,
            json={"name": "Slug Test Workspace"}
        )
        workspace = workspace_response.json()
        slug = workspace["slug"]
        workspace_id = workspace["id"]
        
        # Get by slug
        get_by_slug_response = client.get(
            f"/api/v1/workspaces/{slug}",
            headers=headers
        )
        assert get_by_slug_response.status_code == 200
        retrieved_workspace = get_by_slug_response.json()
        assert retrieved_workspace["id"] == workspace_id
        assert retrieved_workspace["slug"] == slug
        
        # Get by ID (should still work)
        get_by_id_response = client.get(
            f"/api/v1/workspaces/{workspace_id}",
            headers=headers
        )
        assert get_by_id_response.status_code == 200
        assert get_by_id_response.json()["id"] == workspace_id


def test_nested_notebook_creation():
    """Test creating a notebook using the new nested URL structure."""
    with TestClient(app) as client:
        headers = create_test_user(client)
        
        # Create workspace
        workspace_response = client.post(
            "/api/v1/workspaces/",
            headers=headers,
            json={"name": "Notebook Test Workspace"}
        )
        workspace = workspace_response.json()
        workspace_slug = workspace["slug"]
        
        # Create notebook using nested route
        notebook_response = client.post(
            f"/api/v1/workspaces/{workspace_slug}/notebooks",
            headers=headers,
            json={"name": "My Research Notes", "description": "Test notebook"}
        )
        assert notebook_response.status_code == 200
        notebook = notebook_response.json()
        
        # Verify notebook has slug
        assert "slug" in notebook
        assert notebook["slug"] == "my-research-notes"
        assert notebook["name"] == "My Research Notes"
        assert notebook["description"] == "Test notebook"


def test_nested_notebook_get_by_slug():
    """Test getting a notebook by slug using nested URL structure."""
    with TestClient(app) as client:
        headers = create_test_user(client)
        
        # Create workspace
        workspace_response = client.post(
            "/api/v1/workspaces/",
            headers=headers,
            json={"name": "Get Notebook Workspace"}
        )
        workspace_slug = workspace_response.json()["slug"]
        
        # Create notebook
        notebook_response = client.post(
            f"/api/v1/workspaces/{workspace_slug}/notebooks",
            headers=headers,
            json={"name": "Test Notebook", "description": "For retrieval test"}
        )
        notebook = notebook_response.json()
        notebook_slug = notebook["slug"]
        notebook_id = notebook["id"]
        
        # Get notebook by slug
        get_by_slug_response = client.get(
            f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}",
            headers=headers
        )
        assert get_by_slug_response.status_code == 200
        retrieved = get_by_slug_response.json()
        assert retrieved["id"] == notebook_id
        assert retrieved["slug"] == notebook_slug
        assert retrieved["name"] == "Test Notebook"
        
        # Get notebook by ID (should still work)
        get_by_id_response = client.get(
            f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_id}",
            headers=headers
        )
        assert get_by_id_response.status_code == 200
        assert get_by_id_response.json()["id"] == notebook_id


def test_list_notebooks_nested():
    """Test listing notebooks using nested URL structure."""
    with TestClient(app) as client:
        headers = create_test_user(client)
        
        # Create workspace
        workspace_response = client.post(
            "/api/v1/workspaces/",
            headers=headers,
            json={"name": "List Notebooks Workspace"}
        )
        workspace_slug = workspace_response.json()["slug"]
        
        # Create multiple notebooks
        for i in range(3):
            client.post(
                f"/api/v1/workspaces/{workspace_slug}/notebooks",
                headers=headers,
                json={"name": f"Notebook {i+1}", "description": f"Description {i+1}"}
            )
        
        # List notebooks
        list_response = client.get(
            f"/api/v1/workspaces/{workspace_slug}/notebooks",
            headers=headers
        )
        assert list_response.status_code == 200
        notebooks = list_response.json()
        assert len(notebooks) == 3
        
        # Verify all notebooks have slugs
        for notebook in notebooks:
            assert "slug" in notebook
            assert "name" in notebook
            assert notebook["slug"].startswith("notebook-")

"""Tests for slug-based API endpoints."""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from codex.main import app


def test_workspace_by_slug(test_client):
    """Test accessing workspace by slug."""
    # Register and login
    username = f"slug_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Test Workspace"}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    workspace_slug = workspace["slug"]

    # Get workspace by slug
    slug_response = test_client.get(f"/api/v1/workspaces/by-slug/{workspace_slug}", headers=headers)
    assert slug_response.status_code == 200
    workspace_by_slug = slug_response.json()
    assert workspace_by_slug["id"] == workspace["id"]
    assert workspace_by_slug["slug"] == workspace_slug
    assert workspace_by_slug["name"] == "Test Workspace"


def test_notebook_by_slug(test_client):
    """Test accessing notebook by slug."""
    # Register and login
    username = f"slug_nb_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Test Workspace"}, headers=headers
    )
    workspace = workspace_response.json()
    workspace_id = workspace["id"]
    workspace_slug = workspace["slug"]

    # Create notebook
    notebook_response = test_client.post(
        "/api/v1/notebooks/",
        json={"workspace_id": workspace_id, "name": "Test Notebook", "description": "A test notebook"},
        headers=headers,
    )
    assert notebook_response.status_code == 200
    notebook = notebook_response.json()
    notebook_slug = notebook["path"]  # slug is same as path

    # Get notebook by slug
    slug_response = test_client.get(
        f"/api/v1/notebooks/by-slug/{workspace_slug}/{notebook_slug}", headers=headers
    )
    assert slug_response.status_code == 200
    notebook_by_slug = slug_response.json()
    assert notebook_by_slug["id"] == notebook["id"]
    assert notebook_by_slug["slug"] == notebook_slug
    assert notebook_by_slug["name"] == "Test Notebook"
    assert notebook_by_slug["workspace_slug"] == workspace_slug


def test_list_files_by_slug(test_client):
    """Test listing files using workspace and notebook slugs."""
    # Register and login
    username = f"slug_files_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Files Test Workspace"}, headers=headers
    )
    workspace = workspace_response.json()
    workspace_id = workspace["id"]
    workspace_slug = workspace["slug"]

    # Create notebook
    notebook_response = test_client.post(
        "/api/v1/notebooks/",
        json={"workspace_id": workspace_id, "name": "Files Test Notebook", "description": "Testing files"},
        headers=headers,
    )
    notebook = notebook_response.json()
    notebook_id = notebook["id"]
    notebook_slug = notebook["path"]

    # List files using slug-based endpoint
    files_response = test_client.get(
        f"/api/v1/{workspace_slug}/{notebook_slug}/files/", headers=headers
    )
    assert files_response.status_code == 200
    files = files_response.json()
    assert isinstance(files, list)
    # New notebook should have no files initially
    assert len(files) == 0


def test_slug_not_found(test_client):
    """Test that invalid slugs return 404."""
    # Register and login
    username = f"slug_404_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to access non-existent workspace by slug
    response = test_client.get("/api/v1/workspaces/by-slug/nonexistent-workspace", headers=headers)
    assert response.status_code == 404

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "404 Test Workspace"}, headers=headers
    )
    workspace_slug = workspace_response.json()["slug"]

    # Try to access non-existent notebook by slug
    response = test_client.get(
        f"/api/v1/notebooks/by-slug/{workspace_slug}/nonexistent-notebook", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_slug_endpoints_async():
    """Test slug-based endpoints with async client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register and login
        username = f"slug_async_test_{int(time.time() * 1000)}"
        email = f"{username}@example.com"
        password = "testpass123"

        await ac.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
        login_response = await ac.post("/api/v1/users/token", data={"username": username, "password": password})
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create workspace
        workspace_response = await ac.post(
            "/api/v1/workspaces/", json={"name": "Async Test Workspace"}, headers=headers
        )
        workspace = workspace_response.json()
        workspace_slug = workspace["slug"]

        # Get workspace by slug
        slug_response = await ac.get(f"/api/v1/workspaces/by-slug/{workspace_slug}", headers=headers)
        assert slug_response.status_code == 200
        assert slug_response.json()["slug"] == workspace_slug

"""Tests for workspace endpoints."""

import time
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from codex.main import app

client = TestClient(app)


def setup_test_user():
    """Register and login a test user for workspace tests."""
    username = f"test_ws_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    # Register
    client.post("/api/register", json={"username": username, "email": email, "password": password})

    # Login
    login_response = client.post("/api/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def test_list_workspaces():
    """Test listing workspaces for authenticated user."""
    headers, username = setup_test_user()

    # User should have their default workspace
    response = client.get("/api/v1/workspaces/", headers=headers)
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) >= 1

    # Default workspace should be named after username
    default_ws = next((w for w in workspaces if w["name"] == username), None)
    assert default_ws is not None


def test_create_workspace_with_path(temp_workspace_dir):
    """Test creating a workspace with explicit path."""
    headers, _ = setup_test_user()

    response = client.post(
        "/api/v1/workspaces/", json={"name": "Test Workspace", "path": temp_workspace_dir}, headers=headers
    )
    assert response.status_code == 200
    workspace = response.json()
    assert workspace["name"] == "Test Workspace"
    # Cleanup handled by fixture


def test_create_workspace_without_path(cleanup_workspaces):
    """Test creating a workspace without explicit path (auto-generated)."""
    headers, _ = setup_test_user()

    response = client.post("/api/v1/workspaces/", json={"name": "Auto Path Workspace"}, headers=headers)
    assert response.status_code == 200
    workspace = response.json()
    assert workspace["name"] == "Auto Path Workspace"
    assert workspace["path"] is not None
    assert len(workspace["path"]) > 0

    # The path should exist
    assert Path(workspace["path"]).exists()

    # Register for cleanup
    cleanup_workspaces(workspace["path"])


def test_get_workspace_by_id(temp_workspace_dir):
    """Test getting a specific workspace by ID."""
    headers, _ = setup_test_user()

    # Create a workspace
    create_response = client.post(
        "/api/v1/workspaces/", json={"name": "Get By ID Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = create_response.json()["id"]

    # Get workspace by ID
    response = client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    assert response.status_code == 200
    workspace = response.json()
    assert workspace["id"] == workspace_id
    assert workspace["name"] == "Get By ID Workspace"

    # Cleanup handled by fixture


def test_get_nonexistent_workspace():
    """Test getting a workspace that doesn't exist."""
    headers, _ = setup_test_user()

    response = client.get("/api/v1/workspaces/99999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Workspace not found"


def test_get_other_users_workspace(temp_workspace_dir):
    """Test that users cannot access other users' workspaces."""
    # Create first user and workspace
    headers1, _ = setup_test_user()
    create_response = client.post(
        "/api/v1/workspaces/", json={"name": "Private Workspace", "path": temp_workspace_dir}, headers=headers1
    )
    workspace_id = create_response.json()["id"]

    # Create second user
    headers2, _ = setup_test_user()

    # Second user should not be able to access first user's workspace
    response = client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers2)
    assert response.status_code == 404

    # Cleanup handled by fixture


def test_update_workspace_theme(temp_workspace_dir):
    """Test updating workspace theme setting."""
    headers, _ = setup_test_user()

    # Create a workspace
    create_response = client.post(
        "/api/v1/workspaces/", json={"name": "Theme Workspace", "path": temp_workspace_dir}, headers=headers
    )
    workspace_id = create_response.json()["id"]

    # Default theme should be "cream"
    assert create_response.json()["theme_setting"] == "cream"

    # Update theme to dark
    response = client.patch(f"/api/v1/workspaces/{workspace_id}/theme", json={"theme": "dark"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["theme_setting"] == "dark"

    # Verify the change persists
    get_response = client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    assert get_response.json()["theme_setting"] == "dark"

    # Cleanup handled by fixture


def test_update_theme_nonexistent_workspace():
    """Test updating theme for a workspace that doesn't exist."""
    headers, _ = setup_test_user()

    response = client.patch("/api/v1/workspaces/99999/theme", json={"theme": "dark"}, headers=headers)
    assert response.status_code == 404


def test_update_theme_other_users_workspace(temp_workspace_dir):
    """Test that users cannot update theme on other users' workspaces."""
    # Create first user and workspace
    headers1, _ = setup_test_user()
    create_response = client.post(
        "/api/v1/workspaces/", json={"name": "Private Theme Workspace", "path": temp_workspace_dir}, headers=headers1
    )
    workspace_id = create_response.json()["id"]

    # Create second user
    headers2, _ = setup_test_user()

    # Second user should not be able to update theme
    response = client.patch(f"/api/v1/workspaces/{workspace_id}/theme", json={"theme": "dark"}, headers=headers2)
    assert response.status_code == 404

    # Cleanup handled by fixture


def test_workspace_requires_authentication():
    """Test that workspace endpoints require authentication."""
    # No auth header
    response = client.get("/api/v1/workspaces/")
    assert response.status_code == 401

    response = client.post("/api/v1/workspaces/", json={"name": "Test"})
    assert response.status_code == 401

    response = client.get("/api/v1/workspaces/1")
    assert response.status_code == 401

    response = client.patch("/api/v1/workspaces/1/theme", json={"theme": "dark"})
    assert response.status_code == 401


def test_workspace_name_collision_handling(cleanup_workspaces):
    """Test that workspace creation handles name collisions gracefully."""
    headers, _ = setup_test_user()

    # Create first workspace with auto-generated path
    response1 = client.post("/api/v1/workspaces/", json={"name": "Collision Test"}, headers=headers)
    assert response1.status_code == 200
    path1 = response1.json()["path"]
    cleanup_workspaces(path1)

    # Create second workspace with same name
    response2 = client.post("/api/v1/workspaces/", json={"name": "Collision Test"}, headers=headers)
    assert response2.status_code == 200
    path2 = response2.json()["path"]
    cleanup_workspaces(path2)

    # Paths should be different
    assert path1 != path2

    # Cleanup handled by fixture


def test_workspace_special_characters_in_name(cleanup_workspaces):
    """Test creating workspace with special characters in name."""
    headers, _ = setup_test_user()

    response = client.post("/api/v1/workspaces/", json={"name": "Test & Workspace! @#$%"}, headers=headers)
    assert response.status_code == 200
    workspace = response.json()
    assert workspace["name"] == "Test & Workspace! @#$%"
    # Path should be slugified (no special characters)
    assert "@" not in workspace["path"]
    assert "#" not in workspace["path"]

    # Register for cleanup
    cleanup_workspaces(workspace["path"])

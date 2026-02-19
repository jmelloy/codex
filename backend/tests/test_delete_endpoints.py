"""Tests for delete endpoints (notebooks, workspaces, users)."""

import time
from pathlib import Path


def test_delete_notebook(test_client, auth_headers, workspace_and_notebook):
    """Test deleting a notebook removes it from DB and disk."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    notebook_dir = Path(workspace["path"]) / notebook["path"]
    assert notebook_dir.exists()

    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Notebook deleted successfully"

    # Notebook directory should be gone
    assert not notebook_dir.exists()

    # Notebook should no longer be accessible
    get_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}",
        headers=headers,
    )
    assert get_response.status_code == 404


def test_delete_notebook_not_found(test_client, auth_headers, create_workspace):
    """Test deleting a non-existent notebook returns 404."""
    headers = auth_headers[0]
    workspace = create_workspace()

    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/nonexistent",
        headers=headers,
    )
    assert response.status_code == 404


def test_delete_workspace(test_client, auth_headers):
    """Test deleting a workspace removes it, its notebooks, and its directory."""
    headers = auth_headers[0]

    # Create a workspace
    ws_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Delete Me Workspace"}, headers=headers
    )
    assert ws_response.status_code == 200
    workspace = ws_response.json()

    # Create a notebook inside it
    nb_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/",
        json={"name": "Delete Me Notebook"},
        headers=headers,
    )
    assert nb_response.status_code == 200

    ws_dir = Path(workspace["path"])
    assert ws_dir.exists()

    # Delete the workspace
    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Workspace deleted successfully"

    # Workspace directory should be gone
    assert not ws_dir.exists()

    # Workspace should no longer be accessible
    get_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}", headers=headers
    )
    assert get_response.status_code == 404


def test_delete_workspace_not_found(test_client, auth_headers):
    """Test deleting a non-existent workspace returns 404."""
    headers = auth_headers[0]

    response = test_client.delete(
        "/api/v1/workspaces/nonexistent-workspace-99999", headers=headers
    )
    assert response.status_code == 404


def test_delete_user_blocked_by_workspaces(test_client):
    """Test that deleting a user with workspaces returns 409."""
    username = f"delete_blocked_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    # Register (creates a default workspace)
    test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password},
    )
    login_response = test_client.post(
        "/api/v1/users/token", data={"username": username, "password": password}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to delete user — should fail because they own a workspace
    response = test_client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 409
    assert "Delete all workspaces" in response.json()["detail"]


def test_delete_user_success(test_client):
    """Test deleting a user after removing all workspaces."""
    username = f"delete_ok_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    # Register and login
    test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password},
    )
    login_response = test_client.post(
        "/api/v1/users/token", data={"username": username, "password": password}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Delete all workspaces first
    ws_response = test_client.get("/api/v1/workspaces/", headers=headers)
    for ws in ws_response.json():
        test_client.delete(f"/api/v1/workspaces/{ws['id']}", headers=headers)

    # Now delete user
    response = test_client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"

    # User should no longer be able to authenticate
    me_response = test_client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 401

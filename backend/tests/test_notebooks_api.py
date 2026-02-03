"""Integration tests for notebook API endpoints."""

import time
from pathlib import Path


def setup_test_user(test_client):
    """Register and login a test user."""
    username = f"test_nb_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def setup_workspace(test_client, headers, temp_workspace_dir):
    """Create a workspace for testing."""
    ws_response = test_client.post(
        "/api/v1/workspaces/",
        json={"name": "Test Notebooks Workspace", "path": temp_workspace_dir},
        headers=headers,
    )
    assert ws_response.status_code == 200
    return ws_response.json()


def test_list_notebooks(test_client, temp_workspace_dir):
    """Test listing notebooks in a workspace."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create a notebook using nested route
    test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "My Notebook"},
        headers=headers,
    )

    # List notebooks using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(nb["name"] == "My Notebook" for nb in data)


def test_list_notebooks_empty_workspace(test_client, temp_workspace_dir):
    """Test listing notebooks in an empty workspace."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # List notebooks (should be empty initially)
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_create_notebook(test_client, temp_workspace_dir):
    """Test creating a new notebook."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={
            "name": "New Notebook",
            "description": "A test notebook",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Notebook"
    assert data["description"] == "A test notebook"
    assert "id" in data
    assert "path" in data
    assert "created_at" in data


def test_create_notebook_without_description(test_client, temp_workspace_dir):
    """Test creating a notebook without description."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "No Description Notebook"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "No Description Notebook"
    assert data["description"] is None


def test_create_notebook_generates_slug_path(test_client, temp_workspace_dir):
    """Test that notebook path is generated from name as a slug."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "My Special Notebook!"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Path should be slugified (lowercase, no special characters)
    assert data["path"] == "my-special-notebook"


def test_create_notebook_handles_name_collision(test_client, temp_workspace_dir):
    """Test that duplicate notebook names get unique paths."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create first notebook
    response1 = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Collision Test"},
        headers=headers,
    )
    assert response1.status_code == 200
    path1 = response1.json()["path"]

    # Create second notebook with same name
    response2 = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Collision Test"},
        headers=headers,
    )
    assert response2.status_code == 200
    path2 = response2.json()["path"]

    # Paths should be different
    assert path1 != path2
    assert path2.startswith("collision-test-")


def test_get_notebook_by_id(test_client, temp_workspace_dir):
    """Test getting a specific notebook by ID."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Get By ID Test"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # Get notebook
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook_id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == notebook_id
    assert data["name"] == "Get By ID Test"


def test_get_nonexistent_notebook(test_client, temp_workspace_dir):
    """Test getting a notebook that doesn't exist."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/99999",
        headers=headers,
    )
    assert response.status_code == 404
    assert "Notebook not found" in response.json()["detail"]


def test_get_notebook_from_other_workspace(test_client, temp_workspace_dir, cleanup_workspaces):
    """Test that notebook from different workspace is not accessible."""
    headers, _ = setup_test_user(test_client)
    workspace1 = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook in workspace1
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace1['id']}/notebooks/",
        json={"name": "Private Notebook"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # Create workspace2
    ws2_response = test_client.post(
        "/api/v1/workspaces/",
        json={"name": "Other Workspace"},
        headers=headers,
    )
    workspace2 = ws2_response.json()
    cleanup_workspaces(workspace2["path"])

    # Try to access notebook using workspace2
    response = test_client.get(
        f"/api/v1/workspaces/{workspace2['id']}/notebooks/{notebook_id}",
        headers=headers,
    )
    assert response.status_code == 404


def test_list_notebooks_nonexistent_workspace(test_client):
    """Test listing notebooks for a workspace that doesn't exist."""
    headers, _ = setup_test_user(test_client)

    response = test_client.get(
        "/api/v1/workspaces/99999/notebooks/",
        headers=headers,
    )
    assert response.status_code == 404
    assert "Workspace not found" in response.json()["detail"]


def test_list_notebooks_other_users_workspace(test_client, temp_workspace_dir):
    """Test that users cannot list notebooks in other users' workspaces."""
    # Create first user and workspace
    headers1, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers1, temp_workspace_dir)

    # Create second user
    headers2, _ = setup_test_user(test_client)

    # Try to list notebooks
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        headers=headers2,
    )
    assert response.status_code == 404


def test_get_notebook_indexing_status(test_client, temp_workspace_dir):
    """Test getting notebook indexing status."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Indexing Test"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # Get indexing status
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook_id}/indexing-status",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "notebook_id" in data
    assert "status" in data


def test_list_notebook_plugins(test_client, temp_workspace_dir):
    """Test listing plugin configurations for a notebook."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Plugin Test"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # List plugins
    response = test_client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_notebook_plugin_config(test_client, temp_workspace_dir):
    """Test getting plugin configuration for a notebook."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Plugin Config Test"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # Get plugin config (should return default)
    response = test_client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins/some-plugin",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == "some-plugin"
    assert data["enabled"] is True  # Default


def test_update_notebook_plugin_config(test_client, temp_workspace_dir):
    """Test updating plugin configuration for a notebook."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Update Plugin Test"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # Update plugin config
    response = test_client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/test-plugin",
        json={"enabled": False, "config": {"setting1": "value1"}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == "test-plugin"
    assert data["enabled"] is False
    assert data["config"]["setting1"] == "value1"

    # Verify persistence
    get_response = test_client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins/test-plugin",
        headers=headers,
    )
    get_data = get_response.json()
    assert get_data["enabled"] is False
    assert get_data["config"]["setting1"] == "value1"


def test_update_plugin_config_partial(test_client, temp_workspace_dir):
    """Test partially updating plugin configuration."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Partial Update Test"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # Create initial config
    test_client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/partial-plugin",
        json={"enabled": True, "config": {"key1": "val1"}},
        headers=headers,
    )

    # Update only enabled status
    response = test_client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/partial-plugin",
        json={"enabled": False},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    # Config should remain unchanged
    assert data["config"]["key1"] == "val1"


def test_delete_notebook_plugin_config(test_client, temp_workspace_dir):
    """Test deleting plugin configuration for a notebook."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    # Create notebook
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Delete Plugin Test"},
        headers=headers,
    )
    notebook_id = create_response.json()["id"]

    # Create plugin config
    test_client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/delete-me",
        json={"enabled": False},
        headers=headers,
    )

    # Delete plugin config
    response = test_client.delete(
        f"/api/v1/notebooks/{notebook_id}/plugins/delete-me",
        headers=headers,
    )
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify it returns to default
    get_response = test_client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins/delete-me",
        headers=headers,
    )
    assert get_response.json()["enabled"] is True  # Back to default


def test_notebook_requires_authentication(test_client):
    """Test that notebook endpoints require authentication."""
    response = test_client.get("/api/v1/workspaces/1/notebooks/")
    assert response.status_code == 401

    response = test_client.post("/api/v1/workspaces/1/notebooks/", json={"name": "Test"})
    assert response.status_code == 401

    response = test_client.get("/api/v1/workspaces/1/notebooks/1")
    assert response.status_code == 401

    response = test_client.get("/api/v1/notebooks/1/plugins")
    assert response.status_code == 401


def test_notebook_timestamps(test_client, temp_workspace_dir):
    """Test that notebook responses include timestamps."""
    headers, _ = setup_test_user(test_client)
    workspace = setup_workspace(test_client, headers, temp_workspace_dir)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Timestamp Test"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "created_at" in data
    assert "updated_at" in data
    assert data["created_at"] is not None


def test_create_notebook_in_nonexistent_workspace(test_client):
    """Test creating a notebook in a workspace that doesn't exist."""
    headers, _ = setup_test_user(test_client)

    response = test_client.post(
        "/api/v1/workspaces/99999/notebooks/",
        json={"name": "Orphan Notebook"},
        headers=headers,
    )
    assert response.status_code == 404
    assert "Workspace not found" in response.json()["detail"]

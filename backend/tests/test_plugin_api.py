"""Tests for plugin enable/disable API endpoints."""

import time

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
    username = f"testuser_plugin_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/v1/users/token", data={"username": username, "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def workspace_and_notebook(client, auth_headers):
    """Create a test workspace and notebook."""
    # Create workspace
    workspace_response = client.post(
        "/api/v1/workspaces",
        json={"name": f"Test Workspace {int(time.time() * 1000)}"},
        headers=auth_headers,
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]

    # Create notebook using nested route
    notebook_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/notebooks/",
        json={
            "name": f"Test Notebook {int(time.time() * 1000)}",
            "description": "Test notebook for plugin config",
        },
        headers=auth_headers,
    )
    assert notebook_response.status_code == 200
    notebook_id = notebook_response.json()["id"]

    return workspace_id, notebook_id


def test_list_integrations_with_workspace_id(client, auth_headers, workspace_and_notebook):
    """Test listing integrations with workspace_id parameter."""
    workspace_id, _ = workspace_and_notebook
    
    response = client.get(
        f"/api/v1/plugins/integrations?workspace_id={workspace_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    integrations = response.json()
    assert isinstance(integrations, list)
    # All integrations should have enabled field
    for integration in integrations:
        assert "enabled" in integration


def test_enable_disable_integration_workspace(client, auth_headers, workspace_and_notebook):
    """Test enabling/disabling integration at workspace level."""
    workspace_id, _ = workspace_and_notebook
    
    # Note: We can't test with real integrations since none are installed in test env
    # But we can test the endpoint structure
    # In a real scenario, you'd have a test integration plugin
    plugin_id = "test-integration"
    
    # Try to disable a non-existent integration (should fail gracefully)
    response = client.put(
        f"/api/v1/plugins/integrations/{plugin_id}/enable?workspace_id={workspace_id}",
        json={"enabled": False},
        headers=auth_headers,
    )
    # Should return 404 since plugin doesn't exist
    assert response.status_code == 404


def test_list_notebook_plugins_empty(client, auth_headers, workspace_and_notebook):
    """Test listing plugins for a notebook with no configs."""
    _, notebook_id = workspace_and_notebook
    
    response = client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins",
        headers=auth_headers,
    )
    assert response.status_code == 200
    plugins = response.json()
    assert isinstance(plugins, list)
    # Should be empty since no configs exist yet
    assert len(plugins) == 0


def test_get_notebook_plugin_config_default(client, auth_headers, workspace_and_notebook):
    """Test getting plugin config for notebook with no config (should return defaults)."""
    _, notebook_id = workspace_and_notebook
    plugin_id = "test-plugin"
    
    response = client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["plugin_id"] == plugin_id
    assert config["enabled"] is True  # Default to enabled
    assert config["config"] == {}  # Default to empty config


def test_update_notebook_plugin_config(client, auth_headers, workspace_and_notebook):
    """Test updating plugin config for notebook."""
    _, notebook_id = workspace_and_notebook
    plugin_id = "test-plugin"
    
    # Update config
    response = client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        json={"enabled": False, "config": {"key": "value"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["plugin_id"] == plugin_id
    assert config["enabled"] is False
    assert config["config"] == {"key": "value"}
    
    # Verify we can retrieve it
    response = client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is False
    assert config["config"] == {"key": "value"}


def test_update_notebook_plugin_config_partial(client, auth_headers, workspace_and_notebook):
    """Test partially updating plugin config (only enabled or only config)."""
    _, notebook_id = workspace_and_notebook
    plugin_id = "test-plugin-partial"
    
    # Update only enabled
    response = client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        json={"enabled": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is False
    assert config["config"] == {}  # Should remain empty
    
    # Update only config
    response = client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        json={"config": {"api_key": "test123"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is False  # Should remain False
    assert config["config"] == {"api_key": "test123"}


def test_delete_notebook_plugin_config(client, auth_headers, workspace_and_notebook):
    """Test deleting plugin config for notebook."""
    _, notebook_id = workspace_and_notebook
    plugin_id = "test-plugin-delete"
    
    # Create config
    response = client.put(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        json={"enabled": False, "config": {"key": "value"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    
    # Delete config
    response = client.delete(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    
    # Verify it returns to defaults
    response = client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is True  # Back to default
    assert config["config"] == {}  # Back to default


def test_multiple_notebooks_different_configs(client, auth_headers, workspace_and_notebook):
    """Test that different notebooks can have different plugin configs."""
    workspace_id, notebook1_id = workspace_and_notebook
    
    # Create second notebook using nested route
    notebook_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/notebooks/",
        json={
            "name": f"Test Notebook 2 {int(time.time() * 1000)}",
            "description": "Second test notebook",
        },
        headers=auth_headers,
    )
    assert notebook_response.status_code == 200
    notebook2_id = notebook_response.json()["id"]
    
    plugin_id = "test-plugin-multi"
    
    # Configure plugin differently for each notebook
    response1 = client.put(
        f"/api/v1/notebooks/{notebook1_id}/plugins/{plugin_id}",
        json={"enabled": True, "config": {"mode": "notebook1"}},
        headers=auth_headers,
    )
    assert response1.status_code == 200
    
    response2 = client.put(
        f"/api/v1/notebooks/{notebook2_id}/plugins/{plugin_id}",
        json={"enabled": False, "config": {"mode": "notebook2"}},
        headers=auth_headers,
    )
    assert response2.status_code == 200
    
    # Verify each notebook has its own config
    config1 = client.get(
        f"/api/v1/notebooks/{notebook1_id}/plugins/{plugin_id}",
        headers=auth_headers,
    ).json()
    config2 = client.get(
        f"/api/v1/notebooks/{notebook2_id}/plugins/{plugin_id}",
        headers=auth_headers,
    ).json()
    
    assert config1["enabled"] is True
    assert config1["config"]["mode"] == "notebook1"
    assert config2["enabled"] is False
    assert config2["config"]["mode"] == "notebook2"


def test_notebook_plugin_list_after_updates(client, auth_headers, workspace_and_notebook):
    """Test listing all plugins for a notebook after adding configs."""
    _, notebook_id = workspace_and_notebook
    
    # Add configs for multiple plugins
    plugins = ["plugin1", "plugin2", "plugin3"]
    for plugin_id in plugins:
        response = client.put(
            f"/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
            json={"enabled": True, "config": {"id": plugin_id}},
            headers=auth_headers,
        )
        assert response.status_code == 200
    
    # List all plugins
    response = client.get(
        f"/api/v1/notebooks/{notebook_id}/plugins",
        headers=auth_headers,
    )
    assert response.status_code == 200
    configs = response.json()
    assert len(configs) == 3
    
    plugin_ids = {config["plugin_id"] for config in configs}
    assert plugin_ids == set(plugins)


def test_unauthorized_access_notebook_plugins(client):
    """Test that unauthorized access is denied."""
    # Use a fake notebook_id - it shouldn't matter since auth should fail first
    notebook_id = 999
    
    # Try without auth headers
    response = client.get(f"/api/v1/notebooks/{notebook_id}/plugins")
    assert response.status_code == 401


def test_invalid_notebook_id(client, auth_headers):
    """Test accessing plugins for non-existent notebook."""
    invalid_notebook_id = 999999
    
    response = client.get(
        f"/api/v1/notebooks/{invalid_notebook_id}/plugins",
        headers=auth_headers,
    )
    assert response.status_code == 404

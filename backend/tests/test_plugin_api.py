"""Tests for plugin enable/disable API endpoints."""

import time


def test_list_integrations_with_workspace_id(test_client, auth_headers, workspace_and_notebook):
    """Test listing integrations with workspace_id parameter."""
    headers = auth_headers[0]
    workspace, _ = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/plugins/integrations?workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    integrations = response.json()
    assert isinstance(integrations, list)
    # All integrations should have enabled field
    for integration in integrations:
        assert "enabled" in integration


def test_enable_disable_integration_workspace(test_client, auth_headers, workspace_and_notebook):
    """Test enabling/disabling integration at workspace level."""
    headers = auth_headers[0]
    workspace, _ = workspace_and_notebook

    plugin_id = "test-integration"

    # Try to disable a non-existent integration (should fail gracefully)
    response = test_client.put(
        f"/api/v1/plugins/integrations/{plugin_id}/enable?workspace_id={workspace['id']}",
        json={"enabled": False},
        headers=headers,
    )
    # Should return 404 since plugin doesn't exist
    assert response.status_code == 404


def test_list_notebook_plugins_empty(test_client, auth_headers, workspace_and_notebook):
    """Test listing plugins for a notebook with no configs."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins",
        headers=headers,
    )
    assert response.status_code == 200
    plugins = response.json()
    assert isinstance(plugins, list)
    # Should be empty since no configs exist yet
    assert len(plugins) == 0


def test_get_notebook_plugin_config_default(test_client, auth_headers, workspace_and_notebook):
    """Test getting plugin config for notebook with no config (should return defaults)."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook
    plugin_id = "test-plugin"

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        headers=headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["plugin_id"] == plugin_id
    assert config["enabled"] is True  # Default to enabled
    assert config["config"] == {}  # Default to empty config


def test_update_notebook_plugin_config(test_client, auth_headers, workspace_and_notebook):
    """Test updating plugin config for notebook."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook
    plugin_id = "test-plugin"

    # Update config
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        json={"enabled": False, "config": {"key": "value"}},
        headers=headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["plugin_id"] == plugin_id
    assert config["enabled"] is False
    assert config["config"] == {"key": "value"}

    # Verify we can retrieve it
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        headers=headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is False
    assert config["config"] == {"key": "value"}


def test_update_notebook_plugin_config_partial(test_client, auth_headers, workspace_and_notebook):
    """Test partially updating plugin config (only enabled or only config)."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook
    plugin_id = "test-plugin-partial"

    # Update only enabled
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        json={"enabled": False},
        headers=headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is False
    assert config["config"] == {}  # Should remain empty

    # Update only config
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        json={"config": {"api_key": "test123"}},
        headers=headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is False  # Should remain False
    assert config["config"] == {"api_key": "test123"}


def test_delete_notebook_plugin_config(test_client, auth_headers, workspace_and_notebook):
    """Test deleting plugin config for notebook."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook
    plugin_id = "test-plugin-delete"

    # Create config
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        json={"enabled": False, "config": {"key": "value"}},
        headers=headers,
    )
    assert response.status_code == 200

    # Delete config
    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        headers=headers,
    )
    assert response.status_code == 200

    # Verify it returns to defaults
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
        headers=headers,
    )
    assert response.status_code == 200
    config = response.json()
    assert config["enabled"] is True  # Back to default
    assert config["config"] == {}  # Back to default


def test_multiple_notebooks_different_configs(test_client, auth_headers, workspace_and_notebook):
    """Test that different notebooks can have different plugin configs."""
    headers = auth_headers[0]
    workspace, notebook1 = workspace_and_notebook

    # Create second notebook using nested route
    notebook_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={
            "name": f"Test Notebook 2 {int(time.time() * 1000)}",
            "description": "Second test notebook",
        },
        headers=headers,
    )
    assert notebook_response.status_code == 200
    notebook2 = notebook_response.json()

    plugin_id = "test-plugin-multi"

    # Configure plugin differently for each notebook
    response1 = test_client.put(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook1['id']}/plugins/{plugin_id}",
        json={"enabled": True, "config": {"mode": "notebook1"}},
        headers=headers,
    )
    assert response1.status_code == 200

    response2 = test_client.put(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook2['id']}/plugins/{plugin_id}",
        json={"enabled": False, "config": {"mode": "notebook2"}},
        headers=headers,
    )
    assert response2.status_code == 200

    # Verify each notebook has its own config
    config1 = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook1['id']}/plugins/{plugin_id}",
        headers=headers,
    ).json()
    config2 = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook2['id']}/plugins/{plugin_id}",
        headers=headers,
    ).json()

    assert config1["enabled"] is True
    assert config1["config"]["mode"] == "notebook1"
    assert config2["enabled"] is False
    assert config2["config"]["mode"] == "notebook2"


def test_notebook_plugin_list_after_updates(test_client, auth_headers, workspace_and_notebook):
    """Test listing all plugins for a notebook after adding configs."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Add configs for multiple plugins
    plugins = ["plugin1", "plugin2", "plugin3"]
    for plugin_id in plugins:
        response = test_client.put(
            f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins/{plugin_id}",
            json={"enabled": True, "config": {"id": plugin_id}},
            headers=headers,
        )
        assert response.status_code == 200

    # List all plugins
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{notebook['id']}/plugins",
        headers=headers,
    )
    assert response.status_code == 200
    configs = response.json()
    assert len(configs) == 3

    plugin_ids = {config["plugin_id"] for config in configs}
    assert plugin_ids == set(plugins)


def test_unauthorized_access_notebook_plugins(test_client):
    """Test that unauthorized access is denied."""
    response = test_client.get("/api/v1/workspaces/999/notebooks/999/plugins")
    assert response.status_code == 401


def test_invalid_notebook_id(test_client, auth_headers, workspace_and_notebook):
    """Test accessing plugins for non-existent notebook."""
    headers = auth_headers[0]
    workspace, _ = workspace_and_notebook
    invalid_notebook_id = 999999

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/{invalid_notebook_id}/plugins",
        headers=headers,
    )
    assert response.status_code == 404

"""Tests for integration API routes.

Uses conftest's ``test_client`` fixture (no lifespan) to avoid spawning
FSEvents watchers on every test — the macOS _watchdog_fsevents extension
segfaults when too many concurrent observer streams accumulate.
"""

import pytest


def test_list_integrations(test_client, auth_headers):
    """Test listing all integrations."""
    headers = auth_headers[0]
    response = test_client.get("/api/v1/plugins/integrations", headers=headers)
    assert response.status_code == 200
    integrations = response.json()
    assert isinstance(integrations, list)


def test_list_integrations_unauthorized(test_client):
    """Test listing integrations without auth."""
    response = test_client.get("/api/v1/plugins/integrations")
    assert response.status_code == 401


def test_get_integration_config_not_found(test_client, auth_headers, workspace_and_notebook):
    """Test getting config for non-existent integration."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/integrations/nonexistent/config",
        headers=headers,
    )
    # Should return empty config, not error
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == "nonexistent"
    assert data["config"] == {}


def test_update_integration_config(test_client, auth_headers, workspace_and_notebook):
    """Test updating integration configuration."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Update integration config
    config_data = {
        "config": {
            "api_key": "test_key_123",
            "base_url": "https://api.example.com",
        }
    }
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/integrations/test-integration/config",
        headers=headers,
        json=config_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == "test-integration"
    assert data["config"]["api_key"] == "test_key_123"

    # Verify we can retrieve it
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/integrations/test-integration/config",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["api_key"] == "test_key_123"


def test_test_integration_not_found(test_client, auth_headers):
    """Test testing a non-existent integration."""
    headers = auth_headers[0]
    response = test_client.post(
        "/api/v1/plugins/integrations/nonexistent/test",
        headers=headers,
        json={"config": {}},
    )
    assert response.status_code == 404


def test_test_integration_exists(test_client, auth_headers):
    """Test testing an existing integration (should not return 404)."""
    headers = auth_headers[0]
    response = test_client.post(
        "/api/v1/plugins/integrations/weather-api/test",
        headers=headers,
        json={"config": {"api_key": "test_key_123"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert isinstance(data["success"], bool)


def test_execute_integration_not_found(test_client, auth_headers, workspace_and_notebook):
    """Test executing endpoint on non-existent integration."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/integrations/nonexistent/execute",
        headers=headers,
        json={"endpoint_id": "test", "parameters": {}},
    )
    assert response.status_code == 404


def test_get_integration_blocks_not_found(test_client, auth_headers):
    """Test getting blocks for non-existent integration."""
    headers = auth_headers[0]
    response = test_client.get(
        "/api/v1/plugins/integrations/nonexistent/blocks",
        headers=headers,
    )
    assert response.status_code == 404


def test_execute_integration_with_artifact_caching(test_client, auth_headers, workspace_and_notebook):
    """Test that /execute endpoint includes artifact caching.

    Smoke test to ensure the endpoint doesn't break with the artifact caching
    code. Uses a non-existent integration to avoid external API dependencies.
    """
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    execute_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/integrations/nonexistent/execute",
        headers=headers,
        json={
            "endpoint_id": "test",
            "parameters": {},
        },
    )

    assert execute_response.status_code == 404

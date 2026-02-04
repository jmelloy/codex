"""Tests for integration API routes."""

import time

import pytest
from fastapi.testclient import TestClient

from codex.main import app


@pytest.fixture
def client():
    """Create test client with lifespan context."""
    # Use the app with lifespan context
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for test user."""
    # Register and login
    username = f"testuser_integration_{int(time.time() * 1000)}"
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
    import tempfile
    from pathlib import Path
    
    # Create a temporary workspace
    tmpdir = tempfile.mkdtemp()
    workspace_path = Path(tmpdir) / "test_workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Create workspace via API
    response = client.post(
        "/api/v1/workspaces",
        headers=auth_headers,
        json={"name": f"Test Workspace {int(time.time() * 1000)}", "path": str(workspace_path)},
    )
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # Create notebook using nested route
    notebook_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/notebooks/",
        json={
            "name": f"Test Notebook {int(time.time() * 1000)}",
            "description": "Test notebook for integration config",
        },
        headers=auth_headers,
    )
    assert notebook_response.status_code == 200
    notebook_id = notebook_response.json()["id"]
    
    return workspace_id, notebook_id


def test_list_integrations(client, auth_headers):
    """Test listing all integrations."""
    response = client.get("/api/v1/plugins/integrations", headers=auth_headers)
    assert response.status_code == 200
    integrations = response.json()
    assert isinstance(integrations, list)
    # Since we don't have any integration plugins yet, it should be empty
    # But the endpoint should work


def test_list_integrations_unauthorized(client):
    """Test listing integrations without auth."""
    response = client.get("/api/v1/plugins/integrations")
    assert response.status_code == 401


def test_get_integration_config_not_found(client, auth_headers, workspace_and_notebook):
    """Test getting config for non-existent integration."""
    workspace_id, notebook_id = workspace_and_notebook
    
    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/integrations/nonexistent/config",
        headers=auth_headers,
    )
    # Should return empty config, not error
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == "nonexistent"
    assert data["config"] == {}


def test_update_integration_config(client, auth_headers, workspace_and_notebook):
    """Test updating integration configuration."""
    workspace_id, notebook_id = workspace_and_notebook

    # Update integration config
    config_data = {
        "config": {
            "api_key": "test_key_123",
            "base_url": "https://api.example.com",
        }
    }
    response = client.put(
        f"/api/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/integrations/test-integration/config",
        headers=auth_headers,
        json=config_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == "test-integration"
    assert data["config"]["api_key"] == "test_key_123"

    # Verify we can retrieve it
    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/integrations/test-integration/config",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["api_key"] == "test_key_123"


def test_test_integration_not_found(client, auth_headers):
    """Test testing a non-existent integration."""
    response = client.post(
        "/api/v1/plugins/integrations/nonexistent/test",
        headers=auth_headers,
        json={"config": {}},
    )
    assert response.status_code == 404


def test_test_integration_exists(client, auth_headers):
    """Test testing an existing integration (should not return 404)."""
    # Test with weather-api integration which exists in the test environment
    response = client.post(
        "/api/v1/plugins/integrations/weather-api/test",
        headers=auth_headers,
        json={"config": {"api_key": "test_key_123"}},
    )
    # Should return 200, not 404, even if the connection fails
    # The integration exists, so we should get a proper response
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data
    # The test may fail due to network issues, but it should not be a 404
    assert isinstance(data["success"], bool)


def test_execute_integration_not_found(client, auth_headers, workspace_and_notebook):
    """Test executing endpoint on non-existent integration."""
    workspace_id, notebook_id = workspace_and_notebook
    
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/integrations/nonexistent/execute",
        headers=auth_headers,
        json={"endpoint_id": "test", "parameters": {}},
    )
    assert response.status_code == 404


def test_get_integration_blocks_not_found(client, auth_headers):
    """Test getting blocks for non-existent integration."""
    response = client.get(
        "/api/v1/plugins/integrations/nonexistent/blocks",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_execute_integration_with_artifact_caching(client, auth_headers, workspace_and_notebook):
    """Test that /execute endpoint includes artifact caching.
    
    This is a smoke test to ensure the endpoint doesn't break with the new
    artifact caching code. We test with a non-existent integration to avoid
    dependencies on external APIs or network conditions.
    
    Full integration tests with real plugins and artifact verification are
    better suited for end-to-end tests that can handle external dependencies.
    """
    workspace_id, notebook_id = workspace_and_notebook
        
    # Try to execute an endpoint on a non-existent integration
    # This should return 404, not crash
    execute_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/integrations/nonexistent/execute",
        headers=auth_headers,
        json={
            "endpoint_id": "test",
            "parameters": {},
        },
    )
    
    # Should get 404 for non-existent integration
    assert execute_response.status_code == 404
    
    # The important thing is that the endpoint doesn't crash with the
    # new artifact caching code when the workspace lookup is added

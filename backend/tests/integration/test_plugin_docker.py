"""Docker integration tests for plugin system.

These tests validate that the plugin system loads correctly when running
in a Docker container. They require a running backend container.

Run with:
    docker compose -f docker-compose.test.yml up -d --build
    pytest tests/integration/test_plugin_docker.py -v
    docker compose -f docker-compose.test.yml down

Or use the test script:
    ./scripts/run_plugin_docker_tests.sh
"""

import os
import time

import pytest
import requests

# Backend URL for Docker tests
BACKEND_URL = os.environ.get("CODEX_TEST_URL", "http://localhost:8766")

# Expected plugins that should be loaded
EXPECTED_THEMES = ["cream", "manila", "white", "blueprint"]
EXPECTED_VIEW_PLUGINS = ["core", "tasks", "gallery", "corkboard", "rollup"]
EXPECTED_INTEGRATION_PLUGINS = ["github", "weather-api", "opengraph"]


def is_backend_available() -> bool:
    """Check if the backend is available."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def wait_for_backend(max_wait: int = 60) -> bool:
    """Wait for backend to become available."""
    start = time.time()
    while time.time() - start < max_wait:
        if is_backend_available():
            return True
        time.sleep(2)
    return False


# Skip all tests in this module if backend is not available
pytestmark = pytest.mark.skipif(
    not is_backend_available(),
    reason=f"Backend not available at {BACKEND_URL}. Start with: docker compose -f docker-compose.test.yml up -d",
)


class TestPluginDockerHealthCheck:
    """Test basic health and plugin loading."""

    def test_health_check(self):
        """Test that the backend health check passes."""
        response = requests.get(f"{BACKEND_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self):
        """Test that root endpoint is accessible."""
        response = requests.get(f"{BACKEND_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "Codex API" in data["message"]


class TestThemePluginsDocker:
    """Test that theme plugins are loaded correctly in Docker."""

    def test_themes_endpoint_accessible(self):
        """Test that themes endpoint returns successfully."""
        response = requests.get(f"{BACKEND_URL}/api/v1/themes")
        assert response.status_code == 200
        themes = response.json()
        assert isinstance(themes, list)
        assert len(themes) >= 4, "Should have at least 4 built-in themes"

    def test_expected_themes_present(self):
        """Test that all expected themes are loaded."""
        response = requests.get(f"{BACKEND_URL}/api/v1/themes")
        assert response.status_code == 200
        themes = response.json()

        theme_ids = [t["id"] for t in themes]
        for expected_theme in EXPECTED_THEMES:
            assert expected_theme in theme_ids, f"Theme '{expected_theme}' not found"

    def test_theme_has_required_fields(self):
        """Test that themes have all required fields."""
        response = requests.get(f"{BACKEND_URL}/api/v1/themes")
        assert response.status_code == 200
        themes = response.json()

        required_fields = ["id", "name", "label", "className", "category", "version"]

        for theme in themes:
            for field in required_fields:
                assert field in theme, f"Theme {theme.get('id', 'unknown')} missing field: {field}"

    def test_cream_theme_details(self):
        """Test specific details of cream theme."""
        response = requests.get(f"{BACKEND_URL}/api/v1/themes")
        assert response.status_code == 200
        themes = response.json()

        cream = next((t for t in themes if t["id"] == "cream"), None)
        assert cream is not None, "Cream theme not found"
        assert cream["className"] == "theme-cream"
        assert cream["category"] == "light"
        assert cream["version"] == "1.0.0"

    def test_blueprint_theme_is_dark(self):
        """Test that blueprint theme is correctly categorized as dark."""
        response = requests.get(f"{BACKEND_URL}/api/v1/themes")
        assert response.status_code == 200
        themes = response.json()

        blueprint = next((t for t in themes if t["id"] == "blueprint"), None)
        assert blueprint is not None, "Blueprint theme not found"
        assert blueprint["category"] == "dark"

    def test_theme_stylesheet_accessible(self):
        """Test that theme stylesheets can be retrieved."""
        for theme_id in EXPECTED_THEMES:
            response = requests.get(f"{BACKEND_URL}/api/v1/themes/{theme_id}/stylesheet")
            assert response.status_code == 200, f"Failed to get stylesheet for {theme_id}"
            assert response.headers["content-type"] == "text/css; charset=utf-8"
            assert len(response.text) > 0, f"Stylesheet for {theme_id} is empty"

    def test_invalid_theme_stylesheet_404(self):
        """Test that non-existent theme returns 404."""
        response = requests.get(f"{BACKEND_URL}/api/v1/themes/nonexistent-theme/stylesheet")
        assert response.status_code == 404


class TestIntegrationPluginsDocker:
    """Test that integration plugins are loaded correctly in Docker."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for test user."""
        username = f"test_docker_{int(time.time() * 1000)}"

        # Register user
        response = requests.post(
            f"{BACKEND_URL}/api/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )
        assert response.status_code == 201, f"Failed to register: {response.text}"

        # Login
        response = requests.post(
            f"{BACKEND_URL}/api/token",
            data={"username": username, "password": "testpass123"},
        )
        assert response.status_code == 200, f"Failed to login: {response.text}"
        token = response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    def test_integrations_endpoint_requires_auth(self):
        """Test that integrations endpoint requires authentication."""
        response = requests.get(f"{BACKEND_URL}/api/v1/integrations")
        assert response.status_code == 401

    def test_list_integrations(self, auth_headers):
        """Test listing all integration plugins."""
        response = requests.get(f"{BACKEND_URL}/api/v1/integrations", headers=auth_headers)
        assert response.status_code == 200
        integrations = response.json()
        assert isinstance(integrations, list)

    def test_expected_integrations_present(self, auth_headers):
        """Test that expected integration plugins are loaded."""
        response = requests.get(f"{BACKEND_URL}/api/v1/integrations", headers=auth_headers)
        assert response.status_code == 200
        integrations = response.json()

        integration_ids = [i["id"] for i in integrations]
        for expected in EXPECTED_INTEGRATION_PLUGINS:
            assert expected in integration_ids, f"Integration '{expected}' not found"

    def test_github_integration_details(self, auth_headers):
        """Test GitHub integration plugin details."""
        response = requests.get(f"{BACKEND_URL}/api/v1/integrations/github", headers=auth_headers)
        assert response.status_code == 200
        github = response.json()

        assert github["id"] == "github"
        assert github["name"] == "GitHub"
        assert github["type"] == "integration"
        # Check for expected blocks
        assert "blocks" in github or "endpoints" in github

    def test_integration_blocks_endpoint(self, auth_headers):
        """Test getting blocks for GitHub integration."""
        response = requests.get(f"{BACKEND_URL}/api/v1/integrations/github/blocks", headers=auth_headers)
        assert response.status_code == 200
        blocks = response.json()
        assert isinstance(blocks, list)
        # GitHub should have issue, PR, and repo blocks
        block_types = [b.get("type") or b.get("id") for b in blocks]
        assert len(block_types) > 0, "GitHub should have at least one block type"

    def test_weather_api_integration_loaded(self, auth_headers):
        """Test that weather-api integration is loaded."""
        response = requests.get(f"{BACKEND_URL}/api/v1/integrations/weather-api", headers=auth_headers)
        assert response.status_code == 200
        weather = response.json()
        assert weather["id"] == "weather-api"

    def test_nonexistent_integration_404(self, auth_headers):
        """Test that non-existent integration returns 404."""
        response = requests.get(f"{BACKEND_URL}/api/v1/integrations/nonexistent-integration", headers=auth_headers)
        assert response.status_code == 404


class TestTemplateLoadingDocker:
    """Test that plugin templates are loaded correctly."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers."""
        username = f"test_templates_{int(time.time() * 1000)}"

        requests.post(
            f"{BACKEND_URL}/api/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )

        response = requests.post(
            f"{BACKEND_URL}/api/token",
            data={"username": username, "password": "testpass123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_workspace(self, auth_headers):
        """Create a test workspace."""
        response = requests.post(
            f"{BACKEND_URL}/api/v1/workspaces",
            headers=auth_headers,
            json={
                "name": f"Test Workspace {int(time.time())}",
                "path": f"/tmp/test_ws_{int(time.time())}",
            },
        )
        assert response.status_code == 200
        return response.json()

    @pytest.fixture
    def test_notebook(self, auth_headers, test_workspace):
        """Create a test notebook."""
        response = requests.post(
            f"{BACKEND_URL}/api/v1/notebooks",
            headers=auth_headers,
            json={
                "name": f"Test Notebook {int(time.time())}",
                "workspace_id": test_workspace["id"],
            },
        )
        assert response.status_code == 200
        return response.json()

    def test_templates_endpoint_exists(self, auth_headers, test_notebook):
        """Test that templates endpoint returns templates."""
        response = requests.get(
            f"{BACKEND_URL}/api/v1/files/templates", headers=auth_headers, params={"notebook_id": test_notebook["id"]}
        )
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)
        assert len(templates) > 0, "Should have at least one template"

    def test_plugin_templates_loaded(self, auth_headers, test_notebook):
        """Test that plugin templates are included."""
        response = requests.get(
            f"{BACKEND_URL}/api/v1/files/templates", headers=auth_headers, params={"notebook_id": test_notebook["id"]}
        )
        assert response.status_code == 200
        templates = response.json()

        # Check for plugin-provided templates
        plugin_templates = [t for t in templates if t.get("plugin_id")]
        assert len(plugin_templates) > 0, "Should have plugin templates"

        # Check for specific expected templates
        template_ids = [t["id"] for t in templates]
        expected_templates = ["blank-note", "task-board", "photo-gallery"]
        for expected in expected_templates:
            assert expected in template_ids, f"Template '{expected}' not found"


class TestPluginConfigurationDocker:
    """Test plugin configuration and enable/disable in Docker."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers."""
        username = f"test_config_{int(time.time() * 1000)}"

        requests.post(
            f"{BACKEND_URL}/api/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )

        response = requests.post(
            f"{BACKEND_URL}/api/token",
            data={"username": username, "password": "testpass123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_workspace(self, auth_headers):
        """Create a test workspace."""
        response = requests.post(
            f"{BACKEND_URL}/api/v1/workspaces",
            headers=auth_headers,
            json={
                "name": f"Config Test WS {int(time.time())}",
                "path": f"/tmp/test_config_{int(time.time())}",
            },
        )
        return response.json()

    def test_enable_disable_integration(self, auth_headers, test_workspace):
        """Test enabling and disabling an integration at workspace level."""
        workspace_id = test_workspace["id"]

        # Enable GitHub integration
        response = requests.put(
            f"{BACKEND_URL}/api/v1/integrations/github/enable",
            headers=auth_headers,
            params={"workspace_id": workspace_id},
            json={"enabled": True},
        )
        assert response.status_code == 200

        # Disable it
        response = requests.put(
            f"{BACKEND_URL}/api/v1/integrations/github/enable",
            headers=auth_headers,
            params={"workspace_id": workspace_id},
            json={"enabled": False},
        )
        assert response.status_code == 200

    def test_integration_config_persistence(self, auth_headers, test_workspace):
        """Test that integration configuration persists."""
        workspace_id = test_workspace["id"]

        # Set configuration
        config_data = {
            "config": {
                "api_token": "test-token-123",
                "default_org": "test-org",
            }
        }
        response = requests.put(
            f"{BACKEND_URL}/api/v1/integrations/github/config",
            headers=auth_headers,
            params={"workspace_id": workspace_id},
            json=config_data,
        )
        assert response.status_code == 200

        # Retrieve and verify
        response = requests.get(
            f"{BACKEND_URL}/api/v1/integrations/github/config",
            headers=auth_headers,
            params={"workspace_id": workspace_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["api_token"] == "test-token-123"
        assert data["config"]["default_org"] == "test-org"


class TestPluginIsolationDocker:
    """Test that plugin data is properly isolated between workspaces."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers."""
        username = f"test_isolation_{int(time.time() * 1000)}"

        requests.post(
            f"{BACKEND_URL}/api/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )

        response = requests.post(
            f"{BACKEND_URL}/api/token",
            data={"username": username, "password": "testpass123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_workspace_config_isolation(self, auth_headers):
        """Test that plugin configs are isolated between workspaces."""
        # Create two workspaces
        ws1_response = requests.post(
            f"{BACKEND_URL}/api/v1/workspaces",
            headers=auth_headers,
            json={
                "name": f"Isolation WS1 {int(time.time())}",
                "path": f"/tmp/isolation_ws1_{int(time.time())}",
            },
        )
        ws1_id = ws1_response.json()["id"]

        ws2_response = requests.post(
            f"{BACKEND_URL}/api/v1/workspaces",
            headers=auth_headers,
            json={
                "name": f"Isolation WS2 {int(time.time())}",
                "path": f"/tmp/isolation_ws2_{int(time.time())}",
            },
        )
        ws2_id = ws2_response.json()["id"]

        # Set different configs for each workspace
        requests.put(
            f"{BACKEND_URL}/api/v1/integrations/github/config",
            headers=auth_headers,
            params={"workspace_id": ws1_id},
            json={"config": {"token": "ws1-token"}},
        )

        requests.put(
            f"{BACKEND_URL}/api/v1/integrations/github/config",
            headers=auth_headers,
            params={"workspace_id": ws2_id},
            json={"config": {"token": "ws2-token"}},
        )

        # Verify isolation
        response1 = requests.get(
            f"{BACKEND_URL}/api/v1/integrations/github/config", headers=auth_headers, params={"workspace_id": ws1_id}
        )
        response2 = requests.get(
            f"{BACKEND_URL}/api/v1/integrations/github/config", headers=auth_headers, params={"workspace_id": ws2_id}
        )

        assert response1.json()["config"]["token"] == "ws1-token"
        assert response2.json()["config"]["token"] == "ws2-token"


class TestPluginErrorHandlingDocker:
    """Test error handling for plugin operations."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers."""
        username = f"test_errors_{int(time.time() * 1000)}"

        requests.post(
            f"{BACKEND_URL}/api/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )

        response = requests.post(
            f"{BACKEND_URL}/api/token",
            data={"username": username, "password": "testpass123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_invalid_integration_test(self, auth_headers):
        """Test that testing non-existent integration returns 404."""
        response = requests.post(
            f"{BACKEND_URL}/api/v1/integrations/nonexistent/test", headers=auth_headers, json={"config": {}}
        )
        assert response.status_code == 404

    def test_invalid_integration_execute(self, auth_headers):
        """Test that executing on non-existent integration returns 404."""
        response = requests.post(
            f"{BACKEND_URL}/api/v1/integrations/nonexistent/execute",
            headers=auth_headers,
            params={"workspace_id": 1},
            json={"endpoint_id": "test", "parameters": {}},
        )
        assert response.status_code == 404

    def test_missing_workspace_id_for_config(self, auth_headers):
        """Test that missing workspace_id returns appropriate error."""
        response = requests.get(
            f"{BACKEND_URL}/api/v1/integrations/github/config",
            headers=auth_headers,
            # Missing workspace_id
        )
        # Should return 422 (validation error) for missing required param
        assert response.status_code == 422

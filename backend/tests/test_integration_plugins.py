"""Integration tests replacing tests/integration/test_plugins_verification.sh.

These tests verify the plugin system: registration (single and batch),
listing with type filtering, detail retrieval, validation of invalid
inputs, unregistration, and integration plugin APIs (integrations list,
detail, blocks).

The original shell script tested both filesystem-level plugin discovery
(via ``docker compose exec``) and the HTTP API.  Filesystem / loader
tests already live in ``test_plugins.py``; this file focuses on the HTTP
API surface that the shell script was exercising.
"""

import time

import pytest
from fastapi.testclient import TestClient

from codex.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_client() -> TestClient:
    return TestClient(app)


def _register_and_login(client: TestClient) -> dict:
    """Register a unique user and return auth headers."""
    ts = int(time.time() * 1000)
    username = f"plugintest_{ts}"
    password = "testpass123"
    email = f"{username}@example.com"

    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password},
    )
    login = client.post(
        "/api/v1/users/token",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Plugin Registration
# ---------------------------------------------------------------------------


class TestPluginRegistration:
    """Single and batch plugin registration via the API."""

    def test_register_single_plugin(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.post(
            "/api/v1/plugins/register",
            json={
                "id": "test-plugin-ci",
                "name": "CI Test Plugin",
                "version": "1.0.0",
                "type": "view",
                "manifest": {
                    "id": "test-plugin-ci",
                    "name": "CI Test Plugin",
                    "version": "1.0.0",
                    "type": "view",
                },
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["registered"] is True

        # Cleanup
        client.delete("/api/v1/plugins/test-plugin-ci", headers=headers)

    def test_register_batch(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.post(
            "/api/v1/plugins/register-batch",
            json={
                "plugins": [
                    {
                        "id": "batch-theme-ci",
                        "name": "CI Batch Theme",
                        "version": "1.0.0",
                        "type": "theme",
                        "manifest": {
                            "id": "batch-theme-ci",
                            "name": "CI Batch Theme",
                            "version": "1.0.0",
                            "type": "theme",
                        },
                    },
                    {
                        "id": "batch-integration-ci",
                        "name": "CI Batch Integration",
                        "version": "2.0.0",
                        "type": "integration",
                        "manifest": {
                            "id": "batch-integration-ci",
                            "name": "CI Batch Integration",
                            "version": "2.0.0",
                            "type": "integration",
                        },
                    },
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["registered"] + data["updated"] == 2

        # Cleanup
        client.delete("/api/v1/plugins/batch-theme-ci", headers=headers)
        client.delete("/api/v1/plugins/batch-integration-ci", headers=headers)


# ---------------------------------------------------------------------------
# Plugin Listing
# ---------------------------------------------------------------------------


class TestPluginListing:
    """List plugins and filter by type."""

    def test_list_plugins(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.get("/api/v1/plugins", headers=headers)
        assert resp.status_code == 200
        plugins = resp.json()
        assert isinstance(plugins, list)
        # conftest registers at least weather-api and github
        assert len(plugins) >= 2

    def test_filter_by_type(self):
        """Filtering by integration type should return at least the
        weather-api and github plugins seeded by conftest."""
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.get(
            "/api/v1/plugins",
            params={"plugin_type": "integration"},
            headers=headers,
        )
        assert resp.status_code == 200
        plugins = resp.json()
        assert len(plugins) >= 1
        assert all(p["type"] == "integration" for p in plugins)


# ---------------------------------------------------------------------------
# Plugin Detail
# ---------------------------------------------------------------------------


class TestPluginDetail:
    """Get a specific plugin and verify 404 for missing plugins."""

    def test_get_existing_plugin(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        # Register a known plugin
        client.post(
            "/api/v1/plugins/register",
            json={
                "id": "detail-test-ci",
                "name": "Detail Test Plugin",
                "version": "1.0.0",
                "type": "view",
                "manifest": {
                    "id": "detail-test-ci",
                    "name": "Detail Test Plugin",
                    "version": "1.0.0",
                    "type": "view",
                },
            },
            headers=headers,
        )

        resp = client.get("/api/v1/plugins/detail-test-ci", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Test Plugin"

        # Cleanup
        client.delete("/api/v1/plugins/detail-test-ci", headers=headers)

    def test_get_nonexistent_plugin_returns_404(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.get("/api/v1/plugins/does-not-exist", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Plugin Validation
# ---------------------------------------------------------------------------


class TestPluginValidation:
    """Invalid plugin registrations should be rejected."""

    def test_invalid_plugin_id(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.post(
            "/api/v1/plugins/register",
            json={
                "id": "INVALID_ID!",
                "name": "Bad Plugin",
                "version": "1.0.0",
                "type": "view",
                "manifest": {},
            },
            headers=headers,
        )
        assert resp.status_code == 400

    def test_invalid_version_format(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.post(
            "/api/v1/plugins/register",
            json={
                "id": "valid-id-ver",
                "name": "Bad Version",
                "version": "not-semver",
                "type": "view",
                "manifest": {},
            },
            headers=headers,
        )
        assert resp.status_code == 400

    def test_invalid_plugin_type(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        resp = client.post(
            "/api/v1/plugins/register",
            json={
                "id": "valid-id-type",
                "name": "Bad Type",
                "version": "1.0.0",
                "type": "invalid",
                "manifest": {},
            },
            headers=headers,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Plugin Unregister
# ---------------------------------------------------------------------------


class TestPluginUnregister:
    """Delete a plugin and confirm it is gone."""

    def test_unregister_plugin(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        # Register
        client.post(
            "/api/v1/plugins/register",
            json={
                "id": "unreg-ci",
                "name": "Unreg Test",
                "version": "1.0.0",
                "type": "view",
                "manifest": {
                    "id": "unreg-ci",
                    "name": "Unreg Test",
                    "version": "1.0.0",
                    "type": "view",
                },
            },
            headers=headers,
        )

        # Delete
        del_resp = client.delete("/api/v1/plugins/unreg-ci", headers=headers)
        assert del_resp.status_code == 200

        # Verify gone
        get_resp = client.get("/api/v1/plugins/unreg-ci", headers=headers)
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Integration Plugin API
# ---------------------------------------------------------------------------


class TestIntegrationPluginAPI:
    """Integration-specific endpoints: list, detail, blocks."""

    @pytest.fixture(autouse=True)
    def _register_weather_plugin(self):
        """Ensure weather-api integration exists for these tests.

        The conftest already seeds it, but re-register to be safe.
        """
        client = _fresh_client()
        headers = _register_and_login(client)
        self._client = client
        self._headers = headers

        client.post(
            "/api/v1/plugins/register",
            json={
                "id": "weather-api",
                "name": "Weather API Integration",
                "version": "1.0.0",
                "type": "integration",
                "manifest": {
                    "id": "weather-api",
                    "name": "Weather API Integration",
                    "version": "1.0.0",
                    "type": "integration",
                    "description": "Display current weather and forecasts from OpenWeatherMap",
                    "author": "Codex Team",
                    "integration": {
                        "api_type": "rest",
                        "base_url": "https://api.openweathermap.org",
                        "auth_method": "api_key",
                        "test_endpoint": "geocode",
                    },
                    "endpoints": [
                        {
                            "id": "geocode",
                            "name": "Geocode Location",
                            "method": "GET",
                            "path": "/geo/1.0/direct",
                        }
                    ],
                    "blocks": [
                        {
                            "id": "weather",
                            "name": "Weather Block",
                            "description": "Display current weather for a location",
                            "icon": "☀️",
                        }
                    ],
                },
            },
            headers=headers,
        )
        yield

    def test_list_integrations(self):
        resp = self._client.get(
            "/api/v1/plugins/integrations",
            headers=self._headers,
        )
        assert resp.status_code == 200
        integrations = resp.json()
        assert isinstance(integrations, list)
        assert len(integrations) >= 1

    def test_get_integration_detail(self):
        resp = self._client.get(
            "/api/v1/plugins/integrations/weather-api",
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("api_type") == "rest"

    def test_get_integration_blocks(self):
        resp = self._client.get(
            "/api/v1/plugins/integrations/weather-api/blocks",
            headers=self._headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        blocks = data.get("blocks", [])
        assert len(blocks) >= 1


# ---------------------------------------------------------------------------
# Full end-to-end plugin lifecycle
# ---------------------------------------------------------------------------


class TestPluginLifecycle:
    """Single test that walks through the full plugin lifecycle."""

    def test_register_list_detail_unregister(self):
        client = _fresh_client()
        headers = _register_and_login(client)

        plugin_id = f"lifecycle-ci-{int(time.time() * 1000)}"

        # 1. Register
        reg = client.post(
            "/api/v1/plugins/register",
            json={
                "id": plugin_id,
                "name": "Lifecycle Plugin",
                "version": "1.0.0",
                "type": "view",
                "manifest": {
                    "id": plugin_id,
                    "name": "Lifecycle Plugin",
                    "version": "1.0.0",
                    "type": "view",
                },
            },
            headers=headers,
        )
        assert reg.status_code == 200
        assert reg.json()["registered"] is True

        # 2. List (should contain our plugin)
        listing = client.get("/api/v1/plugins", headers=headers)
        assert listing.status_code == 200
        ids = [p["id"] for p in listing.json()]
        assert plugin_id in ids

        # 3. Detail
        detail = client.get(f"/api/v1/plugins/{plugin_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["name"] == "Lifecycle Plugin"

        # 4. Unregister
        delete = client.delete(f"/api/v1/plugins/{plugin_id}", headers=headers)
        assert delete.status_code == 200

        # 5. Verify gone
        gone = client.get(f"/api/v1/plugins/{plugin_id}", headers=headers)
        assert gone.status_code == 404

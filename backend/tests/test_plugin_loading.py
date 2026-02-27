"""End-to-end tests for plugin loading through the backend API.

Verifies the full plugin loading pipeline that the frontend relies on:
1. GET /api/v1/plugins/manifest — serves the unified manifest
2. GET /api/v1/plugins/assets/{path} — serves compiled JS, CSS, and theme stylesheets
3. Security: directory traversal prevention, extension allowlisting
4. Full flow: manifest discovery → batch registration → asset loading
"""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codex.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PLUGINS_DIR = Path(__file__).parent.parent.parent / "plugins"


@pytest.fixture(scope="module")
def _plugin_service():
    """Start the plugin service once per module.

    Initializes the PluginLoader, discovers and loads all plugins from
    the filesystem — the same initialization the app lifespan performs.
    """
    from codex.plugins.loader import PluginLoader

    loader = PluginLoader(PLUGINS_DIR)
    loader.load_all_plugins()
    return loader


@pytest.fixture
def client(_plugin_service):
    """Create a TestClient with the plugin service running.

    Sets up app.state with the initialized plugin loader and plugins_dir
    so the manifest and asset routes can serve plugin data.
    """
    c = TestClient(app)

    app.state.plugins_dir = PLUGINS_DIR
    app.state.plugin_loader = _plugin_service

    yield c

    app.state.plugins_dir = None
    app.state.plugin_loader = None


def _register_and_login(client: TestClient) -> dict:
    """Register a unique user and return auth headers."""
    ts = int(time.time() * 1000)
    username = f"pluginload_{ts}"
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
# Manifest Endpoint
# ---------------------------------------------------------------------------


class TestManifestEndpoint:
    """GET /api/v1/plugins/manifest serves plugin data to the frontend."""

    def test_manifest_returns_valid_structure(self, client):
        """Manifest must have version, buildTime, and plugins array."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

        data = resp.json()
        assert "version" in data
        assert "buildTime" in data
        assert "plugins" in data
        assert isinstance(data["plugins"], list)

    def test_manifest_discovers_plugins_from_filesystem(self, client):
        """When no plugins.json exists, the manifest endpoint should still
        return plugins discovered by the PluginLoader from the filesystem."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

        data = resp.json()
        plugin_ids = [p["id"] for p in data["plugins"]]

        # The plugins directory has well-known plugins
        assert len(plugin_ids) > 0, "Should discover at least some plugins"

    def test_manifest_includes_theme_plugins(self, client):
        """Theme plugins should appear in the manifest with theme config."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

        data = resp.json()
        theme_plugins = [p for p in data["plugins"] if p["type"] == "theme"]
        assert len(theme_plugins) > 0, "Should find at least one theme plugin"

        # Verify theme config is present in manifest
        for theme in theme_plugins:
            manifest = theme.get("manifest", {})
            assert manifest.get("type") == "theme"

    def test_manifest_includes_integration_plugins(self, client):
        """Integration plugins should appear with their integration config."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

        data = resp.json()
        integration_plugins = [p for p in data["plugins"] if p["type"] == "integration"]
        assert len(integration_plugins) > 0, "Should find at least one integration plugin"

    def test_manifest_includes_view_plugins(self, client):
        """View plugins should appear with their views config."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

        data = resp.json()
        view_plugins = [p for p in data["plugins"] if p["type"] == "view"]
        assert len(view_plugins) > 0, "Should find at least one view plugin"

    def test_manifest_plugin_fields(self, client):
        """Each plugin entry must have required fields: id, name, version, type."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

        data = resp.json()
        for plugin in data["plugins"]:
            assert "id" in plugin, f"Plugin missing 'id': {plugin}"
            assert "name" in plugin, f"Plugin missing 'name': {plugin}"
            assert "version" in plugin, f"Plugin missing 'version': {plugin}"
            assert "type" in plugin, f"Plugin missing 'type': {plugin}"
            assert plugin["type"] in ("view", "theme", "integration"), (
                f"Invalid plugin type: {plugin['type']}"
            )

    def test_manifest_does_not_require_auth(self, client):
        """The manifest endpoint should be accessible without authentication
        since it serves static plugin metadata."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

    def test_manifest_from_plugins_json(self, client):
        """When a plugins.json file exists, it should be served directly."""
        plugins_json_path = PLUGINS_DIR / "plugins.json"
        test_manifest = {
            "version": "1.0.0",
            "buildTime": "2026-01-01T00:00:00Z",
            "plugins": [
                {
                    "id": "test-from-json",
                    "name": "Test From JSON",
                    "version": "1.0.0",
                    "type": "view",
                    "manifest": {"id": "test-from-json", "name": "Test From JSON", "version": "1.0.0", "type": "view"},
                    "components": {},
                }
            ],
        }

        had_existing = plugins_json_path.exists()
        existing_content = None
        if had_existing:
            existing_content = plugins_json_path.read_text()

        try:
            plugins_json_path.write_text(json.dumps(test_manifest))

            resp = client.get("/api/v1/plugins/manifest")
            assert resp.status_code == 200

            data = resp.json()
            assert data["buildTime"] == "2026-01-01T00:00:00Z"
            plugin_ids = [p["id"] for p in data["plugins"]]
            assert "test-from-json" in plugin_ids
        finally:
            # Restore original state
            if had_existing and existing_content is not None:
                plugins_json_path.write_text(existing_content)
            elif plugins_json_path.exists():
                plugins_json_path.unlink()


# ---------------------------------------------------------------------------
# Asset Serving
# ---------------------------------------------------------------------------


class TestAssetServing:
    """GET /api/v1/plugins/assets/{path} serves plugin files."""

    def test_serve_theme_stylesheet(self, client):
        """Theme stylesheets should be served with correct content type."""
        resp = client.get("/api/v1/plugins/assets/cream/styles/main.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]
        # Should contain actual CSS content
        assert len(resp.text) > 0

    def test_serve_manifest_yml(self, client):
        """Manifest YAML files should not be served (not an allowed extension)."""
        resp = client.get("/api/v1/plugins/assets/cream/manifest.yml")
        assert resp.status_code == 403

    def test_serve_nonexistent_asset_returns_404(self, client):
        """Requesting a non-existent file returns 404."""
        resp = client.get("/api/v1/plugins/assets/nonexistent/dist/foo.js")
        assert resp.status_code == 404

    def test_serve_json_file(self, client):
        """JSON files should be served with correct content type."""
        # Create a temporary JSON file in a plugin dist dir
        dist_dir = PLUGINS_DIR / "cream" / "dist"
        dist_dir.mkdir(exist_ok=True)
        test_file = dist_dir / "test-asset.json"
        try:
            test_file.write_text('{"test": true}')

            resp = client.get("/api/v1/plugins/assets/cream/dist/test-asset.json")
            assert resp.status_code == 200
            assert "application/json" in resp.headers["content-type"]
        finally:
            test_file.unlink(missing_ok=True)
            # Only remove dist dir if we created it and it's empty
            if dist_dir.exists() and not any(dist_dir.iterdir()):
                dist_dir.rmdir()

    def test_assets_do_not_require_auth(self, client):
        """Asset endpoints should be accessible without authentication
        since they serve static compiled files."""
        resp = client.get("/api/v1/plugins/assets/cream/styles/main.css")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Asset Security
# ---------------------------------------------------------------------------


class TestAssetSecurity:
    """Security checks for the asset serving endpoint."""

    def test_directory_traversal_blocked(self, client):
        """Path traversal attempts must be blocked."""
        resp = client.get("/api/v1/plugins/assets/../backend/codex/main.py")
        assert resp.status_code in (400, 403, 404)

    def test_double_dot_in_path_blocked(self, client):
        """Double-dot sequences in deeper paths must be blocked."""
        resp = client.get("/api/v1/plugins/assets/cream/../../etc/passwd")
        assert resp.status_code in (400, 403, 404)

    def test_disallowed_extension_blocked(self, client):
        """File types not in the allowlist must be rejected."""
        # .yml is not in the allowed extensions
        resp = client.get("/api/v1/plugins/assets/cream/manifest.yml")
        assert resp.status_code == 403

    def test_python_files_blocked(self, client):
        """Python files must never be served."""
        resp = client.get("/api/v1/plugins/assets/shared/types.py")
        assert resp.status_code in (403, 404)

    def test_no_directory_listing(self, client):
        """Requesting a directory path should not list contents."""
        resp = client.get("/api/v1/plugins/assets/cream/")
        assert resp.status_code in (403, 404)
        # Should not contain file names from the directory
        assert "manifest.yml" not in resp.text

    def test_allowed_extensions_served(self, client):
        """Verify that CSS files are served correctly."""
        resp = client.get("/api/v1/plugins/assets/cream/styles/main.css")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Full E2E Plugin Loading Flow
# ---------------------------------------------------------------------------


class TestPluginLoadingFlow:
    """End-to-end: discover plugins → load manifest → register → serve assets.

    Simulates the complete flow the frontend performs on startup.
    """

    def test_frontend_startup_flow(self, client):
        """Simulate the frontend's plugin loading sequence:
        1. Fetch manifest from /api/v1/plugins/manifest
        2. Register plugins via /api/v1/plugins/register-batch
        3. Verify plugins appear in /api/v1/plugins listing
        """
        headers = _register_and_login(client)

        # Step 1: Frontend fetches manifest (no auth needed)
        manifest_resp = client.get("/api/v1/plugins/manifest")
        assert manifest_resp.status_code == 200
        manifest = manifest_resp.json()
        assert len(manifest["plugins"]) > 0, "Manifest should contain plugins"

        # Step 2: Frontend registers plugins with the backend (requires auth)
        plugins_to_register = [
            {
                "id": p["id"],
                "name": p["name"],
                "version": p["version"],
                "type": p["type"],
                "manifest": p.get("manifest", {}),
            }
            for p in manifest["plugins"]
        ]

        batch_resp = client.post(
            "/api/v1/plugins/register-batch",
            json={"plugins": plugins_to_register},
            headers=headers,
        )
        assert batch_resp.status_code == 200
        batch_data = batch_resp.json()
        total_processed = batch_data["registered"] + batch_data["updated"]
        assert total_processed == len(plugins_to_register), (
            f"Expected {len(plugins_to_register)} processed, got {total_processed}"
        )
        assert batch_data["failed"] == 0

        # Step 3: Verify plugins appear in the listing
        list_resp = client.get("/api/v1/plugins", headers=headers)
        assert list_resp.status_code == 200
        registered_ids = {p["id"] for p in list_resp.json()}
        manifest_ids = {p["id"] for p in manifest["plugins"]}
        assert manifest_ids.issubset(registered_ids), (
            f"Manifest plugins {manifest_ids - registered_ids} not found in registered plugins"
        )

    def test_theme_loading_flow(self, client):
        """Simulate loading a theme: manifest → find theme → load stylesheet."""
        # Step 1: Get manifest
        manifest_resp = client.get("/api/v1/plugins/manifest")
        assert manifest_resp.status_code == 200
        manifest = manifest_resp.json()

        # Step 2: Find theme plugins
        theme_plugins = [p for p in manifest["plugins"] if p["type"] == "theme"]
        assert len(theme_plugins) > 0, "Should have theme plugins"

        # Step 3: For each theme with a stylesheet, verify we can load it
        for theme in theme_plugins:
            theme_config = theme.get("manifest", {}).get("theme", {})
            stylesheet = theme_config.get("stylesheet")
            theme_id = theme["id"]

            if stylesheet:
                css_url = f"/api/v1/plugins/assets/{theme_id}/{stylesheet}"
            else:
                css_url = f"/api/v1/plugins/assets/{theme_id}/styles/main.css"

            css_resp = client.get(css_url)
            # Theme stylesheet should be loadable
            assert css_resp.status_code == 200, (
                f"Failed to load stylesheet for theme {theme_id}: {css_url}"
            )
            assert "text/css" in css_resp.headers["content-type"]

    def test_plugin_update_via_manifest_reload(self, client):
        """Simulate a plugin version update: register v1, re-register v2."""
        headers = _register_and_login(client)

        plugin_id = f"update-flow-{int(time.time() * 1000)}"

        # Register v1
        v1_resp = client.post(
            "/api/v1/plugins/register",
            json={
                "id": plugin_id,
                "name": "Update Flow Plugin",
                "version": "1.0.0",
                "type": "view",
                "manifest": {"id": plugin_id, "name": "Update Flow Plugin", "version": "1.0.0", "type": "view"},
            },
            headers=headers,
        )
        assert v1_resp.status_code == 200
        assert v1_resp.json()["message"] == "Plugin registered"

        # Re-register as v2 (simulates manifest reload after build:watch rebuild)
        v2_resp = client.post(
            "/api/v1/plugins/register",
            json={
                "id": plugin_id,
                "name": "Update Flow Plugin v2",
                "version": "2.0.0",
                "type": "view",
                "manifest": {"id": plugin_id, "name": "Update Flow Plugin v2", "version": "2.0.0", "type": "view"},
            },
            headers=headers,
        )
        assert v2_resp.status_code == 200
        assert v2_resp.json()["message"] == "Plugin updated"

        # Verify the latest version is stored
        detail_resp = client.get(f"/api/v1/plugins/{plugin_id}", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["version"] == "2.0.0"
        assert detail_resp.json()["name"] == "Update Flow Plugin v2"

        # Cleanup
        client.delete(f"/api/v1/plugins/{plugin_id}", headers=headers)


# ---------------------------------------------------------------------------
# Manifest with built plugins.json
# ---------------------------------------------------------------------------


class TestBuiltManifest:
    """Tests for manifest serving when plugins.json exists (post-build)."""

    def test_manifest_with_components(self, client):
        """When plugins.json includes component mappings, they should be
        preserved and accessible to the frontend."""
        plugins_json_path = PLUGINS_DIR / "plugins.json"
        had_existing = plugins_json_path.exists()
        existing_content = None
        if had_existing:
            existing_content = plugins_json_path.read_text()

        test_manifest = {
            "version": "1.0.0",
            "buildTime": "2026-02-26T00:00:00Z",
            "plugins": [
                {
                    "id": "test-with-components",
                    "name": "Test With Components",
                    "version": "1.0.0",
                    "type": "integration",
                    "manifest": {
                        "id": "test-with-components",
                        "name": "Test With Components",
                        "version": "1.0.0",
                        "type": "integration",
                        "blocks": [{"id": "test-block", "name": "Test Block"}],
                    },
                    "components": {
                        "test-block": {
                            "blockId": "test-block",
                            "blockName": "Test Block",
                            "file": "test-with-components/1.0.0/test-block.js",
                        }
                    },
                }
            ],
        }

        try:
            plugins_json_path.write_text(json.dumps(test_manifest))

            resp = client.get("/api/v1/plugins/manifest")
            assert resp.status_code == 200

            data = resp.json()
            plugin = data["plugins"][0]
            assert "components" in plugin
            assert "test-block" in plugin["components"]
            assert plugin["components"]["test-block"]["file"] == "test-with-components/1.0.0/test-block.js"
        finally:
            if had_existing and existing_content is not None:
                plugins_json_path.write_text(existing_content)
            elif plugins_json_path.exists():
                plugins_json_path.unlink()

    def test_asset_path_from_manifest_component(self, client):
        """Verify that the component file paths in the manifest can be
        used to construct valid asset URLs."""
        resp = client.get("/api/v1/plugins/manifest")
        assert resp.status_code == 200

        data = resp.json()
        for plugin in data["plugins"]:
            components = plugin.get("components", {})
            for block_id, comp in components.items():
                file_path = comp.get("file", "")
                if file_path:
                    # The file path should form a valid asset URL
                    asset_url = f"/api/v1/plugins/assets/{file_path}"
                    # We don't assert 200 (file may not be built yet),
                    # but the path should not be rejected as invalid
                    asset_resp = client.get(asset_url)
                    assert asset_resp.status_code != 403, (
                        f"Asset path rejected for {block_id}: {asset_url}"
                    )


# ---------------------------------------------------------------------------
# Versioned Asset Paths
# ---------------------------------------------------------------------------


class TestVersionedAssetPaths:
    """Versioned asset paths: /assets/{plugin_id}/{version}/{file}."""

    def test_versioned_path_resolves_to_dist(self, client):
        """A versioned path like cream/1.0.0/test.css should resolve
        to cream/dist/test.css on disk."""
        dist_dir = PLUGINS_DIR / "cream" / "dist"
        dist_dir.mkdir(exist_ok=True)
        test_file = dist_dir / "version-test.css"
        try:
            test_file.write_text("/* versioned */")

            resp = client.get("/api/v1/plugins/assets/cream/1.0.0/version-test.css")
            assert resp.status_code == 200
            assert "text/css" in resp.headers["content-type"]
            assert "versioned" in resp.text
        finally:
            test_file.unlink(missing_ok=True)
            if dist_dir.exists() and not any(dist_dir.iterdir()):
                dist_dir.rmdir()

    def test_versioned_path_missing_file_returns_404(self, client):
        """A versioned path to a non-existent file returns 404."""
        resp = client.get("/api/v1/plugins/assets/cream/99.0.0/nonexistent.js")
        assert resp.status_code == 404

    def test_versioned_path_disallowed_extension_blocked(self, client):
        """Extension allowlist is checked before resolving versioned paths."""
        resp = client.get("/api/v1/plugins/assets/cream/1.0.0/secret.py")
        assert resp.status_code == 403

    def test_direct_path_still_works(self, client):
        """Non-versioned (direct) paths still work for theme stylesheets."""
        resp = client.get("/api/v1/plugins/assets/cream/styles/main.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_prerelease_version_resolves_to_dist(self, client):
        """A pre-release version like cream/1.0.0-alpha/test.css resolves to cream/dist/test.css."""
        dist_dir = PLUGINS_DIR / "cream" / "dist"
        dist_dir.mkdir(exist_ok=True)
        test_file = dist_dir / "prerelease-test.css"
        try:
            test_file.write_text("/* prerelease */")

            resp = client.get("/api/v1/plugins/assets/cream/1.0.0-alpha/prerelease-test.css")
            assert resp.status_code == 200
            assert "text/css" in resp.headers["content-type"]
            assert "prerelease" in resp.text
        finally:
            test_file.unlink(missing_ok=True)
            if dist_dir.exists() and not any(dist_dir.iterdir()):
                dist_dir.rmdir()

    def test_prerelease_dotted_version_resolves_to_dist(self, client):
        """A dotted pre-release version like 1.0.0-beta.1 resolves to dist/."""
        dist_dir = PLUGINS_DIR / "cream" / "dist"
        dist_dir.mkdir(exist_ok=True)
        test_file = dist_dir / "beta-test.js"
        try:
            test_file.write_text("// beta")

            resp = client.get("/api/v1/plugins/assets/cream/1.0.0-beta.1/beta-test.js")
            assert resp.status_code == 200
        finally:
            test_file.unlink(missing_ok=True)
            if dist_dir.exists() and not any(dist_dir.iterdir()):
                dist_dir.rmdir()

    def test_build_metadata_version_resolves_to_dist(self, client):
        """A build-metadata version like 1.0.0+build.42 resolves to dist/."""
        dist_dir = PLUGINS_DIR / "cream" / "dist"
        dist_dir.mkdir(exist_ok=True)
        test_file = dist_dir / "build-test.js"
        try:
            test_file.write_text("// build")

            resp = client.get("/api/v1/plugins/assets/cream/1.0.0+build.42/build-test.js")
            assert resp.status_code == 200
        finally:
            test_file.unlink(missing_ok=True)
            if dist_dir.exists() and not any(dist_dir.iterdir()):
                dist_dir.rmdir()


# ---------------------------------------------------------------------------
# Workspace Plugin Config Version
# ---------------------------------------------------------------------------


class TestWorkspacePluginVersion:
    """Workspace plugin config should include a version field."""

    def test_plugin_config_returns_version(self, client):
        """Plugin config endpoint should return a version field."""
        headers = _register_and_login(client)

        # Create a workspace
        ws_resp = client.post(
            "/api/v1/workspaces/",
            json={"name": f"test-ws-{int(time.time() * 1000)}"},
            headers=headers,
        )
        assert ws_resp.status_code in (200, 201)
        ws_id = ws_resp.json()["id"]

        # Register a plugin
        plugin_id = f"ver-test-{int(time.time() * 1000)}"
        client.post(
            "/api/v1/plugins/register",
            json={
                "id": plugin_id,
                "name": "Version Test Plugin",
                "version": "2.0.0",
                "type": "view",
                "manifest": {"id": plugin_id, "name": "Version Test Plugin", "version": "2.0.0", "type": "view"},
            },
            headers=headers,
        )

        # Enable plugin for workspace with a specific version
        put_resp = client.put(
            f"/api/v1/workspaces/{ws_id}/plugins/{plugin_id}",
            json={"enabled": True, "version": "2.0.0"},
            headers=headers,
        )
        assert put_resp.status_code == 200
        config = put_resp.json()
        assert config["version"] == "2.0.0"
        assert config["enabled"] is True

        # Retrieve and verify version is persisted
        get_resp = client.get(
            f"/api/v1/workspaces/{ws_id}/plugins/{plugin_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == "2.0.0"

        # List workspace plugins should include version
        list_resp = client.get(
            f"/api/v1/workspaces/{ws_id}/plugins",
            headers=headers,
        )
        assert list_resp.status_code == 200
        configs = list_resp.json()
        matching = [c for c in configs if c["plugin_id"] == plugin_id]
        assert len(matching) == 1
        assert matching[0]["version"] == "2.0.0"

        # Cleanup
        client.delete(f"/api/v1/workspaces/{ws_id}", headers=headers)
        client.delete(f"/api/v1/plugins/{plugin_id}", headers=headers)

    def test_default_config_has_null_version(self, client):
        """When no config exists, the default response should have version=null."""
        headers = _register_and_login(client)

        ws_resp = client.post(
            "/api/v1/workspaces/",
            json={"name": f"test-ws-null-{int(time.time() * 1000)}"},
            headers=headers,
        )
        ws_id = ws_resp.json()["id"]

        get_resp = client.get(
            f"/api/v1/workspaces/{ws_id}/plugins/some-unconfigured-plugin",
            headers=headers,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] is None

        # Cleanup
        client.delete(f"/api/v1/workspaces/{ws_id}", headers=headers)

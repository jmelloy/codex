"""Tests for the plugin service API endpoints."""

import hashlib
import os
import tarfile
import io
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from api.catalog import PluginCatalog
from api.main import app


@pytest.fixture
def plugins_dir(tmp_path):
    """Create test plugins directory."""
    theme_dir = tmp_path / "test-theme"
    theme_dir.mkdir()
    (theme_dir / "manifest.yml").write_text(
        yaml.dump(
            {
                "id": "test-theme",
                "name": "Test Theme",
                "version": "1.0.0",
                "type": "theme",
                "description": "A test theme",
                "author": "Test Author",
                "theme": {"display_name": "Test Theme", "category": "light"},
            }
        )
    )

    int_dir = tmp_path / "test-integration"
    int_dir.mkdir()
    (int_dir / "manifest.yml").write_text(
        yaml.dump(
            {
                "id": "test-integration",
                "name": "Test Integration",
                "version": "2.0.0",
                "type": "integration",
                "description": "A test integration",
                "author": "Test Author",
                "integration": {
                    "api_type": "rest",
                    "base_url": "https://api.example.com",
                },
            }
        )
    )

    return tmp_path


@pytest.fixture
def test_client(plugins_dir):
    """Create a test client with a pre-built catalog."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()
    app.state.catalog = catalog
    return TestClient(app)


def test_health(test_client):
    """Test health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_catalog(test_client):
    """Test listing the full catalog."""
    response = test_client.get("/api/v1/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["plugins"]) == 2

    ids = {p["id"] for p in data["plugins"]}
    assert ids == {"test-theme", "test-integration"}


def test_list_catalog_filter_by_type(test_client):
    """Test filtering catalog by type."""
    response = test_client.get("/api/v1/catalog?plugin_type=theme")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["plugins"][0]["id"] == "test-theme"


def test_get_plugin_info(test_client):
    """Test getting specific plugin info."""
    response = test_client.get("/api/v1/catalog/test-theme")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-theme"
    assert data["name"] == "Test Theme"
    assert data["version"] == "1.0.0"
    assert data["type"] == "theme"
    assert data["sha256"]
    assert data["archive_size"] > 0
    assert "manifest" in data


def test_get_plugin_info_not_found(test_client):
    """Test 404 for nonexistent plugin."""
    response = test_client.get("/api/v1/catalog/nonexistent")
    assert response.status_code == 404


def test_download_plugin(test_client):
    """Test downloading a plugin archive."""
    # First get the expected checksum
    info_response = test_client.get("/api/v1/catalog/test-theme")
    expected_sha256 = info_response.json()["sha256"]

    # Download the archive
    response = test_client.get("/api/v1/catalog/test-theme/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/gzip"
    assert response.headers["x-checksum-sha256"] == expected_sha256
    assert "test-theme-1.0.0.tar.gz" in response.headers["content-disposition"]

    # Verify the downloaded archive checksum
    actual_sha256 = hashlib.sha256(response.content).hexdigest()
    assert actual_sha256 == expected_sha256

    # Verify it's a valid tar.gz
    buf = io.BytesIO(response.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert any("manifest.yml" in n for n in names)


def test_download_plugin_not_found(test_client):
    """Test 404 for downloading nonexistent plugin."""
    response = test_client.get("/api/v1/catalog/nonexistent/download")
    assert response.status_code == 404


def test_refresh_catalog(test_client, plugins_dir):
    """Test catalog refresh endpoint."""
    # Add a new plugin
    new_dir = plugins_dir / "new-plugin"
    new_dir.mkdir()
    (new_dir / "manifest.yml").write_text(
        yaml.dump(
            {
                "id": "new-plugin",
                "name": "New Plugin",
                "version": "1.0.0",
                "type": "view",
            }
        )
    )

    # Refresh
    response = test_client.post("/api/v1/catalog/refresh")
    assert response.status_code == 200
    assert response.json()["total"] == 3

    # Verify new plugin is in catalog
    response = test_client.get("/api/v1/catalog/new-plugin")
    assert response.status_code == 200


def test_catalog_entry_has_sha256(test_client):
    """Test that every catalog entry includes a SHA-256 checksum."""
    response = test_client.get("/api/v1/catalog")
    for plugin in response.json()["plugins"]:
        assert "sha256" in plugin
        assert len(plugin["sha256"]) == 64  # SHA-256 hex is 64 chars

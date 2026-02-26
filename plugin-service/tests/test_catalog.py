"""Tests for the plugin catalog builder."""

import hashlib
import tarfile
import io
from pathlib import Path
import tempfile

import pytest
import yaml

from codex_plugin_service.catalog import PluginCatalog, CatalogEntry


@pytest.fixture
def plugins_dir(tmp_path):
    """Create a temporary plugins directory with test plugins."""
    # Create a theme plugin
    theme_dir = tmp_path / "test-theme"
    theme_dir.mkdir()
    (theme_dir / "manifest.yml").write_text(yaml.dump({
        "id": "test-theme",
        "name": "Test Theme",
        "version": "1.0.0",
        "type": "theme",
        "description": "A test theme",
        "author": "Test Author",
        "theme": {
            "display_name": "Test Theme",
            "category": "light",
            "className": "theme-test",
            "stylesheet": "styles/main.css",
        },
    }))
    styles_dir = theme_dir / "styles"
    styles_dir.mkdir()
    (styles_dir / "main.css").write_text("body { background: #fff; }")

    # Create an integration plugin
    int_dir = tmp_path / "test-integration"
    int_dir.mkdir()
    (int_dir / "manifest.yml").write_text(yaml.dump({
        "id": "test-integration",
        "name": "Test Integration",
        "version": "2.0.0",
        "type": "integration",
        "description": "A test integration",
        "author": "Test Author",
        "integration": {
            "api_type": "rest",
            "base_url": "https://api.example.com",
            "auth_method": "api_key",
        },
        "endpoints": [
            {"id": "test", "name": "Test", "method": "GET", "path": "/test"},
        ],
    }))

    # Create a directory that should be skipped (no manifest)
    (tmp_path / "not-a-plugin").mkdir()
    (tmp_path / "not-a-plugin" / "README.md").write_text("Not a plugin")

    # Create a directory that should be skipped (starts with .)
    (tmp_path / ".hidden").mkdir()

    # Create shared directory that should be skipped
    (tmp_path / "shared").mkdir()

    return tmp_path


def test_catalog_build(plugins_dir):
    """Test that catalog discovers and loads valid plugins."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()

    assert len(catalog.entries) == 2
    assert "test-theme" in catalog.entries
    assert "test-integration" in catalog.entries


def test_catalog_entry_fields(plugins_dir):
    """Test that catalog entries have correct fields."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()

    theme = catalog.get_entry("test-theme")
    assert theme is not None
    assert theme.plugin_id == "test-theme"
    assert theme.name == "Test Theme"
    assert theme.version == "1.0.0"
    assert theme.plugin_type == "theme"
    assert theme.description == "A test theme"
    assert theme.author == "Test Author"
    assert theme.archive_sha256  # Non-empty
    assert theme.archive_size > 0


def test_catalog_archive_checksum(plugins_dir):
    """Test that archive checksum is correct."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()

    entry = catalog.get_entry("test-theme")
    archive = catalog.get_archive("test-theme")
    assert archive is not None

    actual_sha256 = hashlib.sha256(archive).hexdigest()
    assert actual_sha256 == entry.archive_sha256


def test_catalog_archive_is_valid_tarball(plugins_dir):
    """Test that the archive is a valid tar.gz file."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()

    archive = catalog.get_archive("test-theme")
    buf = io.BytesIO(archive)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert any("manifest.yml" in n for n in names)
        assert any("main.css" in n for n in names)


def test_catalog_list_entries(plugins_dir):
    """Test listing entries with type filter."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()

    all_entries = catalog.list_entries()
    assert len(all_entries) == 2

    themes = catalog.list_entries(plugin_type="theme")
    assert len(themes) == 1
    assert themes[0].plugin_id == "test-theme"

    integrations = catalog.list_entries(plugin_type="integration")
    assert len(integrations) == 1
    assert integrations[0].plugin_id == "test-integration"

    views = catalog.list_entries(plugin_type="view")
    assert len(views) == 0


def test_catalog_to_dict(plugins_dir):
    """Test CatalogEntry serialization."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()

    entry = catalog.get_entry("test-theme")
    d = entry.to_dict()

    assert d["id"] == "test-theme"
    assert d["name"] == "Test Theme"
    assert d["version"] == "1.0.0"
    assert d["type"] == "theme"
    assert d["sha256"] == entry.archive_sha256
    assert d["archive_size"] == entry.archive_size
    assert "manifest" in d


def test_catalog_empty_dir():
    """Test catalog with empty directory."""
    with tempfile.TemporaryDirectory() as tmp:
        catalog = PluginCatalog(plugins_dir=Path(tmp))
        catalog.build()
        assert len(catalog.entries) == 0


def test_catalog_nonexistent_dir():
    """Test catalog with nonexistent directory."""
    catalog = PluginCatalog(plugins_dir=Path("/nonexistent"))
    catalog.build()
    assert len(catalog.entries) == 0


def test_catalog_invalid_manifest(tmp_path):
    """Test that invalid manifests are skipped."""
    # Plugin missing required fields
    bad_dir = tmp_path / "bad-plugin"
    bad_dir.mkdir()
    (bad_dir / "manifest.yml").write_text(yaml.dump({
        "id": "bad-plugin",
        "name": "Bad Plugin",
        # Missing version and type
    }))

    catalog = PluginCatalog(plugins_dir=tmp_path)
    catalog.build()
    assert len(catalog.entries) == 0


def test_catalog_invalid_plugin_id(tmp_path):
    """Test that invalid plugin IDs are rejected."""
    bad_dir = tmp_path / "BadPlugin"
    bad_dir.mkdir()
    (bad_dir / "manifest.yml").write_text(yaml.dump({
        "id": "Bad_Plugin",  # Invalid: uppercase and underscore
        "name": "Bad Plugin",
        "version": "1.0.0",
        "type": "view",
    }))

    catalog = PluginCatalog(plugins_dir=tmp_path)
    catalog.build()
    assert len(catalog.entries) == 0


def test_catalog_rebuild(plugins_dir):
    """Test that catalog can be rebuilt."""
    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()
    assert len(catalog.entries) == 2

    # Add a new plugin
    new_dir = plugins_dir / "new-plugin"
    new_dir.mkdir()
    (new_dir / "manifest.yml").write_text(yaml.dump({
        "id": "new-plugin",
        "name": "New Plugin",
        "version": "1.0.0",
        "type": "view",
    }))

    catalog.build()
    assert len(catalog.entries) == 3
    assert "new-plugin" in catalog.entries

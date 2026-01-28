"""Tests for plugin loader."""

from pathlib import Path

import pytest

from codex.plugins.loader import PluginLoader
from codex.plugins.models import ThemePlugin

# Get the repository root directory
REPO_ROOT = Path(__file__).parent.parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"


def test_plugin_loader_initialization():
    """Test plugin loader initialization."""
    loader = PluginLoader(PLUGINS_DIR)
    assert loader.plugins_dir == PLUGINS_DIR
    assert loader.plugins == {}


def test_discover_plugins():
    """Test plugin discovery."""
    loader = PluginLoader(PLUGINS_DIR)
    
    discovered = loader.discover_plugins()
    assert len(discovered) >= 4  # At least 4 built-in themes
    
    # Check that theme directories are discovered
    theme_names = [p.name for p in discovered]
    assert "cream" in theme_names or any("cream" in str(p) for p in discovered)


def test_load_theme_plugin():
    """Test loading a theme plugin."""
    loader = PluginLoader(PLUGINS_DIR)
    
    # Load cream theme
    theme_path = PLUGINS_DIR / "themes" / "cream"
    if theme_path.exists():
        plugin = loader.load_plugin(theme_path)
        
        assert isinstance(plugin, ThemePlugin)
        assert plugin.id == "cream"
        assert plugin.name == "Cream"
        assert plugin.type == "theme"
        assert plugin.version == "1.0.0"
        assert plugin.class_name == "theme-cream"


def test_load_all_plugins():
    """Test loading all plugins."""
    loader = PluginLoader(PLUGINS_DIR)
    
    plugins = loader.load_all_plugins()
    assert len(plugins) >= 4  # At least 4 built-in themes
    
    # Check that cream theme is loaded
    if "cream" in plugins:
        cream = plugins["cream"]
        assert cream.name == "Cream"
        assert cream.type == "theme"


def test_get_plugin():
    """Test getting a specific plugin."""
    loader = PluginLoader(PLUGINS_DIR)
    loader.load_all_plugins()
    
    # Get cream theme
    cream = loader.get_plugin("cream")
    if cream:
        assert isinstance(cream, ThemePlugin)
        assert cream.name == "Cream"


def test_get_plugins_by_type():
    """Test getting plugins by type."""
    loader = PluginLoader(PLUGINS_DIR)
    loader.load_all_plugins()
    
    # Get all themes
    themes = loader.get_plugins_by_type("theme")
    assert len(themes) >= 4  # At least 4 built-in themes
    assert all(isinstance(p, ThemePlugin) for p in themes)
    assert all(p.type == "theme" for p in themes)


def test_theme_plugin_properties():
    """Test theme plugin properties."""
    loader = PluginLoader(PLUGINS_DIR)
    
    # Load blueprint theme (dark theme)
    theme_path = PLUGINS_DIR / "themes" / "blueprint"
    if theme_path.exists():
        plugin = loader.load_plugin(theme_path)
        
        assert isinstance(plugin, ThemePlugin)
        assert plugin.id == "blueprint"
        assert plugin.category == "dark"
        assert plugin.stylesheet == "styles/main.css"
        assert plugin.class_name == "theme-blueprint"
        
        # Check colors are loaded
        assert isinstance(plugin.colors, dict)
        assert len(plugin.colors) > 0


def test_invalid_plugin_id():
    """Test validation of invalid plugin ID."""
    loader = PluginLoader(PLUGINS_DIR)
    
    # Create a test manifest with invalid ID
    manifest = {
        "id": "Invalid_ID",  # Contains uppercase and underscore
        "name": "Test",
        "version": "1.0.0",
        "type": "theme"
    }
    
    with pytest.raises(ValueError, match="Invalid plugin ID"):
        loader._validate_manifest(manifest, "theme")


def test_invalid_version():
    """Test validation of invalid version."""
    loader = PluginLoader(PLUGINS_DIR)
    
    # Create a test manifest with invalid version
    manifest = {
        "id": "test",
        "name": "Test",
        "version": "1.0",  # Not semver
        "type": "theme"
    }
    
    with pytest.raises(ValueError, match="Invalid version"):
        loader._validate_manifest(manifest, "theme")


def test_type_mismatch():
    """Test validation of type mismatch."""
    loader = PluginLoader(PLUGINS_DIR)
    
    # Create a test manifest with type mismatch
    manifest = {
        "id": "test",
        "name": "Test",
        "version": "1.0.0",
        "type": "view"
    }
    
    with pytest.raises(ValueError, match="Plugin type mismatch"):
        loader._validate_manifest(manifest, "theme")


def test_missing_required_field():
    """Test validation of missing required field."""
    loader = PluginLoader(PLUGINS_DIR)
    
    # Create a test manifest missing required field
    manifest = {
        "id": "test",
        "name": "Test",
        # Missing version
        "type": "theme"
    }
    
    with pytest.raises(ValueError, match="Missing required field"):
        loader._validate_manifest(manifest, "theme")

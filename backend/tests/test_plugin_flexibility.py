"""Tests for flexible plugin system that allows any plugin to expose themes, templates, and views."""

import tempfile
from pathlib import Path

import pytest
import yaml

from codex.plugins.loader import PluginLoader
from codex.plugins.models import IntegrationPlugin, Plugin


def test_integration_plugin_can_provide_theme():
    """Test that an integration plugin can provide theme configuration."""
    loader = PluginLoader(Path("/tmp/test_plugins"))
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(Path("/tmp/test_plugins/mixed"))
    
    # Verify it's an IntegrationPlugin
    assert isinstance(plugin, IntegrationPlugin)
    assert plugin.type == "integration"
    
    # Verify it has theme capabilities
    assert plugin.has_theme()
    assert plugin.theme_config
    assert plugin.display_name == "Mixed Theme"
    assert plugin.category == "dark"
    assert plugin.class_name == "theme-mixed"
    assert plugin.colors["bg-primary"] == "#1a1a1a"


def test_integration_plugin_can_provide_templates():
    """Test that an integration plugin can provide templates."""
    loader = PluginLoader(Path("/tmp/test_plugins"))
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(Path("/tmp/test_plugins/mixed"))
    
    # Verify it has template capabilities
    assert plugin.has_templates()
    assert len(plugin.templates) == 1
    assert plugin.templates[0]["id"] == "mixed-template"
    assert plugin.templates[0]["name"] == "Mixed Template"


def test_integration_plugin_can_provide_views():
    """Test that an integration plugin can provide views."""
    loader = PluginLoader(Path("/tmp/test_plugins"))
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(Path("/tmp/test_plugins/mixed"))
    
    # Verify it has view capabilities
    assert plugin.has_views()
    assert len(plugin.views) == 1
    assert plugin.views[0]["id"] == "mixed-view"
    assert plugin.views[0]["name"] == "Mixed View"


def test_integration_plugin_still_has_integration_capabilities():
    """Test that integration capabilities are still available."""
    loader = PluginLoader(Path("/tmp/test_plugins"))
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(Path("/tmp/test_plugins/mixed"))
    
    # Verify it still has integration capabilities
    assert plugin.has_integration()
    assert plugin.integration_config
    assert plugin.api_type == "rest"
    assert plugin.base_url == "https://api.example.com"
    assert len(plugin.endpoints) == 1
    assert len(plugin.properties) == 1


def test_get_plugins_with_themes_includes_all_types():
    """Test that get_plugins_with_themes returns plugins of any type with theme config."""
    loader = PluginLoader(Path("/tmp/test_plugins"))
    loader.load_plugin(Path("/tmp/test_plugins/mixed"))
    
    # Get all plugins with themes
    plugins_with_themes = loader.get_plugins_with_themes()
    
    # Should include the integration plugin that has theme config
    assert len(plugins_with_themes) >= 1
    mixed_plugin = next((p for p in plugins_with_themes if p.id == "test-mixed-integration"), None)
    assert mixed_plugin is not None
    assert mixed_plugin.type == "integration"


def test_get_plugins_with_templates_includes_all_types():
    """Test that get_plugins_with_templates returns plugins of any type with templates."""
    loader = PluginLoader(Path("/tmp/test_plugins"))
    loader.load_plugin(Path("/tmp/test_plugins/mixed"))
    
    # Get all plugins with templates
    plugins_with_templates = loader.get_plugins_with_templates()
    
    # Should include the integration plugin that has templates
    assert len(plugins_with_templates) >= 1
    mixed_plugin = next((p for p in plugins_with_templates if p.id == "test-mixed-integration"), None)
    assert mixed_plugin is not None
    assert mixed_plugin.type == "integration"


def test_get_plugins_with_views_includes_all_types():
    """Test that get_plugins_with_views returns plugins of any type with views."""
    loader = PluginLoader(Path("/tmp/test_plugins"))
    loader.load_plugin(Path("/tmp/test_plugins/mixed"))
    
    # Get all plugins with views
    plugins_with_views = loader.get_plugins_with_views()
    
    # Should include the integration plugin that has views
    assert len(plugins_with_views) >= 1
    mixed_plugin = next((p for p in plugins_with_views if p.id == "test-mixed-integration"), None)
    assert mixed_plugin is not None
    assert mixed_plugin.type == "integration"


def test_base_plugin_class_has_all_capabilities():
    """Test that the base Plugin class provides access to all capabilities."""
    # Create a simple plugin directly
    manifest = {
        "id": "test-base",
        "name": "Test Base",
        "version": "1.0.0",
        "type": "view",
        "theme": {"display_name": "Test Theme"},
        "templates": [{"id": "test-template"}],
        "views": [{"id": "test-view"}],
        "integration": {"api_type": "rest"},
    }
    
    plugin = Plugin(Path("/tmp"), manifest)
    
    # All capabilities should be available
    assert plugin.has_theme()
    assert plugin.has_templates()
    assert plugin.has_views()
    assert plugin.has_integration()
    
    # All properties should be accessible
    assert plugin.theme_config["display_name"] == "Test Theme"
    assert plugin.templates[0]["id"] == "test-template"
    assert plugin.views[0]["id"] == "test-view"
    assert plugin.integration_config["api_type"] == "rest"


def test_theme_plugin_can_have_templates():
    """Test that a theme plugin (by type) can also provide templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "test-theme"
        plugin_dir.mkdir()
        
        manifest = {
            "id": "test-theme",
            "name": "Test Theme",
            "version": "1.0.0",
            "type": "theme",
            "theme": {
                "display_name": "Test Theme",
                "category": "light",
            },
            "templates": [
                {"id": "theme-template", "name": "Theme Template"}
            ],
        }
        
        manifest_path = plugin_dir / "theme.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)
        
        loader = PluginLoader(Path(tmpdir))
        plugin = loader.load_plugin(plugin_dir)
        
        # Verify it's a theme with templates
        assert plugin.type == "theme"
        assert plugin.has_theme()
        assert plugin.has_templates()
        assert len(plugin.templates) == 1


def test_view_plugin_can_have_theme():
    """Test that a view plugin (by type) can also provide a theme."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "test-view"
        plugin_dir.mkdir()
        
        manifest = {
            "id": "test-view",
            "name": "Test View",
            "version": "1.0.0",
            "type": "view",
            "views": [
                {"id": "custom-view", "name": "Custom View"}
            ],
            "theme": {
                "display_name": "View Theme",
                "category": "dark",
            },
        }
        
        manifest_path = plugin_dir / "plugin.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)
        
        loader = PluginLoader(Path(tmpdir))
        plugin = loader.load_plugin(plugin_dir)
        
        # Verify it's a view with theme
        assert plugin.type == "view"
        assert plugin.has_views()
        assert plugin.has_theme()
        assert plugin.display_name == "View Theme"


def test_backward_compatibility_with_type_specific_classes():
    """Test that type-specific plugin classes still work for backward compatibility."""
    from codex.plugins.models import ThemePlugin, ViewPlugin, IntegrationPlugin
    
    # All type-specific classes should be subclasses of Plugin
    assert issubclass(ThemePlugin, Plugin)
    assert issubclass(ViewPlugin, Plugin)
    assert issubclass(IntegrationPlugin, Plugin)
    
    # They should have all capabilities
    theme_manifest = {
        "id": "test",
        "name": "Test",
        "version": "1.0.0",
        "type": "theme",
        "theme": {"display_name": "Test"},  # Non-empty theme config
        "templates": [{"id": "test"}],  # Non-empty templates
    }
    
    theme_plugin = ThemePlugin(Path("/tmp"), theme_manifest)
    assert theme_plugin.has_theme()
    assert theme_plugin.has_templates()  # Non-empty list


def test_plugin_without_capabilities():
    """Test plugin that doesn't provide any optional capabilities."""
    manifest = {
        "id": "minimal",
        "name": "Minimal",
        "version": "1.0.0",
        "type": "view",
    }
    
    plugin = Plugin(Path("/tmp"), manifest)
    
    # Should return False for all capability checks
    assert not plugin.has_theme()
    assert not plugin.has_templates()
    assert not plugin.has_views()
    assert not plugin.has_integration()
    
    # Should return empty lists/dicts
    assert plugin.templates == []
    assert plugin.views == []
    assert plugin.theme_config == {}
    assert plugin.integration_config == {}

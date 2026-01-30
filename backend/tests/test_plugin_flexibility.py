"""Tests for flexible plugin system that allows any plugin to expose themes, templates, and views."""

import tempfile
from pathlib import Path

import pytest
import yaml

from codex.plugins.loader import PluginLoader
from codex.plugins.models import IntegrationPlugin, Plugin


@pytest.fixture
def mixed_plugin_dir():
    """Create a temporary mixed integration plugin for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "mixed"
        plugin_dir.mkdir()
        templates_dir = plugin_dir / "templates"
        templates_dir.mkdir()
        
        # Create integration manifest with all capabilities
        manifest = {
            "id": "test-mixed-integration",
            "name": "Test Mixed Integration",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "Integration plugin that also provides theme and templates",
            "type": "integration",
            "integration": {
                "api_type": "rest",
                "base_url": "https://api.example.com",
                "auth_method": "api_key",
            },
            "theme": {
                "display_name": "Mixed Theme",
                "category": "dark",
                "className": "theme-mixed",
                "stylesheet": "styles/main.css",
            },
            "colors": {
                "bg-primary": "#1a1a1a",
                "text-primary": "#ffffff",
            },
            "templates": [
                {
                    "id": "mixed-template",
                    "name": "Mixed Template",
                    "file": "templates/test.yaml",
                    "description": "Template from integration plugin",
                    "icon": "🎨",
                    "default_name": "mixed.cdx",
                }
            ],
            "views": [
                {
                    "id": "mixed-view",
                    "name": "Mixed View",
                    "description": "View from integration plugin",
                    "icon": "👁️",
                }
            ],
            "properties": [
                {
                    "name": "api_key",
                    "type": "string",
                    "description": "API key",
                    "required": True,
                    "secure": True,
                }
            ],
            "endpoints": [
                {
                    "id": "test_endpoint",
                    "name": "Test Endpoint",
                    "method": "GET",
                    "path": "/test",
                }
            ],
            "permissions": ["network_request"],
        }
        
        manifest_path = plugin_dir / "integration.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)
        
        # Create template file
        template = {
            "id": "mixed-template",
            "name": "Mixed Template",
            "description": "Template from integration plugin",
            "content": "# Mixed Template\n\nThis is a test template.",
        }
        template_path = templates_dir / "test.yaml"
        with open(template_path, "w") as f:
            yaml.dump(template, f)
        
        yield Path(tmpdir)


def test_integration_plugin_can_provide_theme(mixed_plugin_dir):
    """Test that an integration plugin can provide theme configuration."""
    loader = PluginLoader(mixed_plugin_dir)
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(mixed_plugin_dir / "mixed")
    
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


def test_integration_plugin_can_provide_templates(mixed_plugin_dir):
    """Test that an integration plugin can provide templates."""
    loader = PluginLoader(mixed_plugin_dir)
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(mixed_plugin_dir / "mixed")
    
    # Verify it has template capabilities
    assert plugin.has_templates()
    assert len(plugin.templates) == 1
    assert plugin.templates[0]["id"] == "mixed-template"
    assert plugin.templates[0]["name"] == "Mixed Template"


def test_integration_plugin_can_provide_views(mixed_plugin_dir):
    """Test that an integration plugin can provide views."""
    loader = PluginLoader(mixed_plugin_dir)
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(mixed_plugin_dir / "mixed")
    
    # Verify it has view capabilities
    assert plugin.has_views()
    assert len(plugin.views) == 1
    assert plugin.views[0]["id"] == "mixed-view"
    assert plugin.views[0]["name"] == "Mixed View"


def test_integration_plugin_still_has_integration_capabilities(mixed_plugin_dir):
    """Test that integration capabilities are still available."""
    loader = PluginLoader(mixed_plugin_dir)
    
    # Load the mixed integration plugin
    plugin = loader.load_plugin(mixed_plugin_dir / "mixed")
    
    # Verify it still has integration capabilities
    assert plugin.has_integration()
    assert plugin.integration_config
    assert plugin.api_type == "rest"
    assert plugin.base_url == "https://api.example.com"
    assert len(plugin.endpoints) == 1
    assert len(plugin.properties) == 1


def test_get_plugins_with_themes_includes_all_types(mixed_plugin_dir):
    """Test that get_plugins_with_themes returns plugins of any type with theme config."""
    loader = PluginLoader(mixed_plugin_dir)
    plugin = loader.load_plugin(mixed_plugin_dir / "mixed")
    
    # Get all plugins with themes
    plugins_with_themes = loader.get_plugins_with_themes()
    
    # Should include the integration plugin that has theme config
    assert any(p.id == "test-mixed-integration" for p in plugins_with_themes), \
        "Mixed integration plugin with theme should be in results"
    
    mixed_plugin = next((p for p in plugins_with_themes if p.id == "test-mixed-integration"), None)
    assert mixed_plugin is not None
    assert mixed_plugin.type == "integration"


def test_get_plugins_with_templates_includes_all_types(mixed_plugin_dir):
    """Test that get_plugins_with_templates returns plugins of any type with templates."""
    loader = PluginLoader(mixed_plugin_dir)
    plugin = loader.load_plugin(mixed_plugin_dir / "mixed")
    
    # Get all plugins with templates
    plugins_with_templates = loader.get_plugins_with_templates()
    
    # Should include the integration plugin that has templates
    assert any(p.id == "test-mixed-integration" for p in plugins_with_templates), \
        "Mixed integration plugin with templates should be in results"
    
    mixed_plugin = next((p for p in plugins_with_templates if p.id == "test-mixed-integration"), None)
    assert mixed_plugin is not None
    assert mixed_plugin.type == "integration"


def test_get_plugins_with_views_includes_all_types(mixed_plugin_dir):
    """Test that get_plugins_with_views returns plugins of any type with views."""
    loader = PluginLoader(mixed_plugin_dir)
    plugin = loader.load_plugin(mixed_plugin_dir / "mixed")
    
    # Get all plugins with views
    plugins_with_views = loader.get_plugins_with_views()
    
    # Should include the integration plugin that has views
    assert any(p.id == "test-mixed-integration" for p in plugins_with_views), \
        "Mixed integration plugin with views should be in results"
    
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


def test_real_world_theme_with_templates():
    """Test that the manila theme plugin provides templates."""
    from pathlib import Path
    
    # Load the actual manila theme
    loader = PluginLoader(Path(__file__).parent.parent / "plugins")
    loader.load_all_plugins()
    
    manila = loader.get_plugin("manila")
    assert manila is not None, "Manila theme plugin should be loaded"
    
    # Verify it's a theme
    assert manila.type == "theme"
    assert manila.has_theme()
    
    # Verify it also has templates
    assert manila.has_templates()
    assert len(manila.templates) >= 1
    
    # Check the template details
    template_ids = [t["id"] for t in manila.templates]
    assert "manila-note" in template_ids


def test_real_world_integration_with_templates():
    """Test that the github integration plugin provides templates."""
    from pathlib import Path
    
    # Load the actual github integration
    loader = PluginLoader(Path(__file__).parent.parent / "plugins")
    loader.load_all_plugins()
    
    github = loader.get_plugin("github")
    assert github is not None, "GitHub integration plugin should be loaded"
    
    # Verify it's an integration
    assert github.type == "integration"
    assert github.has_integration()
    
    # Verify it also has templates
    assert github.has_templates()
    assert len(github.templates) >= 1
    
    # Check the template details
    template_ids = [t["id"] for t in github.templates]
    assert "github-issue-tracker" in template_ids


def test_get_plugins_with_templates_includes_theme_and_integration():
    """Test that capability-based filtering includes all plugin types."""
    from pathlib import Path
    
    loader = PluginLoader(Path(__file__).parent.parent / "plugins")
    loader.load_all_plugins()
    
    # Get all plugins with templates
    plugins_with_templates = loader.get_plugins_with_templates()
    
    # Should include templates from various plugin types
    plugin_types = {p.type for p in plugins_with_templates}
    
    # We should have at least view and theme plugins with templates
    # (and possibly integration if github is loaded)
    assert "view" in plugin_types  # e.g., tasks, gallery
    assert "theme" in plugin_types or "integration" in plugin_types  # manila or github

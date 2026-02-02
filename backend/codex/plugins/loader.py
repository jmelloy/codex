"""Plugin loader for discovering and loading plugins."""

import re
from pathlib import Path
from typing import Any

import yaml

from .models import IntegrationPlugin, Plugin, ThemePlugin, ViewPlugin


class PluginLoader:
    """Load and manage plugins."""

    def __init__(self, plugins_dir: Path):
        """Initialize plugin loader.

        Args:
            plugins_dir: Directory containing plugins
        """
        self.plugins_dir = Path(plugins_dir)
        self.plugins: dict[str, Plugin] = {}
        self._combined_manifest: dict[str, Any] | None = None

    def discover_plugins(self) -> list[Path]:
        """Discover all available plugins.

        Supports three discovery methods:
        1. Combined manifest.yml (new): plugins/manifest.yml with all plugins
        2. Flat structure: plugins/{plugin-name}/{manifest}.yaml
        3. Type-based structure (legacy): plugins/{type}/{plugin-name}/{manifest}.yaml

        Returns:
            List of plugin directory paths
        """
        plugins = []

        if not self.plugins_dir.exists():
            return plugins

        # Check for combined manifest.yml first
        combined_manifest_path = self.plugins_dir / "manifest.yml"
        if combined_manifest_path.exists():
            try:
                with open(combined_manifest_path) as f:
                    self._combined_manifest = yaml.safe_load(f)
                
                # Get plugin directories from combined manifest
                if self._combined_manifest and "plugins" in self._combined_manifest:
                    for plugin_data in self._combined_manifest["plugins"]:
                        # Use _directory if specified, otherwise use id
                        dir_name = plugin_data.get("_directory", plugin_data.get("id"))
                        if dir_name:
                            plugin_dir = self.plugins_dir / dir_name
                            if plugin_dir.exists():
                                plugins.append(plugin_dir)
                    
                    # If we found plugins in the combined manifest, return them
                    if plugins:
                        return plugins
            except Exception as e:
                print(f"Warning: Could not load combined manifest: {e}")
                # Fall through to individual file discovery

        # First, check for plugins in the flat structure (each subdirectory is a plugin)
        for item in self.plugins_dir.iterdir():
            if not item.is_dir():
                continue

            # Skip legacy type-specific directories (they'll be handled below)
            if item.name in ["views", "themes", "integrations"]:
                # Check for plugins in type-specific directories (legacy structure)
                for plugin_dir in item.iterdir():
                    if not plugin_dir.is_dir():
                        continue

                    manifest_path = plugin_dir / self._get_manifest_name(item.name)
                    if manifest_path.exists():
                        plugins.append(plugin_dir)
            else:
                # Flat structure: check for any manifest file directly in the directory
                for manifest_file in ["plugin.yaml", "theme.yaml", "integration.yaml"]:
                    manifest_path = item / manifest_file
                    if manifest_path.exists():
                        plugins.append(item)
                        break  # Only add once even if multiple manifests exist

        return plugins

    def load_plugin(self, plugin_path: Path | str) -> Plugin:
        """Load a plugin from a directory.

        Args:
            plugin_path: Path to plugin directory

        Returns:
            Loaded plugin instance

        Raises:
            ValueError: If manifest is invalid or missing
        """
        plugin_dir = Path(plugin_path)

        # First, try to get plugin data from combined manifest
        manifest_data = None
        plugin_type = None
        
        if self._combined_manifest and "plugins" in self._combined_manifest:
            # Look for this plugin in the combined manifest
            dir_name = plugin_dir.name
            for plugin_info in self._combined_manifest["plugins"]:
                plugin_dir_name = plugin_info.get("_directory", plugin_info.get("id"))
                if plugin_dir_name == dir_name:
                    manifest_data = plugin_info.copy()
                    # Remove internal fields
                    manifest_data.pop("_directory", None)
                    plugin_type = manifest_data.get("type")
                    break
        
        # If not found in combined manifest, load from individual file
        if not manifest_data:
            # Determine plugin type and load manifest
            manifest_files = {
                "plugin.yaml": "view",
                "theme.yaml": "theme",
                "integration.yaml": "integration",
            }

            for manifest_file, ptype in manifest_files.items():
                manifest_path = plugin_dir / manifest_file
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest_data = yaml.safe_load(f)
                    plugin_type = ptype
                    break

        if not manifest_data:
            raise ValueError(f"No valid manifest found in {plugin_dir}")

        # Validate manifest
        self._validate_manifest(manifest_data, plugin_type)

        # Create plugin instance
        if plugin_type == "view":
            plugin = ViewPlugin(plugin_dir, manifest_data)
        elif plugin_type == "theme":
            plugin = ThemePlugin(plugin_dir, manifest_data)
        elif plugin_type == "integration":
            plugin = IntegrationPlugin(plugin_dir, manifest_data)
        else:
            raise ValueError(f"Unknown plugin type: {plugin_type}")

        # Cache the plugin
        self.plugins[plugin.id] = plugin

        return plugin

    def load_all_plugins(self) -> dict[str, Plugin]:
        """Load all discovered plugins.

        Returns:
            Dictionary of plugin ID to plugin instance
        """
        plugin_paths = self.discover_plugins()
        for plugin_path in plugin_paths:
            try:
                self.load_plugin(plugin_path)
            except Exception as e:
                print(f"Error loading plugin from {plugin_path}: {e}")

        return self.plugins

    def get_plugin(self, plugin_id: str) -> Plugin | None:
        """Get a loaded plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_id)

    def get_plugins_by_type(self, plugin_type: str) -> list[Plugin]:
        """Get all plugins of a specific type.

        Args:
            plugin_type: Plugin type ('view', 'theme', 'integration')

        Returns:
            List of plugins of the specified type
        """
        return [p for p in self.plugins.values() if p.type == plugin_type]

    def get_plugins_with_themes(self) -> list[Plugin]:
        """Get all plugins that provide themes.
        
        This includes any plugin type that has theme configuration,
        not just ThemePlugin instances.

        Returns:
            List of plugins that provide themes
        """
        return [p for p in self.plugins.values() if p.has_theme()]

    def get_plugins_with_templates(self) -> list[Plugin]:
        """Get all plugins that provide templates.
        
        This includes any plugin type that has templates,
        not just ViewPlugin instances.

        Returns:
            List of plugins that provide templates
        """
        return [p for p in self.plugins.values() if p.has_templates()]

    def get_plugins_with_views(self) -> list[Plugin]:
        """Get all plugins that provide views.
        
        This includes any plugin type that has views,
        not just ViewPlugin instances.

        Returns:
            List of plugins that provide views
        """
        return [p for p in self.plugins.values() if p.has_views()]

    def get_plugins_with_integrations(self) -> list[Plugin]:
        """Get all plugins that provide integrations.
        
        This includes any plugin type that has integration configuration,
        not just IntegrationPlugin instances.

        Returns:
            List of plugins that provide integrations
        """
        return [p for p in self.plugins.values() if p.has_integration()]

    def _validate_manifest(self, manifest: dict[str, Any], plugin_type: str) -> None:
        """Validate plugin manifest.

        Args:
            manifest: Manifest data
            plugin_type: Expected plugin type

        Raises:
            ValueError: If manifest is invalid
        """
        required_fields = ["id", "name", "version", "type"]

        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Missing required field: {field}")

        # Validate plugin ID format
        if not re.match(r"^[a-z0-9-]+$", manifest["id"]):
            raise ValueError(
                f"Invalid plugin ID: {manifest['id']}. Must contain only lowercase letters, numbers, and hyphens."
            )

        # Validate version format
        if not re.match(r"^\d+\.\d+\.\d+$", manifest["version"]):
            raise ValueError(
                f"Invalid version: {manifest['version']}. Must be in semver format (e.g., 1.0.0)."
            )

        if manifest["type"] != plugin_type:
            raise ValueError(
                f"Plugin type mismatch: {manifest['type']} != {plugin_type}"
            )

    def _get_manifest_name(self, plugin_type: str) -> str:
        """Get manifest filename for plugin type.

        Args:
            plugin_type: Plugin type

        Returns:
            Manifest filename
        """
        return {
            "views": "plugin.yaml",
            "themes": "theme.yaml",
            "integrations": "integration.yaml",
        }[plugin_type]

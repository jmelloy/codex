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

    def discover_plugins(self) -> list[Path]:
        """Discover all available plugins.

        Returns:
            List of plugin directory paths
        """
        plugins = []

        # Check for plugins in type-specific directories
        for plugin_type in ["views", "themes", "integrations"]:
            type_dir = self.plugins_dir / plugin_type
            if not type_dir.exists():
                continue

            for plugin_dir in type_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue

                manifest_path = plugin_dir / self._get_manifest_name(plugin_type)
                if manifest_path.exists():
                    plugins.append(plugin_dir)

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

        # Determine plugin type and load manifest
        manifest_files = {
            "plugin.yaml": "view",
            "theme.yaml": "theme",
            "integration.yaml": "integration",
        }

        plugin_type = None
        manifest_data = None

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

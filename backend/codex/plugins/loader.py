"""Plugin loader for discovering and loading plugins."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .dependencies import (
    CircularDependencyError,
    DependencyError,
    DependencyResolver,
    PluginDependencyInfo,
)
from .models import IntegrationPlugin, Plugin, ThemePlugin, ViewPlugin
from .version import Version, check_codex_compatibility, get_codex_version

logger = logging.getLogger(__name__)


@dataclass
class PluginLoadResult:
    """Result of loading plugins with dependency information."""

    loaded: dict[str, Plugin] = field(default_factory=dict)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (path/id, error)
    load_order: list[str] = field(default_factory=list)
    incompatible: list[tuple[str, str]] = field(default_factory=list)  # (id, reason)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "loaded_count": len(self.loaded),
            "failed_count": len(self.failed),
            "load_order": self.load_order,
            "loaded": list(self.loaded.keys()),
            "failed": [{"path": p, "error": e} for p, e in self.failed],
            "incompatible": [{"plugin_id": p, "reason": r} for p, r in self.incompatible],
            "warnings": self.warnings,
        }


class PluginLoader:
    """Load and manage plugins with version and dependency support."""

    def __init__(self, plugins_dir: Path, validate_dependencies: bool = True):
        """Initialize plugin loader.

        Args:
            plugins_dir: Directory containing plugins
            validate_dependencies: Whether to validate dependencies (default: True)
        """
        self.plugins_dir = Path(plugins_dir)
        self.plugins: dict[str, Plugin] = {}
        self.validate_dependencies = validate_dependencies
        self._resolver: DependencyResolver | None = None
        self._load_result: PluginLoadResult | None = None

    @property
    def resolver(self) -> DependencyResolver:
        """Get or create the dependency resolver."""
        if self._resolver is None:
            self._resolver = DependencyResolver()
            self._resolver.add_plugins(self.plugins)
        return self._resolver

    def discover_plugins(self) -> list[Path]:
        """Discover all available plugins.

        Supports two directory structures:
        1. Flat structure (new): plugins/{plugin-name}/{manifest}.yaml
        2. Type-based structure (legacy): plugins/{type}/{plugin-name}/{manifest}.yaml

        Returns:
            List of plugin directory paths
        """
        plugins = []

        if not self.plugins_dir.exists():
            return plugins

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

    def load_plugin(self, plugin_path: Path | str, skip_codex_check: bool = False) -> Plugin:
        """Load a plugin from a directory.

        Args:
            plugin_path: Path to plugin directory
            skip_codex_check: Skip Codex version compatibility check

        Returns:
            Loaded plugin instance

        Raises:
            ValueError: If manifest is invalid or missing
            DependencyError: If Codex version is incompatible
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

        # Check Codex version compatibility
        if not skip_codex_check:
            codex_version = manifest_data.get("codex_version")
            if codex_version and not check_codex_compatibility(codex_version):
                from .dependencies import CodexVersionError

                raise CodexVersionError(
                    manifest_data["id"],
                    codex_version,
                    str(get_codex_version()),
                )

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

        # Invalidate resolver cache when plugins change
        self._resolver = None

        return plugin

    def load_all_plugins(
        self, respect_load_order: bool = True
    ) -> dict[str, Plugin]:
        """Load all discovered plugins with dependency resolution.

        Args:
            respect_load_order: Load plugins in dependency order (default: True)

        Returns:
            Dictionary of plugin ID to plugin instance
        """
        self._load_result = PluginLoadResult()
        plugin_paths = self.discover_plugins()

        # First pass: load all plugins (skip codex check for now to get full picture)
        temp_plugins: dict[str, Plugin] = {}
        path_to_id: dict[Path, str] = {}

        for plugin_path in plugin_paths:
            try:
                # Load without codex check first
                plugin = self._load_plugin_uncached(plugin_path)
                temp_plugins[plugin.id] = plugin
                path_to_id[plugin_path] = plugin.id
            except Exception as e:
                logger.warning(f"Error loading plugin from {plugin_path}: {e}")
                self._load_result.failed.append((str(plugin_path), str(e)))

        # Check Codex compatibility
        codex_version = get_codex_version()
        loadable_plugins: dict[str, Plugin] = {}

        for plugin_id, plugin in temp_plugins.items():
            if plugin.codex_version:
                if not check_codex_compatibility(plugin.codex_version):
                    reason = (
                        f"Requires Codex {plugin.codex_version}, "
                        f"but {codex_version} is installed"
                    )
                    self._load_result.incompatible.append((plugin_id, reason))
                    logger.warning(f"Plugin '{plugin_id}' incompatible: {reason}")
                    continue
            loadable_plugins[plugin_id] = plugin

        # Resolve dependencies if enabled
        if self.validate_dependencies and respect_load_order:
            resolver = DependencyResolver()
            resolver.add_plugins(loadable_plugins)

            try:
                load_order = resolver.get_load_order()
                self._load_result.load_order = load_order

                # Check which plugins can actually be loaded
                loadable, unloadable = resolver.get_loadable_plugins()

                for plugin_id, reason in unloadable:
                    self._load_result.incompatible.append((plugin_id, reason))
                    logger.warning(f"Plugin '{plugin_id}' cannot load: {reason}")

                # Only add plugins that can be loaded
                for plugin_id in load_order:
                    if plugin_id in loadable:
                        self.plugins[plugin_id] = loadable_plugins[plugin_id]

            except CircularDependencyError as e:
                # Log warning but still load plugins (without order guarantee)
                self._load_result.warnings.append(str(e))
                logger.warning(f"Circular dependency detected: {e}")
                self.plugins.update(loadable_plugins)
                self._load_result.load_order = list(loadable_plugins.keys())
        else:
            # No dependency validation - just load all compatible plugins
            self.plugins.update(loadable_plugins)
            self._load_result.load_order = list(loadable_plugins.keys())

        self._load_result.loaded = self.plugins.copy()
        self._resolver = None  # Reset resolver with new plugins

        return self.plugins

    def _load_plugin_uncached(self, plugin_path: Path) -> Plugin:
        """Load a plugin without caching it.

        Args:
            plugin_path: Path to plugin directory

        Returns:
            Plugin instance (not cached)
        """
        plugin_dir = Path(plugin_path)

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

        self._validate_manifest(manifest_data, plugin_type)

        if plugin_type == "view":
            return ViewPlugin(plugin_dir, manifest_data)
        elif plugin_type == "theme":
            return ThemePlugin(plugin_dir, manifest_data)
        elif plugin_type == "integration":
            return IntegrationPlugin(plugin_dir, manifest_data)
        else:
            raise ValueError(f"Unknown plugin type: {plugin_type}")

    def get_load_result(self) -> PluginLoadResult | None:
        """Get the result of the last load_all_plugins call.

        Returns:
            PluginLoadResult or None if load_all_plugins hasn't been called
        """
        return self._load_result

    def get_plugin(self, plugin_id: str) -> Plugin | None:
        """Get a loaded plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_id)

    def get_plugin_version(self, plugin_id: str) -> Version | None:
        """Get the version of a loaded plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Version object or None if plugin not found
        """
        plugin = self.plugins.get(plugin_id)
        if plugin:
            return plugin.parsed_version
        return None

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

    def get_plugin_dependencies(self, plugin_id: str) -> PluginDependencyInfo | None:
        """Get dependency information for a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginDependencyInfo or None if plugin not found
        """
        if plugin_id not in self.plugins:
            return None
        return self.resolver.check_plugin_dependencies(plugin_id)

    def get_all_dependency_info(self) -> dict[str, PluginDependencyInfo]:
        """Get dependency information for all loaded plugins.

        Returns:
            Dictionary of plugin ID to PluginDependencyInfo
        """
        return self.resolver.check_all_plugins()

    def get_dependency_tree(self, plugin_id: str) -> dict[str, Any] | None:
        """Get the full dependency tree for a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Nested dictionary representing the dependency tree, or None if not found
        """
        if plugin_id not in self.plugins:
            return None
        return self.resolver.get_dependency_tree(plugin_id)

    def can_disable_plugin(self, plugin_id: str) -> tuple[bool, list[str]]:
        """Check if a plugin can be disabled without breaking dependencies.

        Args:
            plugin_id: Plugin to check

        Returns:
            Tuple of (can_disable, list of plugins that would break)
        """
        return self.resolver.validate_can_disable(plugin_id)

    def get_load_order(self) -> list[str]:
        """Get the order in which plugins should be loaded.

        Returns:
            List of plugin IDs in dependency order

        Raises:
            CircularDependencyError: If circular dependencies exist
        """
        return self.resolver.get_load_order()

    def check_circular_dependencies(self) -> list[list[str]]:
        """Check for circular dependencies among loaded plugins.

        Returns:
            List of cycles (each cycle is a list of plugin IDs)
        """
        return self.resolver.detect_circular_dependencies()

    def _validate_manifest(self, manifest: dict[str, Any], plugin_type: str) -> None:
        """Validate plugin manifest.

        Args:
            manifest: Manifest data
            plugin_type: Expected plugin type

        Raises:
            ValueError: If manifest is invalid
        """
        required_fields = ["id", "name", "version", "type"]

        for field_name in required_fields:
            if field_name not in manifest:
                raise ValueError(f"Missing required field: {field_name}")

        # Validate plugin ID format
        if not re.match(r"^[a-z0-9-]+$", manifest["id"]):
            raise ValueError(
                f"Invalid plugin ID: {manifest['id']}. Must contain only lowercase letters, numbers, and hyphens."
            )

        # Validate version format using Version parser
        try:
            Version.parse(manifest["version"])
        except ValueError:
            raise ValueError(
                f"Invalid version: {manifest['version']}. Must be in semver format (e.g., 1.0.0, 1.0.0-beta.1)."
            )

        if manifest["type"] != plugin_type:
            raise ValueError(
                f"Plugin type mismatch: {manifest['type']} != {plugin_type}"
            )

        # Validate codex_version constraint if present
        codex_version = manifest.get("codex_version")
        if codex_version:
            try:
                from .version import VersionConstraint

                VersionConstraint(codex_version)
            except ValueError as e:
                raise ValueError(f"Invalid codex_version constraint: {e}")

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

"""Plugin dependency resolution and validation.

This module provides functionality for:
- Parsing plugin dependencies from manifests
- Resolving dependencies between plugins
- Detecting circular dependencies
- Determining plugin load order
- Validating dependency satisfaction
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from .version import Dependency, Version, VersionConstraint, check_codex_compatibility

if TYPE_CHECKING:
    from .models import Plugin


class DependencyError(Exception):
    """Base exception for dependency-related errors."""

    pass


class DependencyNotFoundError(DependencyError):
    """A required dependency was not found."""

    def __init__(self, plugin_id: str, dependency_id: str):
        self.plugin_id = plugin_id
        self.dependency_id = dependency_id
        super().__init__(f"Plugin '{plugin_id}' requires '{dependency_id}' which is not installed")


class DependencyVersionError(DependencyError):
    """A dependency version constraint is not satisfied."""

    def __init__(
        self,
        plugin_id: str,
        dependency_id: str,
        required: str,
        actual: str,
    ):
        self.plugin_id = plugin_id
        self.dependency_id = dependency_id
        self.required = required
        self.actual = actual
        super().__init__(
            f"Plugin '{plugin_id}' requires '{dependency_id}' version {required}, "
            f"but version {actual} is installed"
        )


class CircularDependencyError(DependencyError):
    """A circular dependency was detected."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle + [cycle[0]])
        super().__init__(f"Circular dependency detected: {cycle_str}")


class CodexVersionError(DependencyError):
    """Plugin is incompatible with the current Codex version."""

    def __init__(self, plugin_id: str, required: str, actual: str):
        self.plugin_id = plugin_id
        self.required = required
        self.actual = actual
        super().__init__(
            f"Plugin '{plugin_id}' requires Codex version {required}, "
            f"but version {actual} is installed"
        )


class DependencyStatus(Enum):
    """Status of a dependency check."""

    SATISFIED = "satisfied"
    MISSING = "missing"
    VERSION_MISMATCH = "version_mismatch"
    OPTIONAL_MISSING = "optional_missing"


@dataclass
class DependencyCheckResult:
    """Result of checking a single dependency."""

    dependency: Dependency
    status: DependencyStatus
    installed_version: Version | None = None
    error_message: str | None = None

    @property
    def is_satisfied(self) -> bool:
        """Check if the dependency is satisfied (or optional and missing)."""
        return self.status in (DependencyStatus.SATISFIED, DependencyStatus.OPTIONAL_MISSING)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "plugin_id": self.dependency.plugin_id,
            "required_version": str(self.dependency.constraint),
            "optional": self.dependency.optional,
            "status": self.status.value,
            "installed_version": str(self.installed_version) if self.installed_version else None,
            "error": self.error_message,
            "satisfied": self.is_satisfied,
        }


@dataclass
class PluginDependencyInfo:
    """Complete dependency information for a plugin."""

    plugin_id: str
    plugin_version: Version
    codex_version_constraint: str | None
    codex_compatible: bool
    dependencies: list[DependencyCheckResult] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)  # Plugins that depend on this one

    @property
    def all_dependencies_satisfied(self) -> bool:
        """Check if all required dependencies are satisfied."""
        return all(dep.is_satisfied for dep in self.dependencies)

    @property
    def can_load(self) -> bool:
        """Check if the plugin can be loaded (codex compatible and deps satisfied)."""
        return self.codex_compatible and self.all_dependencies_satisfied

    @property
    def missing_dependencies(self) -> list[DependencyCheckResult]:
        """Get list of missing required dependencies."""
        return [
            dep
            for dep in self.dependencies
            if dep.status in (DependencyStatus.MISSING, DependencyStatus.VERSION_MISMATCH)
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "plugin_id": self.plugin_id,
            "plugin_version": str(self.plugin_version),
            "codex_version_constraint": self.codex_version_constraint,
            "codex_compatible": self.codex_compatible,
            "all_dependencies_satisfied": self.all_dependencies_satisfied,
            "can_load": self.can_load,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "dependents": self.dependents,
        }


class DependencyResolver:
    """Resolves and validates plugin dependencies."""

    def __init__(self):
        """Initialize the dependency resolver."""
        self._plugins: dict[str, Plugin] = {}
        self._dependency_graph: dict[str, set[str]] = {}
        self._reverse_graph: dict[str, set[str]] = {}

    def add_plugin(self, plugin: Plugin) -> None:
        """Add a plugin to the resolver.

        Args:
            plugin: Plugin to add
        """
        self._plugins[plugin.id] = plugin
        self._dependency_graph[plugin.id] = set()
        if plugin.id not in self._reverse_graph:
            self._reverse_graph[plugin.id] = set()

        # Build dependency graph
        for dep in plugin.dependencies:
            self._dependency_graph[plugin.id].add(dep.plugin_id)
            if dep.plugin_id not in self._reverse_graph:
                self._reverse_graph[dep.plugin_id] = set()
            self._reverse_graph[dep.plugin_id].add(plugin.id)

    def add_plugins(self, plugins: dict[str, Plugin]) -> None:
        """Add multiple plugins to the resolver.

        Args:
            plugins: Dictionary of plugin ID to Plugin
        """
        for plugin in plugins.values():
            self.add_plugin(plugin)

    def clear(self) -> None:
        """Clear all plugins from the resolver."""
        self._plugins.clear()
        self._dependency_graph.clear()
        self._reverse_graph.clear()

    def check_dependency(self, dependency: Dependency) -> DependencyCheckResult:
        """Check if a single dependency is satisfied.

        Args:
            dependency: Dependency to check

        Returns:
            DependencyCheckResult with status
        """
        plugin = self._plugins.get(dependency.plugin_id)

        if plugin is None:
            status = (
                DependencyStatus.OPTIONAL_MISSING if dependency.optional else DependencyStatus.MISSING
            )
            return DependencyCheckResult(
                dependency=dependency,
                status=status,
                error_message=f"Plugin '{dependency.plugin_id}' is not installed"
                if not dependency.optional
                else None,
            )

        installed_version = Version.parse(plugin.version)

        if not dependency.is_satisfied_by(installed_version):
            return DependencyCheckResult(
                dependency=dependency,
                status=DependencyStatus.VERSION_MISMATCH,
                installed_version=installed_version,
                error_message=(
                    f"Requires version {dependency.constraint}, "
                    f"but {installed_version} is installed"
                ),
            )

        return DependencyCheckResult(
            dependency=dependency,
            status=DependencyStatus.SATISFIED,
            installed_version=installed_version,
        )

    def check_plugin_dependencies(self, plugin_id: str) -> PluginDependencyInfo:
        """Check all dependencies for a plugin.

        Args:
            plugin_id: Plugin ID to check

        Returns:
            PluginDependencyInfo with complete dependency status

        Raises:
            KeyError: If plugin is not found
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise KeyError(f"Plugin '{plugin_id}' not found")

        plugin_version = Version.parse(plugin.version)
        codex_constraint = plugin.codex_version
        codex_compatible = check_codex_compatibility(codex_constraint) if codex_constraint else True

        dependency_results = [self.check_dependency(dep) for dep in plugin.dependencies]

        # Get plugins that depend on this one
        dependents = list(self._reverse_graph.get(plugin_id, set()))

        return PluginDependencyInfo(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            codex_version_constraint=codex_constraint,
            codex_compatible=codex_compatible,
            dependencies=dependency_results,
            dependents=dependents,
        )

    def check_all_plugins(self) -> dict[str, PluginDependencyInfo]:
        """Check dependencies for all plugins.

        Returns:
            Dictionary of plugin ID to PluginDependencyInfo
        """
        return {plugin_id: self.check_plugin_dependencies(plugin_id) for plugin_id in self._plugins}

    def detect_circular_dependencies(self) -> list[list[str]]:
        """Detect all circular dependencies.

        Returns:
            List of cycles (each cycle is a list of plugin IDs)
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._dependency_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    cycles.append(cycle.copy())

            path.pop()
            rec_stack.remove(node)

        for node in self._plugins:
            if node not in visited:
                dfs(node)

        return cycles

    def get_load_order(self) -> list[str]:
        """Get the order in which plugins should be loaded.

        Uses topological sort to ensure dependencies are loaded first.

        Returns:
            List of plugin IDs in load order

        Raises:
            CircularDependencyError: If a circular dependency is detected
        """
        # Kahn's algorithm for topological sort
        in_degree: dict[str, int] = {plugin_id: 0 for plugin_id in self._plugins}

        # Calculate in-degrees (number of dependencies)
        for plugin_id, deps in self._dependency_graph.items():
            for dep_id in deps:
                if dep_id in in_degree:
                    in_degree[plugin_id] += 1

        # Start with plugins that have no dependencies
        queue = [plugin_id for plugin_id, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            # Sort to ensure deterministic order
            queue.sort()
            node = queue.pop(0)
            result.append(node)

            # Reduce in-degree for plugins that depend on this one
            for dependent in self._reverse_graph.get(node, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # If we didn't process all plugins, there's a cycle
        if len(result) != len(self._plugins):
            # Find the cycle
            remaining = set(self._plugins.keys()) - set(result)
            # Try to find a specific cycle for error message
            cycles = self.detect_circular_dependencies()
            if cycles:
                raise CircularDependencyError(cycles[0])
            else:
                raise CircularDependencyError(list(remaining))

        return result

    def get_loadable_plugins(self) -> tuple[list[str], list[tuple[str, str]]]:
        """Get plugins that can be loaded and reasons for those that can't.

        Returns:
            Tuple of (loadable_plugin_ids, [(unloadable_id, reason), ...])
        """
        loadable: list[str] = []
        unloadable: list[tuple[str, str]] = []

        for plugin_id in self._plugins:
            info = self.check_plugin_dependencies(plugin_id)
            if info.can_load:
                loadable.append(plugin_id)
            else:
                reasons = []
                if not info.codex_compatible:
                    reasons.append(
                        f"Requires Codex version {info.codex_version_constraint}"
                    )
                for dep in info.missing_dependencies:
                    reasons.append(dep.error_message or f"Missing dependency: {dep.dependency.plugin_id}")
                unloadable.append((plugin_id, "; ".join(reasons)))

        # Sort loadable plugins by load order if possible
        try:
            load_order = self.get_load_order()
            loadable = [p for p in load_order if p in loadable]
        except CircularDependencyError:
            pass  # Keep original order if there's a cycle

        return loadable, unloadable

    def validate_can_disable(self, plugin_id: str) -> tuple[bool, list[str]]:
        """Check if a plugin can be disabled without breaking others.

        Args:
            plugin_id: Plugin to potentially disable

        Returns:
            Tuple of (can_disable, [dependent_plugin_ids])
        """
        dependents = list(self._reverse_graph.get(plugin_id, set()))

        # Filter to only non-optional dependents
        required_by: list[str] = []
        for dep_id in dependents:
            plugin = self._plugins.get(dep_id)
            if plugin:
                for dep in plugin.dependencies:
                    if dep.plugin_id == plugin_id and not dep.optional:
                        required_by.append(dep_id)
                        break

        return len(required_by) == 0, required_by

    def get_dependency_tree(self, plugin_id: str, max_depth: int = 10) -> dict[str, Any]:
        """Get the full dependency tree for a plugin.

        Args:
            plugin_id: Root plugin ID
            max_depth: Maximum depth to traverse

        Returns:
            Nested dictionary representing the dependency tree
        """

        def build_tree(pid: str, depth: int, visited: set[str]) -> dict[str, Any]:
            if depth > max_depth or pid in visited:
                return {"id": pid, "circular": pid in visited, "truncated": depth > max_depth}

            visited = visited | {pid}  # Create new set to avoid mutation
            plugin = self._plugins.get(pid)

            if plugin is None:
                return {"id": pid, "missing": True}

            deps = []
            for dep in plugin.dependencies:
                child_tree = build_tree(dep.plugin_id, depth + 1, visited)
                child_tree["optional"] = dep.optional
                child_tree["version_constraint"] = str(dep.constraint)
                deps.append(child_tree)

            return {
                "id": pid,
                "version": plugin.version,
                "dependencies": deps,
            }

        return build_tree(plugin_id, 0, set())


def parse_dependencies(manifest: dict[str, Any]) -> list[Dependency]:
    """Parse dependencies from a plugin manifest.

    Supports multiple formats:
    - List of strings: ["plugin-a", "plugin-b@>=1.0.0"]
    - List of dicts: [{"plugin_id": "plugin-a", "version": ">=1.0.0"}]
    - Dict format: {"plugin-a": ">=1.0.0", "plugin-b": "^2.0.0"}

    Args:
        manifest: Plugin manifest dictionary

    Returns:
        List of Dependency objects
    """
    deps_raw = manifest.get("dependencies", [])

    if not deps_raw:
        return []

    dependencies: list[Dependency] = []

    if isinstance(deps_raw, dict):
        # Dict format: {"plugin-id": "version-constraint"}
        for plugin_id, version in deps_raw.items():
            if isinstance(version, dict):
                # Nested dict format with optional flag
                version_str = version.get("version", "*")
                optional = version.get("optional", False)
                dependencies.append(
                    Dependency(
                        plugin_id=plugin_id,
                        constraint=VersionConstraint(version_str),
                        optional=optional,
                    )
                )
            else:
                dependencies.append(
                    Dependency(
                        plugin_id=plugin_id,
                        constraint=VersionConstraint(str(version)),
                        optional=False,
                    )
                )
    elif isinstance(deps_raw, list):
        for dep in deps_raw:
            dependencies.append(Dependency.parse(dep))

    return dependencies

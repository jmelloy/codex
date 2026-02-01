"""Tests for plugin versioning and dependency resolution."""

from pathlib import Path

import pytest

from codex.plugins.dependencies import (
    CircularDependencyError,
    DependencyNotFoundError,
    DependencyResolver,
    DependencyStatus,
    DependencyVersionError,
    parse_dependencies,
)
from codex.plugins.loader import PluginLoader
from codex.plugins.models import Plugin
from codex.plugins.version import (
    CODEX_VERSION,
    Dependency,
    Version,
    VersionConstraint,
    check_codex_compatibility,
    get_codex_version,
)

# Get the plugins directory at repository root
BACKEND_DIR = Path(__file__).parent.parent
PLUGINS_DIR = BACKEND_DIR.parent / "plugins"


# ============================================================================
# Version Parsing Tests
# ============================================================================


class TestVersionParsing:
    """Tests for semantic version parsing."""

    def test_parse_basic_version(self):
        """Test parsing a basic version string."""
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None
        assert v.build is None

    def test_parse_version_with_v_prefix(self):
        """Test parsing a version string with 'v' prefix."""
        v = Version.parse("v1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_version_with_prerelease(self):
        """Test parsing a version string with prerelease."""
        v = Version.parse("1.0.0-alpha")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha"

        v = Version.parse("1.0.0-beta.1")
        assert v.prerelease == "beta.1"

    def test_parse_version_with_build(self):
        """Test parsing a version string with build metadata."""
        v = Version.parse("1.0.0+build.123")
        assert v.major == 1
        assert v.build == "build.123"

    def test_parse_version_with_prerelease_and_build(self):
        """Test parsing a version string with prerelease and build."""
        v = Version.parse("1.0.0-rc.1+build.456")
        assert v.prerelease == "rc.1"
        assert v.build == "build.456"

    def test_parse_invalid_version(self):
        """Test parsing an invalid version string."""
        with pytest.raises(ValueError):
            Version.parse("invalid")

        with pytest.raises(ValueError):
            Version.parse("1.0")  # Missing patch

        with pytest.raises(ValueError):
            Version.parse("1.0.0.0")  # Too many parts

    def test_version_string_representation(self):
        """Test version string representation."""
        assert str(Version(1, 2, 3)) == "1.2.3"
        assert str(Version(1, 0, 0, "alpha")) == "1.0.0-alpha"
        assert str(Version(1, 0, 0, None, "build.1")) == "1.0.0+build.1"
        assert str(Version(1, 0, 0, "rc.1", "build.1")) == "1.0.0-rc.1+build.1"


# ============================================================================
# Version Comparison Tests
# ============================================================================


class TestVersionComparison:
    """Tests for version comparison."""

    def test_version_equality(self):
        """Test version equality."""
        assert Version(1, 2, 3) == Version(1, 2, 3)
        assert Version(1, 0, 0, "alpha") == Version(1, 0, 0, "alpha")

    def test_version_inequality(self):
        """Test version inequality."""
        assert Version(1, 2, 3) != Version(1, 2, 4)
        assert Version(1, 0, 0) != Version(1, 0, 0, "alpha")

    def test_version_less_than(self):
        """Test version less than comparison."""
        assert Version(1, 0, 0) < Version(2, 0, 0)
        assert Version(1, 0, 0) < Version(1, 1, 0)
        assert Version(1, 0, 0) < Version(1, 0, 1)

    def test_prerelease_ordering(self):
        """Test prerelease version ordering."""
        # Prerelease versions have lower precedence
        assert Version(1, 0, 0, "alpha") < Version(1, 0, 0)
        assert Version(1, 0, 0, "alpha") < Version(1, 0, 0, "beta")
        assert Version(1, 0, 0, "alpha.1") < Version(1, 0, 0, "alpha.2")

    def test_version_sorting(self):
        """Test sorting versions."""
        versions = [
            Version(1, 0, 0),
            Version(1, 0, 0, "alpha"),
            Version(0, 9, 0),
            Version(1, 0, 0, "beta"),
            Version(2, 0, 0),
        ]
        sorted_versions = sorted(versions)
        assert sorted_versions[0] == Version(0, 9, 0)
        assert sorted_versions[1] == Version(1, 0, 0, "alpha")
        assert sorted_versions[2] == Version(1, 0, 0, "beta")
        assert sorted_versions[3] == Version(1, 0, 0)
        assert sorted_versions[4] == Version(2, 0, 0)

    def test_version_bump(self):
        """Test version bumping."""
        v = Version(1, 2, 3)
        assert v.bump_major() == Version(2, 0, 0)
        assert v.bump_minor() == Version(1, 3, 0)
        assert v.bump_patch() == Version(1, 2, 4)


# ============================================================================
# Version Constraint Tests
# ============================================================================


class TestVersionConstraints:
    """Tests for version constraints."""

    def test_exact_constraint(self):
        """Test exact version constraint."""
        c = VersionConstraint("1.0.0")
        assert c.matches("1.0.0")
        assert not c.matches("1.0.1")
        assert not c.matches("0.9.9")

    def test_greater_than_constraint(self):
        """Test greater than constraint."""
        c = VersionConstraint(">1.0.0")
        assert c.matches("1.0.1")
        assert c.matches("2.0.0")
        assert not c.matches("1.0.0")
        assert not c.matches("0.9.9")

    def test_greater_than_or_equal_constraint(self):
        """Test greater than or equal constraint."""
        c = VersionConstraint(">=1.0.0")
        assert c.matches("1.0.0")
        assert c.matches("1.0.1")
        assert c.matches("2.0.0")
        assert not c.matches("0.9.9")

    def test_less_than_constraint(self):
        """Test less than constraint."""
        c = VersionConstraint("<2.0.0")
        assert c.matches("1.0.0")
        assert c.matches("1.9.9")
        assert not c.matches("2.0.0")
        assert not c.matches("2.0.1")

    def test_less_than_or_equal_constraint(self):
        """Test less than or equal constraint."""
        c = VersionConstraint("<=2.0.0")
        assert c.matches("1.0.0")
        assert c.matches("2.0.0")
        assert not c.matches("2.0.1")

    def test_caret_constraint(self):
        """Test caret (compatible) constraint."""
        # ^1.2.3 means >=1.2.3, <2.0.0
        c = VersionConstraint("^1.2.3")
        assert c.matches("1.2.3")
        assert c.matches("1.9.9")
        assert not c.matches("1.2.2")
        assert not c.matches("2.0.0")

        # ^0.2.3 means >=0.2.3, <0.3.0
        c = VersionConstraint("^0.2.3")
        assert c.matches("0.2.3")
        assert c.matches("0.2.9")
        assert not c.matches("0.3.0")

    def test_tilde_constraint(self):
        """Test tilde (approximately) constraint."""
        # ~1.2.3 means >=1.2.3, <1.3.0
        c = VersionConstraint("~1.2.3")
        assert c.matches("1.2.3")
        assert c.matches("1.2.9")
        assert not c.matches("1.3.0")
        assert not c.matches("1.2.2")

    def test_wildcard_constraint(self):
        """Test wildcard constraint."""
        # 1.x means >=1.0.0, <2.0.0
        c = VersionConstraint("1.x")
        assert c.matches("1.0.0")
        assert c.matches("1.9.9")
        assert not c.matches("2.0.0")

        # 1.2.x means >=1.2.0, <1.3.0
        c = VersionConstraint("1.2.x")
        assert c.matches("1.2.0")
        assert c.matches("1.2.9")
        assert not c.matches("1.3.0")

    def test_range_constraint(self):
        """Test range constraint."""
        c = VersionConstraint(">=1.0.0,<2.0.0")
        assert c.matches("1.0.0")
        assert c.matches("1.9.9")
        assert not c.matches("0.9.9")
        assert not c.matches("2.0.0")

    def test_any_constraint(self):
        """Test any version constraint."""
        c = VersionConstraint("*")
        assert c.matches("0.0.1")
        assert c.matches("99.99.99")


# ============================================================================
# Dependency Parsing Tests
# ============================================================================


class TestDependencyParsing:
    """Tests for dependency parsing."""

    def test_parse_string_dependency(self):
        """Test parsing a string dependency."""
        dep = Dependency.parse("plugin-a")
        assert dep.plugin_id == "plugin-a"
        assert dep.constraint.matches("1.0.0")  # * matches anything

    def test_parse_string_dependency_with_version(self):
        """Test parsing a string dependency with version."""
        dep = Dependency.parse("plugin-a@>=1.0.0")
        assert dep.plugin_id == "plugin-a"
        assert dep.constraint.matches("1.0.0")
        assert not dep.constraint.matches("0.9.9")

    def test_parse_dict_dependency(self):
        """Test parsing a dict dependency."""
        dep = Dependency.parse({
            "plugin_id": "plugin-a",
            "version": ">=1.0.0",
            "optional": True,
        })
        assert dep.plugin_id == "plugin-a"
        assert dep.optional is True
        assert dep.constraint.matches("1.0.0")

    def test_parse_dependencies_from_manifest(self):
        """Test parsing dependencies from manifest."""
        # Dict format
        manifest = {
            "dependencies": {
                "plugin-a": ">=1.0.0",
                "plugin-b": "^2.0.0",
            }
        }
        deps = parse_dependencies(manifest)
        assert len(deps) == 2
        assert deps[0].plugin_id == "plugin-a"
        assert deps[1].plugin_id == "plugin-b"

        # List format
        manifest = {
            "dependencies": [
                "plugin-a@>=1.0.0",
                {"plugin_id": "plugin-b", "version": "^2.0.0"},
            ]
        }
        deps = parse_dependencies(manifest)
        assert len(deps) == 2


# ============================================================================
# Dependency Resolver Tests
# ============================================================================


class TestDependencyResolver:
    """Tests for dependency resolution."""

    def create_test_plugin(self, plugin_id: str, version: str, deps: dict = None) -> Plugin:
        """Create a test plugin."""
        manifest = {
            "id": plugin_id,
            "name": plugin_id.title(),
            "version": version,
            "type": "view",
        }
        if deps:
            manifest["dependencies"] = deps
        return Plugin(Path("/test"), manifest)

    def test_add_plugins(self):
        """Test adding plugins to resolver."""
        resolver = DependencyResolver()
        plugin_a = self.create_test_plugin("plugin-a", "1.0.0")
        resolver.add_plugin(plugin_a)
        assert "plugin-a" in resolver._plugins

    def test_check_satisfied_dependency(self):
        """Test checking a satisfied dependency."""
        resolver = DependencyResolver()
        plugin_a = self.create_test_plugin("plugin-a", "1.0.0")
        plugin_b = self.create_test_plugin("plugin-b", "1.0.0", {"plugin-a": ">=1.0.0"})
        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)

        info = resolver.check_plugin_dependencies("plugin-b")
        assert info.all_dependencies_satisfied
        assert info.can_load

    def test_check_missing_dependency(self):
        """Test checking a missing dependency."""
        resolver = DependencyResolver()
        plugin_b = self.create_test_plugin("plugin-b", "1.0.0", {"plugin-a": ">=1.0.0"})
        resolver.add_plugin(plugin_b)

        info = resolver.check_plugin_dependencies("plugin-b")
        assert not info.all_dependencies_satisfied
        assert len(info.missing_dependencies) == 1
        assert info.missing_dependencies[0].dependency.plugin_id == "plugin-a"

    def test_check_version_mismatch(self):
        """Test checking a version mismatch."""
        resolver = DependencyResolver()
        plugin_a = self.create_test_plugin("plugin-a", "0.9.0")
        plugin_b = self.create_test_plugin("plugin-b", "1.0.0", {"plugin-a": ">=1.0.0"})
        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)

        info = resolver.check_plugin_dependencies("plugin-b")
        assert not info.all_dependencies_satisfied
        assert info.missing_dependencies[0].status == DependencyStatus.VERSION_MISMATCH

    def test_optional_dependency_missing(self):
        """Test optional dependency missing."""
        resolver = DependencyResolver()
        manifest = {
            "id": "plugin-b",
            "name": "Plugin B",
            "version": "1.0.0",
            "type": "view",
            "dependencies": [
                {"plugin_id": "plugin-a", "version": ">=1.0.0", "optional": True}
            ],
        }
        plugin_b = Plugin(Path("/test"), manifest)
        resolver.add_plugin(plugin_b)

        info = resolver.check_plugin_dependencies("plugin-b")
        assert info.all_dependencies_satisfied  # Optional deps don't block
        assert info.can_load

    def test_load_order(self):
        """Test determining plugin load order."""
        resolver = DependencyResolver()
        plugin_a = self.create_test_plugin("plugin-a", "1.0.0")
        plugin_b = self.create_test_plugin("plugin-b", "1.0.0", {"plugin-a": ">=1.0.0"})
        plugin_c = self.create_test_plugin("plugin-c", "1.0.0", {"plugin-b": ">=1.0.0"})

        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)
        resolver.add_plugin(plugin_c)

        order = resolver.get_load_order()
        assert order.index("plugin-a") < order.index("plugin-b")
        assert order.index("plugin-b") < order.index("plugin-c")

    def test_circular_dependency_detection(self):
        """Test detecting circular dependencies."""
        resolver = DependencyResolver()
        plugin_a = self.create_test_plugin("plugin-a", "1.0.0", {"plugin-b": ">=1.0.0"})
        plugin_b = self.create_test_plugin("plugin-b", "1.0.0", {"plugin-a": ">=1.0.0"})

        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)

        cycles = resolver.detect_circular_dependencies()
        assert len(cycles) > 0

        with pytest.raises(CircularDependencyError):
            resolver.get_load_order()

    def test_can_disable_plugin(self):
        """Test checking if plugin can be disabled."""
        resolver = DependencyResolver()
        plugin_a = self.create_test_plugin("plugin-a", "1.0.0")
        plugin_b = self.create_test_plugin("plugin-b", "1.0.0", {"plugin-a": ">=1.0.0"})

        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)

        can_disable, dependents = resolver.validate_can_disable("plugin-a")
        assert not can_disable
        assert "plugin-b" in dependents

        can_disable, dependents = resolver.validate_can_disable("plugin-b")
        assert can_disable
        assert len(dependents) == 0

    def test_dependency_tree(self):
        """Test getting dependency tree."""
        resolver = DependencyResolver()
        plugin_a = self.create_test_plugin("plugin-a", "1.0.0")
        plugin_b = self.create_test_plugin("plugin-b", "1.0.0", {"plugin-a": ">=1.0.0"})
        plugin_c = self.create_test_plugin("plugin-c", "1.0.0", {"plugin-b": ">=1.0.0"})

        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)
        resolver.add_plugin(plugin_c)

        tree = resolver.get_dependency_tree("plugin-c")
        assert tree["id"] == "plugin-c"
        assert len(tree["dependencies"]) == 1
        assert tree["dependencies"][0]["id"] == "plugin-b"
        assert len(tree["dependencies"][0]["dependencies"]) == 1
        assert tree["dependencies"][0]["dependencies"][0]["id"] == "plugin-a"


# ============================================================================
# Codex Version Compatibility Tests
# ============================================================================


class TestCodexCompatibility:
    """Tests for Codex version compatibility checking."""

    def test_get_codex_version(self):
        """Test getting Codex version."""
        version = get_codex_version()
        assert isinstance(version, Version)
        assert version == CODEX_VERSION

    def test_check_compatible_version(self):
        """Test checking compatible Codex version."""
        assert check_codex_compatibility(">=1.0.0")
        assert check_codex_compatibility(f">={CODEX_VERSION}")

    def test_check_empty_constraint(self):
        """Test checking empty constraint."""
        assert check_codex_compatibility("")
        assert check_codex_compatibility(None)


# ============================================================================
# Plugin Loader Integration Tests
# ============================================================================


class TestPluginLoaderVersioning:
    """Tests for PluginLoader versioning integration."""

    def test_load_plugins_with_dependencies(self):
        """Test loading plugins with dependencies."""
        loader = PluginLoader(PLUGINS_DIR)
        plugins = loader.load_all_plugins()

        # Tasks depends on core
        if "tasks" in plugins and "core" in plugins:
            tasks = plugins["tasks"]
            assert tasks.has_dependencies
            assert "core" in tasks.dependency_ids

            # Check dependency info
            info = loader.get_plugin_dependencies("tasks")
            assert info is not None
            assert info.all_dependencies_satisfied

    def test_get_load_order(self):
        """Test getting plugin load order."""
        loader = PluginLoader(PLUGINS_DIR)
        loader.load_all_plugins()

        order = loader.get_load_order()
        assert len(order) > 0

        # Core should come before tasks (tasks depends on core)
        if "core" in order and "tasks" in order:
            assert order.index("core") < order.index("tasks")

    def test_get_load_result(self):
        """Test getting plugin load result."""
        loader = PluginLoader(PLUGINS_DIR)
        loader.load_all_plugins()

        result = loader.get_load_result()
        assert result is not None
        assert len(result.loaded) > 0
        assert isinstance(result.load_order, list)

    def test_plugin_codex_compatibility(self):
        """Test plugin Codex compatibility check."""
        loader = PluginLoader(PLUGINS_DIR)
        loader.load_all_plugins()

        for plugin in loader.plugins.values():
            if plugin.codex_version:
                # All loaded plugins should be compatible
                assert plugin.is_codex_compatible()

    def test_check_circular_dependencies(self):
        """Test checking for circular dependencies."""
        loader = PluginLoader(PLUGINS_DIR)
        loader.load_all_plugins()

        cycles = loader.check_circular_dependencies()
        # Should be no circular dependencies in built-in plugins
        assert len(cycles) == 0

    def test_can_disable_plugin(self):
        """Test checking if plugin can be disabled."""
        loader = PluginLoader(PLUGINS_DIR)
        loader.load_all_plugins()

        if "tasks" in loader.plugins:
            can_disable, dependents = loader.can_disable_plugin("tasks")
            # Tasks may or may not have dependents depending on loaded plugins

        if "core" in loader.plugins and "tasks" in loader.plugins:
            can_disable, dependents = loader.can_disable_plugin("core")
            # Core is depended on by tasks
            assert "tasks" in dependents

    def test_get_dependency_tree(self):
        """Test getting dependency tree."""
        loader = PluginLoader(PLUGINS_DIR)
        loader.load_all_plugins()

        if "tasks" in loader.plugins:
            tree = loader.get_dependency_tree("tasks")
            assert tree is not None
            assert tree["id"] == "tasks"

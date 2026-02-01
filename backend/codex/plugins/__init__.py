"""Plugin system for Codex."""

from .dependencies import (
    CircularDependencyError,
    CodexVersionError,
    DependencyCheckResult,
    DependencyError,
    DependencyNotFoundError,
    DependencyResolver,
    DependencyStatus,
    DependencyVersionError,
    PluginDependencyInfo,
    parse_dependencies,
)
from .loader import PluginLoadResult, PluginLoader
from .models import IntegrationPlugin, Plugin, ThemePlugin, ViewPlugin
from .version import (
    CODEX_VERSION,
    Dependency,
    Version,
    VersionConstraint,
    check_codex_compatibility,
    get_codex_version,
)

__all__ = [
    # Loader
    "PluginLoader",
    "PluginLoadResult",
    # Models
    "Plugin",
    "ViewPlugin",
    "ThemePlugin",
    "IntegrationPlugin",
    # Version
    "Version",
    "VersionConstraint",
    "Dependency",
    "CODEX_VERSION",
    "get_codex_version",
    "check_codex_compatibility",
    # Dependencies
    "DependencyResolver",
    "DependencyCheckResult",
    "DependencyStatus",
    "PluginDependencyInfo",
    "parse_dependencies",
    # Exceptions
    "DependencyError",
    "DependencyNotFoundError",
    "DependencyVersionError",
    "CircularDependencyError",
    "CodexVersionError",
]

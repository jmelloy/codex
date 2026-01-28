"""Plugin type classes."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Plugin:
    """Base plugin class."""

    plugin_dir: Path
    manifest: dict[str, Any]

    @property
    def id(self) -> str:
        """Get plugin ID."""
        return self.manifest["id"]

    @property
    def name(self) -> str:
        """Get plugin name."""
        return self.manifest["name"]

    @property
    def version(self) -> str:
        """Get plugin version."""
        return self.manifest["version"]

    @property
    def type(self) -> str:
        """Get plugin type."""
        return self.manifest["type"]

    @property
    def description(self) -> str:
        """Get plugin description."""
        return self.manifest.get("description", "")

    @property
    def author(self) -> str:
        """Get plugin author."""
        return self.manifest.get("author", "")


@dataclass
class ViewPlugin(Plugin):
    """View plugin with custom views and templates."""

    @property
    def properties(self) -> list[dict[str, Any]]:
        """Get custom properties defined by this plugin."""
        return self.manifest.get("properties", [])

    @property
    def views(self) -> list[dict[str, Any]]:
        """Get view types provided by this plugin."""
        return self.manifest.get("views", [])

    @property
    def templates(self) -> list[dict[str, Any]]:
        """Get templates provided by this plugin."""
        return self.manifest.get("templates", [])

    @property
    def examples(self) -> list[dict[str, Any]]:
        """Get example files provided by this plugin."""
        return self.manifest.get("examples", [])


@dataclass
class ThemePlugin(Plugin):
    """Theme plugin with CSS styling."""

    @property
    def theme_config(self) -> dict[str, Any]:
        """Get theme configuration."""
        return self.manifest.get("theme", {})

    @property
    def display_name(self) -> str:
        """Get theme display name."""
        return self.theme_config.get("display_name", self.name)

    @property
    def category(self) -> str:
        """Get theme category (light/dark)."""
        return self.theme_config.get("category", "light")

    @property
    def class_name(self) -> str:
        """Get CSS class name."""
        return self.theme_config.get("className", f"theme-{self.id}")

    @property
    def stylesheet(self) -> str:
        """Get main stylesheet path."""
        return self.theme_config.get("stylesheet", "styles/main.css")

    @property
    def additional_styles(self) -> list[str]:
        """Get additional stylesheet paths."""
        return self.theme_config.get("additional_styles", [])

    @property
    def colors(self) -> dict[str, str]:
        """Get color palette."""
        return self.manifest.get("colors", {})

    @property
    def preview_image(self) -> str | None:
        """Get preview image path."""
        return self.theme_config.get("preview")

    def get_stylesheet_path(self, relative_path: str) -> Path:
        """Get full path to a stylesheet."""
        return self.plugin_dir / relative_path


@dataclass
class IntegrationPlugin(Plugin):
    """Integration plugin with API connections."""

    @property
    def integration_config(self) -> dict[str, Any]:
        """Get integration configuration."""
        return self.manifest.get("integration", {})

    @property
    def api_type(self) -> str:
        """Get API type (rest, graphql, etc)."""
        return self.integration_config.get("api_type", "rest")

    @property
    def base_url(self) -> str | None:
        """Get base URL for API."""
        return self.integration_config.get("base_url")

    @property
    def auth_method(self) -> str | None:
        """Get authentication method."""
        return self.integration_config.get("auth_method")

    @property
    def properties(self) -> list[dict[str, Any]]:
        """Get configuration properties."""
        return self.manifest.get("properties", [])

    @property
    def blocks(self) -> list[dict[str, Any]]:
        """Get block types provided by this plugin."""
        return self.manifest.get("blocks", [])

    @property
    def endpoints(self) -> list[dict[str, Any]]:
        """Get API endpoints."""
        return self.manifest.get("endpoints", [])

    @property
    def settings_component(self) -> str | None:
        """Get settings component path."""
        return self.manifest.get("settings_component")

    @property
    def permissions(self) -> list[str]:
        """Get required permissions."""
        return self.manifest.get("permissions", [])

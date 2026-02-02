"""Plugin registry for database-stored plugins.

This module provides a PluginRegistry class that works with plugins
stored in the database rather than the filesystem. It provides a
similar interface to the filesystem-based PluginLoader but sources
plugin data from the database.
"""

from dataclasses import dataclass
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from codex.db.models import Plugin as PluginModel


@dataclass
class RegisteredPlugin:
    """A plugin loaded from the database registry.

    This class provides the same interface as the filesystem-based Plugin
    class but sources data from the database.
    """

    plugin_id: str
    name: str
    version: str
    type: str
    enabled: bool
    manifest: dict[str, Any]

    @property
    def id(self) -> str:
        """Get plugin ID."""
        return self.plugin_id

    @property
    def description(self) -> str:
        """Get plugin description."""
        return self.manifest.get("description", "")

    @property
    def author(self) -> str:
        """Get plugin author."""
        return self.manifest.get("author", "")

    # View/Template capabilities
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

    # Theme capabilities
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
    def colors(self) -> dict[str, str]:
        """Get color palette."""
        return self.manifest.get("colors", {})

    # Integration capabilities
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
    def blocks(self) -> list[dict[str, Any]]:
        """Get block types provided by this plugin."""
        return self.manifest.get("blocks", [])

    @property
    def endpoints(self) -> list[dict[str, Any]]:
        """Get API endpoints."""
        return self.manifest.get("endpoints", [])

    @property
    def test_endpoint(self) -> str | None:
        """Get the endpoint ID to use for testing connection.
        
        Returns the endpoint ID specified in integration.test_endpoint,
        or None to use the first endpoint.
        """
        return self.integration_config.get("test_endpoint")

    @property
    def permissions(self) -> list[str]:
        """Get required permissions."""
        return self.manifest.get("permissions", [])

    # Capability checks
    def has_theme(self) -> bool:
        """Check if this plugin provides a theme."""
        return bool(self.theme_config)

    def has_templates(self) -> bool:
        """Check if this plugin provides templates."""
        return bool(self.templates)

    def has_views(self) -> bool:
        """Check if this plugin provides views."""
        return bool(self.views)

    def has_integration(self) -> bool:
        """Check if this plugin provides an integration."""
        return bool(self.integration_config)


class PluginRegistry:
    """Registry for database-stored plugins.

    This class provides methods to query plugins from the database,
    similar to the filesystem-based PluginLoader but working with
    the database as the source of truth.
    """

    @staticmethod
    def _to_registered_plugin(db_plugin: PluginModel) -> RegisteredPlugin:
        """Convert a database Plugin model to a RegisteredPlugin.

        Args:
            db_plugin: Database plugin model

        Returns:
            RegisteredPlugin instance
        """
        return RegisteredPlugin(
            plugin_id=db_plugin.plugin_id,
            name=db_plugin.name,
            version=db_plugin.version,
            type=db_plugin.type,
            enabled=db_plugin.enabled,
            manifest=db_plugin.manifest or {},
        )

    @staticmethod
    async def get_plugin(
        session: AsyncSession, plugin_id: str
    ) -> RegisteredPlugin | None:
        """Get a plugin by ID.

        Args:
            session: Database session
            plugin_id: Plugin identifier

        Returns:
            RegisteredPlugin or None if not found
        """
        stmt = select(PluginModel).where(PluginModel.plugin_id == plugin_id)
        result = await session.execute(stmt)
        db_plugin = result.scalar_one_or_none()

        if not db_plugin:
            return None

        return PluginRegistry._to_registered_plugin(db_plugin)

    @staticmethod
    async def get_all_plugins(session: AsyncSession) -> list[RegisteredPlugin]:
        """Get all registered plugins.

        Args:
            session: Database session

        Returns:
            List of all registered plugins
        """
        stmt = select(PluginModel)
        result = await session.execute(stmt)
        db_plugins = result.scalars().all()

        return [PluginRegistry._to_registered_plugin(p) for p in db_plugins]

    @staticmethod
    async def get_plugins_by_type(
        session: AsyncSession, plugin_type: str
    ) -> list[RegisteredPlugin]:
        """Get all plugins of a specific type.

        Args:
            session: Database session
            plugin_type: Plugin type ('view', 'theme', 'integration')

        Returns:
            List of plugins of the specified type
        """
        stmt = select(PluginModel).where(PluginModel.type == plugin_type)
        result = await session.execute(stmt)
        db_plugins = result.scalars().all()

        return [PluginRegistry._to_registered_plugin(p) for p in db_plugins]

    @staticmethod
    async def get_plugins_with_integrations(
        session: AsyncSession,
    ) -> list[RegisteredPlugin]:
        """Get all plugins that provide integrations.

        This includes any plugin that has integration configuration,
        not just plugins of type 'integration'.

        Args:
            session: Database session

        Returns:
            List of plugins with integration capabilities
        """
        # First get all plugins, then filter by capability
        # (JSON querying varies by database, so we filter in Python)
        all_plugins = await PluginRegistry.get_all_plugins(session)
        return [p for p in all_plugins if p.has_integration()]

    @staticmethod
    async def get_plugins_with_views(session: AsyncSession) -> list[RegisteredPlugin]:
        """Get all plugins that provide views.

        Args:
            session: Database session

        Returns:
            List of plugins with view capabilities
        """
        all_plugins = await PluginRegistry.get_all_plugins(session)
        return [p for p in all_plugins if p.has_views()]

    @staticmethod
    async def get_plugins_with_themes(session: AsyncSession) -> list[RegisteredPlugin]:
        """Get all plugins that provide themes.

        Args:
            session: Database session

        Returns:
            List of plugins with theme capabilities
        """
        all_plugins = await PluginRegistry.get_all_plugins(session)
        return [p for p in all_plugins if p.has_theme()]

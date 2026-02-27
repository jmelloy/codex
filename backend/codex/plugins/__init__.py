"""Plugin system for Codex."""

from .loader import PluginLoader
from .models import IntegrationPlugin, Plugin, ThemePlugin, ViewPlugin

__all__ = [
    "PluginLoader",
    "Plugin",
    "ViewPlugin",
    "ThemePlugin",
    "IntegrationPlugin",
]

# Optional AWS components (only available when boto3 is installed)
try:
    from .dynamo_registry import DynamoPluginRegistry
    from .s3_client import S3PluginClient

    __all__ += ["DynamoPluginRegistry", "S3PluginClient"]
except ImportError:
    pass

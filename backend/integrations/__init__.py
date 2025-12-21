"""Integration system for Lab Notebook."""

# Import integrations to register them
from integrations import (
    api_call,  # noqa: F401
    comfyui,  # noqa: F401
    database_query,  # noqa: F401
    graphql,  # noqa: F401
)
from integrations.base import IntegrationBase
from integrations.registry import IntegrationRegistry

__all__ = ["IntegrationBase", "IntegrationRegistry"]

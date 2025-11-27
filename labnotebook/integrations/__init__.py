"""Integration system for Lab Notebook."""

from labnotebook.integrations.base import IntegrationBase
from labnotebook.integrations.registry import IntegrationRegistry

__all__ = ["IntegrationBase", "IntegrationRegistry"]

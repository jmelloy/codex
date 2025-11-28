"""Integration registry for Lab Notebook."""

from typing import Type

from codex.integrations.base import IntegrationBase


class IntegrationRegistry:
    """Registry for entry type integrations."""

    _integrations: dict[str, Type[IntegrationBase]] = {}

    @classmethod
    def register(cls, entry_type: str):
        """Decorator to register integration."""
        def decorator(integration_class: Type[IntegrationBase]):
            cls._integrations[entry_type] = integration_class
            return integration_class
        return decorator

    @classmethod
    def get(cls, entry_type: str) -> Type[IntegrationBase]:
        """Get integration for entry type."""
        if entry_type not in cls._integrations:
            raise ValueError(f"No integration registered for: {entry_type}")
        return cls._integrations[entry_type]

    @classmethod
    def list_integrations(cls) -> list[str]:
        """List all registered integration types."""
        return list(cls._integrations.keys())

    @classmethod
    def has_integration(cls, entry_type: str) -> bool:
        """Check if an integration is registered."""
        return entry_type in cls._integrations


# Register built-in integrations
@IntegrationRegistry.register("custom")
class CustomIntegration(IntegrationBase):
    """Custom/manual entry integration."""

    async def execute(self, inputs: dict) -> dict:
        """Custom entries don't execute automatically."""
        return {
            "outputs": inputs.get("outputs", {}),
            "artifacts": [],
        }

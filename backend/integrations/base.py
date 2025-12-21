"""Base integration class for Lab Notebook."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.workspace import Workspace


class IntegrationBase:
    """Base integration class."""

    # Override this in subclasses to specify the integration type name
    integration_type: str = ""

    def __init__(self, workspace: "Workspace"):
        """Initialize the integration."""
        self.workspace = workspace

    def get_default_variables(self) -> dict:
        """Get default variables for this integration from the workspace.

        Returns a dictionary of variable names to values that were
        stored as defaults for this integration type.
        """
        if not self.integration_type or not self.workspace:
            return {}
        return self.workspace.db_manager.get_integration_variables(
            self.integration_type
        )

    def merge_inputs_with_defaults(self, inputs: dict) -> dict:
        """Merge entry inputs with stored default variables.

        Default variables are used as fallbacks - entry inputs take precedence.
        For nested dictionaries (like 'headers'), defaults are merged with inputs.

        Args:
            inputs: The inputs provided with the entry

        Returns:
            Merged inputs dictionary with defaults filled in
        """
        defaults = self.get_default_variables()
        if not defaults:
            return inputs

        merged = dict(defaults)
        for key, value in inputs.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                # Merge nested dicts (e.g., headers)
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value

        return merged

    async def execute(self, inputs: dict) -> dict:
        """
        Execute and return results.

        Returns:
            dict with keys:
                - outputs: dict of output data
                - artifacts: list of artifact dicts with keys:
                    - type: MIME type
                    - data: bytes
                    - metadata: optional dict
        """
        raise NotImplementedError

    def validate_inputs(self, inputs: dict) -> bool:
        """Validate inputs."""
        return True

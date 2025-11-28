"""Base integration class for Lab Notebook."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codex.core.workspace import Workspace


class IntegrationBase:
    """Base integration class."""

    def __init__(self, workspace: "Workspace"):
        """Initialize the integration."""
        self.workspace = workspace

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

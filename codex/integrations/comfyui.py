"""ComfyUI workflow integration for Lab Notebook.

This integration supports executing ComfyUI workflows and tracking their
generated images and outputs.

ComfyUI is a node-based UI for Stable Diffusion and other AI image generation models.
It runs a local server (typically on http://localhost:8188) with a WebSocket API.

Supports storing default variables for:
- server_url: Base URL of the ComfyUI server (default: http://127.0.0.1:8188)
"""

import asyncio
import time
import uuid
from typing import Any, Optional

import aiohttp

from codex.integrations.base import IntegrationBase
from codex.integrations.registry import IntegrationRegistry


class ComfyUIClient:
    """Client for interacting with ComfyUI server."""

    def __init__(self, server_url: str = "http://127.0.0.1:8188"):
        """Initialize ComfyUI client.

        Args:
            server_url: Base URL of ComfyUI server
        """
        self.server_url = server_url.rstrip("/")

    async def queue_prompt(self, workflow: dict, client_id: Optional[str] = None) -> str:
        """Queue a workflow for execution.

        Args:
            workflow: ComfyUI workflow dictionary
            client_id: Optional client ID for WebSocket tracking

        Returns:
            prompt_id: ID of the queued prompt

        Raises:
            aiohttp.ClientError: If request fails
        """
        if client_id is None:
            client_id = str(uuid.uuid4())

        payload = {"prompt": workflow, "client_id": client_id}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/prompt", json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result["prompt_id"]

    async def get_history(self, prompt_id: str) -> dict[str, Any]:
        """Get execution history for a prompt.

        Args:
            prompt_id: ID of the prompt

        Returns:
            History dictionary with execution details

        Raises:
            aiohttp.ClientError: If request fails
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.server_url}/history/{prompt_id}"
            ) as response:
                response.raise_for_status()
                history = await response.json()
                return history.get(prompt_id, {})

    async def wait_for_completion(
        self, prompt_id: str, timeout: float = 300, poll_interval: float = 1.0
    ) -> dict[str, Any]:
        """Wait for workflow execution to complete.

        Args:
            prompt_id: ID of the prompt to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds

        Returns:
            History dictionary with outputs

        Raises:
            TimeoutError: If execution doesn't complete within timeout
            aiohttp.ClientError: If request fails
        """
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Workflow execution timed out after {timeout} seconds"
                )

            history = await self.get_history(prompt_id)

            # Check if execution is complete
            if history and "outputs" in history:
                return history

            # Check for errors
            if history and "status" in history:
                status = history["status"]
                if status.get("status_str") == "error":
                    error_msg = status.get("messages", ["Unknown error"])
                    raise RuntimeError(f"Workflow execution failed: {error_msg}")

            await asyncio.sleep(poll_interval)

    async def download_image(
        self, filename: str, subfolder: str = "", folder_type: str = "output"
    ) -> bytes:
        """Download an image from ComfyUI server.

        Args:
            filename: Name of the image file
            subfolder: Optional subfolder path
            folder_type: Type of folder (output, input, temp)

        Returns:
            Image data as bytes

        Raises:
            aiohttp.ClientError: If download fails
        """
        params = {"filename": filename, "type": folder_type}
        if subfolder:
            params["subfolder"] = subfolder

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.server_url}/view", params=params
            ) as response:
                response.raise_for_status()
                return await response.read()


@IntegrationRegistry.register("comfyui")
class ComfyUIIntegration(IntegrationBase):
    """ComfyUI workflow execution integration.

    Executes ComfyUI workflows and collects generated images as artifacts.

    Default Variables (stored via integration variables):
        server_url: Base URL of ComfyUI server (default: http://127.0.0.1:8188)

    Inputs:
        workflow: ComfyUI workflow dictionary (required)
        timeout: Maximum execution time in seconds (optional, default: 300)
        poll_interval: Status check interval in seconds (optional, default: 1.0)

    Outputs:
        prompt_id: ComfyUI prompt ID
        execution_time: Time taken to execute workflow
        node_outputs: Dictionary of outputs from each node
    """

    integration_type = "comfyui"

    async def execute(self, inputs: dict) -> dict:
        """Execute a ComfyUI workflow.

        Args:
            inputs: Dictionary containing workflow and optional parameters

        Returns:
            Dictionary with outputs and artifacts
        """
        # Merge inputs with stored defaults
        merged = self.merge_inputs_with_defaults(inputs)

        workflow = merged.get("workflow")
        if not workflow:
            raise ValueError("workflow is required")

        server_url = merged.get("server_url", "http://127.0.0.1:8188")
        timeout = merged.get("timeout", 300)
        poll_interval = merged.get("poll_interval", 1.0)

        client = ComfyUIClient(server_url)

        start_time = time.time()

        try:
            # Queue the workflow
            prompt_id = await client.queue_prompt(workflow)

            # Wait for completion
            history = await client.wait_for_completion(
                prompt_id, timeout=timeout, poll_interval=poll_interval
            )

            execution_time = time.time() - start_time

            # Extract outputs and collect image artifacts
            artifacts = []
            node_outputs = history.get("outputs", {})

            for node_id, node_output in node_outputs.items():
                # Check for images in output
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        # Download the image
                        image_data = await client.download_image(
                            filename=img_info["filename"],
                            subfolder=img_info.get("subfolder", ""),
                            folder_type=img_info.get("type", "output"),
                        )

                        # Determine MIME type from filename
                        filename = img_info["filename"].lower()
                        if filename.endswith(".png"):
                            mime_type = "image/png"
                        elif filename.endswith((".jpg", ".jpeg")):
                            mime_type = "image/jpeg"
                        elif filename.endswith(".webp"):
                            mime_type = "image/webp"
                        else:
                            mime_type = "image/png"  # Default to PNG

                        artifacts.append(
                            {
                                "type": mime_type,
                                "data": image_data,
                                "metadata": {
                                    "filename": img_info["filename"],
                                    "subfolder": img_info.get("subfolder", ""),
                                    "node_id": node_id,
                                },
                            }
                        )

            return {
                "outputs": {
                    "prompt_id": prompt_id,
                    "execution_time": execution_time,
                    "node_outputs": node_outputs,
                    "num_images": len(artifacts),
                },
                "artifacts": artifacts,
            }

        except TimeoutError as e:
            execution_time = time.time() - start_time
            return {
                "outputs": {
                    "error": str(e),
                    "execution_time": execution_time,
                },
                "artifacts": [],
            }

        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "outputs": {
                    "error": str(e),
                    "execution_time": execution_time,
                },
                "artifacts": [],
            }

    def validate_inputs(self, inputs: dict) -> bool:
        """Validate inputs for ComfyUI workflow.

        Validates against merged inputs (including defaults).
        """
        merged = self.merge_inputs_with_defaults(inputs)
        if "workflow" not in merged:
            return False
        if not isinstance(merged["workflow"], dict):
            return False
        return True

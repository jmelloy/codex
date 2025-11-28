"""API call integration for Lab Notebook.

This integration supports executing HTTP API calls and tracking their
requests and responses.
"""

import json
import time
from typing import Any

from codex.integrations.base import IntegrationBase
from codex.integrations.registry import IntegrationRegistry


@IntegrationRegistry.register("api_call")
class APICallIntegration(IntegrationBase):
    """HTTP API call tracking integration.

    Supports executing HTTP requests against any API endpoint.

    Inputs:
        url: API endpoint URL
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
        headers: Optional dict of HTTP headers
        body: Optional request body (for POST, PUT, PATCH)

    Outputs:
        status_code: HTTP status code
        headers: Response headers
        body: Response body
        duration_seconds: Request duration
    """

    async def execute(self, inputs: dict) -> dict:
        """Execute an API call."""
        import aiohttp

        method = inputs.get("method", "GET")
        url = inputs["url"]
        headers = inputs.get("headers", {})
        body = inputs.get("body")

        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, headers=headers, json=body
                ) as response:
                    response_text = await response.text()
                    duration = time.time() - start_time

                    # Try to parse response as JSON for better formatting
                    try:
                        response_json: Any = json.loads(response_text)
                        is_json = True
                    except json.JSONDecodeError:
                        response_json = None
                        is_json = False

                    output_data = {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "body": response_json if is_json else response_text,
                        "duration_seconds": duration,
                        "is_json_response": is_json,
                        "url": url,
                        "method": method,
                    }

                    # Create JSON artifact with request/response data
                    artifact_data = json.dumps(
                        {
                            "request": {
                                "url": url,
                                "method": method,
                                "headers": headers,
                                "body": body,
                            },
                            "response": {
                                "status_code": response.status,
                                "headers": dict(response.headers),
                                "body": response_json if is_json else response_text,
                            },
                            "duration_seconds": duration,
                        },
                        indent=2,
                    )

                    return {
                        "outputs": output_data,
                        "artifacts": [
                            {
                                "type": "application/json",
                                "data": artifact_data.encode("utf-8"),
                                "metadata": {
                                    "status_code": response.status,
                                    "content_type": response.headers.get("Content-Type"),
                                },
                            }
                        ],
                    }

        except aiohttp.ClientError as e:
            duration = time.time() - start_time
            error_msg = str(e)
            return {
                "outputs": {
                    "error": error_msg,
                    "duration_seconds": duration,
                    "url": url,
                    "method": method,
                },
                "artifacts": [
                    {
                        "type": "application/json",
                        "data": json.dumps({"error": error_msg}).encode("utf-8"),
                        "metadata": {"error": True},
                    }
                ],
            }

    def validate_inputs(self, inputs: dict) -> bool:
        """Validate inputs for API call."""
        if "url" not in inputs:
            return False
        return True

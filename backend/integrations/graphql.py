"""GraphQL API integration for Lab Notebook.

This integration supports executing GraphQL queries and mutations against
GraphQL API endpoints.

Supports storing default variables for:
- url: Default GraphQL endpoint URL
- headers: Default headers to include in all requests
"""

import json
import time
from typing import Any, Optional

from codex.integrations.base import IntegrationBase
from codex.integrations.registry import IntegrationRegistry


def _extract_error_message(response_data: dict) -> Optional[str]:
    """Extract error message from GraphQL response."""
    errors = response_data.get("errors")
    if errors and isinstance(errors, list) and len(errors) > 0:
        first_error = errors[0]
        if isinstance(first_error, dict):
            return first_error.get("message", str(first_error))
        return str(first_error)
    return None


@IntegrationRegistry.register("graphql")
class GraphQLIntegration(IntegrationBase):
    """GraphQL API call integration.

    Supports executing GraphQL queries and mutations against any GraphQL endpoint.

    Default Variables (stored via integration variables):
        url: Default GraphQL endpoint URL
        headers: Default headers to include in all requests

    Inputs:
        url: GraphQL endpoint URL
        query: GraphQL query or mutation string
        variables: Optional dict of query variables
        headers: Optional dict of HTTP headers (merged with defaults)
        operation_name: Optional operation name (for documents with multiple operations)

    Outputs:
        data: The data field from the GraphQL response
        errors: List of errors from the GraphQL response (if any)
        status_code: HTTP status code
        duration_seconds: Request duration
        has_errors: Boolean indicating if there were any errors
    """

    integration_type = "graphql"

    async def execute(self, inputs: dict) -> dict:
        """Execute a GraphQL query or mutation."""
        import aiohttp

        # Merge inputs with stored defaults
        merged = self.merge_inputs_with_defaults(inputs)

        url = merged["url"]
        query = merged["query"]
        variables = merged.get("variables", {})
        headers = merged.get("headers", {})
        operation_name = merged.get("operation_name")

        # Prepare the GraphQL request payload
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        # Set default Content-Type if not provided
        if "Content-Type" not in headers and "content-type" not in headers:
            headers["Content-Type"] = "application/json"

        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response_text = await response.text()
                    duration = time.time() - start_time

                    # Try to parse as JSON
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_data = {"raw_response": response_text}

                    # Extract data and errors
                    data = response_data.get("data")
                    errors = response_data.get("errors", [])
                    has_errors = bool(errors)
                    error_message = _extract_error_message(response_data)

                    output_data = {
                        "data": data,
                        "errors": errors,
                        "status_code": response.status,
                        "duration_seconds": duration,
                        "has_errors": has_errors,
                        "error_message": error_message,
                        "query": query,
                        "variables": variables,
                    }

                    # Create JSON artifact with the full response
                    artifact_data = json.dumps(
                        {
                            "data": data,
                            "errors": errors,
                            "status_code": response.status,
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
                                    "has_errors": has_errors,
                                    "content_type": response.headers.get(
                                        "Content-Type"
                                    ),
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
                    "query": query,
                    "variables": variables,
                    "has_errors": True,
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
        """Validate inputs for GraphQL query.

        Validates against merged inputs (including defaults).
        """
        merged = self.merge_inputs_with_defaults(inputs)
        if "url" not in merged:
            return False
        if "query" not in merged:
            return False
        return True

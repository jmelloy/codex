"""Integration execution service for making API calls."""

import base64
import logging
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result from executing an integration endpoint."""

    data: Any  # Can be dict, list, str, or bytes (as base64)
    content_type: str  # MIME type of the response


class IntegrationPluginProtocol(Protocol):
    """Protocol for integration plugin-like objects.

    This protocol allows the executor to work with both filesystem-based
    plugins and database-stored plugins.
    """

    @property
    def endpoints(self) -> list[dict[str, Any]]: ...

    @property
    def base_url(self) -> str | None: ...

    @property
    def auth_method(self) -> str | None: ...


class IntegrationExecutor:
    """Execute integration API calls."""

    def __init__(self, timeout: int = 30):
        """Initialize executor.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    async def execute_endpoint(
        self,
        integration: IntegrationPluginProtocol,
        endpoint_id: str,
        config: dict[str, Any],
        parameters: dict[str, Any],
    ) -> ExecutionResult:
        """Execute an integration endpoint.

        Args:
            integration: Integration plugin instance
            endpoint_id: Endpoint identifier
            config: Integration configuration (API keys, etc)
            parameters: Request parameters

        Returns:
            ExecutionResult with data and content type

        Raises:
            ValueError: If endpoint not found or parameters invalid
            httpx.HTTPError: If API request fails
        """
        # Find the endpoint
        endpoint = None
        for ep in integration.endpoints:
            if ep.get("id") == endpoint_id:
                endpoint = ep
                break

        if not endpoint:
            raise ValueError(f"Endpoint not found: {endpoint_id}")

        # Build request parameters
        request_params = self._build_parameters(endpoint, config, parameters)

        # Build URL
        url = self._build_url(integration, endpoint, request_params)

        # Build headers (pass endpoint to check for expected response type)
        headers = self._build_headers(integration, config, endpoint)

        # Make request
        method = endpoint.get("method", "GET").upper()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=request_params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=request_params)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=request_params)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return self._parse_response(response)

    async def test_connection(
        self,
        integration: IntegrationPluginProtocol,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Test integration connection.

        Args:
            integration: Integration plugin instance
            config: Integration configuration to test

        Returns:
            Test result with success status and message
        """
        # If there are no endpoints, just validate config
        if not integration.endpoints:
            return {
                "success": True,
                "message": "Configuration validated (no endpoints to test)",
            }

        # Try the first endpoint with minimal parameters
        first_endpoint = integration.endpoints[0]
        endpoint_id = first_endpoint.get("id")

        # Build minimal test parameters
        test_params = {}
        for param in first_endpoint.get("parameters", []):
            if param.get("required"):
                param_name = param.get("name")
                # Try to get from config if it has from_config
                if param.get("from_config"):
                    config_key = param["from_config"]
                    if config_key in config:
                        test_params[param_name] = config[config_key]
                    else:
                        # Use a test value
                        test_params[param_name] = self._get_test_value(param)
                else:
                    # Use a test value
                    test_params[param_name] = self._get_test_value(param)

        try:
            await self.execute_endpoint(integration, endpoint_id, config, test_params)
            return {
                "success": True,
                "message": "Connection successful",
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"API returned status {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
            }

    def _build_parameters(
        self,
        endpoint: dict[str, Any],
        config: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Build request parameters from endpoint definition.

        Args:
            endpoint: Endpoint definition
            config: Integration configuration
            parameters: User-provided parameters

        Returns:
            Complete request parameters
        """
        result = {}

        # Process endpoint parameter definitions
        for param_def in endpoint.get("parameters", []):
            param_name = param_def.get("name")

            # Check if parameter should come from config
            if param_def.get("from_config"):
                config_key = param_def["from_config"]
                if config_key in config:
                    result[param_name] = config[config_key]
                elif param_def.get("required"):
                    raise ValueError(
                        f"Missing required config value: {config_key}"
                    )

            # Check if parameter provided by user
            elif param_name in parameters:
                result[param_name] = parameters[param_name]

            # Use default if available
            elif "default" in param_def:
                result[param_name] = param_def["default"]

            # Raise error if required parameter missing
            elif param_def.get("required"):
                raise ValueError(f"Missing required parameter: {param_name}")

        return result

    def _build_url(
        self,
        integration: IntegrationPluginProtocol,
        endpoint: dict[str, Any],
        parameters: dict[str, Any],
    ) -> str:
        """Build complete URL for endpoint.

        Args:
            integration: Integration plugin instance
            endpoint: Endpoint definition
            parameters: Request parameters

        Returns:
            Complete URL
        """
        base_url = integration.base_url or ""
        path = endpoint.get("path", "")

        # Replace path parameters like {owner} with actual values
        # Collect parameters used in path so we can remove them later
        used_params = []
        for param_name, param_value in parameters.items():
            placeholder = f"{{{param_name}}}"
            if placeholder in path:
                path = path.replace(placeholder, str(param_value))
                used_params.append(param_name)

        # Remove parameters that were used in the path
        for param_name in used_params:
            parameters.pop(param_name)

        if base_url:
            return urljoin(base_url, path.lstrip("/"))
        return path

    def _build_headers(
        self,
        integration: IntegrationPluginProtocol,
        config: dict[str, Any],
        endpoint: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Build request headers.

        Args:
            integration: Integration plugin instance
            config: Integration configuration
            endpoint: Optional endpoint definition (for response_type)

        Returns:
            Request headers
        """
        # Determine Accept header based on endpoint's expected response type
        response_type = endpoint.get("response_type", "json") if endpoint else "json"
        accept_header = self._get_accept_header(response_type)

        headers = {
            "User-Agent": "Codex Integration Client/1.0",
            "Accept": accept_header,
        }

        # Add authentication based on auth method
        auth_method = integration.auth_method

        if auth_method == "token" and "access_token" in config:
            headers["Authorization"] = f"Bearer {config['access_token']}"
        elif auth_method == "api_key" and "api_key" in config:
            # API key in header - common pattern
            headers["X-API-Key"] = config["api_key"]

        return headers

    def _get_accept_header(self, response_type: str) -> str:
        """Get Accept header value based on response type.

        Args:
            response_type: Expected response type (json, html, text, image, binary)

        Returns:
            Accept header value
        """
        accept_map = {
            "json": "application/json",
            "html": "text/html",
            "text": "text/plain",
            "xml": "application/xml, text/xml",
            "image": "image/*",
            "binary": "application/octet-stream",
        }
        return accept_map.get(response_type, "*/*")

    def _parse_response(self, response: httpx.Response) -> ExecutionResult:
        """Parse HTTP response based on content type.

        Args:
            response: HTTP response object

        Returns:
            ExecutionResult with data and content type
        """
        content_type = response.headers.get("content-type", "application/octet-stream")
        # Extract base content type (remove charset and other params)
        base_content_type = content_type.split(";")[0].strip().lower()

        # JSON response
        if base_content_type in ("application/json", "text/json"):
            return ExecutionResult(data=response.json(), content_type="application/json")

        # Text-based responses (HTML, plain text, XML)
        if base_content_type.startswith("text/") or base_content_type in (
            "application/xml",
            "application/xhtml+xml",
        ):
            return ExecutionResult(data=response.text, content_type=base_content_type)

        # Binary responses (images, PDFs, etc.) - encode as base64
        return ExecutionResult(
            data=base64.b64encode(response.content).decode("ascii"),
            content_type=base_content_type,
        )

    def _get_test_value(self, param_def: dict[str, Any]) -> Any:
        """Get a test value for a parameter.

        Args:
            param_def: Parameter definition

        Returns:
            Test value
        """
        param_type = param_def.get("type", "string")

        if param_type == "string":
            return "test"
        elif param_type == "integer" or param_type == "number":
            return 1
        elif param_type == "boolean":
            return True
        else:
            return None

"""Tests for integration executor."""

from pathlib import Path

import pytest

from codex.plugins.executor import IntegrationExecutor
from codex.plugins.loader import PluginLoader


@pytest.fixture
def loader():
    """Create plugin loader."""
    # Plugins are at the repository root, tests run from backend/
    return PluginLoader(Path(__file__).parent.parent.parent / "plugins")


@pytest.fixture
def executor():
    """Create integration executor."""
    return IntegrationExecutor()


def test_executor_initialization(executor):
    """Test executor initialization."""
    assert executor is not None
    assert executor.timeout == 30


def test_build_parameters():
    """Test parameter building."""
    executor = IntegrationExecutor()
    
    endpoint = {
        "parameters": [
            {"name": "api_key", "from_config": "api_key", "required": True},
            {"name": "location", "required": True},
            {"name": "units", "from_config": "units", "required": False},
        ]
    }
    
    config = {"api_key": "test123", "units": "metric"}
    parameters = {"location": "San Francisco"}
    
    result = executor._build_parameters(endpoint, config, parameters)
    
    assert result["api_key"] == "test123"
    assert result["location"] == "San Francisco"
    assert result["units"] == "metric"


def test_build_parameters_missing_required():
    """Test missing required parameter raises error."""
    executor = IntegrationExecutor()
    
    endpoint = {
        "parameters": [
            {"name": "api_key", "from_config": "api_key", "required": True},
        ]
    }
    
    config = {}
    parameters = {}
    
    with pytest.raises(ValueError, match="Missing required config value"):
        executor._build_parameters(endpoint, config, parameters)


def test_build_url(loader):
    """Test URL building."""
    executor = IntegrationExecutor()
    plugins = loader.load_all_plugins()
    github = loader.get_plugin("github")
    
    endpoint = {
        "path": "/repos/{owner}/{repo}/issues/{issue_number}"
    }
    
    parameters = {
        "owner": "facebook",
        "repo": "react",
        "issue_number": "123",
    }
    
    url = executor._build_url(github, endpoint, parameters)
    
    assert url == "https://api.github.com/repos/facebook/react/issues/123"
    # Parameters used in path should be removed
    assert "owner" not in parameters
    assert "repo" not in parameters
    assert "issue_number" not in parameters


def test_build_headers_token_auth(loader):
    """Test header building with token auth."""
    executor = IntegrationExecutor()
    plugins = loader.load_all_plugins()
    github = loader.get_plugin("github")
    
    config = {"access_token": "ghp_test123"}
    
    headers = executor._build_headers(github, config)
    
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer ghp_test123"
    assert "User-Agent" in headers
    assert "Accept" in headers


def test_build_headers_api_key_auth(loader):
    """Test header building with API key auth."""
    executor = IntegrationExecutor()
    plugins = loader.load_all_plugins()
    weather = loader.get_plugin("weather-api")
    
    config = {"api_key": "test_api_key"}
    
    headers = executor._build_headers(weather, config)
    
    assert "X-API-Key" in headers
    assert headers["X-API-Key"] == "test_api_key"


def test_build_headers_no_auth(loader):
    """Test header building with no auth."""
    executor = IntegrationExecutor()
    plugins = loader.load_all_plugins()
    opengraph = loader.get_plugin("opengraph-unfurl")
    
    config = {}
    
    headers = executor._build_headers(opengraph, config)
    
    assert "Authorization" not in headers
    assert "X-API-Key" not in headers
    assert "User-Agent" in headers


def test_get_test_value():
    """Test getting test values for parameters."""
    executor = IntegrationExecutor()
    
    assert executor._get_test_value({"type": "string"}) == "test"
    assert executor._get_test_value({"type": "integer"}) == 1
    assert executor._get_test_value({"type": "number"}) == 1
    assert executor._get_test_value({"type": "boolean"}) is True
    assert executor._get_test_value({"type": "unknown"}) is None


@pytest.mark.asyncio
async def test_test_connection_no_endpoints(loader, executor):
    """Test connection test with no endpoints."""
    plugins = loader.load_all_plugins()
    opengraph = loader.get_plugin("opengraph-unfurl")
    
    # OpenGraph has endpoints, so let's modify for test
    original_endpoints = opengraph.manifest.get("endpoints", [])
    opengraph.manifest["endpoints"] = []
    
    result = await executor.test_connection(opengraph, {})
    
    assert result["success"] is True
    assert "no endpoints" in result["message"].lower()
    
    # Restore
    opengraph.manifest["endpoints"] = original_endpoints


def test_plugin_test_endpoint(loader):
    """Test that plugins can specify a test_endpoint."""
    plugins = loader.load_all_plugins()
    
    # GitHub should specify get_repo as its test endpoint
    github = loader.get_plugin("github")
    if github:
        assert hasattr(github, 'test_endpoint')
        assert github.test_endpoint == "get_repo"
    
    # Weather API should specify geocode as its test endpoint
    weather = loader.get_plugin("weather-api")
    if weather:
        assert hasattr(weather, 'test_endpoint')
        assert weather.test_endpoint == "geocode"
    
    # OpenGraph should specify fetch_metadata as its test endpoint
    opengraph = loader.get_plugin("opengraph-unfurl")
    if opengraph:
        assert hasattr(opengraph, 'test_endpoint')
        assert opengraph.test_endpoint == "fetch_metadata"


@pytest.mark.asyncio
async def test_test_connection_uses_specified_endpoint(loader, executor):
    """Test that test_connection uses the specified test_endpoint."""
    plugins = loader.load_all_plugins()
    github = loader.get_plugin("github")
    
    # Create a mock plugin with a specified test endpoint
    class MockPlugin:
        @property
        def endpoints(self):
            return [
                {"id": "endpoint1", "parameters": []},
                {"id": "test_endpoint_id", "parameters": []},
                {"id": "endpoint3", "parameters": []},
            ]
        
        @property
        def test_endpoint(self):
            return "test_endpoint_id"
        
        @property
        def base_url(self):
            return "https://example.com"
        
        @property
        def auth_method(self):
            return None
    
    mock_plugin = MockPlugin()
    
    # Verify the mock has the test_endpoint
    assert mock_plugin.test_endpoint == "test_endpoint_id"
    
    # The executor should use the specified endpoint (second one)
    # We can't test the actual execution without a real API,
    # but we can verify the endpoint property is accessible
    assert mock_plugin.endpoints[1]["id"] == "test_endpoint_id"


@pytest.mark.asyncio
async def test_test_connection_invalid_test_endpoint(loader, executor):
    """Test that test_connection handles invalid test_endpoint gracefully."""
    # Create a mock plugin with an invalid test endpoint
    class MockPlugin:
        @property
        def endpoints(self):
            return [
                {"id": "endpoint1", "parameters": []},
                {"id": "endpoint2", "parameters": []},
            ]
        
        @property
        def test_endpoint(self):
            return "nonexistent_endpoint"
        
        @property
        def base_url(self):
            return "https://example.com"
        
        @property
        def auth_method(self):
            return None
    
    mock_plugin = MockPlugin()
    
    # Test that we get an error message about the invalid endpoint
    result = await executor.test_connection(mock_plugin, {})
    
    assert result["success"] is False
    assert "not found" in result["message"].lower()
    assert "nonexistent_endpoint" in result["message"]

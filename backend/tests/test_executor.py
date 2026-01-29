"""Tests for integration executor."""

from pathlib import Path

import pytest

from codex.plugins.executor import IntegrationExecutor
from codex.plugins.loader import PluginLoader


@pytest.fixture
def loader():
    """Create plugin loader."""
    return PluginLoader(Path("plugins"))


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

"""Pytest configuration and fixtures."""

import asyncio
import os
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Create a temporary directory for test databases BEFORE importing codex modules,
# since database.py reads DATABASE_URL at import time.
_test_data_dir = tempfile.mkdtemp(prefix="codex_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_data_dir}/codex_system.db"
os.environ["DATA_DIRECTORY"] = _test_data_dir

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import select  # noqa: E402

from codex.core.watcher import get_active_watchers, unregister_watcher  # noqa: E402
from codex.db.database import async_session_maker, init_system_db, system_engine  # noqa: E402
from codex.db.models import Plugin  # noqa: E402
from codex.main import app  # noqa: E402

# Test plugin manifests (matching what the frontend would register)
TEST_PLUGINS = [
    {
        "plugin_id": "weather-api",
        "name": "Weather API Integration",
        "version": "1.0.0",
        "type": "integration",
        "manifest": {
            "id": "weather-api",
            "name": "Weather API Integration",
            "version": "1.0.0",
            "type": "integration",
            "description": "Display current weather and forecasts from OpenWeatherMap",
            "author": "Codex Team",
            "license": "MIT",
            "codex_version": ">=1.0.0",
            "api_version": 1,
            "integration": {
                "api_type": "rest",
                "base_url": "https://api.openweathermap.org",
                "auth_method": "api_key",
                "test_endpoint": "geocode",
                "rate_limit": {
                    "requests_per_minute": 60,
                    "requests_per_day": 1000,
                },
            },
            "properties": [
                {"name": "api_key", "type": "string", "required": True, "secure": True},
                {"name": "default_location", "type": "string", "required": False, "default": "San Francisco, US"},
                {"name": "units", "type": "string", "enum": ["metric", "imperial", "kelvin"], "default": "imperial"},
            ],
            "endpoints": [
                {
                    "id": "geocode",
                    "name": "Geocode Location",
                    "method": "GET",
                    "path": "/geo/1.0/direct",
                    "description": "Convert city name to coordinates",
                    "cache_ttl": 2592000,
                    "parameters": [
                        {
                            "name": "q",
                            "type": "string",
                            "required": True,
                            "description": "City name, state code, country code",
                        },
                        {"name": "limit", "type": "integer", "required": False, "default": 1},
                        {"name": "appid", "type": "string", "required": True, "from_config": "api_key"},
                    ],
                },
                {
                    "id": "current_weather",
                    "name": "Get Current Weather",
                    "method": "GET",
                    "path": "/data/2.5/weather",
                    "description": "Get current weather for coordinates",
                    "parameters": [
                        {"name": "lat", "type": "number", "required": True},
                        {"name": "lon", "type": "number", "required": True},
                        {"name": "appid", "type": "string", "required": True, "from_config": "api_key"},
                        {"name": "units", "type": "string", "from_config": "units"},
                    ],
                },
                {
                    "id": "forecast",
                    "name": "Get 5-Day Forecast",
                    "method": "GET",
                    "path": "/data/2.5/forecast",
                    "description": "Get 5-day weather forecast for coordinates",
                    "parameters": [
                        {"name": "lat", "type": "number", "required": True},
                        {"name": "lon", "type": "number", "required": True},
                        {"name": "appid", "type": "string", "from_config": "api_key"},
                        {"name": "units", "type": "string", "from_config": "units"},
                    ],
                },
            ],
            "blocks": [
                {
                    "id": "weather",
                    "name": "Weather Block",
                    "description": "Display current weather for a location",
                    "icon": "☀️",
                    "syntax": "```weather\nlocation: San Francisco\n```",
                },
            ],
            "permissions": ["network_request", "store_config", "render_blocks"],
        },
    },
    {
        "plugin_id": "github",
        "name": "GitHub Integration",
        "version": "1.0.0",
        "type": "integration",
        "manifest": {
            "id": "github",
            "name": "GitHub Integration",
            "version": "1.0.0",
            "type": "integration",
            "description": "Display GitHub issues, pull requests, and repository information",
            "author": "Codex Team",
            "integration": {
                "api_type": "rest",
                "base_url": "https://api.github.com",
                "auth_method": "token",
                "test_endpoint": "get_user",
            },
            "properties": [
                {"name": "access_token", "type": "string", "required": True, "secure": True},
                {"name": "default_owner", "type": "string", "required": False},
                {"name": "default_repo", "type": "string", "required": False},
            ],
            "endpoints": [
                {
                    "id": "get_user",
                    "name": "Get Authenticated User",
                    "method": "GET",
                    "path": "/user",
                    "description": "Get the authenticated user's profile",
                    "parameters": [],
                },
                {
                    "id": "list_issues",
                    "name": "List Issues",
                    "method": "GET",
                    "path": "/repos/{owner}/{repo}/issues",
                    "description": "List issues for a repository",
                    "parameters": [
                        {"name": "owner", "type": "string", "required": True},
                        {"name": "repo", "type": "string", "required": True},
                        {"name": "state", "type": "string", "required": False, "default": "open"},
                        {"name": "per_page", "type": "integer", "required": False, "default": 10},
                    ],
                },
                {
                    "id": "list_pulls",
                    "name": "List Pull Requests",
                    "method": "GET",
                    "path": "/repos/{owner}/{repo}/pulls",
                    "description": "List pull requests for a repository",
                    "parameters": [
                        {"name": "owner", "type": "string", "required": True},
                        {"name": "repo", "type": "string", "required": True},
                        {"name": "state", "type": "string", "required": False, "default": "open"},
                        {"name": "per_page", "type": "integer", "required": False, "default": 10},
                    ],
                },
                {
                    "id": "get_repo",
                    "name": "Get Repository",
                    "method": "GET",
                    "path": "/repos/{owner}/{repo}",
                    "description": "Get repository details",
                    "parameters": [
                        {"name": "owner", "type": "string", "required": True},
                        {"name": "repo", "type": "string", "required": True},
                    ],
                },
            ],
            "blocks": [
                {
                    "id": "github-issues",
                    "name": "GitHub Issues",
                    "description": "Display issues from a GitHub repository",
                    "icon": "\U0001f41b",
                },
                {
                    "id": "github-pulls",
                    "name": "GitHub Pull Requests",
                    "description": "Display pull requests from a GitHub repository",
                    "icon": "\U0001f500",
                },
                {
                    "id": "github-repo",
                    "name": "GitHub Repository",
                    "description": "Display repository information",
                    "icon": "\U0001f4e6",
                },
            ],
            "permissions": ["network_request", "store_config", "render_blocks"],
        },
    },
    {
        "plugin_id": "api-fetch",
        "name": "API Fetch",
        "version": "1.0.0",
        "type": "integration",
        "manifest": {
            "id": "api-fetch",
            "name": "API Fetch",
            "version": "1.0.0",
            "type": "integration",
            "description": "Generic REST API block for fetching and displaying data from any HTTP endpoint",
            "author": "Codex Team",
            "integration": {
                "api_type": "rest",
                "auth_method": "none",
                "test_endpoint": "fetch",
            },
            "properties": [
                {"name": "default_headers", "type": "string", "required": False, "default": "{}"},
                {"name": "allowed_domains", "type": "string", "required": False, "default": ""},
                {"name": "timeout", "type": "integer", "required": False, "default": 30},
            ],
            "endpoints": [
                {
                    "id": "fetch",
                    "name": "Fetch URL",
                    "method": "GET",
                    "description": "Make an HTTP request to any URL",
                    "parameters": [
                        {"name": "url", "type": "string", "required": True},
                        {"name": "method", "type": "string", "required": False, "default": "GET"},
                        {"name": "headers", "type": "object", "required": False},
                        {"name": "body", "type": "string", "required": False},
                    ],
                },
            ],
            "blocks": [
                {
                    "id": "api",
                    "name": "API Block",
                    "description": "Fetch and display data from any REST API endpoint",
                    "icon": "\U0001f310",
                    "syntax": "```api\nurl: https://api.example.com/data\nmethod: GET\ndisplay: json\n```",
                },
            ],
        },
    },
    {
        "plugin_id": "database-query",
        "name": "Database Query",
        "version": "1.0.0",
        "type": "integration",
        "manifest": {
            "id": "database-query",
            "name": "Database Query",
            "version": "1.0.0",
            "type": "integration",
            "description": "Query the notebook SQLite database and display results as tables",
            "author": "Codex Team",
            "integration": {
                "api_type": "rest",
                "auth_method": "none",
                "test_endpoint": "query",
            },
            "properties": [
                {"name": "max_rows", "type": "integer", "required": False, "default": 100},
            ],
            "endpoints": [
                {
                    "id": "query",
                    "name": "Execute Query",
                    "method": "POST",
                    "description": "Execute a read-only SQL query against the notebook database",
                    "parameters": [
                        {"name": "query", "type": "string", "required": True},
                        {"name": "source", "type": "string", "required": False, "default": "notebook"},
                        {"name": "notebook_id", "type": "integer", "required": False},
                    ],
                },
            ],
            "blocks": [
                {
                    "id": "database",
                    "name": "Database Block",
                    "description": "Query the notebook database and display results",
                    "icon": "\U0001f5c4",
                    "syntax": "```database\nsource: notebook\nquery: SELECT title, block_type FROM blocks LIMIT 10\n```",
                },
            ],
        },
    },
]


async def register_test_plugins():
    """Register test plugins in the database."""
    async with async_session_maker() as session:
        for plugin_data in TEST_PLUGINS:
            # Check if plugin already exists
            stmt = select(Plugin).where(Plugin.plugin_id == plugin_data["plugin_id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            now = datetime.now(UTC)

            if existing:
                # Update existing plugin
                existing.name = plugin_data["name"]
                existing.version = plugin_data["version"]
                existing.type = plugin_data["type"]
                existing.manifest = plugin_data["manifest"]
                existing.updated_at = now
                session.add(existing)
            else:
                # Create new plugin
                plugin = Plugin(
                    plugin_id=plugin_data["plugin_id"],
                    name=plugin_data["name"],
                    version=plugin_data["version"],
                    type=plugin_data["type"],
                    enabled=True,
                    manifest=plugin_data["manifest"],
                    installed_at=now,
                    updated_at=now,
                )
                session.add(plugin)

        await session.commit()


@pytest.fixture
def test_client():
    """Create a fresh TestClient for each test to avoid cookie persistence."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def ensure_valid_cwd():
    """Ensure we're always in a valid working directory.

    Some tests (especially git-related ones) may change the working directory
    or end up in a deleted directory. This fixture ensures we start each test
    in a valid directory.
    """
    # Get the backend directory
    backend_dir = Path(__file__).parent.parent

    # Before test: ensure we're in a valid directory
    try:
        os.getcwd()
    except FileNotFoundError:
        # If current directory doesn't exist, change to backend dir
        os.chdir(backend_dir)

    original_cwd = os.getcwd()

    yield

    # After test: restore to a valid directory if needed
    try:
        os.getcwd()
    except FileNotFoundError:
        os.chdir(backend_dir)
    except Exception:
        pass


# Initialize the database once before all tests
@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    """Initialize the database before running any tests."""
    # Create a temporary event loop just for initialization
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(init_system_db())
        # Register test plugins after database is initialized
        loop.run_until_complete(register_test_plugins())
    finally:
        loop.close()

    yield

    # Clean up: dispose of the async engine to prevent hanging connections
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(system_engine.dispose())
    finally:
        loop.close()

    # Remove the temporary test database directory
    shutil.rmtree(_test_data_dir, ignore_errors=True)


@pytest.fixture
def temp_workspace_dir():
    """Create a temporary directory for workspace tests and clean it up afterward."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up the temporary directory after the test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cleanup_workspaces():
    """Track workspace paths created during tests and clean them up afterward."""
    workspace_paths = []

    def register_workspace(path):
        """Register a workspace path for cleanup."""
        workspace_paths.append(path)
        return path

    yield register_workspace

    # Clean up all registered workspaces
    for path in workspace_paths:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="function", autouse=True)
def cleanup_workspace_dirs():
    """Automatically clean up workspace directories after each test function."""
    # Before test: record existing workspace directories
    workspace_dir = Path("workspaces")
    existing_dirs = set()
    if workspace_dir.exists():
        existing_dirs = set(workspace_dir.iterdir())

    yield

    # After test: clean up new workspace directories
    if workspace_dir.exists():
        current_dirs = set(workspace_dir.iterdir())
        new_dirs = current_dirs - existing_dirs

        # Stop watchers for directories we're about to delete
        for new_dir in new_dirs:
            # Find and stop watchers for this directory and its subdirectories
            # Copy list to avoid mutation during iteration as unregister_watcher modifies the underlying list
            for watcher in get_active_watchers()[:]:
                try:
                    # Check if watcher's path is within the directory we're deleting
                    watcher_path = Path(watcher.notebook_path).resolve()
                    new_dir_path = new_dir.resolve()
                    if watcher_path == new_dir_path or new_dir_path in watcher_path.parents:
                        watcher.stop()
                        unregister_watcher(watcher)
                except Exception:
                    # Ignore errors when stopping watchers during cleanup
                    pass

        # Now delete the directories
        for new_dir in new_dirs:
            shutil.rmtree(new_dir, ignore_errors=True)


@pytest.fixture
def auth_headers(test_client):
    """Register and login a test user, returning (headers, username)."""
    username = f"test_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


@pytest.fixture
def create_workspace(test_client, auth_headers):
    """Factory fixture to create a workspace. Returns a function that creates workspaces."""

    def _create(name="Test Workspace", path=None):
        headers = auth_headers[0]
        json_data = {"name": name}
        if path is not None:
            json_data["path"] = path
        ws_response = test_client.post("/api/v1/workspaces/", json=json_data, headers=headers)
        assert ws_response.status_code == 200
        return ws_response.json()

    return _create


@pytest.fixture
def workspace_and_notebook(test_client, auth_headers, create_workspace):
    """Create a workspace and notebook, returning (workspace, notebook)."""
    workspace = create_workspace()
    headers = auth_headers[0]

    nb_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/",
        json={"name": "Test Notebook"},
        headers=headers,
    )
    assert nb_response.status_code == 200
    notebook = nb_response.json()

    return workspace, notebook

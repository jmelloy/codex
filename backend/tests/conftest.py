"""Pytest configuration and fixtures."""

import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from codex.db.database import init_system_db, system_engine, async_session_maker
from codex.db.models import Plugin
from codex.main import app


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
            "description": "OpenWeatherMap integration for weather data",
            "author": "Codex Team",
            "integration": {
                "api_type": "rest",
                "base_url": "https://api.openweathermap.org/data/2.5",
                "auth_method": "api_key",
            },
            "properties": [
                {"name": "api_key", "type": "string", "required": True, "secure": True},
                {"name": "default_location", "type": "string", "required": False},
                {"name": "units", "type": "string", "enum": ["metric", "imperial"], "default": "metric"},
            ],
            "endpoints": [
                {
                    "id": "current_weather",
                    "name": "Current Weather",
                    "method": "GET",
                    "path": "/weather",
                    "parameters": [
                        {"name": "q", "type": "string", "required": True, "description": "City name"},
                        {"name": "appid", "type": "string", "required": True, "from_config": "api_key"},
                        {"name": "units", "type": "string", "from_config": "units"},
                    ],
                },
            ],
            "blocks": [
                {"id": "weather", "name": "Weather Block", "description": "Displays current weather", "icon": "☀️"},
            ],
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
            "description": "GitHub integration for issues, PRs, and repos",
            "author": "Codex Team",
            "integration": {
                "api_type": "rest",
                "base_url": "https://api.github.com",
                "auth_method": "token",
            },
            "endpoints": [],
            "blocks": [],
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

            now = datetime.now(timezone.utc)

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
        for new_dir in new_dirs:
            shutil.rmtree(new_dir, ignore_errors=True)

"""Pytest configuration and fixtures."""

import pytest
import asyncio
import tempfile
import shutil
import os
from pathlib import Path
from codex.db.database import init_system_db, system_engine


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

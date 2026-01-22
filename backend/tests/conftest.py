"""Pytest configuration and fixtures."""

import pytest
import asyncio
from backend.db.database import init_system_db, system_engine


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

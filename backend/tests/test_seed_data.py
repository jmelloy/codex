"""
Tests for the seed_test_data script.

Tests that the seed script:
- Creates test users correctly
- Creates workspaces, notebooks, and files
- Is idempotent (can be run multiple times)
- Can clean up test data
"""

from pathlib import Path

import pytest
from sqlmodel import select

from codex.db.database import get_system_session, init_system_db
from codex.db.models import Notebook, User, Workspace
from codex.scripts.seed_test_data import TEST_USERS, clean_test_data, seed_data


@pytest.mark.asyncio
async def test_seed_creates_users():
    """Test that seed_data creates all test users."""
    await init_system_db()

    # Clean up any existing test data first
    await clean_test_data()

    # Run seed script
    await seed_data()

    # Verify users were created
    async for session in get_system_session():
        try:
            for user_data in TEST_USERS:
                result = await session.execute(select(User).where(User.username == user_data["username"]))
                user = result.scalar_one_or_none()
                assert user is not None, f"User {user_data['username']} not created"
                assert user.email == user_data["email"]
                assert user.is_active is True
        finally:
            break


@pytest.mark.asyncio
async def test_seed_creates_workspaces():
    """Test that seed_data creates workspaces for each user."""
    await init_system_db()

    # Run seed script (should skip existing users)
    await seed_data()

    # Verify workspaces were created
    async for session in get_system_session():
        try:
            for user_data in TEST_USERS:
                result = await session.execute(select(User).where(User.username == user_data["username"]))
                user = result.scalar_one_or_none()
                assert user is not None

                # Check workspaces
                result = await session.execute(select(Workspace).where(Workspace.owner_id == user.id))
                workspaces = result.scalars().all()
                assert len(workspaces) >= len(user_data["workspaces"])
        finally:
            break


@pytest.mark.asyncio
async def test_seed_creates_notebooks():
    """Test that seed_data creates notebooks in workspaces."""
    await init_system_db()

    # Run seed script
    await seed_data()

    # Verify notebooks were created
    async for session in get_system_session():
        try:
            # Get demo user
            result = await session.execute(select(User).where(User.username == "demo"))
            user = result.scalar_one_or_none()
            assert user is not None

            # Get user's workspaces
            result = await session.execute(select(Workspace).where(Workspace.owner_id == user.id))
            workspaces = result.scalars().all()
            assert len(workspaces) > 0

            # Check notebooks exist
            for workspace in workspaces:
                result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
                notebooks = result.scalars().all()
                assert len(notebooks) > 0, f"No notebooks in workspace {workspace.name}"
        finally:
            break


@pytest.mark.asyncio
async def test_seed_creates_markdown_files():
    """Test that seed_data creates markdown files in notebooks."""
    await init_system_db()

    # Clean up and re-seed to ensure fresh data
    await clean_test_data()
    await seed_data()

    # Verify that seed data users and their workspaces exist
    async for session in get_system_session():
        try:
            # Check the first test user
            user_data = TEST_USERS[0]
            result = await session.execute(select(User).where(User.username == user_data["username"]))
            user = result.scalar_one_or_none()
            assert user is not None, f"Test user '{user_data['username']}' not found after seeding"

            # Get user's workspaces
            result = await session.execute(select(Workspace).where(Workspace.owner_id == user.id))
            workspaces = result.scalars().all()
            assert len(workspaces) > 0, f"No workspaces found for user '{user.username}' after seeding"

            # Check for notebooks and files
            found_file_with_frontmatter = False
            for workspace in workspaces:
                workspace_path = Path(workspace.path)
                if not workspace_path.exists():
                    continue

                # Get notebooks for this workspace
                result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
                notebooks = result.scalars().all()

                for notebook in notebooks:
                    notebook_path = workspace_path / notebook.path
                    if notebook_path.exists():
                        md_files = list(notebook_path.glob("*.md"))
                        for md_file in md_files:
                            if not md_file.name.startswith("."):
                                content = md_file.read_text()
                                if "---" in content:  # Has frontmatter
                                    found_file_with_frontmatter = True
                                    break
                        if found_file_with_frontmatter:
                            break
                if found_file_with_frontmatter:
                    break

            assert found_file_with_frontmatter, f"No markdown files with frontmatter found for user '{user.username}' after clean seeding"
        finally:
            pass


@pytest.mark.asyncio
async def test_seed_is_idempotent():
    """Test that running seed_data multiple times doesn't create duplicates."""
    await init_system_db()

    # Run seed script twice
    await seed_data()
    await seed_data()

    # Verify no duplicate users
    async for session in get_system_session():
        try:
            for user_data in TEST_USERS:
                result = await session.execute(select(User).where(User.username == user_data["username"]))
                users = result.scalars().all()
                assert len(users) == 1, f"Duplicate users found for {user_data['username']}"
        finally:
            break


@pytest.mark.asyncio
async def test_clean_removes_test_data():
    """Test that clean_test_data removes all test users and data."""
    await init_system_db()

    # Ensure data exists
    await seed_data()

    # Clean up
    await clean_test_data()

    # Verify users were deleted
    async for session in get_system_session():
        try:
            for user_data in TEST_USERS:
                result = await session.execute(select(User).where(User.username == user_data["username"]))
                user = result.scalar_one_or_none()
                assert user is None, f"User {user_data['username']} not deleted"
        finally:
            break


@pytest.mark.asyncio
async def test_password_hashing():
    """Test that passwords are properly hashed."""
    await init_system_db()

    # Run seed script
    await seed_data()

    # Verify password is hashed (not plain text)
    async for session in get_system_session():
        try:
            result = await session.execute(select(User).where(User.username == "demo"))
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.hashed_password != "demo123456"
            assert "$" in user.hashed_password  # PBKDF2 format includes $
            assert len(user.hashed_password) > 50  # Hashed passwords are long
        finally:
            break


@pytest.mark.asyncio
async def test_workspace_theme_settings():
    """Test that workspaces have theme settings."""
    await init_system_db()

    # Run seed script
    await seed_data()

    # Verify workspaces have theme settings
    async for session in get_system_session():
        try:
            result = await session.execute(select(Workspace))
            workspaces = result.scalars().all()

            for workspace in workspaces:
                assert workspace.theme_setting is not None
                assert workspace.theme_setting in ["cream", "manila", "white", "obsidian"]
        finally:
            break

"""Unit tests for the workspace permission level resolver (codex.core.permissions)."""

from uuid import uuid4

import pytest
from sqlmodel import select

from codex.api.auth import get_password_hash
from codex.core.permissions import (
    PermissionLevel,
    check_permission,
    effective_level,
    has_permission,
)
from codex.db.database import async_session_maker
from codex.db.models import User, Workspace, WorkspacePermission


async def _create_user(session, *, username: str | None = None) -> User:
    username = username or f"user-{uuid4().hex[:8]}"
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("password123"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_workspace(session, *, owner: User) -> Workspace:
    slug = f"ws-{uuid4().hex[:8]}"
    workspace = Workspace(
        name=slug,
        slug=slug,
        path=f"/tmp/codex-test-{slug}",
        owner_id=owner.id,
    )
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace


async def _grant(session, *, workspace: Workspace, user: User, level: str) -> WorkspacePermission:
    grant = WorkspacePermission(workspace_id=workspace.id, user_id=user.id, permission_level=level)
    session.add(grant)
    await session.commit()
    await session.refresh(grant)
    return grant


class TestPermissionLevelHierarchy:
    """The hierarchy must order as read < comment < write < admin."""

    def test_ordering(self):
        assert PermissionLevel.READ < PermissionLevel.COMMENT
        assert PermissionLevel.COMMENT < PermissionLevel.WRITE
        assert PermissionLevel.WRITE < PermissionLevel.ADMIN
        assert PermissionLevel.READ < PermissionLevel.ADMIN

    def test_equal_level_satisfies_itself(self):
        for level in PermissionLevel:
            assert has_permission(level, level)

    def test_higher_level_satisfies_lower_requirement(self):
        assert has_permission(PermissionLevel.ADMIN, PermissionLevel.WRITE)
        assert has_permission(PermissionLevel.ADMIN, PermissionLevel.COMMENT)
        assert has_permission(PermissionLevel.ADMIN, PermissionLevel.READ)
        assert has_permission(PermissionLevel.WRITE, PermissionLevel.COMMENT)
        assert has_permission(PermissionLevel.WRITE, PermissionLevel.READ)
        assert has_permission(PermissionLevel.COMMENT, PermissionLevel.READ)

    def test_lower_level_does_not_satisfy_higher_requirement(self):
        assert not has_permission(PermissionLevel.READ, PermissionLevel.COMMENT)
        assert not has_permission(PermissionLevel.READ, PermissionLevel.WRITE)
        assert not has_permission(PermissionLevel.READ, PermissionLevel.ADMIN)
        assert not has_permission(PermissionLevel.COMMENT, PermissionLevel.WRITE)
        assert not has_permission(PermissionLevel.COMMENT, PermissionLevel.ADMIN)
        assert not has_permission(PermissionLevel.WRITE, PermissionLevel.ADMIN)

    def test_none_level_satisfies_nothing(self):
        for required in PermissionLevel:
            assert not has_permission(None, required)

    def test_from_str_round_trip(self):
        assert PermissionLevel.from_str("read") is PermissionLevel.READ
        assert PermissionLevel.from_str("comment") is PermissionLevel.COMMENT
        assert PermissionLevel.from_str("write") is PermissionLevel.WRITE
        assert PermissionLevel.from_str("admin") is PermissionLevel.ADMIN
        assert PermissionLevel.from_str("ADMIN") is PermissionLevel.ADMIN

    def test_from_str_rejects_unknown_level(self):
        with pytest.raises(ValueError):
            PermissionLevel.from_str("superadmin")


class TestEffectiveLevelResolver:
    """effective_level() must resolve owner, granted collaborator, and no-access cases."""

    async def test_owner_is_always_admin(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)

            level = await effective_level(owner, workspace, session)

            assert level is PermissionLevel.ADMIN

    async def test_owner_is_admin_even_without_explicit_grant_row(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)

            # No WorkspacePermission row exists for the owner; ownership alone grants admin.
            result = await session.execute(
                select(WorkspacePermission).where(WorkspacePermission.workspace_id == workspace.id)
            )
            assert result.scalar_one_or_none() is None

            assert await effective_level(owner, workspace, session) is PermissionLevel.ADMIN

    @pytest.mark.parametrize("granted_level", ["read", "comment", "write", "admin"])
    async def test_collaborator_gets_granted_level(self, granted_level):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)
            collaborator = await _create_user(session)
            await _grant(session, workspace=workspace, user=collaborator, level=granted_level)

            level = await effective_level(collaborator, workspace, session)

            assert level is PermissionLevel.from_str(granted_level)

    async def test_user_without_grant_has_no_access(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)
            stranger = await _create_user(session)

            level = await effective_level(stranger, workspace, session)

            assert level is None

    async def test_grant_on_other_workspace_does_not_leak(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace_a = await _create_workspace(session, owner=owner)
            workspace_b = await _create_workspace(session, owner=owner)
            collaborator = await _create_user(session)
            await _grant(session, workspace=workspace_a, user=collaborator, level="admin")

            assert await effective_level(collaborator, workspace_a, session) is PermissionLevel.ADMIN
            assert await effective_level(collaborator, workspace_b, session) is None


class TestCheckPermission:
    """check_permission() combines resolution with the hierarchical comparison."""

    async def test_owner_passes_any_required_level(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)

            for required in PermissionLevel:
                assert await check_permission(owner, workspace, required, session)

    async def test_read_grant_fails_write_requirement(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)
            collaborator = await _create_user(session)
            await _grant(session, workspace=workspace, user=collaborator, level="read")

            assert await check_permission(collaborator, workspace, PermissionLevel.READ, session)
            assert not await check_permission(collaborator, workspace, PermissionLevel.COMMENT, session)
            assert not await check_permission(collaborator, workspace, PermissionLevel.WRITE, session)
            assert not await check_permission(collaborator, workspace, PermissionLevel.ADMIN, session)

    async def test_write_grant_satisfies_comment_and_read(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)
            collaborator = await _create_user(session)
            await _grant(session, workspace=workspace, user=collaborator, level="write")

            assert await check_permission(collaborator, workspace, PermissionLevel.READ, session)
            assert await check_permission(collaborator, workspace, PermissionLevel.COMMENT, session)
            assert await check_permission(collaborator, workspace, PermissionLevel.WRITE, session)
            assert not await check_permission(collaborator, workspace, PermissionLevel.ADMIN, session)

    async def test_no_access_fails_every_requirement(self):
        async with async_session_maker() as session:
            owner = await _create_user(session)
            workspace = await _create_workspace(session, owner=owner)
            stranger = await _create_user(session)

            for required in PermissionLevel:
                assert not await check_permission(stranger, workspace, required, session)

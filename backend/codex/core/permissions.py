"""Workspace permission level resolution.

Defines the permission level hierarchy (read < comment < write < admin) and a
single `effective_level` resolver that every access-control decision (routes,
websockets, search) should call rather than re-implementing its own checks.

Resolution order (design doc §2.3):
1. Workspace owner -> ADMIN, unconditionally.
2. Org role, if `workspace.org_id` is set: owner/admin -> ADMIN; member ->
   `workspace.org_member_default_level`; guest -> no default (falls through to 3).
3. Explicit `WorkspacePermission` grant for the user -> the granted level.
4. The higher of (2) and (3), or None if neither applies.
"""

from enum import IntEnum

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.core.org_permissions import OrgRoleRank, get_membership
from codex.db.models import User, Workspace, WorkspacePermission


class PermissionLevel(IntEnum):
    """Workspace permission levels, ordered from least to most access."""

    READ = 1
    COMMENT = 2
    WRITE = 3
    ADMIN = 4

    @classmethod
    def from_str(cls, value: str) -> "PermissionLevel":
        """Parse a stored permission_level string (e.g. "read") into a level."""
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Unknown permission level: {value!r}") from None


async def effective_level(
    user: User,
    workspace: Workspace,
    session: AsyncSession,
) -> PermissionLevel | None:
    """Resolve the effective permission level a user has on a workspace.

    Returns None if the user has no access at all.
    """
    if workspace.owner_id == user.id:
        return PermissionLevel.ADMIN

    org_level: PermissionLevel | None = None
    if workspace.org_id is not None:
        membership = await get_membership(session, workspace.org_id, user.id)
        if membership is not None:
            org_rank = OrgRoleRank.from_str(membership.role)
            if org_rank >= OrgRoleRank.ADMIN:
                return PermissionLevel.ADMIN
            if org_rank == OrgRoleRank.MEMBER:
                org_level = PermissionLevel.from_str(workspace.org_member_default_level)
            # Guest gets no default level; access requires an explicit grant below.

    result = await session.execute(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace.id,
            WorkspacePermission.user_id == user.id,
        )
    )
    grants = result.scalars().all()
    grant_level = max((PermissionLevel.from_str(g.permission_level) for g in grants), default=None)

    if org_level is None:
        return grant_level
    if grant_level is None:
        return org_level
    return max(org_level, grant_level)


def has_permission(level: PermissionLevel | None, required: PermissionLevel) -> bool:
    """Return True if `level` meets or exceeds `required` in the hierarchy."""
    if level is None:
        return False
    return level >= required


async def check_permission(
    user: User,
    workspace: Workspace,
    required: PermissionLevel,
    session: AsyncSession,
) -> bool:
    """Resolve `user`'s level on `workspace` and check it against `required`."""
    level = await effective_level(user, workspace, session)
    return has_permission(level, required)


async def require_level(
    user: User,
    workspace: Workspace,
    required: PermissionLevel,
    session: AsyncSession,
) -> None:
    """Assert `user` has at least `required` access to `workspace`.

    Raises a 404 if the user has no access at all (so the workspace's existence
    isn't leaked to outsiders) and a 403 if they have some access but not enough
    to satisfy `required`.
    """
    level = await effective_level(user, workspace, session)
    if level is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not has_permission(level, required):
        raise HTTPException(status_code=403, detail="Insufficient permission for this operation")

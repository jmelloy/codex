"""Collaborator management routes: CRUD over WorkspacePermission grants.

All endpoints here require ADMIN-level access to the workspace, checked via the
permission resolver in `codex.core.permissions`. This is the business-logic layer
described in docs/design/multi-user-multi-org.md §8 phase 1 ("invited collaborators
via the existing table").
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.api.schemas import MessageResponse
from codex.core.permissions import PermissionLevel
from codex.core.websocket import connection_manager, principal_channel
from codex.db.database import get_system_session
from codex.db.models import User, WorkspacePermission

VALID_PERMISSION_LEVELS = {"read", "comment", "write", "admin"}


class CollaboratorInvite(BaseModel):
    """Request body for inviting a collaborator by username or email."""

    username_or_email: str
    permission_level: str = "read"


class CollaboratorUpdate(BaseModel):
    """Request body for updating a collaborator's permission level."""

    permission_level: str


class CollaboratorResponse(BaseModel):
    """A single collaborator entry: a user plus their effective permission level."""

    user_id: int
    username: str
    email: str
    permission_level: str
    is_owner: bool = False
    created_at: str | None = None


router = APIRouter()


def _validate_level(value: str) -> str:
    level = value.lower()
    if level not in VALID_PERMISSION_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission level: {value!r}. Must be one of {sorted(VALID_PERMISSION_LEVELS)}",
        )
    return level


async def _find_user_by_username_or_email(session: AsyncSession, username_or_email: str) -> User | None:
    result = await session.execute(
        select(User).where((User.username == username_or_email) | (User.email == username_or_email))
    )
    return result.scalar_one_or_none()


@router.get("/", response_model=list[CollaboratorResponse])
async def list_collaborators(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all collaborators on a workspace, with the owner marked separately."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )

    owner = await session.get(User, workspace.owner_id)
    collaborators = [
        CollaboratorResponse(
            user_id=owner.id,
            username=owner.username,
            email=owner.email,
            permission_level="admin",
            is_owner=True,
            created_at=workspace.created_at.isoformat() if workspace.created_at else None,
        )
    ]

    result = await session.execute(
        select(WorkspacePermission, User)
        .join(User, WorkspacePermission.user_id == User.id)
        .where(WorkspacePermission.workspace_id == workspace.id)
        .where(WorkspacePermission.user_id != workspace.owner_id)
    )
    for permission, user in result.all():
        collaborators.append(
            CollaboratorResponse(
                user_id=user.id,
                username=user.username,
                email=user.email,
                permission_level=permission.permission_level,
                is_owner=False,
                created_at=permission.created_at.isoformat() if permission.created_at else None,
            )
        )

    return collaborators


@router.post("/", response_model=CollaboratorResponse, status_code=201)
async def invite_collaborator(
    workspace_identifier: str,
    body: CollaboratorInvite,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Invite a collaborator to a workspace by username or email, granting a permission level."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )

    level = _validate_level(body.permission_level)

    grantee = await _find_user_by_username_or_email(session, body.username_or_email)
    if grantee is None:
        raise HTTPException(status_code=404, detail="No user found matching that username or email")

    if grantee.id == workspace.owner_id:
        raise HTTPException(status_code=400, detail="Workspace owner already has admin access")

    existing = await session.execute(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace.id,
            WorkspacePermission.user_id == grantee.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="User is already a collaborator on this workspace")

    permission = WorkspacePermission(workspace_id=workspace.id, user_id=grantee.id, permission_level=level)
    session.add(permission)
    await session.commit()
    await session.refresh(permission)

    await connection_manager.broadcast(
        principal_channel(grantee.id),
        {
            "type": "collaborator_added",
            "workspace_id": workspace.id,
            "workspace_slug": workspace.slug,
            "workspace_name": workspace.name,
            "permission_level": level,
        },
    )

    return CollaboratorResponse(
        user_id=grantee.id,
        username=grantee.username,
        email=grantee.email,
        permission_level=level,
        is_owner=False,
        created_at=permission.created_at.isoformat() if permission.created_at else None,
    )


@router.patch("/{user_id}", response_model=CollaboratorResponse)
async def update_collaborator(
    workspace_identifier: str,
    user_id: int,
    body: CollaboratorUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Change a collaborator's permission level. The owner's level cannot be changed."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )

    if user_id == workspace.owner_id:
        raise HTTPException(status_code=400, detail="Cannot change the workspace owner's permission level")

    level = _validate_level(body.permission_level)

    result = await session.execute(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace.id,
            WorkspacePermission.user_id == user_id,
        )
    )
    permission = result.scalar_one_or_none()
    if permission is None:
        raise HTTPException(status_code=404, detail="Collaborator not found")

    permission.permission_level = level
    session.add(permission)
    await session.commit()
    await session.refresh(permission)

    grantee = await session.get(User, user_id)

    await connection_manager.broadcast(
        principal_channel(user_id),
        {
            "type": "collaborator_updated",
            "workspace_id": workspace.id,
            "workspace_slug": workspace.slug,
            "permission_level": level,
        },
    )

    return CollaboratorResponse(
        user_id=grantee.id,
        username=grantee.username,
        email=grantee.email,
        permission_level=level,
        is_owner=False,
        created_at=permission.created_at.isoformat() if permission.created_at else None,
    )


@router.delete("/{user_id}", response_model=MessageResponse)
async def revoke_collaborator(
    workspace_identifier: str,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Revoke a collaborator's access to a workspace. The owner cannot be revoked."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )

    if user_id == workspace.owner_id:
        raise HTTPException(status_code=400, detail="Cannot revoke the workspace owner's access")

    result = await session.execute(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace.id,
            WorkspacePermission.user_id == user_id,
        )
    )
    permission = result.scalar_one_or_none()
    if permission is None:
        raise HTTPException(status_code=404, detail="Collaborator not found")

    await session.delete(permission)
    await session.commit()

    await connection_manager.broadcast(
        principal_channel(user_id),
        {
            "type": "collaborator_removed",
            "workspace_id": workspace.id,
            "workspace_slug": workspace.slug,
        },
    )

    return {"message": "Collaborator removed"}

"""Workspace routes."""

import re
from pathlib import Path
from typing import Optional
from unicodedata import name
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.db.database import get_system_session, DATA_DIRECTORY
from codex.db.models import User, Workspace



class WorkspaceCreate(BaseModel):
    """Request body for creating a workspace."""

    name: str
    path: Optional[str] = None


class ThemeUpdate(BaseModel):
    """Request body for updating theme setting."""

    theme: str


def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    # Convert to lowercase, replace spaces and special chars with hyphens
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "workspace"

router = APIRouter()


@router.get("/")
async def list_workspaces(
    current_user: User = Depends(get_current_active_user), session: AsyncSession = Depends(get_system_session)
) -> list[Workspace]:
    """List all workspaces for the current user."""
    result = await session.execute(select(Workspace).where(Workspace.owner_id == current_user.id))
    return result.scalars().all()


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Get a specific workspace."""
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/")
async def create_workspace(
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Create a new workspace.

    If path is not provided, automatically creates a folder in the data directory
    based on the workspace name.
    """
    name = body.name
    path = body.path or slugify(name)
    
    base_path = Path(DATA_DIRECTORY) / "workspaces"
    workspace_path = base_path / path

    # Handle name collisions by appending a number
    
    while workspace_path.exists():
        counter = uuid4().hex[:8]
        slug = f"{path}-{counter}"
        workspace_path = base_path / slug

    path = str(workspace_path)

    # Create the workspace directory
    workspace_dir = Path(path)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    workspace = Workspace(name=name, path=path, owner_id=current_user.id)
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace


@router.patch("/{workspace_id}/theme")
async def update_workspace_theme(
    workspace_id: int,
    body: ThemeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Update the theme setting for a workspace."""
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace.theme_setting = body.theme
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace

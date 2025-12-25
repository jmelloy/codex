"""Workspace routes."""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.api.auth import get_current_active_user
from backend.db.database import get_system_session
from backend.db.models import User, Workspace

router = APIRouter()


@router.get("/")
async def list_workspaces(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
) -> list[Workspace]:
    """List all workspaces for the current user."""
    result = await session.execute(
        select(Workspace).where(Workspace.owner_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
) -> Workspace:
    """Get a specific workspace."""
    result = await session.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/")
async def create_workspace(
    name: str,
    path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
) -> Workspace:
    """Create a new workspace."""
    workspace = Workspace(name=name, path=path, owner_id=current_user.id)
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace

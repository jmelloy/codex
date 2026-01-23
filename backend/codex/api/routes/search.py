"""Search routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.db.database import get_system_session
from codex.db.models import User, Workspace

router = APIRouter()


@router.get("/")
async def search(
    q: str,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files and content in a workspace."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # For now, return empty results since search index is not populated
    # This would need proper full-text search implementation with a search engine
    # or SQLite FTS (Full-Text Search) extension
    return {
        "query": q,
        "workspace_id": workspace_id,
        "results": [],
        "message": "Full-text search requires search index population",
    }


@router.get("/tags")
async def search_by_tags(
    tags: str,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files by tags."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    tag_list = [tag.strip() for tag in tags.split(",")]

    # For now, return empty results since tags are stored per-notebook
    # This would require iterating through notebooks in the workspace
    return {
        "tags": tag_list,
        "workspace_id": workspace_id,
        "results": [],
        "message": "Tag search requires notebook-level database queries",
    }

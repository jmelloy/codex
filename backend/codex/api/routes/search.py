"""Search routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.notebooks import get_notebook_by_slug_or_id
from codex.api.routes.workspaces import get_workspace_by_slug_or_id
from codex.db.database import get_system_session
from codex.db.models import Notebook, User, Workspace

router = APIRouter()


@router.get("/")
async def search_deprecated():
    """Search endpoint (REMOVED - use nested route instead)."""
    raise HTTPException(
        status_code=410,
        detail="This endpoint has been removed. Use GET /api/v1/workspaces/{workspace_slug}/search instead"
    )


@router.get("/tags")
async def search_by_tags_deprecated():
    """Tag search endpoint (REMOVED - use nested route instead)."""
    raise HTTPException(
        status_code=410,
        detail="This endpoint has been removed. Use GET /api/v1/workspaces/{workspace_slug}/search/tags instead"
    )


# New nested router for workspace-based search routes
nested_router = APIRouter()


@nested_router.get("/")
async def search_workspace(
    workspace_identifier: str,
    q: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files and content in a workspace (all notebooks)."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)

    # For now, return empty results since search index is not populated
    # This would need proper full-text search implementation with a search engine
    # or SQLite FTS (Full-Text Search) extension
    return {
        "query": q,
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "results": [],
        "message": "Full-text search requires search index population",
    }


@nested_router.get("/tags")
async def search_workspace_by_tags(
    workspace_identifier: str,
    tags: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files by tags in a workspace (all notebooks)."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)

    tag_list = [tag.strip() for tag in tags.split(",")]

    # For now, return empty results since tags are stored per-notebook
    # This would require iterating through notebooks in the workspace
    return {
        "tags": tag_list,
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "results": [],
        "message": "Tag search requires notebook-level database queries",
    }


# Notebook-level nested router
notebook_nested_router = APIRouter()


@notebook_nested_router.get("/")
async def search_notebook(
    workspace_identifier: str,
    notebook_identifier: str,
    q: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files and content in a specific notebook."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    # For now, return empty results since search index is not populated
    return {
        "query": q,
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "notebook_id": notebook.id,
        "notebook_slug": notebook.slug,
        "results": [],
        "message": "Full-text search requires search index population",
    }


@notebook_nested_router.get("/tags")
async def search_notebook_by_tags(
    workspace_identifier: str,
    notebook_identifier: str,
    tags: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files by tags in a specific notebook."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    tag_list = [tag.strip() for tag in tags.split(",")]

    return {
        "tags": tag_list,
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "notebook_id": notebook.id,
        "notebook_slug": notebook.slug,
        "results": [],
        "message": "Tag search requires notebook-level database queries",
    }

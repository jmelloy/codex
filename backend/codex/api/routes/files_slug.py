"""Slug-based file routes for v1 API.

These routes use workspace and notebook slugs instead of IDs:
/api/v1/{workspace_slug}/{notebook_slug}/files/...
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import FileMetadata, Notebook, User, Workspace

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_notebook_by_slugs(
    workspace_slug: str, notebook_slug: str, current_user: User, session: AsyncSession
) -> tuple[Path, Notebook, Workspace]:
    """Helper to get and verify notebook path using slugs.

    Returns:
        Tuple of (notebook_path, notebook_model, workspace_model)

    Raises:
        HTTPException if workspace or notebook not found
    """
    # Verify workspace access by slug
    result = await session.execute(
        select(Workspace).where(Workspace.slug == workspace_slug, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get notebook from system database by slug
    result = await session.execute(
        select(Notebook).where(Notebook.slug == notebook_slug, Notebook.workspace_id == workspace.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Get notebook path
    workspace_path = Path(workspace.path)
    notebook_path = workspace_path / notebook.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found")

    return notebook_path, notebook, workspace


@router.get("/{workspace_slug}/{notebook_slug}/files/")
async def list_files_by_slug(
    workspace_slug: str,
    notebook_slug: str,
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all files in a notebook using workspace and notebook slugs."""
    notebook_path, notebook, workspace = await get_notebook_by_slugs(
        workspace_slug, notebook_slug, current_user, session
    )

    # Get files from the notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = nb_session.execute(select(FileMetadata).offset(skip).limit(limit))
        files = result.scalars().all()

        return [
            {
                "id": f.id,
                "path": f.path,
                "name": f.name,
                "content_type": f.content_type,
                "size": f.size,
                "hash": f.hash,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "modified_at": f.modified_at.isoformat() if f.modified_at else None,
                "indexed_at": f.indexed_at.isoformat() if f.indexed_at else None,
            }
            for f in files
        ]
    finally:
        nb_session.close()


@router.get("/{workspace_slug}/{notebook_slug}/files/{file_id}")
async def get_file_by_slug(
    workspace_slug: str,
    notebook_slug: str,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file metadata using workspace and notebook slugs."""
    notebook_path, notebook, workspace = await get_notebook_by_slugs(
        workspace_slug, notebook_slug, current_user, session
    )

    # Get file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        file = result.scalar_one_or_none()

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "id": file.id,
            "path": file.path,
            "name": file.name,
            "content_type": file.content_type,
            "size": file.size,
            "hash": file.hash,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "modified_at": file.modified_at.isoformat() if file.modified_at else None,
            "indexed_at": file.indexed_at.isoformat() if file.indexed_at else None,
            "notebook_id": notebook.id,
            "notebook_slug": notebook.slug,
            "workspace_id": workspace.id,
            "workspace_slug": workspace.slug,
        }
    finally:
        nb_session.close()


@router.get("/{workspace_slug}/{notebook_slug}/files/by-path")
async def get_file_by_path_and_slug(
    workspace_slug: str,
    notebook_slug: str,
    path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file metadata by path using workspace and notebook slugs."""
    notebook_path, notebook, workspace = await get_notebook_by_slugs(
        workspace_slug, notebook_slug, current_user, session
    )

    # Get file from notebook database by path
    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = nb_session.execute(select(FileMetadata).where(FileMetadata.path == path))
        file = result.scalar_one_or_none()

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "id": file.id,
            "path": file.path,
            "name": file.name,
            "content_type": file.content_type,
            "size": file.size,
            "hash": file.hash,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "modified_at": file.modified_at.isoformat() if file.modified_at else None,
            "indexed_at": file.indexed_at.isoformat() if file.indexed_at else None,
            "notebook_id": notebook.id,
            "notebook_slug": notebook.slug,
            "workspace_id": workspace.id,
            "workspace_slug": workspace.slug,
        }
    finally:
        nb_session.close()

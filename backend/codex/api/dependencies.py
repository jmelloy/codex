"""Shared API dependencies for workspace and notebook lookup by slug."""

from pathlib import Path

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.db.database import get_system_session
from codex.db.models import Notebook, User, Workspace


def extract_workspace_slug(workspace: Workspace) -> str:
    """Extract slug from workspace's full path.

    The workspace slug is the last component of the path.
    E.g., /data/workspaces/my-lab -> my-lab
    """
    return Path(workspace.path).name


async def get_workspace_by_slug(
    workspace: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Get workspace by slug with authorization check.

    Args:
        workspace: The workspace slug (last component of workspace path)
        current_user: The authenticated user
        session: Database session

    Returns:
        The Workspace object

    Raises:
        HTTPException: 404 if workspace not found or not owned by user
    """
    result = await session.execute(select(Workspace).where(Workspace.owner_id == current_user.id))
    workspaces = result.scalars().all()

    for ws in workspaces:
        if extract_workspace_slug(ws) == workspace:
            return ws

    raise HTTPException(status_code=404, detail="Workspace not found")


async def get_notebook_by_slugs(
    workspace: str,
    notebook: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> tuple[Workspace, Notebook]:
    """Get workspace and notebook by their slugs.

    Args:
        workspace: The workspace slug
        notebook: The notebook slug (relative path from workspace)
        current_user: The authenticated user
        session: Database session

    Returns:
        Tuple of (Workspace, Notebook)

    Raises:
        HTTPException: 404 if workspace or notebook not found
    """
    ws = await get_workspace_by_slug(workspace, current_user, session)

    result = await session.execute(
        select(Notebook).where(Notebook.workspace_id == ws.id, Notebook.path == notebook)
    )
    nb = result.scalar_one_or_none()

    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    return ws, nb


async def get_notebook_path_from_slugs(
    workspace: str,
    notebook: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> tuple[Workspace, Notebook, Path]:
    """Get workspace, notebook, and computed notebook path by slugs.

    Args:
        workspace: The workspace slug
        notebook: The notebook slug
        current_user: The authenticated user
        session: Database session

    Returns:
        Tuple of (Workspace, Notebook, notebook_path)

    Raises:
        HTTPException: 404 if workspace, notebook, or path not found
    """
    ws, nb = await get_notebook_by_slugs(workspace, notebook, current_user, session)

    workspace_path = Path(ws.path)
    notebook_path = workspace_path / nb.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found")

    return ws, nb, notebook_path

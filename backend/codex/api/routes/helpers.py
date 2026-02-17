"""Shared helper functions for API routes."""

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from codex.api.routes.notebooks import get_notebook_by_slug_or_id
from codex.api.routes.workspaces import get_workspace_by_slug_or_id
from codex.db.models import Notebook, User, Workspace


async def get_notebook_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User,
    session: AsyncSession,
) -> tuple[Path, Notebook, Workspace]:
    """Get and verify notebook path using workspace and notebook identifiers.

    Returns:
        Tuple of (notebook_path, notebook_model, workspace_model)

    Raises:
        HTTPException if workspace or notebook not found
    """
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    workspace_path = Path(workspace.path).resolve()
    notebook_path = workspace_path / notebook.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found")

    return notebook_path, notebook, workspace

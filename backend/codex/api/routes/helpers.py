"""Shared helper functions for API routes."""

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from codex.api.routes.notebooks import get_notebook_by_slug
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.core.permissions import PermissionLevel
from codex.db.models import Notebook, User, Workspace


async def get_notebook_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User,
    session: AsyncSession,
    required_level: PermissionLevel = PermissionLevel.READ,
) -> tuple[Path, Notebook, Workspace]:
    """Get and verify notebook path using workspace and notebook identifiers.

    Args:
        required_level: Minimum permission level required for this operation

    Returns:
        Tuple of (notebook_path, notebook_model, workspace_model)

    Raises:
        HTTPException if workspace or notebook not found, or the caller's permission
            level is below `required_level`
    """
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=required_level
    )
    notebook = await get_notebook_by_slug(notebook_identifier, workspace, session)

    workspace_path = Path(workspace.path).resolve()
    notebook_path = workspace_path / notebook.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found")

    return notebook_path, notebook, workspace

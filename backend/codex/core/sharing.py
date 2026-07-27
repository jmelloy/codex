"""Shared-workspace detection for the git export-only demotion (issue #544).

Design doc §3.5: for shared workspaces, S3 versioning + the sync journal are
the source of truth for history; per-notebook git stops being the
sync/concurrency mechanism and becomes a downstream export only. A workspace
counts as "shared" once more than its owner can reach it -- it belongs to an
org, or it has explicit `WorkspacePermission` grants to other users. Personal
workspaces (no org, no grants) keep today's bidirectional git behavior
untouched.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from codex.db.database import get_system_session_sync
from codex.db.models import Notebook, Workspace, WorkspacePermission

logger = logging.getLogger(__name__)


async def is_workspace_shared(workspace: Workspace, session: AsyncSession) -> bool:
    """Async check for use from API routes (already hold an AsyncSession)."""
    if workspace.org_id is not None:
        return True
    result = await session.execute(
        select(WorkspacePermission.id).where(WorkspacePermission.workspace_id == workspace.id).limit(1)
    )
    return result.first() is not None


def is_workspace_shared_sync(workspace: Workspace, session: Session) -> bool:
    """Sync equivalent of `is_workspace_shared`, for callers holding a sync `Session`."""
    if workspace.org_id is not None:
        return True
    result = session.execute(
        select(WorkspacePermission.id).where(WorkspacePermission.workspace_id == workspace.id).limit(1)
    )
    return result.first() is not None


def is_notebook_shared(notebook_id: int) -> bool:
    """Sync, self-contained lookup for use from watcher threads (no async context there).

    Fails open (returns False) if the notebook or workspace can't be resolved,
    so a transient system-DB hiccup doesn't wedge git sync for personal
    notebooks -- the common case.
    """
    try:
        with get_system_session_sync() as session:
            notebook = session.get(Notebook, notebook_id)
            if notebook is None:
                return False
            workspace = session.get(Workspace, notebook.workspace_id)
            if workspace is None:
                return False
            return is_workspace_shared_sync(workspace, session)
    except Exception as e:
        logger.warning(f"Could not determine sharing status for notebook {notebook_id}: {e}")
        return False

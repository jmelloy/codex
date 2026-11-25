"""Remote git endpoints: clone a notebook from a remote, manage remotes, fetch/pull/push."""

import asyncio
import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from codex.api.auth import get_current_active_user
from codex.api.routes.helpers import get_notebook_path_nested
from codex.api.routes.notebooks import slug_exists_for_workspace
from codex.api.routes.utils import slugify
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.core.git_manager import GitManager
from codex.core.git_remote import RemoteGitError, clone_repository, redact_url, validate_remote_url
from codex.core.permissions import PermissionLevel
from codex.core.watcher import NotebookWatcher
from codex.core.workspace_sharing import is_shared_workspace
from codex.db.database import get_system_session, init_notebook_db
from codex.db.models import Notebook, User

logger = logging.getLogger(__name__)

clone_router = APIRouter()
router = APIRouter()


class RemoteAuth(BaseModel):
    """Per-request credentials. Never stored."""

    token: str | None = Field(default=None, repr=False)
    username: str | None = None
    ssh_private_key: str | None = Field(default=None, repr=False)

    def kwargs(self) -> dict:
        return {"token": self.token, "username": self.username, "ssh_private_key": self.ssh_private_key}


class CloneRequest(RemoteAuth):
    url: str
    name: str | None = None
    branch: str | None = None


class RemoteSet(BaseModel):
    name: str = "origin"
    url: str


class RemoteOperation(RemoteAuth):
    remote: str = "origin"
    ref: str | None = None


@clone_router.post("/clone")
async def clone_notebook(
    workspace_identifier: str,
    body: CloneRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a notebook by cloning a remote git repository."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.WRITE
    )
    if is_shared_workspace(workspace):
        raise HTTPException(status_code=400, detail="Git remotes are not supported for shared workspaces")
    try:
        validate_remote_url(body.url)
    except RemoteGitError as e:
        raise HTTPException(status_code=400, detail=str(e))

    default_name = Path(redact_url(body.url).rstrip("/")).name.removesuffix(".git") or "notebook"
    name = body.name or default_name
    final_slug = slugify(name, default="notebook")
    workspace_path = Path(workspace.path).resolve()
    while (workspace_path / final_slug).exists() or await slug_exists_for_workspace(session, final_slug, workspace.id):
        final_slug = f"{slugify(name, default='notebook')}-{uuid4().hex[:8]}"
    notebook_path = workspace_path / final_slug

    try:
        await asyncio.to_thread(clone_repository, body.url, str(notebook_path), body.branch, **body.kwargs())
    except RemoteGitError as e:
        shutil.rmtree(notebook_path, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Clone failed: {e}")

    try:
        init_notebook_db(str(notebook_path))
        notebook = Notebook(workspace_id=workspace.id, name=name, slug=final_slug, path=final_slug)
        session.add(notebook)
        await session.commit()
        await session.refresh(notebook)
        try:
            NotebookWatcher(str(notebook_path), notebook.id).start()
        except Exception:
            logger.exception("Cloned notebook but watcher failed to start: %s", notebook_path)
    except Exception as e:
        shutil.rmtree(notebook_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Error registering cloned notebook: {e}")

    return {"id": notebook.id, "slug": notebook.slug, "name": notebook.name, "path": notebook.path}


@router.get("/")
async def list_remotes(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    path, _, _ = await get_notebook_path_nested(workspace_identifier, notebook_identifier, current_user, session)
    return await asyncio.to_thread(GitManager(str(path)).list_remotes)


@router.put("/")
async def set_remote(
    workspace_identifier: str,
    notebook_identifier: str,
    body: RemoteSet,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    path, _, _ = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session, PermissionLevel.WRITE
    )
    try:
        await asyncio.to_thread(GitManager(str(path)).set_remote, body.name, body.url)
    except RemoteGitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"name": body.name, "url": redact_url(body.url)}


@router.delete("/{remote_name}")
async def delete_remote(
    workspace_identifier: str,
    notebook_identifier: str,
    remote_name: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    path, _, _ = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session, PermissionLevel.WRITE
    )
    if not await asyncio.to_thread(GitManager(str(path)).remove_remote, remote_name):
        raise HTTPException(status_code=404, detail="Remote not found")
    return {"message": "Remote removed"}


def _operation_route(op: str):
    async def handler(
        workspace_identifier: str,
        notebook_identifier: str,
        body: RemoteOperation | None = None,
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_system_session),
    ):
        body = body or RemoteOperation()
        path, _, _ = await get_notebook_path_nested(
            workspace_identifier, notebook_identifier, current_user, session, PermissionLevel.WRITE
        )
        try:
            output = await asyncio.to_thread(
                GitManager(str(path)).remote_operation, op, body.remote, body.ref, **body.kwargs()
            )
        except RemoteGitError as e:
            raise HTTPException(status_code=400, detail=f"{op} failed: {e}")
        return {"operation": op, "remote": body.remote, "output": output}

    handler.__name__ = f"remote_{op}"
    return handler


for _op in ("fetch", "pull", "push"):
    router.post(f"/{_op}")(_operation_route(_op))

"""S3 sync journal + change feed routes (issue #541, design doc §3.2/§3.4).

`POST .../sync/push-complete` records a journal row for a completed S3 write,
attributed to the calling principal. `GET .../sync/changes?since=cursor` lets
sync clients pull new rows incrementally. Both are workspace-scoped; the
change feed also fans out live over the existing `workspace:{id}` WebSocket
channel so connected clients don't have to poll.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import PermissionScope, get_current_active_user, require_scope
from codex.api.routes.notebooks import get_notebook_by_slug
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.core.permissions import PermissionLevel
from codex.core.websocket import connection_manager, workspace_channel
from codex.db.database import get_system_session
from codex.db.models import SyncJournal, User

router = APIRouter()

VALID_OPS = {"created", "modified", "deleted"}
DEFAULT_CHANGES_LIMIT = 200
MAX_CHANGES_LIMIT = 500


class PushCompleteRequest(BaseModel):
    """Body for `POST .../sync/push-complete`."""

    notebook_slug: str
    path: str  # S3 object key for the synced file
    s3_version_id: str
    op: str  # "created" | "modified" | "deleted"


class SyncChangeOut(BaseModel):
    """A single `sync_journal` row, as returned by the change feed."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ws_id: int
    nb_id: int
    path: str
    s3_version_id: str
    actor_principal_id: int | None
    op: str
    ts: datetime


class SyncChangesResponse(BaseModel):
    """Response for `GET .../sync/changes`."""

    changes: list[SyncChangeOut]
    cursor: int


async def _record_journal_entry(
    session: AsyncSession,
    *,
    ws_id: int,
    nb_id: int,
    path: str,
    s3_version_id: str,
    op: str,
    actor_principal_id: int | None,
) -> tuple[SyncJournal, bool]:
    """Insert a journal row, deduplicating on (path, s3_version_id).

    Returns `(entry, created)`. `created` is False when a row for this exact
    (path, s3_version_id) pair already exists — e.g. this push-complete call
    raced a bucket-notification-sourced write for the same S3 object version —
    in which case the existing row is returned rather than inserting a
    duplicate.
    """
    entry = SyncJournal(
        ws_id=ws_id,
        nb_id=nb_id,
        path=path,
        s3_version_id=s3_version_id,
        op=op,
        actor_principal_id=actor_principal_id,
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(SyncJournal).where(
                SyncJournal.path == path,
                SyncJournal.s3_version_id == s3_version_id,
            )
        )
        return result.scalar_one(), False
    await session.refresh(entry)
    return entry, True


@router.post("/push-complete", response_model=SyncChangeOut)
async def push_complete(
    workspace_identifier: str,
    body: PushCompleteRequest,
    current_user: User = Depends(require_scope(PermissionScope.SYNC_CREDENTIALS)),
    session: AsyncSession = Depends(get_system_session),
) -> SyncJournal:
    """Record a completed S3 push in the sync journal, attributed to the caller.

    Requires the `sync:credentials` scope when authenticated via a personal
    access token (design doc §3.4); full human sessions are unaffected.
    Duplicate (path, s3_version_id) pairs are deduplicated: calling this twice
    for the same object version returns the existing journal row instead of
    creating a second one.
    """
    if body.op not in VALID_OPS:
        raise HTTPException(status_code=400, detail=f"op must be one of {sorted(VALID_OPS)}")

    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.WRITE
    )
    notebook = await get_notebook_by_slug(body.notebook_slug, workspace, session)

    entry, created = await _record_journal_entry(
        session,
        ws_id=workspace.id,
        nb_id=notebook.id,
        path=body.path,
        s3_version_id=body.s3_version_id,
        op=body.op,
        actor_principal_id=current_user.id,
    )

    if created:
        await connection_manager.broadcast(
            workspace_channel(workspace.id),
            {
                "type": "sync.change",
                "id": entry.id,
                "ws_id": entry.ws_id,
                "nb_id": entry.nb_id,
                "path": entry.path,
                "s3_version_id": entry.s3_version_id,
                "actor_principal_id": entry.actor_principal_id,
                "op": entry.op,
                "ts": entry.ts.isoformat(),
            },
        )

    return entry


@router.get("/changes", response_model=SyncChangesResponse)
async def get_changes(
    workspace_identifier: str,
    since: int = 0,
    limit: int = DEFAULT_CHANGES_LIMIT,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> SyncChangesResponse:
    """Cursor-based incremental pull of journal rows for a workspace.

    Returns every row with `id > since`, in cursor order, plus the cursor to
    pass as `since` on the next call (the highest `id` returned, or `since`
    unchanged if there are no new rows).
    """
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    limit = max(1, min(limit, MAX_CHANGES_LIMIT))

    result = await session.execute(
        select(SyncJournal)
        .where(SyncJournal.ws_id == workspace.id, SyncJournal.id > since)
        .order_by(SyncJournal.id.asc())
        .limit(limit)
    )
    changes = list(result.scalars().all())
    cursor = changes[-1].id if changes else since
    return SyncChangesResponse(changes=changes, cursor=cursor)

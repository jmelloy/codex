"""S3 sync routes: credential vending + journal/change feed + conflicts.

Credential vending (issue #540, design doc §3.3):
    POST .../sync/credentials  - scoped, short-lived STS credentials
    POST .../sync/presign      - presigned-URL batch fallback for stores without STS

Journal + change feed (issue #541, design doc §3.2/§3.4):
    POST .../sync/push-complete - records a journal row for a completed S3 write
    GET  .../sync/changes       - lets sync clients pull new rows incrementally

Conflict detection + conflict copies (issue #543, design doc §3.4):
    POST .../sync/push-complete - also runs compare-and-swap conflict detection
                                  when the caller reports `base_s3_version_id`
    GET  .../sync/conflicts     - lists detected conflicts for the workspace
    POST .../sync/conflicts/{id}/resolve - marks a conflict acknowledged

Both groups work identically for human JWTs and bot PATs: a JWT represents a
full human session (permission level is the only gate), while a PAT must carry
the `sync:credentials` scope and, if it's bound to a specific workspace, can
only act on that workspace. The change feed also fans out live over the
existing `workspace:{id}` WebSocket channel so connected clients don't have to
poll.
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import PermissionScope, User, get_current_active_user, require_scope
from codex.api.routes.notebooks import get_notebook_by_slug
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.core.events import build_event, enqueue_fanout
from codex.core.permissions import PermissionLevel
from codex.core.sync_conflicts import copy_object_version, get_latest_journal_entry, unique_conflict_copy_path
from codex.core.sync_credentials import (
    SYNC_CREDENTIAL_TTL,
    WRITE_OPERATIONS,
    generate_presigned_batch,
    is_sts_configured,
    vend_sts_credentials,
)
from codex.core.websocket import connection_manager, workspace_channel
from codex.db.database import get_system_session
from codex.db.models import SyncJournal, Workspace

router = APIRouter()

VALID_OPS = {"created", "modified", "deleted"}
DEFAULT_CHANGES_LIMIT = 200
MAX_CHANGES_LIMIT = 500


class CredentialsRequest(BaseModel):
    """Request body for /sync/credentials. `write=True` asks for read-write creds."""

    write: bool = False


class CredentialsResponse(BaseModel):
    """Short-lived, workspace-scoped STS credentials (design doc §3.3)."""

    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: str
    bucket: str
    prefix: str
    region: str
    endpoint_url: str | None = None


class PresignItem(BaseModel):
    """One requested presigned URL: `key` is relative to the workspace's S3 prefix."""

    key: str
    operation: Literal["get", "put", "delete", "list"]


class PresignRequest(BaseModel):
    """Request body for /sync/presign: a batch of key+operation pairs."""

    items: list[PresignItem]


class PresignedURL(BaseModel):
    """One presigned URL result."""

    key: str
    operation: str
    method: str
    url: str


class PresignResponse(BaseModel):
    """Batch presign response, sharing one bucket/prefix/expiry across all items."""

    bucket: str
    prefix: str
    expires_in: int
    urls: list[PresignedURL]


class PushCompleteRequest(BaseModel):
    """Body for `POST .../sync/push-complete`.

    `base_s3_version_id` is optional and opt-in (issue #543): a client that
    reports it gets compare-and-swap conflict detection against the journal's
    current state for `path`; a client that omits it just records the write,
    matching the pre-#543 behavior.
    """

    notebook_slug: str
    path: str  # S3 object key for the synced file
    s3_version_id: str
    op: str  # "created" | "modified" | "deleted"
    base_s3_version_id: str | None = None


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
    base_s3_version_id: str | None = None
    conflict: bool = False
    conflict_of_id: int | None = None
    conflict_copy_path: str | None = None
    resolved_at: datetime | None = None
    resolved_by_id: int | None = None


class SyncChangesResponse(BaseModel):
    """Response for `GET .../sync/changes`."""

    changes: list[SyncChangeOut]
    cursor: int


class ConflictOut(BaseModel):
    """A detected conflict: the winning write plus the losing version it raced (issue #543)."""

    id: int  # the winning journal row's id -- this conflict's identifier
    ws_id: int
    nb_id: int
    path: str
    winning_s3_version_id: str
    winning_actor_id: int | None
    losing_s3_version_id: str
    losing_actor_id: int | None
    conflict_copy_path: str
    detected_at: datetime
    resolved_at: datetime | None
    resolved_by_id: int | None


class ConflictsResponse(BaseModel):
    """Response for `GET .../sync/conflicts`."""

    conflicts: list[ConflictOut]


def _enforce_pat_workspace_scope(request: Request, workspace: Workspace) -> None:
    """Reject the request if the caller's PAT is bound to a different workspace.

    A JWT (full human session) has no workspace binding (`token_workspace_id`
    is None) and always passes. A workspace-scoped PAT may only vend
    credentials for its own workspace (design doc §3.3).
    """
    token_workspace_id = getattr(request.state, "token_workspace_id", None)
    if token_workspace_id is not None and token_workspace_id != workspace.id:
        raise HTTPException(status_code=403, detail="This token is scoped to a different workspace")


@router.post("/credentials", response_model=CredentialsResponse)
async def get_sync_credentials(
    workspace_identifier: str,
    body: CredentialsRequest,
    request: Request,
    current_user: User = Depends(require_scope(PermissionScope.SYNC_CREDENTIALS)),
    session: AsyncSession = Depends(get_system_session),
) -> CredentialsResponse:
    """Vend short-lived STS credentials scoped to this workspace's S3 prefix.

    Requires READ access for read-only credentials, WRITE access for
    read-write credentials (`body.write=True`). Returns 501 if STS vending
    isn't configured on this server -- clients should fall back to
    `POST .../sync/presign` in that case.
    """
    required_level = PermissionLevel.WRITE if body.write else PermissionLevel.READ
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session, required_level=required_level)
    _enforce_pat_workspace_scope(request, workspace)

    if not is_sts_configured():
        raise HTTPException(
            status_code=501,
            detail="STS credential vending is not configured on this server; use /sync/presign instead",
        )

    try:
        creds = vend_sts_credentials(workspace, body.write)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return CredentialsResponse(
        access_key_id=creds["access_key_id"],
        secret_access_key=creds["secret_access_key"],
        session_token=creds["session_token"],
        expiration=creds["expiration"].isoformat(),
        bucket=creds["bucket"],
        prefix=creds["prefix"],
        region=creds["region"],
        endpoint_url=creds["endpoint_url"],
    )


@router.post("/presign", response_model=PresignResponse)
async def get_sync_presigned_urls(
    workspace_identifier: str,
    body: PresignRequest,
    request: Request,
    current_user: User = Depends(require_scope(PermissionScope.SYNC_CREDENTIALS)),
    session: AsyncSession = Depends(get_system_session),
) -> PresignResponse:
    """Presigned-URL batch fallback for S3-compatible stores without STS support.

    Same authz as /credentials: any put/delete in the batch requires WRITE
    access to the workspace; a batch of only get/list requires READ.
    """
    if not body.items:
        raise HTTPException(status_code=400, detail="items must not be empty")

    required_level = (
        PermissionLevel.WRITE
        if any(item.operation in WRITE_OPERATIONS for item in body.items)
        else PermissionLevel.READ
    )
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session, required_level=required_level)
    _enforce_pat_workspace_scope(request, workspace)

    try:
        bucket, prefix, urls = generate_presigned_batch(workspace, [(item.key, item.operation) for item in body.items])
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return PresignResponse(
        bucket=bucket,
        prefix=prefix,
        expires_in=SYNC_CREDENTIAL_TTL,
        urls=[PresignedURL(**url) for url in urls],
    )


async def _record_journal_entry(
    session: AsyncSession,
    *,
    ws_id: int,
    nb_id: int,
    path: str,
    s3_version_id: str,
    op: str,
    actor_principal_id: int | None,
    base_s3_version_id: str | None = None,
    conflict: bool = False,
    conflict_of_id: int | None = None,
    conflict_copy_path: str | None = None,
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
        base_s3_version_id=base_s3_version_id,
        conflict=conflict,
        conflict_of_id=conflict_of_id,
        conflict_copy_path=conflict_copy_path,
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


async def _broadcast_change(workspace_id: int, entry: SyncJournal) -> None:
    """Fan a journal row out over the `workspace:{id}` WebSocket channel."""
    await connection_manager.broadcast(
        workspace_channel(workspace_id),
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
            "conflict": entry.conflict,
            "conflict_copy_path": entry.conflict_copy_path,
        },
    )


async def _handle_conflict(
    request: Request,
    session: AsyncSession,
    *,
    workspace: Workspace,
    notebook_id: int,
    prior: SyncJournal,
    winner: SyncJournal,
) -> SyncJournal:
    """Materialize `prior`'s content as a conflict copy and notify both writers.

    `prior` is the losing version -- current in the journal when `winner`'s
    write raced past it. Copies `prior`'s S3 object version to a new
    `name (conflict YYYY-MM-DD).ext` key, journals that copy, flags `winner`
    with the conflict pointer, and fires a `sync.conflict` event to both
    writers (design doc §3.4).
    """
    today = datetime.now(UTC).date()
    dest_key = await unique_conflict_copy_path(
        session, ws_id=workspace.id, nb_id=notebook_id, path=prior.path, when=today
    )

    try:
        copy_version_id = copy_object_version(prior.path, prior.s3_version_id, dest_key)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    copy_entry, _ = await _record_journal_entry(
        session,
        ws_id=workspace.id,
        nb_id=notebook_id,
        path=dest_key,
        s3_version_id=copy_version_id,
        op="created",
        actor_principal_id=None,
        conflict=True,
        conflict_of_id=prior.id,
    )
    await _broadcast_change(workspace.id, copy_entry)

    winner.conflict = True
    winner.conflict_of_id = prior.id
    winner.conflict_copy_path = dest_key
    session.add(winner)

    event = build_event(
        workspace_id=workspace.id,
        actor_id=winner.actor_principal_id,
        kind="sync.conflict",
        subject={
            "path": prior.path,
            "notebook_id": notebook_id,
            "conflict_copy_path": dest_key,
            "winning_actor_id": winner.actor_principal_id,
            "losing_actor_id": prior.actor_principal_id,
            "winning_s3_version_id": winner.s3_version_id,
            "losing_s3_version_id": prior.s3_version_id,
        },
    )
    session.add(event)

    await session.commit()
    await session.refresh(winner)
    await session.refresh(event)

    await enqueue_fanout(request, event.id)

    return winner


@router.post("/push-complete", response_model=SyncChangeOut)
async def push_complete(
    workspace_identifier: str,
    body: PushCompleteRequest,
    request: Request,
    current_user: User = Depends(require_scope(PermissionScope.SYNC_CREDENTIALS)),
    session: AsyncSession = Depends(get_system_session),
) -> SyncJournal:
    """Record a completed S3 push in the sync journal, attributed to the caller.

    Requires the `sync:credentials` scope when authenticated via a personal
    access token (design doc §3.4); full human sessions are unaffected.
    Duplicate (path, s3_version_id) pairs are deduplicated: calling this twice
    for the same object version returns the existing journal row instead of
    creating a second one.

    If `body.base_s3_version_id` is set, runs compare-and-swap conflict
    detection (issue #543): when the journal's latest entry for `path` no
    longer matches that base version, the write still lands, but the prior
    (losing) version is copied out to a conflict-copy key and both writers
    are notified.
    """
    if body.op not in VALID_OPS:
        raise HTTPException(status_code=400, detail=f"op must be one of {sorted(VALID_OPS)}")

    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.WRITE
    )
    notebook = await get_notebook_by_slug(body.notebook_slug, workspace, session)

    prior = None
    if body.base_s3_version_id is not None:
        prior = await get_latest_journal_entry(session, ws_id=workspace.id, nb_id=notebook.id, path=body.path)
        if prior is not None and prior.s3_version_id == body.base_s3_version_id:
            prior = None  # base matches -- no conflict

    entry, created = await _record_journal_entry(
        session,
        ws_id=workspace.id,
        nb_id=notebook.id,
        path=body.path,
        s3_version_id=body.s3_version_id,
        op=body.op,
        actor_principal_id=current_user.id,
        base_s3_version_id=body.base_s3_version_id,
    )

    if created and prior is not None:
        entry = await _handle_conflict(
            request, session, workspace=workspace, notebook_id=notebook.id, prior=prior, winner=entry
        )

    if created:
        await _broadcast_change(workspace.id, entry)

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


@router.get("/conflicts", response_model=ConflictsResponse)
async def list_conflicts(
    workspace_identifier: str,
    resolved: bool | None = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> ConflictsResponse:
    """List detected conflicts for a workspace (issue #543).

    Each conflict is identified by the winning write's journal row id. Pass
    `resolved=false` (the default view most clients want) or `resolved=true`
    to filter; omit it to see both.
    """
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)

    query = select(SyncJournal).where(
        SyncJournal.ws_id == workspace.id, SyncJournal.conflict_copy_path.is_not(None)
    )
    if resolved is True:
        query = query.where(SyncJournal.resolved_at.is_not(None))
    elif resolved is False:
        query = query.where(SyncJournal.resolved_at.is_(None))
    query = query.order_by(SyncJournal.id.desc())

    result = await session.execute(query)
    winners = list(result.scalars().all())

    losers: dict[int, SyncJournal] = {}
    loser_ids = {w.conflict_of_id for w in winners if w.conflict_of_id is not None}
    if loser_ids:
        loser_result = await session.execute(select(SyncJournal).where(SyncJournal.id.in_(loser_ids)))
        losers = {loser.id: loser for loser in loser_result.scalars().all()}

    conflicts = []
    for winner in winners:
        loser = losers.get(winner.conflict_of_id) if winner.conflict_of_id is not None else None
        conflicts.append(
            ConflictOut(
                id=winner.id,
                ws_id=winner.ws_id,
                nb_id=winner.nb_id,
                path=winner.path,
                winning_s3_version_id=winner.s3_version_id,
                winning_actor_id=winner.actor_principal_id,
                losing_s3_version_id=loser.s3_version_id if loser else "",
                losing_actor_id=loser.actor_principal_id if loser else None,
                conflict_copy_path=winner.conflict_copy_path,
                detected_at=winner.ts,
                resolved_at=winner.resolved_at,
                resolved_by_id=winner.resolved_by_id,
            )
        )

    return ConflictsResponse(conflicts=conflicts)


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictOut)
async def resolve_conflict(
    workspace_identifier: str,
    conflict_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> ConflictOut:
    """Mark a detected conflict acknowledged/resolved. Requires WRITE access to the workspace.

    Both versions remain in S3 regardless (the original at `path`, the loser
    at `conflict_copy_path`) -- this only records that a human has dealt with
    the conflict, it doesn't delete or merge anything.
    """
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.WRITE
    )

    winner = await session.get(SyncJournal, conflict_id)
    if winner is None or winner.ws_id != workspace.id or winner.conflict_copy_path is None:
        raise HTTPException(status_code=404, detail="Conflict not found")

    if winner.resolved_at is None:
        winner.resolved_at = datetime.now(UTC)
        winner.resolved_by_id = current_user.id
        session.add(winner)
        await session.commit()
        await session.refresh(winner)

    loser = None
    if winner.conflict_of_id is not None:
        loser = await session.get(SyncJournal, winner.conflict_of_id)

    return ConflictOut(
        id=winner.id,
        ws_id=winner.ws_id,
        nb_id=winner.nb_id,
        path=winner.path,
        winning_s3_version_id=winner.s3_version_id,
        winning_actor_id=winner.actor_principal_id,
        losing_s3_version_id=loser.s3_version_id if loser else "",
        losing_actor_id=loser.actor_principal_id if loser else None,
        conflict_copy_path=winner.conflict_copy_path,
        detected_at=winner.ts,
        resolved_at=winner.resolved_at,
        resolved_by_id=winner.resolved_by_id,
    )

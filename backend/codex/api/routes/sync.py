"""S3 sync routes: credential vendor (#540) + journal/change feed (#541).

Design doc §3.3/§3.4. All routes are nested under
/workspaces/{workspace_identifier}/sync:

    POST .../sync/credentials     - scoped, short-lived STS credentials
    POST .../sync/presign         - presigned-URL batch fallback for stores without STS
    POST .../sync/push-complete   - record a completed S3 write in the sync journal
    GET  .../sync/changes         - cursor-based incremental pull of journal rows

Credential/presign endpoints work identically for human JWTs and bot PATs: a
JWT represents a full human session (permission level is the only gate),
while a PAT must carry the `sync:credentials` scope and, if it's bound to a
specific workspace, can only vend for that workspace.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import PermissionScope, User, get_current_active_user, require_scope
from codex.api.routes.notebooks import get_notebook_by_slug
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.core.permissions import PermissionLevel
from codex.core.s3_indexer import is_safe_relative_path
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
    """Body for `POST .../sync/push-complete`."""

    notebook_slug: str
    path: str  # notebook-relative path under the notebook's S3 content prefix, not the full S3 key
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
) -> tuple[SyncJournal, bool]:
    """Insert a journal row, deduplicating on (ws_id, nb_id, path, s3_version_id).

    Returns `(entry, created)`. `created` is False when a row for this exact
    (ws_id, nb_id, path, s3_version_id) key already exists — e.g. this
    push-complete call raced a bucket-notification-sourced write for the same
    S3 object version — in which case the existing row is returned rather than
    inserting a duplicate. ws_id/nb_id are part of the lookup (matching the
    unique constraint) since `path` is only notebook-relative and could
    otherwise match an unrelated notebook's row.
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
                SyncJournal.ws_id == ws_id,
                SyncJournal.nb_id == nb_id,
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
    request: Request,
    current_user: User = Depends(require_scope(PermissionScope.SYNC_CREDENTIALS)),
    session: AsyncSession = Depends(get_system_session),
) -> SyncJournal:
    """Record a completed S3 push in the sync journal, attributed to the caller.

    Requires the `sync:credentials` scope when authenticated via a personal
    access token (design doc §3.4); full human sessions are unaffected.
    Duplicate (ws_id, nb_id, path, s3_version_id) keys are deduplicated:
    calling this twice for the same object version returns the existing
    journal row instead of creating a second one.
    """
    if body.op not in VALID_OPS:
        raise HTTPException(status_code=400, detail=f"op must be one of {sorted(VALID_OPS)}")
    if not is_safe_relative_path(body.path):
        raise HTTPException(status_code=400, detail="path must be a notebook-relative path with no '..' segments")

    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.WRITE
    )
    _enforce_pat_workspace_scope(request, workspace)
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

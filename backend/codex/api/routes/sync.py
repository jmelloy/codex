"""S3 sync credential vendor routes (issue #540, design doc §3.3).

Two endpoints, both nested under /workspaces/{workspace_identifier}/sync:
    POST .../sync/credentials  - scoped, short-lived STS credentials
    POST .../sync/presign      - presigned-URL batch fallback for stores without STS

Both work identically for human JWTs and bot PATs: a JWT represents a full
human session (permission level is the only gate), while a PAT must carry the
`sync:credentials` scope and, if it's bound to a specific workspace, can only
vend for that workspace.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codex.api.auth import PermissionScope, User, require_scope
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.core.permissions import PermissionLevel
from codex.core.sync_credentials import (
    SYNC_CREDENTIAL_TTL,
    WRITE_OPERATIONS,
    generate_presigned_batch,
    is_sts_configured,
    vend_sts_credentials,
)
from codex.db.database import get_system_session
from codex.db.models import Workspace

router = APIRouter()


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

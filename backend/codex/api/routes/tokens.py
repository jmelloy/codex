"""Personal access token routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import ALLOWED_SCOPES, generate_pat, get_current_active_user, hash_token
from codex.core.permissions import PermissionLevel, check_permission
from codex.db.database import get_system_session
from codex.db.models import PersonalAccessToken, User, Workspace, WorkspacePermission

router = APIRouter()


class CreateTokenRequest(BaseModel):
    """Request to create a personal access token."""

    name: str
    scopes: list[str] | None = None  # e.g. ["workspace:write"], must be drawn from ALLOWED_SCOPES
    workspace_id: int | None = None
    notebook_id: int | None = None
    expires_at: datetime | None = None


class TokenResponse(BaseModel):
    """Response after creating a token (includes the plain token once)."""

    id: int
    name: str
    token: str  # Only returned on creation
    token_prefix: str
    scopes: list[str] | None = None
    workspace_id: int | None = None
    notebook_id: int | None = None
    expires_at: datetime | None = None
    created_at: datetime


class TokenListItem(BaseModel):
    """Token info for listing (no secret)."""

    id: int
    name: str
    token_prefix: str
    scopes: list[str] | None = None
    workspace_id: int | None = None
    notebook_id: int | None = None
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime


@router.post("/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def create_token(
    request: CreateTokenRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> TokenResponse:
    """Create a new personal access token.

    The plain token is returned only in this response. Store it securely.
    """
    if request.scopes:
        invalid = [s for s in request.scopes if s not in ALLOWED_SCOPES]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown scope(s): {', '.join(invalid)}. Allowed scopes: {', '.join(ALLOWED_SCOPES)}",
            )

    plain_token = generate_pat()
    token_hash_value = hash_token(plain_token)

    pat = PersonalAccessToken(
        user_id=current_user.id,
        name=request.name,
        token_hash=token_hash_value,
        token_prefix=plain_token[:12],  # "cdx_" + first 8 chars of random part
        scopes=request.scopes,
        workspace_id=request.workspace_id,
        notebook_id=request.notebook_id,
        expires_at=request.expires_at,
    )
    session.add(pat)
    await session.commit()
    await session.refresh(pat)

    return TokenResponse(
        id=pat.id,
        name=pat.name,
        token=plain_token,
        token_prefix=pat.token_prefix,
        scopes=pat.scopes,
        workspace_id=pat.workspace_id,
        notebook_id=pat.notebook_id,
        expires_at=pat.expires_at,
        created_at=pat.created_at,
    )


@router.get("/", response_model=list[TokenListItem])
async def list_tokens(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[TokenListItem]:
    """List all personal access tokens for the current user."""
    result = await session.execute(
        select(PersonalAccessToken)
        .where(PersonalAccessToken.user_id == current_user.id)
        .order_by(PersonalAccessToken.created_at.desc())
    )
    tokens = result.scalars().all()
    return [
        TokenListItem(
            id=t.id,
            name=t.name,
            token_prefix=t.token_prefix,
            scopes=t.scopes,
            workspace_id=t.workspace_id,
            notebook_id=t.notebook_id,
            last_used_at=t.last_used_at,
            expires_at=t.expires_at,
            is_active=t.is_active,
            created_at=t.created_at,
        )
        for t in tokens
    ]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Revoke (deactivate) a personal access token."""
    result = await session.execute(
        select(PersonalAccessToken).where(
            PersonalAccessToken.id == token_id,
            PersonalAccessToken.user_id == current_user.id,
        )
    )
    pat = result.scalar_one_or_none()
    if not pat:
        raise HTTPException(status_code=404, detail="Token not found")

    pat.is_active = False
    session.add(pat)
    await session.commit()


# ── PATs for bot service accounts (issue #533) ───────────────────────


class CreateBotTokenRequest(BaseModel):
    """Request to issue a personal access token for a bot, scoped to one workspace."""

    name: str
    workspace_id: int  # Bot PATs are always workspace-scoped, unlike human PATs.
    scopes: list[str] | None = None
    expires_at: datetime | None = None


async def _get_bot_or_404(bot_id: int, session: AsyncSession) -> User:
    bot = await session.get(User, bot_id)
    if bot is None or not bot.is_bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    return bot


async def _assert_can_manage_bot(bot: User, current_user: User, session: AsyncSession) -> None:
    """Raise 403 unless `current_user` has ADMIN on at least one workspace the bot belongs to."""
    grants = await session.execute(
        select(WorkspacePermission.workspace_id).where(WorkspacePermission.user_id == bot.id)
    )
    workspace_ids = [row[0] for row in grants.all()]
    if workspace_ids:
        workspaces_result = await session.execute(select(Workspace).where(Workspace.id.in_(workspace_ids)))
        for workspace in workspaces_result.scalars().all():
            if await check_permission(current_user, workspace, PermissionLevel.ADMIN, session):
                return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission to manage this bot")


@router.post("/bots/{bot_id}/tokens", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def create_bot_token(
    bot_id: int,
    request: CreateBotTokenRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> TokenResponse:
    """Issue a workspace-scoped PAT for a bot (requires ADMIN on that workspace).

    The bot must already have a `WorkspacePermission` grant on the target
    workspace (granted at bot creation, or via the collaborators endpoint) —
    this only issues credentials, it doesn't itself grant access.
    """
    bot = await _get_bot_or_404(bot_id, session)

    workspace = await session.get(Workspace, request.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if not await check_permission(current_user, workspace, PermissionLevel.ADMIN, session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission for this operation")

    grant = await session.execute(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace.id,
            WorkspacePermission.user_id == bot.id,
        )
    )
    if grant.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Bot does not have access to this workspace"
        )

    if request.scopes:
        invalid = [s for s in request.scopes if s not in ALLOWED_SCOPES]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown scope(s): {', '.join(invalid)}. Allowed scopes: {', '.join(ALLOWED_SCOPES)}",
            )

    plain_token = generate_pat()
    pat = PersonalAccessToken(
        user_id=bot.id,
        name=request.name,
        token_hash=hash_token(plain_token),
        token_prefix=plain_token[:12],
        scopes=request.scopes,
        workspace_id=request.workspace_id,
        expires_at=request.expires_at,
    )
    session.add(pat)
    await session.commit()
    await session.refresh(pat)

    return TokenResponse(
        id=pat.id,
        name=pat.name,
        token=plain_token,
        token_prefix=pat.token_prefix,
        scopes=pat.scopes,
        workspace_id=pat.workspace_id,
        notebook_id=pat.notebook_id,
        expires_at=pat.expires_at,
        created_at=pat.created_at,
    )


async def _caller_is_admin_on_workspace(workspace_id: int | None, current_user: User, session: AsyncSession) -> bool:
    """Check ADMIN on a specific workspace_id (False if the workspace is gone or unset)."""
    if workspace_id is None:
        return False
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        return False
    return await check_permission(current_user, workspace, PermissionLevel.ADMIN, session)


@router.get("/bots/{bot_id}/tokens", response_model=list[TokenListItem])
async def list_bot_tokens(
    bot_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[TokenListItem]:
    """List a bot's personal access tokens, restricted to workspaces the caller administers.

    A bot can hold PATs scoped to multiple workspaces; `_assert_can_manage_bot` only
    proves the caller administers *some* workspace the bot belongs to, so each token
    is additionally checked against its own `workspace_id` before being surfaced —
    otherwise an admin of workspace A could see a bot's token scoped to workspace B.
    """
    bot = await _get_bot_or_404(bot_id, session)
    await _assert_can_manage_bot(bot, current_user, session)

    result = await session.execute(
        select(PersonalAccessToken)
        .where(PersonalAccessToken.user_id == bot.id)
        .order_by(PersonalAccessToken.created_at.desc())
    )
    tokens = result.scalars().all()

    admin_by_workspace: dict[int, bool] = {}
    visible_tokens = []
    for t in tokens:
        if t.workspace_id not in admin_by_workspace:
            admin_by_workspace[t.workspace_id] = await _caller_is_admin_on_workspace(
                t.workspace_id, current_user, session
            )
        if admin_by_workspace[t.workspace_id]:
            visible_tokens.append(t)

    return [
        TokenListItem(
            id=t.id,
            name=t.name,
            token_prefix=t.token_prefix,
            scopes=t.scopes,
            workspace_id=t.workspace_id,
            notebook_id=t.notebook_id,
            last_used_at=t.last_used_at,
            expires_at=t.expires_at,
            is_active=t.is_active,
            created_at=t.created_at,
        )
        for t in visible_tokens
    ]


@router.delete("/bots/{bot_id}/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_bot_token(
    bot_id: int,
    token_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Revoke (deactivate) a bot's personal access token.

    Requires ADMIN on the *token's own* `workspace_id` — being admin of some other
    workspace the bot also belongs to isn't enough to revoke this one.
    """
    bot = await _get_bot_or_404(bot_id, session)

    result = await session.execute(
        select(PersonalAccessToken).where(
            PersonalAccessToken.id == token_id,
            PersonalAccessToken.user_id == bot.id,
        )
    )
    pat = result.scalar_one_or_none()
    if not pat:
        raise HTTPException(status_code=404, detail="Token not found")

    if not await _caller_is_admin_on_workspace(pat.workspace_id, current_user, session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission for this operation")

    pat.is_active = False
    session.add(pat)
    await session.commit()

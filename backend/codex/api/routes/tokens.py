"""Personal access token routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import generate_pat, get_current_active_user, hash_token
from codex.db.database import get_system_session
from codex.db.models import PersonalAccessToken, User

router = APIRouter()


class CreateTokenRequest(BaseModel):
    """Request to create a personal access token."""

    name: str
    scopes: str | None = None  # e.g. "snippets:write"
    workspace_id: int | None = None
    notebook_id: int | None = None
    expires_at: datetime | None = None


class TokenResponse(BaseModel):
    """Response after creating a token (includes the plain token once)."""

    id: int
    name: str
    token: str  # Only returned on creation
    token_prefix: str
    scopes: str | None = None
    workspace_id: int | None = None
    notebook_id: int | None = None
    expires_at: datetime | None = None
    created_at: datetime


class TokenListItem(BaseModel):
    """Token info for listing (no secret)."""

    id: int
    name: str
    token_prefix: str
    scopes: str | None = None
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
        select(PersonalAccessToken).where(PersonalAccessToken.user_id == current_user.id).order_by(PersonalAccessToken.created_at.desc())
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

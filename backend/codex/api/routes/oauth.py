"""OAuth routes for connecting external providers."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import create_access_token, get_current_active_user
from codex.core.oauth import (
    exchange_google_code,
    get_google_auth_url,
    revoke_oauth_connection,
    save_oauth_connection,
)
from codex.db.database import get_system_session
from codex.db.models import OAuthConnection, User

logger = logging.getLogger(__name__)

router = APIRouter()


class OAuthAuthorizeResponse(BaseModel):
    """Response containing the OAuth authorization URL."""

    authorization_url: str


class OAuthCallbackRequest(BaseModel):
    """Request body for the OAuth callback."""

    code: str
    state: str | None = None


class OAuthCallbackResponse(BaseModel):
    """Response after successful OAuth callback."""

    provider: str
    provider_email: str | None = None
    connected: bool = True


class OAuthConnectionResponse(BaseModel):
    """Response for listing OAuth connections."""

    id: int
    provider: str
    provider_email: str | None = None
    scopes: str | None = None
    is_active: bool
    created_at: str
    updated_at: str


class OAuthDisconnectResponse(BaseModel):
    """Response after disconnecting an OAuth provider."""

    provider: str
    disconnected: bool = True


@router.get("/google/authorize", response_model=OAuthAuthorizeResponse)
async def google_authorize(
    current_user: User = Depends(get_current_active_user),
):
    """Generate Google OAuth2 authorization URL.

    The frontend should redirect the user to this URL to initiate the OAuth flow.
    After authorization, Google will redirect back to the configured redirect URI.
    """
    try:
        # Encode user_id in state for CSRF protection
        state = create_access_token(data={"sub": current_user.username, "oauth": True})
        url = get_google_auth_url(state=state)
        return OAuthAuthorizeResponse(authorization_url=url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/google/callback", response_model=OAuthCallbackResponse)
async def google_callback(
    body: OAuthCallbackRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Handle Google OAuth2 callback.

    Exchanges the authorization code for tokens and stores the connection.
    """
    try:
        token_data = exchange_google_code(body.code)
    except Exception as e:
        logger.error(f"Failed to exchange Google auth code: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {e}",
        )

    connection = await save_oauth_connection(
        session=session,
        user_id=current_user.id,
        provider="google",
        token_data=token_data,
    )

    return OAuthCallbackResponse(
        provider="google",
        provider_email=connection.provider_email,
        connected=True,
    )


@router.get("/connections", response_model=list[OAuthConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all OAuth connections for the current user."""
    result = await session.execute(
        select(OAuthConnection).where(
            OAuthConnection.user_id == current_user.id,
            OAuthConnection.is_active == True,  # noqa: E712
        )
    )
    connections = result.scalars().all()

    return [
        OAuthConnectionResponse(
            id=conn.id,
            provider=conn.provider,
            provider_email=conn.provider_email,
            scopes=conn.scopes,
            is_active=conn.is_active,
            created_at=conn.created_at.isoformat(),
            updated_at=conn.updated_at.isoformat(),
        )
        for conn in connections
    ]


@router.delete("/google/disconnect", response_model=OAuthDisconnectResponse)
async def google_disconnect(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Disconnect Google OAuth connection."""
    disconnected = await revoke_oauth_connection(session, current_user.id, "google")
    if not disconnected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google connection found",
        )
    return OAuthDisconnectResponse(provider="google", disconnected=True)

"""OAuth routes for connecting external providers."""

import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_active_user,
    get_password_hash,
)
from codex.api.routes.workspaces import WorkspaceCreate, create_workspace
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


class OAuthLoginCallbackResponse(BaseModel):
    """Response after successful Google sign-in (returns JWT)."""

    access_token: str
    token_type: str = "bearer"
    provider_email: str | None = None


# --- Unauthenticated Google Sign-In endpoints ---


@router.get("/google/login", response_model=OAuthAuthorizeResponse)
async def google_login():
    """Generate Google OAuth2 authorization URL for sign-in/sign-up.

    This endpoint does NOT require authentication. It is used on the login
    and register pages to initiate the "Sign in with Google" flow.
    """
    try:
        state = create_access_token(data={"mode": "login"}, expires_delta=timedelta(minutes=10))
        url = get_google_auth_url(state=state)
        return OAuthAuthorizeResponse(authorization_url=url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/google/login/callback", response_model=OAuthLoginCallbackResponse)
async def google_login_callback(
    body: OAuthCallbackRequest,
    response: Response,
    session: AsyncSession = Depends(get_system_session),
):
    """Handle Google OAuth2 callback for sign-in/sign-up.

    This endpoint does NOT require authentication. It exchanges the Google
    authorization code for tokens, finds or creates the user, and returns
    a JWT access token so the frontend can log them in.
    """
    try:
        token_data = exchange_google_code(body.code)
    except Exception as e:
        logger.error(f"Failed to exchange Google auth code: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {e}",
        )

    provider_email = token_data.get("provider_email")
    provider_user_id = token_data.get("provider_user_id")

    if not provider_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve email from Google. Please ensure email permissions are granted.",
        )

    # Look up existing user by email
    result = await session.execute(select(User).where(User.email == provider_email))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create user from Google profile
        # Generate a username from the email prefix, ensuring uniqueness
        base_username = provider_email.split("@")[0].lower()
        # Sanitize: keep only alphanumeric and underscores
        base_username = "".join(c if c.isalnum() or c == "_" else "" for c in base_username)
        if len(base_username) < 3:
            base_username = "user_" + base_username

        username = base_username
        # Check uniqueness and add suffix if needed
        for _ in range(10):
            exists = await session.execute(select(User).where(User.username == username))
            if not exists.scalar_one_or_none():
                break
            username = f"{base_username}_{secrets.token_hex(3)}"

        # Create user with a random password (they'll sign in via Google)
        random_password = secrets.token_urlsafe(32)
        user = User(
            username=username,
            email=provider_email,
            hashed_password=get_password_hash(random_password),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create a default workspace for the new user
        default_workspace = await create_workspace(
            body=WorkspaceCreate(name=username), current_user=user, session=session
        )
        session.add(default_workspace)
        await session.commit()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    # Save the OAuth connection (for calendar access etc.)
    await save_oauth_connection(
        session=session,
        user_id=user.id,
        provider="google",
        token_data=token_data,
    )

    # Issue a JWT for the user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    # Set cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
    )

    return OAuthLoginCallbackResponse(
        access_token=access_token,
        provider_email=provider_email,
    )


# --- Authenticated Google connection endpoints ---


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

"""OAuth service for managing external provider connections.

Handles the Google OAuth2 authorization code flow:
1. Generate authorization URL with required scopes
2. Exchange authorization code for tokens
3. Store/refresh tokens in the database
4. Encrypt tokens at rest using Fernet symmetric encryption
"""

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.db.models import OAuthConnection

logger = logging.getLogger(__name__)

# Configuration from environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://codex.melloy.life/oauth/callback")

# Encryption key for token storage (generate with Fernet.generate_key())
OAUTH_ENCRYPTION_KEY = os.getenv("OAUTH_ENCRYPTION_KEY", "")

# Google Calendar scopes
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _get_fernet() -> Fernet:
    """Get Fernet cipher for token encryption."""
    key = OAUTH_ENCRYPTION_KEY
    if not key:
        # Fall back to SECRET_KEY-based derivation for development
        import base64
        import hashlib

        from codex.api.auth import SECRET_KEY

        derived = hashlib.sha256(SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(token: str) -> str:
    """Encrypt a token for database storage."""
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from database storage."""
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode()).decode()


def get_google_auth_url(state: str | None = None) -> str:
    """Generate Google OAuth2 authorization URL.

    Args:
        state: Optional state parameter for CSRF protection (e.g., JWT with user_id).

    Returns:
        Authorization URL to redirect the user to.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_CALENDAR_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    return authorization_url


def exchange_google_code(code: str) -> dict:
    """Exchange an authorization code for tokens.

    Args:
        code: The authorization code from Google's callback.

    Returns:
        Dict with access_token, refresh_token, token_expiry, and user info.
    """
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_CALENDAR_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Get user info from the ID token
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    user_info = {}
    if credentials.id_token:
        try:
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                GOOGLE_CLIENT_ID,
            )
            user_info = {
                "email": id_info.get("email"),
                "sub": id_info.get("sub"),  # Google user ID
            }
        except Exception as e:
            logger.warning(f"Failed to verify ID token: {e}")

    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_expiry": credentials.expiry,
        "scopes": ",".join(credentials.scopes or GOOGLE_CALENDAR_SCOPES),
        "provider_email": user_info.get("email"),
        "provider_user_id": user_info.get("sub"),
    }


async def save_oauth_connection(
    session: AsyncSession,
    user_id: int,
    provider: str,
    token_data: dict,
) -> OAuthConnection:
    """Save or update an OAuth connection for a user.

    If a connection already exists for this user+provider, it is updated.
    """
    # Check for existing connection
    result = await session.execute(
        select(OAuthConnection).where(
            OAuthConnection.user_id == user_id,
            OAuthConnection.provider == provider,
            OAuthConnection.is_active == True,  # noqa: E712
        )
    )
    connection = result.scalar_one_or_none()

    encrypted_access = encrypt_token(token_data["access_token"])
    encrypted_refresh = encrypt_token(token_data["refresh_token"]) if token_data.get("refresh_token") else None

    if connection:
        connection.access_token = encrypted_access
        if encrypted_refresh:
            connection.refresh_token = encrypted_refresh
        connection.token_expires_at = token_data.get("token_expiry")
        connection.scopes = token_data.get("scopes")
        connection.provider_email = token_data.get("provider_email")
        connection.provider_user_id = token_data.get("provider_user_id")
        connection.updated_at = datetime.now(UTC)
    else:
        connection = OAuthConnection(
            user_id=user_id,
            provider=provider,
            provider_user_id=token_data.get("provider_user_id"),
            provider_email=token_data.get("provider_email"),
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            token_expires_at=token_data.get("token_expiry"),
            scopes=token_data.get("scopes"),
        )

    session.add(connection)
    await session.commit()
    await session.refresh(connection)
    return connection


async def _load_and_refresh_credentials(session: AsyncSession, connection: OAuthConnection) -> Credentials | None:
    """Decrypt a connection's tokens into `Credentials`, refreshing if expired.

    Shared by both the user-keyed lookup (`get_google_credentials`, used by the personal
    Calendar feature) and the connection-id-keyed resolver (`get_credentials_for_connection`,
    used by workspace integrations). Returns None if the stored refresh token can't produce
    a fresh access token -- the caller decides what that means for its use case.
    """
    access_token = decrypt_token(connection.access_token)
    refresh_token = decrypt_token(connection.refresh_token) if connection.refresh_token else None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=connection.scopes.split(",") if connection.scopes else GOOGLE_CALENDAR_SCOPES,
    )

    # Set expiry
    if connection.token_expires_at:
        creds.expiry = connection.token_expires_at

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
            # Update stored tokens
            connection.access_token = encrypt_token(creds.token)
            if creds.expiry:
                connection.token_expires_at = creds.expiry
            connection.updated_at = datetime.now(UTC)
            session.add(connection)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to refresh Google credentials for connection {connection.id}: {e}")
            return None

    return creds


async def get_google_credentials(session: AsyncSession, user_id: int) -> Credentials | None:
    """Get valid Google credentials for a user, refreshing if needed.

    Returns None if no connection exists or tokens cannot be refreshed. This is the
    user-keyed lookup used by the personal Calendar feature, where "whose token" is
    always "the caller's own" by design. Workspace integrations must NOT use this --
    see `get_credentials_for_connection` below.
    """
    result = await session.execute(
        select(OAuthConnection).where(
            OAuthConnection.user_id == user_id,
            OAuthConnection.provider == "google",
            OAuthConnection.is_active == True,  # noqa: E712
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        return None

    return await _load_and_refresh_credentials(session, connection)


class OAuthConnectionStatus(StrEnum):
    """Outcome of resolving an explicit, workspace-bound OAuth connection.

    Deliberately distinct from a bare `None` return: a shared-workspace integration
    must tell "nobody has bound a connection yet" (NOT_CONFIGURED) apart from "a
    connection was bound but it's since been revoked/deactivated or won't refresh"
    (REVOKED) so the UI can render the right explicit state instead of silently doing
    nothing (design doc §1 L12).
    """

    NOT_CONFIGURED = "not_configured"
    REVOKED = "connection_revoked"
    VALID = "valid"


@dataclass
class ResolvedOAuthConnection:
    """Result of `get_credentials_for_connection`."""

    status: OAuthConnectionStatus
    connection: OAuthConnection | None = None
    credentials: Credentials | None = None


async def get_credentials_for_connection(
    session: AsyncSession, connection_id: int | None
) -> ResolvedOAuthConnection:
    """Resolve credentials for an explicit, workspace-bound `OAuthConnection` id.

    Unlike `get_google_credentials` (keyed by `user_id`, for the personal Calendar
    feature), this is keyed by the connection's own primary key: a shared-workspace
    integration binds to exactly one connection (`PluginConfig.oauth_connection_id`)
    and this resolver uses that connection regardless of who is viewing -- it never
    falls back to "whichever member happens to have a connection for this provider".
    """
    if connection_id is None:
        return ResolvedOAuthConnection(status=OAuthConnectionStatus.NOT_CONFIGURED)

    connection = await session.get(OAuthConnection, connection_id)
    if connection is None or not connection.is_active:
        return ResolvedOAuthConnection(status=OAuthConnectionStatus.REVOKED, connection=connection)

    creds = await _load_and_refresh_credentials(session, connection)
    if creds is None:
        return ResolvedOAuthConnection(status=OAuthConnectionStatus.REVOKED, connection=connection)

    return ResolvedOAuthConnection(status=OAuthConnectionStatus.VALID, connection=connection, credentials=creds)


async def revoke_oauth_connection(session: AsyncSession, user_id: int, provider: str) -> bool:
    """Revoke (deactivate) an OAuth connection."""
    result = await session.execute(
        select(OAuthConnection).where(
            OAuthConnection.user_id == user_id,
            OAuthConnection.provider == provider,
            OAuthConnection.is_active == True,  # noqa: E712
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        return False

    connection.is_active = False
    connection.updated_at = datetime.now(UTC)
    session.add(connection)
    await session.commit()
    return True

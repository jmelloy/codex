"""Authentication utilities."""

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.db.database import get_system_session
from codex.db.models import PersonalAccessToken, RefreshToken, User

DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

PAT_PREFIX = "cdx_"
REFRESH_TOKEN_PREFIX = "cdxr_"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class PermissionScope(StrEnum):
    """Formal scopes that can be granted to a personal access token.

    Replaces the old free-form comma-delimited scope string (design doc L11).
    """

    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    COMMENTS_WRITE = "comments:write"
    SYNC_CREDENTIALS = "sync:credentials"


ALLOWED_SCOPES: list[str] = [scope.value for scope in PermissionScope]


def is_default_secret_key() -> bool:
    """Return True if SECRET_KEY is still the hardcoded placeholder value."""
    return SECRET_KEY == DEFAULT_SECRET_KEY


def is_multi_user_mode() -> bool:
    """Return True if the MULTI_USER env flag is set."""
    return os.getenv("MULTI_USER", "").strip().lower() in {"1", "true", "yes"}


def assert_secret_key_is_safe() -> None:
    """Refuse to run in multi-user mode with the default SECRET_KEY.

    Multi-user mode is opted into explicitly via the MULTI_USER env flag
    (issue #527 acceptance: "default secret + multi-user flag"). Raises
    RuntimeError so startup fails loudly instead of issuing tokens that are
    trivially forgeable once other users are present.
    """
    if is_multi_user_mode() and is_default_secret_key():
        raise RuntimeError(
            "Default SECRET_KEY detected while MULTI_USER is enabled. Refusing to start: "
            "set a secure, unique SECRET_KEY in your .env file before running in multi-user mode."
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using PBKDF2."""
    try:
        # Split the stored hash into salt and hash
        salt, stored_hash = hashed_password.split("$")
        # Hash the plain password with the same salt
        password_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), bytes.fromhex(salt), 100000)
        return password_hash.hex() == stored_hash
    except (
        ValueError,
        AttributeError,
    ):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using PBKDF2 with a random salt."""
    # Generate a random salt
    salt = secrets.token_bytes(32)
    # Hash the password with PBKDF2
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)  # Number of iterations
    # Return salt and hash separated by $
    return f"{salt.hex()}${password_hash.hex()}"


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def generate_pat() -> str:
    """Generate a new personal access token string."""
    return PAT_PREFIX + secrets.token_urlsafe(32)


def generate_refresh_token() -> str:
    """Generate a new refresh token string."""
    return REFRESH_TOKEN_PREFIX + secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Hash a token for storage using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_refresh_token(user: User, session: AsyncSession) -> str:
    """Create and persist a new refresh token for a user, returning the plain token."""
    plain_token = generate_refresh_token()
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(plain_token),
        expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(refresh_token)
    await session.commit()
    return plain_token


async def rotate_refresh_token(plain_token: str, session: AsyncSession) -> tuple[str, str]:
    """Validate a refresh token, revoke it, and issue new access + refresh tokens.

    Returns (access_token, refresh_token). Raises HTTPException(401) if the
    supplied refresh token is missing, expired, already revoked, or the
    associated user is gone/inactive.
    """
    invalid_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
    )

    token_hash_value = hash_token(plain_token)
    now = datetime.now(UTC)

    # Atomically claim the token by flipping revoked_at from NULL in a single
    # UPDATE. Only one of two concurrent requests presenting the same refresh
    # token can match the WHERE clause, so only one can mint a new token pair.
    claim_result = await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash_value, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await session.commit()

    if claim_result.rowcount == 0:
        # Either the token never existed, or a concurrent refresh already claimed it.
        raise invalid_exception

    result = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash_value))
    stored = result.scalar_one_or_none()

    if stored is None:
        raise invalid_exception

    # SQLite drops tzinfo on round-trip even for DateTime(timezone=True) columns,
    # so a value read back in a fresh session/connection comes back naive.
    stored_expires_at = stored.expires_at
    if stored_expires_at.tzinfo is None:
        stored_expires_at = stored_expires_at.replace(tzinfo=UTC)

    if stored_expires_at < now:
        raise invalid_exception

    user_result = await session.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise invalid_exception

    new_access_token = create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await session.commit()

    return new_access_token, new_refresh_token


async def get_user_by_username(username: str, session: AsyncSession) -> User | None:
    """Retrieve a user by username."""
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def _authenticate_via_pat(token: str, session: AsyncSession) -> tuple[User | None, PersonalAccessToken | None]:
    """Authenticate using a personal access token. Returns (user, pat) or (None, None)."""
    token_hash_value = hash_token(token)
    result = await session.execute(
        select(PersonalAccessToken).where(
            PersonalAccessToken.token_hash == token_hash_value,
            PersonalAccessToken.is_active == True,  # noqa: E712
        )
    )
    pat = result.scalar_one_or_none()
    if pat is None:
        return None, None

    # Check expiration
    if pat.expires_at and pat.expires_at < datetime.now(UTC):
        return None, None

    # Update last_used_at
    pat.last_used_at = datetime.now(UTC)
    session.add(pat)
    await session.commit()

    # Load user
    user_result = await session.execute(select(User).where(User.id == pat.user_id))
    return user_result.scalar_one_or_none(), pat


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_system_session),
    token: str | None = Depends(oauth2_scheme),
    access_token: str | None = Cookie(None),
) -> User:
    """Get the current authenticated user from Bearer token, PAT, or cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Authorization header takes priority over cookie
    jwt_token = token or access_token

    if not jwt_token:
        raise credentials_exception

    # Check if this is a personal access token (starts with cdx_)
    if jwt_token.startswith(PAT_PREFIX):
        user, pat = await _authenticate_via_pat(jwt_token, session)
        if user is None:
            raise credentials_exception
        # Stash the token's scopes so route-level require_scope() dependencies can enforce them.
        request.state.token_scopes = list(pat.scopes) if pat.scopes else []
        return user

    # Otherwise treat as JWT
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_username(username, session)
    if user is None:
        raise credentials_exception

    # A JWT represents a full human session (not a scope-restricted PAT).
    request.state.token_scopes = None
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_scope(scope: PermissionScope):
    """Build a FastAPI dependency that enforces a PAT carries the given scope.

    JWT/cookie-authenticated sessions represent a full human session and are
    never scope-restricted. Only personal access tokens are checked, and a
    token missing the scope gets a 403 naming the missing scope.
    """

    async def _dependency(
        request: Request,
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        token_scopes = getattr(request.state, "token_scopes", None)
        if token_scopes is not None and scope.value not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This token is missing the required scope: {scope.value}",
            )
        return current_user

    return _dependency

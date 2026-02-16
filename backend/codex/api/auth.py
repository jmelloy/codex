"""Authentication utilities."""

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.db.database import get_system_session
from codex.db.models import PersonalAccessToken, User

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

PAT_PREFIX = "cdx_"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


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


def hash_token(token: str) -> str:
    """Hash a token for storage using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_user_by_username(username: str, session: AsyncSession) -> User | None:
    """Retrieve a user by username."""
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def _authenticate_via_pat(token: str, session: AsyncSession) -> User | None:
    """Authenticate using a personal access token. Returns the user or None."""
    token_hash_value = hash_token(token)
    result = await session.execute(
        select(PersonalAccessToken).where(
            PersonalAccessToken.token_hash == token_hash_value,
            PersonalAccessToken.is_active == True,  # noqa: E712
        )
    )
    pat = result.scalar_one_or_none()
    if pat is None:
        return None

    # Check expiration
    if pat.expires_at and pat.expires_at < datetime.now(UTC):
        return None

    # Update last_used_at
    pat.last_used_at = datetime.now(UTC)
    session.add(pat)
    await session.commit()

    # Load user
    user_result = await session.execute(select(User).where(User.id == pat.user_id))
    return user_result.scalar_one_or_none()


async def get_current_user(
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
        user = await _authenticate_via_pat(jwt_token, session)
        if user is None:
            raise credentials_exception
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
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

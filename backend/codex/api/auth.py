"""Authentication utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from codex.db.models import User
from codex.db.database import get_system_session
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_by_username(username: str, session: AsyncSession) -> Optional[User]:
    """Retrieve a user by username."""
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_current_user(
    session: AsyncSession = Depends(get_system_session),
    token: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(None),
) -> User:
    """Get the current authenticated user from Bearer token or cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try cookie first, then Authorization header
    jwt_token = access_token or token

    if not jwt_token:
        raise credentials_exception

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

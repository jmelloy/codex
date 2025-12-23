"""Authentication utilities for JWT token management."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from api.utils import DEFAULT_WORKSPACE_PATH
from core.workspace import Workspace
from db.models import User

# Security configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes for access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days for refresh tokens

security = HTTPBearer()


class Token(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data model."""

    username: Optional[str] = None


class UserInDB(BaseModel):
    """User model for database operations."""

    id: int
    username: str
    email: str
    workspace_path: str
    is_active: bool


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, username: str) -> tuple[str, datetime]:
    """Create a refresh token and return it with its expiration time.
    
    Args:
        user_id: The user's ID
        username: The user's username
        
    Returns:
        Tuple of (token_string, expiration_datetime)
    """
    import secrets
    from pathlib import Path
    from db.operations import DatabaseManager
    from db.models import RefreshToken
    
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store in database
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    
    session = db_manager.get_session()
    try:
        RefreshToken.create(
            session,
            validate_fk=False,
            token=token,
            user_id=user_id,
            expires_at=expires_at,
        )
        session.commit()
    finally:
        session.close()
    
    return token, expires_at


def validate_refresh_token(token: str) -> Optional[int]:
    """Validate a refresh token and return the user_id if valid.
    
    Args:
        token: The refresh token to validate
        
    Returns:
        The user_id if the token is valid, None otherwise
    """
    from pathlib import Path
    from db.operations import DatabaseManager
    from db.models import RefreshToken
    
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"
    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    
    session = db_manager.get_session()
    try:
        refresh_token = RefreshToken.find_one_by(session, token=token)
        
        if refresh_token is None:
            return None
            
        # Check if token is revoked
        if refresh_token.revoked:
            return None
            
        # Check if token is expired
        # Make expires_at timezone-aware if it's naive
        expires_at = refresh_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < datetime.now(timezone.utc):
            return None
            
        return refresh_token.user_id
    finally:
        session.close()


def revoke_refresh_token(token: str) -> bool:
    """Revoke a refresh token.
    
    Args:
        token: The refresh token to revoke
        
    Returns:
        True if token was revoked, False if not found
    """
    from pathlib import Path
    from db.operations import DatabaseManager
    from db.models import RefreshToken
    
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"
    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    
    session = db_manager.get_session()
    try:
        refresh_token = RefreshToken.find_one_by(session, token=token)
        
        if refresh_token is None:
            return False
            
        refresh_token.update(session, revoked=True)
        session.commit()
        return True
    finally:
        session.close()


def decode_token(token: str) -> TokenData:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(username=username)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInDB:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    token_data = decode_token(token)
    
    # Get user from database
    from pathlib import Path
    from db.operations import DatabaseManager
    
    # Use the default workspace database to store users
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"
    
    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    db_manager = DatabaseManager(db_path)
    db_manager.initialize()  # Initialize database with migrations
    
    session = db_manager.get_session()
    try:
        user = User.find_one_by(session, username=token_data.username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return UserInDB(
            id=user.id,
            username=user.username,
            email=user.email,
            workspace_path=user.workspace_path,
            is_active=user.is_active,
        )
    finally:
        session.close()


async def get_current_user_workspace(
    current_user: UserInDB = Depends(get_current_user),
) -> Workspace:
    """Get the workspace for the current authenticated user."""
    from pathlib import Path
    
    workspace_path = Path(current_user.workspace_path)
    try:
        return Workspace.load(workspace_path)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User workspace not found or not initialized"
        )

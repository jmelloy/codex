"""Authentication API routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.auth import (
    UserInDB,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    validate_refresh_token,
    verify_password,
)
from api.utils import DEFAULT_WORKSPACE_PATH, get_core_db_path
from core.workspace import Workspace
from db.core_operations import CoreDatabaseManager

router = APIRouter()


class UserRegisterRequest(BaseModel):
    """Request model for user registration."""

    username: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    """Request model for user login."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Response model for user info."""

    id: int
    username: str
    email: str
    workspace_path: str
    is_active: bool
    created_at: str


class LoginResponse(BaseModel):
    """Response model for login."""

    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest):
    """Register a new user."""
    # Get core database connection
    db_path = get_core_db_path()

    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    core_db = CoreDatabaseManager(db_path)
    core_db.initialize()  # Initialize core database

    # Check if username already exists
    existing_user = core_db.get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Create user workspace path
    workspaces_dir = Path(DEFAULT_WORKSPACE_PATH).parent / "workspaces"
    user_workspace_path = workspaces_dir / request.username

    # Create the user
    hashed_password = get_password_hash(request.password)
    user = core_db.create_user(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password,
        workspace_path=str(user_workspace_path),
    )

    # Initialize user's workspace
    try:
        Workspace.initialize(user_workspace_path, f"{request.username}'s Workspace")
    except Exception as e:
        # If workspace initialization fails, we can't easily rollback in this architecture
        # The user will exist but have no workspace
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize workspace: {str(e)}"
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token_str, _ = create_refresh_token(user.id, user.username)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            workspace_path=user.workspace_path,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: UserLoginRequest):
    """Login a user."""
    # Get core database connection
    db_path = get_core_db_path()
    core_db = CoreDatabaseManager(db_path)
    core_db.initialize()

    # Find user by username
    user = core_db.get_user_by_username(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token_str, _ = create_refresh_token(user.id, user.username)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            workspace_path=user.workspace_path,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """Get current user information."""
    # Get full user data from database
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"

    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()  # Initialize database with migrations

    session = db_manager.get_session()
    try:
        user = User.find_one_by(session, username=current_user.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            workspace_path=user.workspace_path,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )
    finally:
        session.close()


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Response model for token refresh."""

    access_token: str
    token_type: str = "bearer"


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(request: RefreshTokenRequest):
    """Refresh an access token using a refresh token."""
    # Validate refresh token
    user_id = validate_refresh_token(request.refresh_token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()

    session = db_manager.get_session()
    try:
        user = User.get_by_id(session, user_id)
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

        # Create new access token
        access_token = create_access_token(data={"sub": user.username})

        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer"
        )
    finally:
        session.close()


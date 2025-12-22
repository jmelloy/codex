"""Authentication API routes."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.auth import (
    UserInDB,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from api.utils import DEFAULT_WORKSPACE_PATH
from core.workspace import Workspace
from db.models import User
from db.operations import DatabaseManager

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
    token_type: str
    user: UserResponse


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest):
    """Register a new user."""
    # Get database connection from default workspace
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"
    db_manager = DatabaseManager(db_path)
    
    with db_manager.session() as session:
        # Check if username already exists
        existing_user = User.find_one_by(session, username=request.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = User.find_one_by(session, email=request.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user workspace path
        workspaces_dir = Path(DEFAULT_WORKSPACE_PATH).parent / "workspaces"
        user_workspace_path = workspaces_dir / request.username
        
        # Create the user
        hashed_password = get_password_hash(request.password)
        user = User.create(
            session,
            validate_fk=False,
            username=request.username,
            email=request.email,
            hashed_password=hashed_password,
            workspace_path=str(user_workspace_path),
            is_active=True,
        )
        session.commit()
        
        # Initialize user's workspace
        try:
            Workspace.initialize(user_workspace_path, f"{request.username}'s Workspace")
        except Exception as e:
            # If workspace initialization fails, rollback user creation
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize workspace: {str(e)}"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user.username})
        
        return LoginResponse(
            access_token=access_token,
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
    # Get database connection from default workspace
    db_path = Path(DEFAULT_WORKSPACE_PATH) / ".lab" / "db" / "index.db"
    db_manager = DatabaseManager(db_path)
    
    with db_manager.session() as session:
        # Find user by username
        user = User.find_one_by(session, username=request.username)
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
        
        # Create access token
        access_token = create_access_token(data={"sub": user.username})
        
        return LoginResponse(
            access_token=access_token,
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
    db_manager = DatabaseManager(db_path)
    
    with db_manager.session() as session:
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

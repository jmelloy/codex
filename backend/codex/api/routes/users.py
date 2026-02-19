"""User and authentication routes."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)
from codex.api.routes.workspaces import WorkspaceCreate, create_workspace
from codex.api.schemas import ThemeUpdate, UserCreate, UserResponse
from codex.db.database import get_system_session
from codex.db.models import AgentSession, OAuthConnection, PersonalAccessToken, User, Workspace, WorkspacePermission

router = APIRouter()


@router.post("/token")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_system_session),
):
    """Login endpoint to get access token."""
    result = await session.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    # Set cookie with the access token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_system_session)) -> UserResponse:
    """Register a new user."""
    # Check if username already exists
    result = await session.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    # Check if email already exists
    result = await session.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(username=user_data.username, email=user_data.email, hashed_password=hashed_password, is_active=True)

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    default_workspace = await create_workspace(
        body=WorkspaceCreate(name=user_data.username), current_user=new_user, session=session
    )

    session.add(default_workspace)
    await session.commit()

    return UserResponse.model_validate(new_user)


@router.delete("/me")
async def delete_user(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete the current user's account.

    The user must delete all owned workspaces first.
    """
    # Check if user still owns workspaces
    ws_result = await session.execute(
        select(Workspace).where(Workspace.owner_id == current_user.id)
    )
    if ws_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete all workspaces before deleting your account",
        )

    # Delete personal access tokens
    pat_result = await session.execute(
        select(PersonalAccessToken).where(PersonalAccessToken.user_id == current_user.id)
    )
    for token in pat_result.scalars().all():
        await session.delete(token)

    # Delete OAuth connections
    oauth_result = await session.execute(
        select(OAuthConnection).where(OAuthConnection.user_id == current_user.id)
    )
    for conn in oauth_result.scalars().all():
        await session.delete(conn)

    # Delete agent sessions owned by user
    as_result = await session.execute(
        select(AgentSession).where(AgentSession.user_id == current_user.id)
    )
    for agent_session in as_result.scalars().all():
        await session.delete(agent_session)

    # Delete workspace permissions
    wp_result = await session.execute(
        select(WorkspacePermission).where(WorkspacePermission.user_id == current_user.id)
    )
    for perm in wp_result.scalars().all():
        await session.delete(perm)

    # Delete the user record
    await session.delete(current_user)
    await session.commit()

    # Clear the auth cookie
    response.delete_cookie(key="access_token")

    return {"message": "User deleted successfully"}


@router.patch("/me/theme")
async def update_user_theme(
    body: ThemeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> UserResponse:
    """Update the theme setting for the current user."""
    current_user.theme_setting = body.theme
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return UserResponse.model_validate(current_user)

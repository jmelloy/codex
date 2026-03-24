"""User and authentication routes."""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    hash_token,
    verify_password,
)
from codex.api.routes.workspaces import WorkspaceCreate, create_workspace
from codex.api.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    ThemeUpdate,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from codex.db.database import get_system_session
from codex.db.models import (
    AgentSession,
    OAuthConnection,
    PasswordResetToken,
    PersonalAccessToken,
    User,
    Workspace,
    WorkspacePermission,
)

logger = logging.getLogger(__name__)

PASSWORD_RESET_EXPIRE_MINUTES = 60

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
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


@router.post("/me/password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Change the current user's password."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    current_user.hashed_password = get_password_hash(body.new_password)
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    await session.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_system_session),
):
    """Request a password reset token.

    Always returns success to avoid leaking whether an email exists.
    The token is logged server-side; use the CLI or email integration to deliver it.
    """
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user:
        # Invalidate any existing unused tokens for this user
        existing = await session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at == None,  # noqa: E711
            )
        )
        for old_token in existing.scalars().all():
            old_token.used_at = datetime.now(UTC)  # Mark as used/invalidated
            session.add(old_token)

        # Generate new token
        plain_token = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(plain_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES),
        )
        session.add(reset_token)
        await session.commit()

        # Log the token for admin/CLI retrieval (no email system yet)
        logger.info("Password reset token generated for user %s: %s", user.username, plain_token)

    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_system_session),
):
    """Reset password using a reset token."""
    token_hash_value = hash_token(body.token)
    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash_value,
            PasswordResetToken.used_at == None,  # noqa: E711
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    if reset_token.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    # Load the user
    user_result = await session.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    # Update password and mark token as used
    user.hashed_password = get_password_hash(body.new_password)
    user.updated_at = datetime.now(UTC)
    reset_token.used_at = datetime.now(UTC)
    session.add(user)
    session.add(reset_token)
    await session.commit()

    return {"message": "Password has been reset successfully"}


@router.delete("/me", response_model=MessageResponse)
async def delete_user(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete the current user's account.

    The user must delete all owned workspaces first.
    """
    # Check if user still owns workspaces
    ws_result = await session.execute(select(Workspace).where(Workspace.owner_id == current_user.id))
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
    oauth_result = await session.execute(select(OAuthConnection).where(OAuthConnection.user_id == current_user.id))
    for conn in oauth_result.scalars().all():
        await session.delete(conn)

    # Delete agent sessions owned by user
    as_result = await session.execute(select(AgentSession).where(AgentSession.user_id == current_user.id))
    for agent_session in as_result.scalars().all():
        await session.delete(agent_session)

    # Delete workspace permissions
    wp_result = await session.execute(select(WorkspacePermission).where(WorkspacePermission.user_id == current_user.id))
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

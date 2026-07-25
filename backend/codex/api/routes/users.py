"""User and authentication routes."""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    hash_token,
    issue_refresh_token,
    verify_password,
)
from codex.api.routes.utils import slugify
from codex.api.routes.workspaces import WorkspaceCreate, create_workspace, get_workspace_by_slug
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
from codex.core.permissions import PermissionLevel
from codex.db.database import get_system_session
from codex.db.models import (
    AgentSession,
    OAuthConnection,
    PasswordResetToken,
    PersonalAccessToken,
    RefreshToken,
    User,
    UserKind,
    Workspace,
    WorkspacePermission,
)

logger = logging.getLogger(__name__)

PASSWORD_RESET_EXPIRE_MINUTES = 60

router = APIRouter()

# Bot lifecycle endpoints, mounted separately at
# /api/v1/workspaces/{workspace_identifier}/bots (see codex/main.py). Split from
# `router` because it's nested under a workspace path rather than /api/v1/users.
bots_router = APIRouter()


@router.post("/token", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_system_session),
):
    """Login endpoint to get access token."""
    result = await session.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user and user.is_bot:
        # Bots have no password and never log in interactively (issue #533
        # acceptance: "Login endpoint rejects bot credentials outright").
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot accounts cannot log in. Authenticate with a personal access token instead.",
        )

    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    refresh_token = await issue_refresh_token(user, session)

    # Set cookies with the access and refresh tokens
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        path="/api/v1/auth/refresh",
    )

    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


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

    # Delete refresh tokens
    refresh_result = await session.execute(select(RefreshToken).where(RefreshToken.user_id == current_user.id))
    for refresh_token in refresh_result.scalars().all():
        await session.delete(refresh_token)

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

    # Clear the auth cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")

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


# ── Bot service accounts (issue #533) ────────────────────────────────


class BotCreate(BaseModel):
    """Request body for creating a bot service account."""

    display_name: str = Field(..., min_length=1, max_length=100)
    avatar_url: str | None = None


class BotUpdate(BaseModel):
    """Request body for updating a bot's profile."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = None


async def _get_bot_in_workspace(bot_id: int, workspace: Workspace, session: AsyncSession) -> User:
    """Fetch a bot by id, scoped to `workspace` (the bot must have a permission grant there)."""
    bot = await session.get(User, bot_id)
    if bot is None or not bot.is_bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    grant_result = await session.execute(
        select(WorkspacePermission).where(
            WorkspacePermission.workspace_id == workspace.id,
            WorkspacePermission.user_id == bot.id,
        )
    )
    if grant_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found in this workspace")

    return bot


@bots_router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    workspace_identifier: str,
    body: BotCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> UserResponse:
    """Create a bot service account for a workspace (workspace admin only).

    Auto-generates a unique username from `display_name`. The bot has no
    password (`hashed_password` stays null) and authenticates exclusively via
    PATs issued through `/api/v1/tokens/bots/{bot_id}/tokens`. It's granted
    READ access to this workspace immediately so an issued PAT can read it
    right away; an admin can raise the level via the collaborators endpoint.
    """
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )

    base_username = f"bot-{slugify(body.display_name, default='bot')}"
    username = base_username
    while (await session.execute(select(User).where(User.username == username))).scalar_one_or_none() is not None:
        username = f"{base_username}-{secrets.token_hex(3)}"

    bot = User(
        username=username,
        email=f"{username}@bots.codex.internal",
        hashed_password=None,
        kind=UserKind.BOT.value,
        display_name=body.display_name,
        avatar_url=body.avatar_url,
        is_active=True,
    )
    session.add(bot)
    await session.commit()
    await session.refresh(bot)

    session.add(WorkspacePermission(workspace_id=workspace.id, user_id=bot.id, permission_level="read"))
    await session.commit()

    return UserResponse.model_validate(bot)


@bots_router.patch("/{bot_id}", response_model=UserResponse)
async def update_bot(
    workspace_identifier: str,
    bot_id: int,
    body: BotUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> UserResponse:
    """Update a bot's display_name/avatar_url (workspace admin only)."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    bot = await _get_bot_in_workspace(bot_id, workspace, session)

    if body.display_name is not None:
        bot.display_name = body.display_name
    if body.avatar_url is not None:
        bot.avatar_url = body.avatar_url

    session.add(bot)
    await session.commit()
    await session.refresh(bot)
    return UserResponse.model_validate(bot)


@bots_router.post("/{bot_id}/deactivate", response_model=UserResponse)
async def deactivate_bot(
    workspace_identifier: str,
    bot_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> UserResponse:
    """Deactivate a bot and revoke all its PATs (workspace admin only).

    `is_active=false` alone already blocks every route gated on
    `get_current_active_user`, but PATs are revoked too so `GET /tokens`
    reflects reality and a later reactivation doesn't resurrect old tokens
    (issue #533 acceptance: "is_active=false kills all bot access immediately").
    """
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    bot = await _get_bot_in_workspace(bot_id, workspace, session)

    bot.is_active = False
    session.add(bot)

    pat_result = await session.execute(select(PersonalAccessToken).where(PersonalAccessToken.user_id == bot.id))
    for pat in pat_result.scalars().all():
        pat.is_active = False
        session.add(pat)

    await session.commit()
    await session.refresh(bot)
    return UserResponse.model_validate(bot)

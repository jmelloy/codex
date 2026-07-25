"""Notification and workspace-watch routes (issue #530).

Notifications are read-only from the API's perspective — they are populated
entirely by the async `fanout_event` ARQ job (see `codex.worker.tasks`), never
created directly by a route. This module only exposes listing/marking-read for
the current user's own notifications, and get/set/clear for a user's
workspace-watch (opt-in/mute) preference.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.api.schemas import MessageResponse
from codex.core.events import serialize_notification
from codex.db.database import get_system_session
from codex.db.models import Event, Notification, User, WorkspaceWatch

# Top-level, mounted at /notifications
router = APIRouter()

# Nested under /workspaces/{workspace_identifier}/watch
watch_router = APIRouter()


class NotificationResponse(BaseModel):
    """A single notification, denormalized with its underlying event."""

    id: int
    event_id: int
    kind: str
    workspace_id: int
    actor_id: int | None
    subject: dict
    read_at: str | None = None
    created_at: str


class WorkspaceWatchResponse(BaseModel):
    """The current user's opt-in/mute notification preference for a workspace."""

    watching: bool
    muted: bool


class WorkspaceWatchUpdate(BaseModel):
    """Request body for opting in to watching a workspace."""

    muted: bool = False


class UnreadCountResponse(BaseModel):
    """The current user's unread notification count."""

    unread_count: int


def _serialize_notification(notification: Notification, event: Event) -> NotificationResponse:
    return NotificationResponse(**serialize_notification(notification, event))


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List the current user's notifications across all workspaces, newest first."""
    stmt = (
        select(Notification, Event)
        .join(Event, Event.id == Notification.event_id)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return [_serialize_notification(notification, event) for notification, event in result.all()]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get the count of the current user's unread notifications."""
    result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == current_user.id,
            Notification.read_at.is_(None),
        )
    )
    return UnreadCountResponse(unread_count=result.scalar_one())


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Mark a notification read. Only the recipient may mark their own notification."""
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.recipient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

    event = await session.get(Event, notification.event_id)
    return _serialize_notification(notification, event)


@router.post("/mark-all-read", response_model=MessageResponse)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Mark all of the current user's unread notifications as read."""
    now = datetime.now(UTC)
    result = await session.execute(
        select(Notification).where(
            Notification.recipient_id == current_user.id,
            Notification.read_at.is_(None),
        )
    )
    notifications = result.scalars().all()
    for notification in notifications:
        notification.read_at = now
        session.add(notification)
    await session.commit()
    return {"message": f"Marked {len(notifications)} notification(s) as read"}


@watch_router.get("/", response_model=WorkspaceWatchResponse)
async def get_workspace_watch(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get the current user's opt-in/mute notification preference for a workspace."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    result = await session.execute(
        select(WorkspaceWatch).where(
            WorkspaceWatch.workspace_id == workspace.id,
            WorkspaceWatch.user_id == current_user.id,
        )
    )
    watch = result.scalar_one_or_none()
    if watch is None:
        return WorkspaceWatchResponse(watching=False, muted=False)
    return WorkspaceWatchResponse(watching=True, muted=watch.muted)


@watch_router.put("/", response_model=WorkspaceWatchResponse)
async def set_workspace_watch(
    workspace_identifier: str,
    body: WorkspaceWatchUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Opt in to watching a workspace (or update the mute flag if already watching)."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    result = await session.execute(
        select(WorkspaceWatch).where(
            WorkspaceWatch.workspace_id == workspace.id,
            WorkspaceWatch.user_id == current_user.id,
        )
    )
    watch = result.scalar_one_or_none()
    if watch is None:
        watch = WorkspaceWatch(workspace_id=workspace.id, user_id=current_user.id, muted=body.muted)
    else:
        watch.muted = body.muted
        watch.updated_at = datetime.now(UTC)
    session.add(watch)
    await session.commit()
    await session.refresh(watch)
    return WorkspaceWatchResponse(watching=True, muted=watch.muted)


@watch_router.delete("/", response_model=MessageResponse)
async def unwatch_workspace(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Opt out of watching a workspace entirely (removes the preference row)."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    result = await session.execute(
        select(WorkspaceWatch).where(
            WorkspaceWatch.workspace_id == workspace.id,
            WorkspaceWatch.user_id == current_user.id,
        )
    )
    watch = result.scalar_one_or_none()
    if watch is not None:
        await session.delete(watch)
        await session.commit()
    return {"message": "Workspace unwatched"}

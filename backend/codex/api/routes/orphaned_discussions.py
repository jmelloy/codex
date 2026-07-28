"""Orphaned-discussions admin routes (design doc §4 / phase 6, issue #547).

All endpoints require ADMIN-level access to the workspace - restoring re-anchors a
thread to a block its participants didn't originally choose, and deleting is
permanent (no soft-delete, unlike `comments.py`'s `delete_comment`) - so only admins
may act here, mirroring `collaborators.py`'s all-admin-gated pattern. Every mutating
action also appends a `comment.orphan_*` `Event`, which doubles as this feature's
admin audit log (`GET /audit-log`).
"""

from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.api.schemas import (
    OrphanAuditLogEntryResponse,
    OrphanBulkActionRequest,
    OrphanBulkActionResponse,
    OrphanBulkActionResult,
    OrphanedCommentResponse,
    OrphanedThreadResponse,
    OrphanRestoreRequest,
)
from codex.core.blocks import get_block
from codex.core.events import build_event, enqueue_fanout
from codex.core.orphaned_discussions import OrphanedThread, find_orphaned_threads, get_orphaned_thread
from codex.core.permissions import PermissionLevel
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import Comment, CommentMention, Event, User, Workspace

router = APIRouter()


async def _usernames(session: AsyncSession, user_ids: set[int | None]) -> dict[int, str]:
    ids = {uid for uid in user_ids if uid is not None}
    if not ids:
        return {}
    result = await session.execute(select(User.id, User.username).where(User.id.in_(ids)))
    return dict(result.all())


def _serialize_comment(comment: Comment, usernames: dict[int, str]) -> OrphanedCommentResponse:
    return OrphanedCommentResponse(
        id=comment.id,
        author_id=comment.author_id,
        author_username=usernames.get(comment.author_id),
        body=comment.body,
        created_at=comment.created_at.isoformat(),
        deleted_at=comment.deleted_at.isoformat() if comment.deleted_at else None,
    )


async def _serialize_thread(session: AsyncSession, thread: OrphanedThread) -> OrphanedThreadResponse:
    user_ids = {thread.root.author_id, thread.root.archived_by_id, *(r.author_id for r in thread.replies)}
    usernames = await _usernames(session, user_ids)
    return OrphanedThreadResponse(
        thread_id=thread.thread_id,
        workspace_id=thread.root.workspace_id,
        notebook_id=thread.notebook.id,
        notebook_name=thread.notebook.name,
        block_id=thread.root.block_id,
        reason=thread.reason,
        root=_serialize_comment(thread.root, usernames),
        replies=[_serialize_comment(reply, usernames) for reply in thread.replies],
        reply_count=len(thread.live_replies),
        last_activity_at=thread.last_activity_at.isoformat(),
        archived_at=thread.root.archived_at.isoformat() if thread.root.archived_at else None,
        archived_by_id=thread.root.archived_by_id,
        archived_by_username=usernames.get(thread.root.archived_by_id),
    )


def _parse_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date: {value!r}. Expected YYYY-MM-DD.") from None
    time_part = datetime.max.time() if end_of_day else datetime.min.time()
    return datetime.combine(parsed, time_part, tzinfo=UTC)


async def _restore_thread(
    request: Request,
    session: AsyncSession,
    workspace: Workspace,
    current_user: User,
    thread: OrphanedThread,
    new_block_id: str | None,
) -> OrphanedThread:
    old_block_id = thread.root.block_id
    if thread.reason == "block_deleted":
        if not new_block_id:
            raise HTTPException(
                status_code=400, detail="block_id is required to restore a thread whose block was deleted"
            )
        notebook_path = Path(workspace.path).resolve() / thread.notebook.path
        nb_session = get_notebook_session(str(notebook_path))
        try:
            if get_block(thread.notebook.id, new_block_id, nb_session) is None:
                raise HTTPException(status_code=404, detail="Target block not found in this notebook")
        finally:
            nb_session.close()
        for comment in (thread.root, *thread.replies):
            comment.block_id = new_block_id
            session.add(comment)

    thread.root.deleted_at = None
    thread.root.archived_at = None
    thread.root.archived_by_id = None
    session.add(thread.root)
    for reply in thread.replies:
        reply.archived_at = None
        reply.archived_by_id = None
        session.add(reply)

    event = build_event(
        workspace_id=workspace.id,
        actor_id=current_user.id,
        kind="comment.orphan_restored",
        subject={
            "thread_id": thread.thread_id,
            "notebook_id": thread.notebook.id,
            "reason": thread.reason,
            "old_block_id": old_block_id,
            "new_block_id": new_block_id if thread.reason == "block_deleted" else old_block_id,
        },
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    await enqueue_fanout(request, event.id)

    await session.refresh(thread.root)
    for reply in thread.replies:
        await session.refresh(reply)
    return thread


async def _archive_thread(
    session: AsyncSession, workspace: Workspace, current_user: User, thread: OrphanedThread
) -> OrphanedThread:
    now = datetime.now(UTC)
    for comment in (thread.root, *thread.replies):
        comment.archived_at = now
        comment.archived_by_id = current_user.id
        session.add(comment)

    event = build_event(
        workspace_id=workspace.id,
        actor_id=current_user.id,
        kind="comment.orphan_archived",
        subject={"thread_id": thread.thread_id, "notebook_id": thread.notebook.id, "reason": thread.reason},
    )
    session.add(event)
    await session.commit()

    await session.refresh(thread.root)
    for reply in thread.replies:
        await session.refresh(reply)
    return thread


async def _delete_thread(
    session: AsyncSession, workspace: Workspace, current_user: User, thread: OrphanedThread
) -> None:
    comment_ids = [thread.root.id, *(r.id for r in thread.replies)]
    subject = {
        "thread_id": thread.thread_id,
        "notebook_id": thread.notebook.id,
        "reason": thread.reason,
        "block_id": thread.root.block_id,
        "comment_count": len(comment_ids),
        "author_ids": list({thread.root.author_id, *(r.author_id for r in thread.replies)}),
    }

    mention_result = await session.execute(select(CommentMention).where(CommentMention.comment_id.in_(comment_ids)))
    for mention in mention_result.scalars().all():
        await session.delete(mention)
    for comment in (thread.root, *thread.replies):
        await session.delete(comment)

    event = build_event(
        workspace_id=workspace.id, actor_id=current_user.id, kind="comment.orphan_deleted", subject=subject
    )
    session.add(event)
    await session.commit()


@router.get("/", response_model=list[OrphanedThreadResponse])
async def list_orphaned_discussions(
    workspace_identifier: str,
    notebook_id: int | None = None,
    author_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List orphaned discussion threads for a workspace, most recent activity first.

    Requires workspace admin access. Filterable by notebook, original author, and a
    created-at date range (`start_date`/`end_date`, `YYYY-MM-DD`); archived threads
    are excluded unless `include_archived=true`.
    """
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    threads = await find_orphaned_threads(
        session,
        workspace,
        notebook_id=notebook_id,
        author_id=author_id,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date, end_of_day=True),
        include_archived=include_archived,
    )
    page = threads[offset : offset + limit]
    return [await _serialize_thread(session, thread) for thread in page]


@router.get("/audit-log", response_model=list[OrphanAuditLogEntryResponse])
async def get_orphan_audit_log(
    workspace_identifier: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List admin actions taken on orphaned discussions (restore/archive/delete), newest
    first. Requires workspace admin access."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    result = await session.execute(
        select(Event)
        .where(Event.workspace_id == workspace.id, Event.kind.like("comment.orphan_%"))
        .order_by(Event.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = list(result.scalars().all())
    usernames = await _usernames(session, {e.actor_id for e in events})
    return [
        OrphanAuditLogEntryResponse(
            id=event.id,
            kind=event.kind,
            actor_id=event.actor_id,
            actor_username=usernames.get(event.actor_id),
            subject=event.subject,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]


@router.get("/{thread_id}", response_model=OrphanedThreadResponse)
async def get_orphaned_discussion(
    workspace_identifier: str,
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a single orphaned discussion thread's detail. Requires workspace admin access."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    thread = await get_orphaned_thread(session, workspace, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Orphaned discussion not found")
    return await _serialize_thread(session, thread)


@router.post("/{thread_id}/restore", response_model=OrphanedThreadResponse)
async def restore_orphaned_discussion(
    workspace_identifier: str,
    thread_id: int,
    payload: OrphanRestoreRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Restore an orphaned thread: re-anchor it to `block_id` (required when the block
    was deleted) or clear its root's soft-delete (when only the root was deleted).
    Requires workspace admin access."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    thread = await get_orphaned_thread(session, workspace, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Orphaned discussion not found")

    thread = await _restore_thread(request, session, workspace, current_user, thread, payload.block_id)
    return await _serialize_thread(session, thread)


@router.post("/{thread_id}/archive", response_model=OrphanedThreadResponse)
async def archive_orphaned_discussion(
    workspace_identifier: str,
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Archive an orphaned thread so it stops appearing in the default list, without
    deleting or un-orphaning it. Requires workspace admin access."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    thread = await get_orphaned_thread(session, workspace, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Orphaned discussion not found")

    thread = await _archive_thread(session, workspace, current_user, thread)
    return await _serialize_thread(session, thread)


@router.delete("/{thread_id}", response_model=OrphanBulkActionResult)
async def delete_orphaned_discussion(
    workspace_identifier: str,
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Permanently delete an orphaned thread (root, replies, and their mentions) - unlike
    `DELETE /comments/{id}`, this is not a soft delete. Requires workspace admin access."""
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    thread = await get_orphaned_thread(session, workspace, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Orphaned discussion not found")

    await _delete_thread(session, workspace, current_user, thread)
    return OrphanBulkActionResult(thread_id=thread_id, success=True, detail="Permanently deleted")


@router.post("/bulk-action", response_model=OrphanBulkActionResponse)
async def bulk_action_orphaned_discussions(
    workspace_identifier: str,
    payload: OrphanBulkActionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Apply the same action (archive/restore/delete) to multiple orphaned threads at
    once. Each thread is processed independently, so one failure doesn't abort the
    rest. A `restore` bulk action re-anchors every thread to the same `block_id`
    (e.g. several threads whose pages were merged into one). Requires workspace admin
    access.
    """
    workspace = await get_workspace_by_slug(
        workspace_identifier, current_user, session, required_level=PermissionLevel.ADMIN
    )
    if payload.action == "restore" and not payload.block_id:
        raise HTTPException(status_code=400, detail="block_id is required for bulk restore")

    results = []
    for thread_id in payload.thread_ids:
        try:
            thread = await get_orphaned_thread(session, workspace, thread_id)
            if thread is None:
                results.append(
                    OrphanBulkActionResult(thread_id=thread_id, success=False, detail="Not found or not orphaned")
                )
                continue

            if payload.action == "archive":
                await _archive_thread(session, workspace, current_user, thread)
                results.append(OrphanBulkActionResult(thread_id=thread_id, success=True, detail="Archived"))
            elif payload.action == "restore":
                await _restore_thread(request, session, workspace, current_user, thread, payload.block_id)
                results.append(OrphanBulkActionResult(thread_id=thread_id, success=True, detail="Restored"))
            else:
                await _delete_thread(session, workspace, current_user, thread)
                results.append(OrphanBulkActionResult(thread_id=thread_id, success=True, detail="Permanently deleted"))
        except HTTPException as e:
            results.append(OrphanBulkActionResult(thread_id=thread_id, success=False, detail=str(e.detail)))

    return OrphanBulkActionResponse(results=results)

"""Comment routes: threaded comments anchored to a block ULID (issue #529).

Comments live in the system database and are anchored to `Block.block_id`
(the ULID that survives file renames/moves), not the notebook-local numeric
block id. Mentions are parsed against workspace-visible principals once, at
post time, and never re-parsed on read (design doc §4).
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import PermissionScope, get_current_active_user, require_scope
from codex.api.routes.helpers import get_notebook_path_nested
from codex.api.schemas import CommentCreate, CommentMentionResponse, CommentResponse, CommentUpdate, MessageResponse
from codex.core.blocks import get_block
from codex.core.permissions import PermissionLevel, effective_level, has_permission, require_level
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import Comment, CommentMention, User, Workspace, WorkspacePermission

# Matches @handle tokens; handles are usernames, which this codebase restricts
# to alphanumerics/underscore/period/hyphen (see UserCreate).
MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_.-]+)")

# Nested under /workspaces/{workspace_identifier}/notebooks/{notebook_identifier}/blocks/{block_id}/comments
nested_router = APIRouter()

# Top-level, mounted at /comments
router = APIRouter()


def _assert_block_exists(notebook_path: Path, notebook_id: int, block_id: str) -> None:
    nb_session = get_notebook_session(str(notebook_path))
    try:
        if get_block(notebook_id, block_id, nb_session) is None:
            raise HTTPException(status_code=404, detail="Block not found")
    finally:
        nb_session.close()


async def _parse_and_store_mentions(comment: Comment, workspace: Workspace, session: AsyncSession) -> list[CommentMention]:
    """Resolve @handles in `comment.body` against workspace-visible principals and persist them.

    Called once at comment creation. `comment.id` must already be assigned
    (caller has flushed) since mentions FK to it.
    """
    handles = set(MENTION_RE.findall(comment.body))
    if not handles:
        return []

    result = await session.execute(
        select(User).where(
            User.username.in_(handles),
            (User.id == workspace.owner_id)
            | (
                User.id.in_(
                    select(WorkspacePermission.user_id).where(WorkspacePermission.workspace_id == workspace.id)
                )
            ),
        )
    )
    principals_by_handle = {user.username: user for user in result.scalars().all()}

    mentions = []
    for handle in handles:
        principal = principals_by_handle.get(handle)
        if principal is None:
            continue
        mention = CommentMention(comment_id=comment.id, mentioned_principal_id=principal.id, handle=handle)
        session.add(mention)
        mentions.append(mention)
    return mentions


def _serialize(comment: Comment, author_username: str | None, mentions: list[CommentMention]) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        workspace_id=comment.workspace_id,
        notebook_id=comment.notebook_id,
        block_id=comment.block_id,
        thread_id=comment.thread_id,
        author_id=comment.author_id,
        author_username=author_username,
        body=comment.body,
        resolved_at=comment.resolved_at.isoformat() if comment.resolved_at else None,
        resolved_by_id=comment.resolved_by_id,
        created_at=comment.created_at.isoformat(),
        updated_at=comment.updated_at.isoformat(),
        mentions=[CommentMentionResponse.model_validate(m) for m in mentions],
    )


async def _get_comment_or_404(comment_id: int, session: AsyncSession) -> tuple[Comment, Workspace]:
    comment = await session.get(Comment, comment_id)
    if comment is None or comment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Comment not found")
    workspace = await session.get(Workspace, comment.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment, workspace


@nested_router.get("/", response_model=list[CommentResponse])
async def list_comments(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List non-deleted comments on a block, oldest first. Requires read access."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session, required_level=PermissionLevel.READ
    )
    _assert_block_exists(notebook_path, notebook.id, block_id)

    result = await session.execute(
        select(Comment, User.username)
        .join(User, User.id == Comment.author_id)
        .where(
            Comment.workspace_id == workspace.id,
            Comment.notebook_id == notebook.id,
            Comment.block_id == block_id,
            Comment.deleted_at.is_(None),
        )
        .order_by(Comment.created_at)
    )
    rows = result.all()

    comment_ids = [comment.id for comment, _ in rows]
    mentions_by_comment: dict[int, list[CommentMention]] = {cid: [] for cid in comment_ids}
    if comment_ids:
        mention_result = await session.execute(
            select(CommentMention).where(CommentMention.comment_id.in_(comment_ids))
        )
        for mention in mention_result.scalars().all():
            mentions_by_comment[mention.comment_id].append(mention)

    return [_serialize(comment, username, mentions_by_comment[comment.id]) for comment, username in rows]


@nested_router.post("/", response_model=CommentResponse, status_code=201)
async def create_comment(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    payload: CommentCreate,
    current_user: User = Depends(require_scope(PermissionScope.COMMENTS_WRITE)),
    session: AsyncSession = Depends(get_system_session),
):
    """Post a comment on a block. Requires `comment` permission level (or higher)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session, required_level=PermissionLevel.COMMENT
    )
    _assert_block_exists(notebook_path, notebook.id, block_id)

    thread_id = None
    if payload.thread_id is not None:
        root = await session.get(Comment, payload.thread_id)
        if (
            root is None
            or root.deleted_at is not None
            or root.workspace_id != workspace.id
            or root.notebook_id != notebook.id
            or root.block_id != block_id
        ):
            raise HTTPException(status_code=404, detail="Parent comment not found")
        # Flatten to the thread root so replies never nest more than one level deep.
        thread_id = root.thread_id or root.id

    comment = Comment(
        workspace_id=workspace.id,
        notebook_id=notebook.id,
        block_id=block_id,
        thread_id=thread_id,
        author_id=current_user.id,
        body=payload.body,
    )
    session.add(comment)
    await session.flush()

    mentions = await _parse_and_store_mentions(comment, workspace, session)
    await session.commit()
    await session.refresh(comment)

    return _serialize(comment, current_user.username, mentions)


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    payload: CommentUpdate,
    current_user: User = Depends(require_scope(PermissionScope.COMMENTS_WRITE)),
    session: AsyncSession = Depends(get_system_session),
):
    """Edit a comment's body. Only the comment's author may edit it."""
    comment, workspace = await _get_comment_or_404(comment_id, session)
    level = await effective_level(current_user, workspace, session)
    if level is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the comment's author can edit it")
    if not has_permission(level, PermissionLevel.COMMENT):
        raise HTTPException(status_code=403, detail="Insufficient permission for this operation")

    comment.body = payload.body
    comment.updated_at = datetime.now(timezone.utc)
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    mention_result = await session.execute(select(CommentMention).where(CommentMention.comment_id == comment.id))
    mentions = list(mention_result.scalars().all())

    return _serialize(comment, current_user.username, mentions)


@router.delete("/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(require_scope(PermissionScope.COMMENTS_WRITE)),
    session: AsyncSession = Depends(get_system_session),
):
    """Soft-delete a comment. The author or a workspace admin may delete it.

    No cascade: replies and mentions are left in place, and the deleted parent
    resurfaces the thread as orphaned (design doc §4 / phase-6 orphaned-discussions view).
    """
    comment, workspace = await _get_comment_or_404(comment_id, session)
    level = await effective_level(current_user, workspace, session)
    if level is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    is_author = comment.author_id == current_user.id
    is_admin = has_permission(level, PermissionLevel.ADMIN)
    if not is_admin and not (is_author and has_permission(level, PermissionLevel.COMMENT)):
        raise HTTPException(status_code=403, detail="Only the comment's author or a workspace admin can delete it")

    comment.deleted_at = datetime.now(timezone.utc)
    session.add(comment)
    await session.commit()

    return {"message": "Comment deleted"}


@router.post("/{comment_id}/resolve", response_model=CommentResponse)
async def resolve_comment(
    comment_id: int,
    current_user: User = Depends(require_scope(PermissionScope.COMMENTS_WRITE)),
    session: AsyncSession = Depends(get_system_session),
):
    """Mark a comment thread resolved. Requires `comment` permission level (or higher).

    Resolves the thread root: if `comment_id` refers to a reply, the root
    comment (`thread_id`) is resolved instead so the whole thread is marked
    resolved regardless of which reply the client passed in.
    """
    comment, workspace = await _get_comment_or_404(comment_id, session)
    await require_level(current_user, workspace, PermissionLevel.COMMENT, session)

    if comment.thread_id is not None:
        comment, workspace = await _get_comment_or_404(comment.thread_id, session)

    comment.resolved_at = datetime.now(timezone.utc)
    comment.resolved_by_id = current_user.id
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    author = await session.get(User, comment.author_id)
    mention_result = await session.execute(select(CommentMention).where(CommentMention.comment_id == comment.id))
    mentions = list(mention_result.scalars().all())

    return _serialize(comment, author.username if author else None, mentions)

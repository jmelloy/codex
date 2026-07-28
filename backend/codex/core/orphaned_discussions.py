"""Orphaned discussion thread discovery (design doc §4 / phase 6, issue #547).

A discussion thread orphans in one of two ways:

1. Its anchor block is hard-deleted. Blocks have no tombstone -
   `codex.core.blocks.delete_block` removes the row outright - so detecting this
   requires a cross-database join: `Comment.block_id` lives in the system db,
   `Block.block_id` in a per-notebook db. This module fetches the live block ids
   for a notebook once and diffs comment threads against that set in Python,
   rather than every caller re-implementing the same join.
2. Its root comment is soft-deleted (`comments.py`'s `delete_comment`) while at
   least one reply remains live - deletes never cascade, so the thread is still
   there, just missing its root.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.db.database import get_notebook_session
from codex.db.models import Block, Comment, Notebook, Workspace


@dataclass
class OrphanedThread:
    """A thread root plus its replies, already established to be orphaned."""

    root: Comment
    replies: list[Comment]
    notebook: Notebook
    reason: str  # "block_deleted" | "root_deleted"

    @property
    def thread_id(self) -> int:
        return self.root.id

    @property
    def last_activity_at(self) -> datetime:
        return max([self.root.created_at, *(r.created_at for r in self.replies)])

    @property
    def live_replies(self) -> list[Comment]:
        return [r for r in self.replies if r.deleted_at is None]


def _live_block_ids(notebook_path: Path, notebook_id: int) -> set[str]:
    nb_session = get_notebook_session(str(notebook_path))
    try:
        rows = nb_session.exec(select(Block.block_id).where(Block.notebook_id == notebook_id)).all()
        return set(rows)
    finally:
        nb_session.close()


def _classify(root: Comment, replies: list[Comment], live_block_ids: set[str]) -> str | None:
    """Return the orphan reason for a thread, or None if it isn't (currently) orphaned."""
    if root.block_id not in live_block_ids:
        return "block_deleted"
    if root.deleted_at is not None and any(r.deleted_at is None for r in replies):
        return "root_deleted"
    return None


async def _group_threads(
    session: AsyncSession, workspace: Workspace, notebook: Notebook
) -> list[tuple[Comment, list[Comment]]]:
    result = await session.execute(
        select(Comment).where(Comment.workspace_id == workspace.id, Comment.notebook_id == notebook.id)
    )
    comments = list(result.scalars().all())
    roots_by_id = {c.id: c for c in comments if c.thread_id is None}
    replies_by_root: dict[int, list[Comment]] = {rid: [] for rid in roots_by_id}
    for comment in comments:
        if comment.thread_id is not None and comment.thread_id in replies_by_root:
            replies_by_root[comment.thread_id].append(comment)
    return [(root, replies_by_root[root.id]) for root in roots_by_id.values()]


async def find_orphaned_threads(
    session: AsyncSession,
    workspace: Workspace,
    *,
    notebook_id: int | None = None,
    author_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    include_archived: bool = False,
) -> list[OrphanedThread]:
    """Find every orphaned discussion thread in a workspace, across all its notebooks.

    Threads are sorted by most-recent activity first. Pagination is the caller's
    responsibility (this returns the full matching set - orphaned-thread volume is
    expected to be small relative to total comment volume).
    """
    notebook_query = select(Notebook).where(Notebook.workspace_id == workspace.id)
    if notebook_id is not None:
        notebook_query = notebook_query.where(Notebook.id == notebook_id)
    result = await session.execute(notebook_query)
    notebooks = list(result.scalars().all())

    workspace_path = Path(workspace.path).resolve()

    threads: list[OrphanedThread] = []
    for notebook in notebooks:
        notebook_path = workspace_path / notebook.path
        if not notebook_path.exists():
            continue
        live_block_ids = _live_block_ids(notebook_path, notebook.id)

        for root, replies in await _group_threads(session, workspace, notebook):
            reason = _classify(root, replies, live_block_ids)
            if reason is None:
                continue
            if not include_archived and root.archived_at is not None:
                continue
            if author_id is not None and root.author_id != author_id:
                continue
            if start_date is not None and root.created_at < start_date:
                continue
            if end_date is not None and root.created_at > end_date:
                continue
            threads.append(OrphanedThread(root=root, replies=replies, notebook=notebook, reason=reason))

    threads.sort(key=lambda t: t.last_activity_at, reverse=True)
    return threads


async def get_orphaned_thread(session: AsyncSession, workspace: Workspace, thread_id: int) -> OrphanedThread | None:
    """Look up a single orphaned thread by its root comment id.

    Returns None if the comment doesn't exist, isn't a thread root, doesn't belong
    to this workspace, or isn't (currently) orphaned.
    """
    root = await session.get(Comment, thread_id)
    if root is None or root.workspace_id != workspace.id or root.thread_id is not None:
        return None
    notebook = await session.get(Notebook, root.notebook_id)
    if notebook is None:
        return None
    notebook_path = Path(workspace.path).resolve() / notebook.path
    if not notebook_path.exists():
        return None
    live_block_ids = _live_block_ids(notebook_path, notebook.id)

    result = await session.execute(select(Comment).where(Comment.thread_id == thread_id))
    replies = list(result.scalars().all())

    reason = _classify(root, replies, live_block_ids)
    if reason is None:
        return None
    return OrphanedThread(root=root, replies=replies, notebook=notebook, reason=reason)

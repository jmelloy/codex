"""Server working-copy indexer for shared (org) notebooks.

Issue #542, design doc §3.2/§1 (L3/L5). For shared workspaces S3 is the
canonical content store; the server materializes a working copy per notebook
on local disk and reuses the existing watcher/metadata pipeline
(`codex.core.watcher.update_file_metadata`) unchanged on top of it. The
per-notebook SQLite DB is a **derived index that is never synced** -- this
process rebuilds/updates its own from S3 state, exactly like a future offline
client would, sidestepping SQLite-over-S3 corruption entirely.

Two entry points:
    rebuild_notebook_index(workspace, notebook)   - full rebuild from an S3 listing
    apply_journal_entry(workspace, notebook, entry) - incremental, one `sync_journal`
        row (the change feed from issue #541) applied to the working copy

`S3IndexerService` is the background poller wired into `main.py`'s lifespan:
for every shared (org) workspace it does a cold-start full rebuild for
notebooks with no local working copy yet, then applies new journal rows
incrementally. Personal workspaces (`org_id is None`) are never touched --
they keep the existing filesystem-watcher path (#542 acceptance criterion).

The incremental cursor is persisted to a local `.codex/sync_cursor` file (not
synced -- like the rest of `.codex/`, it's derived state) so a server restart
resumes from where it left off instead of re-scanning S3 or replaying the
whole journal.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

from sqlmodel import select

from codex.core.s3_storage import S3_BUCKET, download_binary, get_s3_client, is_s3_configured
from codex.core.sync_credentials import build_workspace_prefix
from codex.core.watcher import update_file_metadata
from codex.db.database import get_notebook_session, get_system_session_sync, init_notebook_db
from codex.db.models import Block, Notebook, SyncJournal, Workspace

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5.0  # seconds; matches watcher.FileOperationQueue.BATCH_INTERVAL
CURSOR_FILENAME = "sync_cursor"


def is_shared_workspace(workspace: Workspace) -> bool:
    """Org workspaces are S3-synced (shared); personal workspaces are not (design doc §1)."""
    return workspace.org_id is not None


def notebook_working_copy_path(workspace: Workspace, notebook: Notebook) -> Path:
    """Local materialized-copy path for a notebook -- same layout as the filesystem watcher's."""
    return (Path(workspace.path) / notebook.path).resolve()


def notebook_content_prefix(workspace: Workspace, notebook: Notebook) -> str:
    """S3 prefix for a notebook's content tree (design doc §3.2)."""
    return f"{build_workspace_prefix(workspace)}notebooks/{notebook.id}/content/"


def _cursor_file(notebook_path: Path) -> Path:
    return notebook_path / ".codex" / CURSOR_FILENAME


def _read_cursor(notebook_path: Path) -> int | None:
    try:
        return int(_cursor_file(notebook_path).read_text().strip())
    except (OSError, ValueError):
        return None


def _write_cursor(notebook_path: Path, cursor: int) -> None:
    cursor_file = _cursor_file(notebook_path)
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    cursor_file.write_text(str(cursor))


# ---------------------------------------------------------------------------
# Concurrency: serialize rebuild/apply per notebook so a poll tick can never
# race a concurrently triggered rebuild (or another tick) over the same
# working copy / notebook DB.
# ---------------------------------------------------------------------------
_notebook_locks: dict[int, threading.Lock] = {}
_locks_registry_lock = threading.Lock()


def _lock_for_notebook(notebook_id: int) -> threading.Lock:
    with _locks_registry_lock:
        return _notebook_locks.setdefault(notebook_id, threading.Lock())


@dataclass
class IndexResult:
    """Outcome of a rebuild or incremental apply."""

    processed: int = 0
    deleted: int = 0
    errors: list[str] = field(default_factory=list)


def _local_path(notebook_path: Path, relative_path: str) -> Path:
    return notebook_path / relative_path


def _materialize_object(notebook_path: Path, relative_path: str, s3_key: str, version_id: str | None) -> Path:
    """Download an S3 object into the notebook's local working copy. Returns the local path."""
    local_file = _local_path(notebook_path, relative_path)
    local_file.parent.mkdir(parents=True, exist_ok=True)
    data = download_binary(s3_key, version_id=version_id)
    local_file.write_bytes(data)
    return local_file


def rebuild_notebook_index(workspace: Workspace, notebook: Notebook) -> IndexResult:
    """Full rebuild: materialize every object under the notebook's S3 content prefix
    into its local working copy, then reindex via the watcher pipeline.

    Local files (and their `Block` rows) that no longer exist in S3 are removed,
    so a stale or missing working copy converges back to S3 state -- this is the
    "cold start" path (#542 acceptance: server rebuilds a notebook working copy +
    index from S3 alone).
    """
    result = IndexResult()
    if not is_s3_configured():
        logger.warning("S3 not configured; skipping rebuild for notebook %s", notebook.id)
        return result

    with _lock_for_notebook(notebook.id):
        notebook_path = notebook_working_copy_path(workspace, notebook)
        notebook_path.mkdir(parents=True, exist_ok=True)
        init_notebook_db(str(notebook_path))

        # Capture the journal cursor *before* listing S3, so any change that lands
        # concurrently with this rebuild is picked up by the next incremental poll
        # rather than silently lost between the listing and the cursor write.
        system_session = get_system_session_sync()
        try:
            latest_entry = system_session.exec(
                select(SyncJournal).where(SyncJournal.nb_id == notebook.id).order_by(SyncJournal.id.desc()).limit(1)
            ).first()
        finally:
            system_session.close()
        baseline_cursor = latest_entry.id if latest_entry else 0

        prefix = notebook_content_prefix(workspace, notebook)
        client = get_s3_client()

        seen_relative_paths: set[str] = set()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                relative_path = key[len(prefix) :]
                if not relative_path or relative_path.endswith("/"):
                    continue
                seen_relative_paths.add(relative_path)
                try:
                    local_file = _materialize_object(notebook_path, relative_path, key, version_id=None)
                    update_file_metadata(str(notebook_path), notebook.id, str(local_file), "scanned")
                    result.processed += 1
                except Exception as e:
                    logger.error("Failed to materialize %s for notebook %s: %s", key, notebook.id, e, exc_info=True)
                    result.errors.append(f"{relative_path}: {e}")

        notebook_session = get_notebook_session(str(notebook_path))
        try:
            existing_paths = {b.path for b in notebook_session.execute(select(Block)).scalars().all()}
        finally:
            notebook_session.close()

        for stale_path in existing_paths - seen_relative_paths:
            local_file = _local_path(notebook_path, stale_path)
            if local_file.exists():
                local_file.unlink()
            update_file_metadata(str(notebook_path), notebook.id, str(local_file), "deleted")
            result.deleted += 1

        _write_cursor(notebook_path, baseline_cursor)

    return result


def apply_journal_entry(workspace: Workspace, notebook: Notebook, entry: SyncJournal) -> None:
    """Apply one `sync_journal` row to the notebook's local working copy + index.

    If no working copy exists yet, falls back to a full rebuild instead of
    patching in a single file -- consistent with the cold-start path above.
    """
    notebook_path = notebook_working_copy_path(workspace, notebook)
    if not (notebook_path / ".codex" / "notebook.db").exists():
        rebuild_notebook_index(workspace, notebook)
        return

    with _lock_for_notebook(notebook.id):
        local_file = _local_path(notebook_path, entry.path)

        if entry.op == "deleted":
            if local_file.exists():
                local_file.unlink()
            update_file_metadata(str(notebook_path), notebook.id, str(local_file), "deleted")
            return

        prefix = notebook_content_prefix(workspace, notebook)
        s3_key = f"{prefix}{entry.path}"
        _materialize_object(notebook_path, entry.path, s3_key, version_id=entry.s3_version_id)
        update_file_metadata(str(notebook_path), notebook.id, str(local_file), "scanned")


class S3IndexerService:
    """Background poller applying the S3 change feed to shared notebooks' working copies.

    Plays the same role for shared (org) notebooks that `NotebookWatcher` plays
    for personal ones, except the source of change events is the `sync_journal`
    table (issue #541) rather than filesystem events, since S3 -- not the local
    disk -- is canonical for shared notebooks.
    """

    def __init__(self, poll_interval: float = POLL_INTERVAL):
        self.poll_interval = poll_interval
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._cursors: dict[int, int] = {}

    def start(self) -> None:
        if not is_s3_configured():
            logger.info("S3 not configured; S3 working-copy indexer will not start")
            return
        if self._task is not None:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run())
        logger.info("S3 working-copy indexer started (poll interval=%ss)", self.poll_interval)

    async def stop(self) -> None:
        if self._task is None:
            return
        assert self._stop_event is not None
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=self.poll_interval + 5)
        except TimeoutError:
            self._task.cancel()
        self._task = None
        self._stop_event = None

    async def _run(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self.poll_once)
            except Exception:
                logger.error("S3 indexer poll failed", exc_info=True)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except TimeoutError:
                pass

    def poll_once(self) -> None:
        """Poll every shared workspace's notebooks once, synchronously.

        Safe to call directly (e.g. from tests or a thread pool) without the
        background loop running.
        """
        session = get_system_session_sync()
        try:
            rows = session.exec(select(Notebook, Workspace).join(Workspace, Notebook.workspace_id == Workspace.id))
            for notebook, workspace in rows.all():
                if not is_shared_workspace(workspace):
                    continue
                try:
                    self._poll_notebook(session, notebook, workspace)
                except Exception:
                    logger.error("Failed to poll notebook %s for S3 changes", notebook.id, exc_info=True)
        finally:
            session.close()

    def _poll_notebook(self, session, notebook: Notebook, workspace: Workspace) -> None:
        notebook_path = notebook_working_copy_path(workspace, notebook)
        has_working_copy = (notebook_path / ".codex" / "notebook.db").exists()

        cursor = self._cursors.get(notebook.id)
        if cursor is None:
            cursor = _read_cursor(notebook_path) if has_working_copy else None

        if cursor is None or not has_working_copy:
            rebuild_notebook_index(workspace, notebook)
            cursor = _read_cursor(notebook_path) or 0

        self._cursors[notebook.id] = cursor

        entries = session.exec(
            select(SyncJournal)
            .where(SyncJournal.nb_id == notebook.id, SyncJournal.id > cursor)
            .order_by(SyncJournal.id.asc())
        ).all()

        for entry in entries:
            try:
                apply_journal_entry(workspace, notebook, entry)
            except Exception:
                logger.error(
                    "Failed to apply sync journal entry %s for notebook %s; will retry next poll",
                    entry.id,
                    notebook.id,
                    exc_info=True,
                )
                break
            self._cursors[notebook.id] = entry.id
            _write_cursor(notebook_path, entry.id)


indexer_service = S3IndexerService()

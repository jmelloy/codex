"""File system watcher for monitoring changes."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlmodel import select
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from codex.core.metadata import MetadataParser
from codex.core.websocket import notify_file_change
from codex.db.database import get_notebook_session
from codex.db.models import FileMetadata

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Global registry of active watchers
_active_watchers: list[NotebookWatcher] = []


def get_active_watchers() -> list[NotebookWatcher]:
    """Get the list of active notebook watchers."""
    return _active_watchers


def register_watcher(watcher: NotebookWatcher) -> None:
    """Register a watcher in the global registry."""
    _active_watchers.append(watcher)


def unregister_watcher(watcher: NotebookWatcher) -> None:
    """Remove a watcher from the global registry."""
    if watcher in _active_watchers:
        _active_watchers.remove(watcher)


def get_watcher_for_notebook(notebook_path: str) -> NotebookWatcher | None:
    """Get the active watcher for a notebook path.

    Args:
        notebook_path: Path to the notebook directory (will be resolved to absolute path)

    Returns:
        The NotebookWatcher for this notebook, or None if not found
    """
    resolved_path = str(Path(notebook_path).resolve())

    for watcher in _active_watchers:
        watcher_path = str(Path(watcher.notebook_path).resolve())
        if watcher_path == resolved_path:
            return watcher

    return None


def stop_all_watchers() -> None:
    """Stop all active watchers."""
    for watcher in _active_watchers[:]:  # Copy list to avoid mutation during iteration
        try:
            watcher.stop()
            unregister_watcher(watcher)
        except Exception as e:
            logger.error(f"Error stopping watcher: {e}", exc_info=True)


@dataclass
class FileOperation:
    """Represents a file operation to be processed by the queue."""

    filepath: str  # Absolute path
    sidecar_path: str | None  # Sidecar file path
    operation: str  # "created", "modified", "deleted", "scanned"
    comment: str | None = None  # Optional commit message
    file_hash: str | None = None  # For move detection (captured at enqueue for deletes)
    timestamp: float = field(default_factory=time.time)  # When enqueued
    completion_event: threading.Event | None = None  # For synchronous waiting
    result: dict | None = None  # Result after processing
    error: Exception | None = None  # Error if processing failed


class FileOperationQueue:
    """Thread-safe queue for batching file operations."""

    BATCH_INTERVAL = 5.0  # Process batch every 5 seconds

    def __init__(
        self,
        notebook_path: str,
        notebook_id: int,
        process_callback: Callable[[str, str | None, str], None],
    ):
        """Initialize the queue.

        Args:
            notebook_path: Path to the notebook directory
            notebook_id: ID of the notebook
            process_callback: Function to call to process a single file operation.
                              Signature: (filepath, sidecar_path, operation) -> None
        """
        self.notebook_path = notebook_path
        self.notebook_id = notebook_id
        self.process_callback = process_callback
        self._queue: queue.Queue[FileOperation] = queue.Queue()
        self._stop_event = threading.Event()
        self._processor_thread: threading.Thread | None = None

    def enqueue(
        self,
        filepath: str,
        sidecar_path: str | None = None,
        operation: str = "modified",
        comment: str | None = None,
        file_hash: str | None = None,
        wait: bool = False,
    ) -> FileOperation:
        """Add a file operation to the queue.

        Args:
            filepath: Absolute path to the file
            sidecar_path: Optional path to sidecar file
            operation: Type of operation ("created", "modified", "deleted", "scanned")
            comment: Optional commit message
            file_hash: Hash of file content (for move detection on deletes)
            wait: If True, process immediately and block until complete

        Returns:
            The FileOperation object (check .error for failures if wait=True)
        """
        op = FileOperation(
            filepath=filepath,
            sidecar_path=sidecar_path,
            operation=operation,
            comment=comment,
            file_hash=file_hash,
        )

        if wait:
            # Process immediately for synchronous operations (don't wait for batch)
            self._process_single(op)
            # Do immediate git commit for this single operation
            self._batch_git_commit([op])
        else:
            self._queue.put(op)
            logger.debug(f"Enqueued {operation} for {filepath}")

        return op

    def start(self):
        """Start the background processor thread."""
        if self._processor_thread and self._processor_thread.is_alive():
            return

        self._stop_event.clear()
        self._processor_thread = threading.Thread(
            target=self._process_loop,
            name=f"queue-processor-{self.notebook_id}",
            daemon=True,
        )
        self._processor_thread.start()
        logger.info(f"Started queue processor for notebook {self.notebook_id}")

    def stop(self, timeout: float = 30.0):
        """Stop the processor and drain remaining items.

        Args:
            timeout: Maximum time to wait for processing to complete
        """
        logger.info(f"Stopping queue processor for notebook {self.notebook_id}")
        self._stop_event.set()

        if self._processor_thread and self._processor_thread.is_alive():
            self._processor_thread.join(timeout=timeout)

    def _process_loop(self):
        """Main processing loop - collects and processes batches."""
        while not self._stop_event.is_set():
            # Wait for batch interval or until stopped
            self._stop_event.wait(timeout=self.BATCH_INTERVAL)

            # Collect all pending operations
            batch = self._collect_batch()
            if batch:
                self._process_batch(batch)

        # Process any remaining items on shutdown
        remaining = self._collect_batch()
        if remaining:
            logger.info(f"Processing {len(remaining)} remaining operations on shutdown")
            self._process_batch(remaining)

    def _collect_batch(self) -> list[FileOperation]:
        """Collect all pending operations from the queue."""
        operations = []
        while True:
            try:
                op = self._queue.get_nowait()
                operations.append(op)
            except queue.Empty:
                break
        return operations

    def _process_batch(self, operations: list[FileOperation]):
        """Process a batch of operations.

        Consolidates operations and detects moves.
        """
        if not operations:
            return

        logger.debug(f"Processing batch of {len(operations)} operations")

        # Consolidate operations by path - keep latest for same file
        consolidated: dict[str, FileOperation] = {}
        for op in operations:
            existing = consolidated.get(op.filepath)
            if existing is None or op.timestamp > existing.timestamp:
                consolidated[op.filepath] = op

        # Detect moves: delete + create with same hash
        deletes = {
            op.filepath: op
            for op in consolidated.values()
            if op.operation == "deleted" and op.file_hash
        }
        creates = {
            op.filepath: op
            for op in consolidated.values()
            if op.operation == "created"
        }

        moves: list[tuple[FileOperation, FileOperation]] = []  # (delete, create) pairs
        moves_handled: set[str] = set()

        # Find matching hashes between deletes and creates
        for del_path, del_op in deletes.items():
            if del_op.file_hash:
                for create_path, create_op in creates.items():
                    if create_path in moves_handled:
                        continue
                    # Compute hash for created file if needed
                    if os.path.exists(create_path):
                        try:
                            create_hash = calculate_file_hash(create_path)
                            if create_hash == del_op.file_hash and del_path != create_path:
                                moves.append((del_op, create_op))
                                moves_handled.add(del_path)
                                moves_handled.add(create_path)
                                break
                        except Exception as e:
                            logger.warning(f"Could not compute hash for {create_path}: {e}")

        # Process moves first (update path in DB)
        for del_op, create_op in moves:
            self._process_move(del_op, create_op)

        # Process remaining operations (excluding those that were part of moves)
        for filepath, op in consolidated.items():
            if filepath in moves_handled:
                continue
            self._process_single(op)

        # Batch git commit for all changes
        self._batch_git_commit(operations)

    def _process_move(self, del_op: FileOperation, create_op: FileOperation):
        """Process a file move (detected from delete + create with same hash)."""
        try:
            session = get_notebook_session(self.notebook_path)
            try:
                old_rel_path = os.path.relpath(del_op.filepath, self.notebook_path)
                new_rel_path = os.path.relpath(create_op.filepath, self.notebook_path)

                # Find the file record by old path (and clean up duplicates if any)
                file_meta = deduplicate_file_metadata(session, self.notebook_id, old_rel_path)

                if file_meta:
                    # Update path to new location
                    file_meta.path = new_rel_path
                    file_meta.filename = os.path.basename(new_rel_path)
                    file_meta.updated_at = datetime.now(UTC)

                    # Update sidecar path if applicable
                    if create_op.sidecar_path:
                        file_meta.sidecar_path = os.path.relpath(
                            create_op.sidecar_path, self.notebook_path
                        )

                    session.commit()
                    logger.info(f"Moved file in DB: {old_rel_path} -> {new_rel_path}")

                    # Notify WebSocket clients about the move
                    notify_file_change(
                        notebook_id=self.notebook_id,
                        event_type="moved",
                        path=new_rel_path,
                        old_path=old_rel_path,
                    )
                else:
                    # File not found by old path, treat as new create
                    self._process_single(create_op)

            finally:
                session.close()

            # Signal completion
            if del_op.completion_event:
                del_op.result = {"moved_to": create_op.filepath}
                del_op.completion_event.set()
            if create_op.completion_event:
                create_op.result = {"moved_from": del_op.filepath}
                create_op.completion_event.set()

        except Exception as e:
            logger.error(f"Error processing move {del_op.filepath} -> {create_op.filepath}: {e}")
            if del_op.completion_event:
                del_op.error = e
                del_op.completion_event.set()
            if create_op.completion_event:
                create_op.error = e
                create_op.completion_event.set()

    def _process_single(self, op: FileOperation):
        """Process a single file operation."""
        try:
            self.process_callback(op.filepath, op.sidecar_path, op.operation)
            op.result = {"status": "success"}

            # Notify WebSocket clients about the file change
            rel_path = os.path.relpath(op.filepath, self.notebook_path)
            notify_file_change(
                notebook_id=self.notebook_id,
                event_type=op.operation,
                path=rel_path,
            )
        except Exception as e:
            logger.error(f"Error processing {op.operation} for {op.filepath}: {e}")
            op.error = e
        finally:
            if op.completion_event:
                op.completion_event.set()

    def _batch_git_commit(self, operations: list[FileOperation]):
        """Create a single git commit for all operations in the batch."""
        from codex.core.git_manager import GitManager

        try:
            git_manager = GitManager(self.notebook_path)

            # Collect all files that need to be committed
            files_to_add = []
            commit_lines = []

            for op in operations:
                rel_path = os.path.relpath(op.filepath, self.notebook_path)
                if op.operation == "deleted":
                    commit_lines.append(f"Delete {rel_path}")
                elif op.operation == "created":
                    if os.path.exists(op.filepath):
                        files_to_add.append(op.filepath)
                        if op.sidecar_path and os.path.exists(op.sidecar_path):
                            files_to_add.append(op.sidecar_path)
                    commit_lines.append(f"Create {rel_path}")
                elif op.operation in ("modified", "scanned"):
                    if os.path.exists(op.filepath):
                        files_to_add.append(op.filepath)
                        if op.sidecar_path and os.path.exists(op.sidecar_path):
                            files_to_add.append(op.sidecar_path)
                    commit_lines.append(f"Update {rel_path}")

            if commit_lines:
                message = f"Batch update: {len(commit_lines)} changes\n\n" + "\n".join(commit_lines[:50])
                if len(commit_lines) > 50:
                    message += f"\n... and {len(commit_lines) - 50} more"

                commit_hash = git_manager.commit(message, files_to_add if files_to_add else None)
                if commit_hash:
                    logger.debug(f"Batch commit: {commit_hash[:8]} ({len(commit_lines)} changes)")

        except Exception as e:
            logger.warning(f"Could not create batch git commit: {e}")


def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# Patterns to ignore when watching files
IGNORE_PATTERNS = [".codex", ".git", "__pycache__", ".DS_Store", "node_modules"]


def should_ignore_path(path: str) -> bool:
    """Check if path should be ignored."""
    return any(pattern in path for pattern in IGNORE_PATTERNS)


def deduplicate_file_metadata(session, notebook_id: int, rel_path: str) -> FileMetadata | None:
    """Get file metadata and remove duplicates if they exist.
    
    This function queries for FileMetadata entries and removes duplicates if found.
    Note: This function commits the session when duplicates are removed.
    
    Args:
        session: Database session
        notebook_id: ID of the notebook
        rel_path: Relative path of the file
        
    Returns:
        The first FileMetadata entry (oldest by ID), or None if not found
    """
    result = session.execute(
        select(FileMetadata)
        .where(FileMetadata.notebook_id == notebook_id, FileMetadata.path == rel_path)
        .order_by(FileMetadata.id)
    )
    all_results = result.scalars().all()
    
    if len(all_results) == 0:
        return None
    
    if len(all_results) > 1:
        # Keep the first one (oldest by ID), delete the rest
        logger.warning(f'Found {len(all_results)} duplicate entries for path "{rel_path}", removing duplicates')
        file_meta = all_results[0]
        for duplicate in all_results[1:]:
            session.delete(duplicate)
        session.commit()
        return file_meta
    
    return all_results[0]


def update_file_metadata(
    notebook_path: str,
    notebook_id: int,
    filepath: str,
    event_type: str,
    callback: Callable | None = None,
) -> None:
    """Update file metadata in database.

    Args:
        notebook_path: Path to the notebook directory
        notebook_id: ID of the notebook
        filepath: Absolute path to the file
        event_type: Type of event ("created", "modified", "deleted", "scanned")
        callback: Optional callback to invoke after update
    """
    if should_ignore_path(filepath):
        return

    if Path(filepath).is_dir():
        return

    logger.debug(f"Updating metadata for {filepath} due to {event_type} event")
    session = None
    try:
        session = get_notebook_session(notebook_path)

        rel_path = os.path.relpath(filepath, notebook_path)
        filename = os.path.basename(filepath)

        # Check if file exists in database (and clean up duplicates if any)
        file_meta = deduplicate_file_metadata(session, notebook_id, rel_path)

        if event_type == "deleted":
            if file_meta:
                session.delete(file_meta)
                session.commit()
        else:
            filepath, sidecar = MetadataParser.resolve_sidecar(filepath)
            # File created or modified
            if os.path.exists(filepath):
                file_stats = os.stat(filepath)
                file_hash = calculate_file_hash(filepath)
                is_binary = is_binary_file(filepath)

                # Get content type (MIME type)
                content_type = get_content_type(filepath)
                metadata = MetadataParser.extract_all_metadata(filepath)

                if file_meta:
                    # Update existing
                    file_meta.size = file_stats.st_size
                    file_meta.hash = file_hash
                    file_meta.content_type = content_type
                    file_meta.updated_at = datetime.now(UTC)
                    file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)
                    file_meta.properties = json.dumps(metadata)

                    if sidecar:
                        file_meta.sidecar_path = os.path.relpath(sidecar, notebook_path)

                    if "title" in metadata:
                        file_meta.title = metadata["title"]
                    if "description" in metadata:
                        file_meta.description = metadata["description"]
                    if "type" in metadata:
                        file_meta.file_type = metadata["type"]

                    if "created" in metadata:
                        try:
                            created_dt = datetime.fromisoformat(metadata["created"])
                            file_meta.file_created_at = created_dt
                        except Exception:
                            pass

                else:
                    # Create new
                    file_meta = FileMetadata(
                        notebook_id=notebook_id,
                        path=rel_path,
                        filename=filename,
                        content_type=content_type,
                        size=file_stats.st_size,
                        hash=file_hash,
                        git_tracked=not is_binary,
                        properties=json.dumps(metadata),
                        sidecar_path=os.path.relpath(sidecar, notebook_path) if sidecar else None,
                        file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                        file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
                    )
                    if "title" in metadata:
                        file_meta.title = metadata["title"]
                    if "description" in metadata:
                        file_meta.description = metadata["description"]
                    if "type" in metadata:
                        file_meta.file_type = metadata["type"]

                    if "created" in metadata:
                        try:
                            created_dt = datetime.fromisoformat(metadata["created"])
                            file_meta.file_created_at = created_dt
                        except Exception:
                            pass
                    session.add(file_meta)

                # Auto-commit to git if file should be tracked
                # Skip git commits during scan - these are existing files
                if event_type != "scanned":
                    from codex.core.git_manager import GitManager

                    git_manager = GitManager(notebook_path)

                    try:
                        commit_hash = git_manager.auto_commit_on_change(filepath, sidecar)
                        if commit_hash:
                            file_meta.last_commit_hash = commit_hash
                    except Exception as e:
                        logger.warning(f"Could not commit file to git: {e}")

                try:
                    session.commit()
                except Exception as commit_error:
                    # Handle race condition: another process created the record
                    session.rollback()
                    if "UNIQUE constraint failed" in str(commit_error):
                        # Re-query and update instead (deduplicate in case multiple were created)
                        file_meta = deduplicate_file_metadata(session, notebook_id, rel_path)
                        if file_meta:
                            file_meta.size = file_stats.st_size
                            file_meta.hash = file_hash
                            file_meta.content_type = content_type
                            file_meta.updated_at = datetime.now(UTC)
                            file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)
                            session.commit()
                    else:
                        raise

        if callback:
            callback(filepath, event_type)

    except Exception as e:
        # Check if this is a database table missing error (e.g., during test cleanup)
        error_msg = str(e)
        if "no such table" in error_msg or "OperationalError" in str(type(e)):
            # Database or table has been removed (e.g., during test cleanup)
            # This is expected in some scenarios, so just log at debug level
            logger.debug(f"Database table not found for {filepath}, likely during cleanup: {e}")
        else:
            # Unexpected error - log at error level
            logger.error(f"Error updating metadata for {filepath}: {e}", exc_info=True)
    finally:
        if session:
            session.close()


def is_binary_file(filepath: str) -> bool:
    """Check if a file is binary."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
            return b"\0" in chunk
    except Exception:
        return False


def get_content_type(filepath: str) -> str:
    """Get MIME type (content type) for a file.

    Uses Python's mimetypes library with custom mappings for special file types.
    Falls back to application/octet-stream for unknown binary files.
    """
    import mimetypes

    # Special handling for custom extensions
    filename_lower = os.path.basename(filepath).lower()
    filepath_lower = filepath.lower()

    # Custom file types that don't have standard MIME types
    if filepath_lower.endswith(".cdx"):
        return "application/x-codex-view"
    elif filepath_lower.endswith(".md"):
        return "text/markdown"
    elif filename_lower in ("dockerfile", "makefile", "gnumakefile"):
        return "text/x-makefile"
    elif filepath_lower.endswith(".dockerfile"):
        return "text/x-dockerfile"

    # Use mimetypes library for standard types
    mime_type, _ = mimetypes.guess_type(filepath)

    if mime_type:
        return mime_type

    # Fall back based on binary detection
    if is_binary_file(filepath):
        return "application/octet-stream"
    else:
        return "text/plain"


class NotebookFileHandler(FileSystemEventHandler):
    """Handler for file system events in a notebook."""

    def __init__(
        self,
        notebook_path: str,
        notebook_id: int,
        callback: Callable | None = None,
        queue: FileOperationQueue | None = None,
    ):
        self.notebook_path = notebook_path
        self.notebook_id = notebook_id
        self.callback = callback
        self.queue = queue
        # Cache for storing file hashes before delete (for move detection)
        self._hash_cache: dict[str, str] = {}
        super().__init__()

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [".codex", ".git", "__pycache__", ".DS_Store", "node_modules"]
        return any(pattern in path for pattern in ignore_patterns)

    def _get_cached_hash(self, filepath: str) -> str | None:
        """Get cached hash for a file (used for move detection on delete)."""
        return self._hash_cache.pop(filepath, None)

    def _cache_hash(self, filepath: str):
        """Cache a file's hash before it's deleted (for move detection)."""
        try:
            if os.path.exists(filepath) and not Path(filepath).is_dir():
                self._hash_cache[filepath] = calculate_file_hash(filepath)
        except Exception as e:
            logger.debug(f"Could not cache hash for {filepath}: {e}")

    def _update_file_metadata(self, filepath: str, event_type: str):
        """Update file metadata in database."""
        if self._should_ignore(filepath):
            return

        if Path(filepath).is_dir():
            return

        logger.debug(f"Updating metadata for {filepath} due to {event_type} event")
        session = None
        try:
            session = get_notebook_session(self.notebook_path)

            rel_path = os.path.relpath(filepath, self.notebook_path)
            filename = os.path.basename(filepath)

            # Check if file exists in database (and clean up duplicates if any)
            file_meta = deduplicate_file_metadata(session, self.notebook_id, rel_path)

            if event_type == "deleted":
                if file_meta:
                    session.delete(file_meta)
                    session.commit()
            else:
                filepath, sidecar = MetadataParser.resolve_sidecar(filepath)
                # File created or modified
                if os.path.exists(filepath):
                    file_stats = os.stat(filepath)
                    file_hash = calculate_file_hash(filepath)
                    is_binary = is_binary_file(filepath)

                    # Get content type (MIME type)
                    content_type = get_content_type(filepath)
                    metadata = MetadataParser.extract_all_metadata(filepath)

                    if file_meta:
                        # Update existing
                        file_meta.size = file_stats.st_size
                        file_meta.hash = file_hash
                        file_meta.content_type = content_type
                        from datetime import datetime

                        file_meta.updated_at = datetime.now(UTC)
                        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)
                        file_meta.properties = json.dumps(metadata)

                        if sidecar:
                            file_meta.sidecar_path = os.path.relpath(sidecar, self.notebook_path)

                        if "title" in metadata:
                            file_meta.title = metadata["title"]
                        if "description" in metadata:
                            file_meta.description = metadata["description"]
                        if "type" in metadata:
                            file_meta.file_type = metadata["type"]

                        if "created" in metadata:
                            from datetime import datetime

                            try:
                                created_dt = datetime.fromisoformat(metadata["created"])
                                file_meta.file_created_at = created_dt
                            except Exception:
                                pass

                    else:
                        # Create new
                        from datetime import datetime

                        file_meta = FileMetadata(
                            notebook_id=self.notebook_id,
                            path=rel_path,
                            filename=filename,
                            content_type=content_type,
                            size=file_stats.st_size,
                            hash=file_hash,
                            git_tracked=not is_binary,
                            properties=json.dumps(metadata),
                            sidecar_path=os.path.relpath(sidecar, self.notebook_path) if sidecar else None,
                            file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                            file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
                        )
                        if "title" in metadata:
                            file_meta.title = metadata["title"]
                        if "description" in metadata:
                            file_meta.description = metadata["description"]
                        if "type" in metadata:
                            file_meta.file_type = metadata["type"]

                        if "created" in metadata:
                            try:
                                created_dt = datetime.fromisoformat(metadata["created"])
                                file_meta.file_created_at = created_dt
                            except Exception:
                                pass
                        session.add(file_meta)

                    # Auto-commit to git if file should be tracked
                    # Skip git commits during scan - these are existing files
                    if event_type != "scanned":
                        from codex.core.git_manager import GitManager

                        git_manager = GitManager(self.notebook_path)

                        try:
                            commit_hash = git_manager.auto_commit_on_change(filepath, sidecar)
                            if commit_hash:
                                file_meta.last_commit_hash = commit_hash
                        except Exception as e:
                            logger.warning(f"Could not commit file to git: {e}")

                    try:
                        session.commit()
                    except Exception as commit_error:
                        # Handle race condition: another process created the record
                        session.rollback()
                        if "UNIQUE constraint failed" in str(commit_error):
                            # Re-query and update instead (deduplicate in case multiple were created)
                            file_meta = deduplicate_file_metadata(session, self.notebook_id, rel_path)
                            if file_meta:
                                file_meta.size = file_stats.st_size
                                file_meta.hash = file_hash
                                file_meta.content_type = content_type
                                from datetime import datetime

                                file_meta.updated_at = datetime.now(UTC)
                                file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)
                                session.commit()
                        else:
                            raise

            if self.callback:
                self.callback(filepath, event_type)

        except Exception as e:
            # Check if this is a database table missing error (e.g., during test cleanup)
            error_msg = str(e)
            if "no such table" in error_msg or "OperationalError" in str(type(e)):
                # Database or table has been removed (e.g., during test cleanup)
                # This is expected in some scenarios, so just log at debug level
                logger.debug(f"Database table not found for {filepath}, likely during cleanup: {e}")
            else:
                # Unexpected error - log at error level and re-raise so caller can handle it
                logger.error(f"Error updating metadata for {filepath}: {e}", exc_info=True)
                raise
        finally:
            if session:
                session.close()

    def on_created(self, event):
        """Called when a file or directory is created."""
        src_path = str(event.src_path)
        if self._should_ignore(src_path):
            return

        if event.is_directory:
            # When a directory is created, scan it for any files that may already exist
            # This handles cases like copying a folder with contents, or extracting an archive
            self._scan_new_directory(src_path)
        else:
            if self.queue:
                # Resolve sidecar for the operation
                filepath, sidecar = MetadataParser.resolve_sidecar(src_path)
                self.queue.enqueue(filepath, sidecar, "created")
            else:
                self._update_file_metadata(src_path, "created")

    def _scan_new_directory(self, dir_path: str):
        """Scan a newly created directory for files and index them."""
        logger.debug(f"Scanning newly created directory: {dir_path}")
        try:
            for root, dirs, files in os.walk(dir_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]

                for filename in files:
                    filepath = os.path.join(root, filename)
                    if self._should_ignore(filepath):
                        continue

                    if self.queue:
                        abs_filepath, abs_sidecar = MetadataParser.resolve_sidecar(filepath)
                        self.queue.enqueue(abs_filepath, abs_sidecar, "created")
                    else:
                        self._update_file_metadata(filepath, "created")
        except Exception as e:
            logger.error(f"Error scanning new directory {dir_path}: {e}", exc_info=True)

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if not event.is_directory:
            src_path = str(event.src_path)
            if self._should_ignore(src_path):
                return
            if self.queue:
                filepath, sidecar = MetadataParser.resolve_sidecar(src_path)
                self.queue.enqueue(filepath, sidecar, "modified")
            else:
                self._update_file_metadata(src_path, "modified")

    def on_deleted(self, event):
        """Called when a file or directory is deleted."""
        src_path = str(event.src_path)
        if self._should_ignore(src_path):
            return

        if event.is_directory:
            # When a directory is deleted, we need to delete all files within it
            # Since the directory no longer exists, we query the database for files with matching prefix
            self._delete_directory_files(src_path)
        else:
            if self.queue:
                # Get cached hash for move detection
                file_hash = self._get_cached_hash(src_path)
                self.queue.enqueue(src_path, None, "deleted", file_hash=file_hash)
            else:
                self._update_file_metadata(src_path, "deleted")

    def _delete_directory_files(self, dir_path: str):
        """Delete all files in a deleted directory from the database."""
        logger.debug(f"Handling deleted directory: {dir_path}")
        try:
            session = get_notebook_session(self.notebook_path)
            try:
                rel_dir = os.path.relpath(dir_path, self.notebook_path)
                prefix = f"{rel_dir}/"

                # Find all files that start with this directory path
                result = session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == self.notebook_id,
                        FileMetadata.path.startswith(prefix),
                    )
                )
                files_to_delete = result.scalars().all()

                for f in files_to_delete:
                    filepath = os.path.join(self.notebook_path, f.path)
                    if self.queue:
                        self.queue.enqueue(filepath, None, "deleted")
                    else:
                        session.delete(f)

                if not self.queue:
                    session.commit()

                logger.debug(f"Queued deletion of {len(files_to_delete)} files from deleted directory {dir_path}")
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error handling deleted directory {dir_path}: {e}", exc_info=True)

    def on_moved(self, event):
        """Called when a file or directory is moved."""
        src_path = str(event.src_path)
        dest_path = str(event.dest_path)

        src_ignored = self._should_ignore(src_path)
        dest_ignored = self._should_ignore(dest_path)

        # If both source and destination are ignored, skip entirely
        if src_ignored and dest_ignored:
            return

        if event.is_directory:
            # Directory move: delete files at old location, scan files at new location
            if not src_ignored:
                self._delete_directory_files(src_path)
            if not dest_ignored:
                self._scan_new_directory(dest_path)
        else:
            if self.queue:
                # For moves, we enqueue delete (with hash) and create
                # The queue will detect this as a move via hash matching
                try:
                    # Try to get hash from the destination (file already moved)
                    file_hash = calculate_file_hash(dest_path) if os.path.exists(dest_path) else None
                except Exception:
                    file_hash = None
                if not src_ignored:
                    self.queue.enqueue(src_path, None, "deleted", file_hash=file_hash)
                if not dest_ignored:
                    dest_filepath, dest_sidecar = MetadataParser.resolve_sidecar(dest_path)
                    self.queue.enqueue(dest_filepath, dest_sidecar, "created")
            else:
                if not src_ignored:
                    self._update_file_metadata(src_path, "deleted")
                if not dest_ignored:
                    self._update_file_metadata(dest_path, "created")


class NotebookWatcher:
    """Watcher for monitoring notebook filesystem changes."""

    def __init__(self, notebook_path: str, notebook_id: int, callback: Callable | None = None):
        self.notebook_path = notebook_path
        self.notebook_id = notebook_id
        self.callback = callback

        # Create the operation queue
        self.queue = FileOperationQueue(
            notebook_path=notebook_path,
            notebook_id=notebook_id,
            process_callback=self._process_file_operation,
        )

        # Create handler with queue reference
        self.handler = NotebookFileHandler(notebook_path, notebook_id, callback, queue=self.queue)

        self.observer = Observer()
        self._indexing_status = "not_started"  # not_started, in_progress, completed, error
        self._indexing_thread: threading.Thread | None = None

    def _process_file_operation(self, filepath: str, sidecar_path: str | None, operation: str):
        """Callback for processing file operations from the queue.

        This is called by the queue processor for each operation.
        """
        # Use the handler's _update_file_metadata method
        self.handler._update_file_metadata(filepath, operation)

    def enqueue_operation(
        self,
        filepath: str,
        sidecar_path: str | None = None,
        operation: str = "modified",
        comment: str | None = None,
        file_hash: str | None = None,
        wait: bool = False,
    ) -> FileOperation:
        """Enqueue a file operation for processing.

        This method is exposed for API routes to use when they need to
        notify the watcher about file changes they've made.

        Args:
            filepath: Absolute path to the file
            sidecar_path: Optional path to sidecar file
            operation: Type of operation ("created", "modified", "deleted", "scanned")
            comment: Optional commit message
            file_hash: Hash of file content (for move detection on deletes)
            wait: If True, block until the operation is processed

        Returns:
            The FileOperation object (check .error for failures if wait=True)
        """
        return self.queue.enqueue(
            filepath=filepath,
            sidecar_path=sidecar_path,
            operation=operation,
            comment=comment,
            file_hash=file_hash,
            wait=wait,
        )

    def start(self):
        """Start watching the notebook directory."""
        logger.info(f"Starting watcher for notebook at {self.notebook_path}")

        # Start the queue processor first
        self.queue.start()

        # Then start the filesystem observer
        self.observer.schedule(self.handler, self.notebook_path, recursive=True)
        self.observer.start()

        # Start indexing in a background thread
        self._start_background_indexing()

    def stop(self, queue_timeout: float = 30.0):
        """Stop watching the notebook directory.

        Args:
            queue_timeout: Maximum time to wait for queue to drain
        """
        # Stop the filesystem observer first (no new events)
        self.observer.stop()
        self.observer.join()

        # Stop the queue processor (drains remaining items)
        self.queue.stop(timeout=queue_timeout)

        # Wait for indexing thread to complete if it's still running
        if self._indexing_thread and self._indexing_thread.is_alive():
            logger.info(f"Waiting for background indexing to complete for {self.notebook_path}")
            self._indexing_thread.join(timeout=10)

    def _start_background_indexing(self):
        """Start the file scan in a background thread.

        Note: Uses daemon=True so the thread doesn't block server shutdown.
        This is acceptable because:
        1. Indexing is resumable - files are indexed incrementally
        2. File changes are captured by the watcher in real-time
        3. On next startup, any missed files will be indexed
        4. The stop() method attempts to wait for completion (10s timeout)
        """
        self._indexing_status = "in_progress"
        self._indexing_thread = threading.Thread(
            target=self._run_indexing, name=f"indexer-{self.notebook_id}", daemon=True
        )
        self._indexing_thread.start()
        logger.info(f"Started background indexing thread for notebook {self.notebook_id}")

    def _run_indexing(self):
        """Run the indexing scan in a background thread."""
        try:
            self.scan_existing_files()
            self._indexing_status = "completed"
            logger.info(f"Background indexing completed for notebook {self.notebook_id}")
        except Exception as e:
            self._indexing_status = "error"
            logger.error(f"Background indexing failed for notebook {self.notebook_id}: {e}", exc_info=True)

    def get_indexing_status(self) -> dict:
        """Get the current indexing status."""
        return {
            "notebook_id": self.notebook_id,
            "status": self._indexing_status,
            "is_alive": self._indexing_thread.is_alive() if self._indexing_thread else False,
        }

    def scan_existing_files(self):
        """Scan and index existing files in the notebook, skipping unchanged files."""
        from datetime import datetime

        notebook_session = get_notebook_session(self.notebook_path)

        try:
            # Get all existing file records from database
            result = notebook_session.execute(select(FileMetadata).where(FileMetadata.notebook_id == self.notebook_id))
            existing_files = {}
            sidecar_files = {}
            for f in result.scalars().all():
                existing_files[f.path] = f
                if f.sidecar_path:
                    sidecar_files[f.sidecar_path] = f

            # Track which paths we've seen on disk
            
            updated_count = 0

            files_to_process = set()

            seen_files = 0
            seen_sidecars = 0
            seen_paths = set()

            for root, dirs, files in os.walk(self.notebook_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if not self.handler._should_ignore(os.path.join(root, d))]

                for filename in files:
                    filepath = os.path.join(root, filename)
                    if self.handler._should_ignore(filepath):
                        continue

                    abs_filepath, abs_sidecar = MetadataParser.resolve_sidecar(filepath)

                    rel_path = os.path.relpath(abs_filepath, self.notebook_path)

                    is_sidecar = abs_sidecar and abs_sidecar == filepath 

                    seen_files += 1 if not is_sidecar else 0
                    seen_sidecars += 1 if is_sidecar else 0

                    existing = existing_files.get(rel_path) 
                    seen_paths.add(rel_path)

                    if abs_filepath in files_to_process:
                        continue

                    try:
                        file_stats = os.stat(filepath)
                        
                    except OSError:
                        # File may have been deleted between walk and stat
                        continue
                    
                    file_mtime = datetime.fromtimestamp(file_stats.st_mtime)
                    file_size = file_stats.st_size
                    
                    if existing and not is_sidecar:
                        # Compare size first (cheap check)
                        if existing.size != file_size or file_mtime > existing.updated_at:
                            files_to_process.add(abs_filepath)
                        # Compare modification time (allow 1 second tolerance for filesystem precision)
                        elif existing.file_modified_at:
                            if file_mtime > existing.file_modified_at:
                                files_to_process.add(abs_filepath)
                        elif existing.git_tracked and not existing.last_commit_hash:
                            files_to_process.add(abs_filepath)
                        else:
                            # No mtime recorded, need to update
                            files_to_process.add(abs_filepath)

                    elif is_sidecar and abs_sidecar:
                        sidecar = sidecar_files.get(os.path.relpath(abs_sidecar, self.notebook_path))
                        if sidecar:
                            if file_mtime > sidecar.updated_at:
                                files_to_process.add(abs_filepath)
                        else:
                            # Sidecar file not in database - update metadata
                            files_to_process.add(abs_filepath)
                    else:
                        # New file not in database
                        files_to_process.add(abs_filepath)

            logger.debug(f"Files to process after scan: {len(files_to_process)}")

            # Enqueue all file operations to the queue for batched processing
            for filepath in files_to_process:
                abs_filepath, abs_sidecar = MetadataParser.resolve_sidecar(filepath)
                self.queue.enqueue(abs_filepath, abs_sidecar, "scanned")
                updated_count += 1

            # Find deleted files (in database but not on disk)
            deleted_paths = set(existing_files.keys()) - seen_paths
            for rel_path in deleted_paths:
                filepath = os.path.join(self.notebook_path, rel_path)
                self.queue.enqueue(filepath, None, "deleted")

            # Log scan summary
            new_count = len(files_to_process - set(existing_files.keys()))
            deleted_count = len(deleted_paths)
            unchanged_count = len(set(existing_files.keys()) - files_to_process)
            logger.info(f"Scan complete: {seen_files} files ({seen_sidecars} sidecars) on disk, {len(existing_files)} in database")
            logger.info(
                f"  New: {new_count}, Updated: {updated_count}, Deleted: {deleted_count}, Unchanged: {unchanged_count}"
            )

        except Exception as e:
            logger.error(f"Error during file scan: {e}", exc_info=True)
        finally:
            notebook_session.close()

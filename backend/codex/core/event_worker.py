"""Event worker for processing file operation events.

This module provides the EventWorker class which processes events from the
file event queue. It handles:

1. Processing file create/update/move/delete operations
2. Batching git commits via GitBatcher
3. Updating metadata in the notebook database
4. Retry handling for transient errors
"""

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from codex.core.git_batcher import GitBatcher
from codex.core.metadata import MetadataParser
from codex.core.watcher import calculate_file_hash, get_content_type, is_binary_file
from codex.db.database import get_notebook_session, get_system_session_sync
from codex.db.models import FileEvent, FileEventStatus, FileEventType, FileMetadata, Notebook, Workspace

logger = logging.getLogger(__name__)


class EventWorker:
    """Processes file events from the queue for a specific notebook."""

    def __init__(
        self,
        notebook_id: int,
        notebook_path: str,
        git_batcher: GitBatcher,
        poll_interval: float = 0.1,
        batch_size: int = 50,
        max_retries: int = 3,
    ):
        """Initialize the event worker.

        Args:
            notebook_id: ID of the notebook to process events for
            notebook_path: Filesystem path to the notebook
            git_batcher: Shared GitBatcher instance for batching commits
            poll_interval: Seconds between polling for new events
            batch_size: Maximum events to process per batch
            max_retries: Maximum retry attempts for failed events
        """
        self.notebook_id = notebook_id
        self.notebook_path = Path(notebook_path)
        self.git_batcher = git_batcher
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.max_retries = max_retries

        self._running = False
        self._thread: threading.Thread | None = None
        self._processed_count = 0
        self._error_count = 0

    def start(self) -> None:
        """Start the worker thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name=f"event-worker-{self.notebook_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"Started event worker for notebook {self.notebook_id}")

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the worker thread.

        Args:
            timeout: Seconds to wait for thread to finish
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(f"Event worker for notebook {self.notebook_id} did not stop in time")
        logger.info(f"Stopped event worker for notebook {self.notebook_id}")

    def _run(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                # Process pending events
                events = self._fetch_pending_events()
                for event in events:
                    if not self._running:
                        break
                    self._process_event(event)

                # Check if it's time for a git commit
                if self.git_batcher.should_commit(self.notebook_id):
                    self.git_batcher.commit(self.notebook_id)

                # Sleep briefly if no events
                if not events:
                    time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Worker error for notebook {self.notebook_id}: {e}", exc_info=True)
                time.sleep(1.0)  # Back off on error

    def _fetch_pending_events(self) -> list[FileEvent]:
        """Fetch pending events from the queue.

        Returns:
            List of pending FileEvent instances
        """
        session = get_system_session_sync()
        try:
            result = session.execute(
                select(FileEvent)
                .where(
                    FileEvent.notebook_id == self.notebook_id,
                    FileEvent.status == FileEventStatus.PENDING.value,
                )
                .order_by(FileEvent.correlation_id, FileEvent.sequence, FileEvent.created_at)
                .limit(self.batch_size)
            )
            events = list(result.scalars().all())

            # Mark as processing
            for event in events:
                event.status = FileEventStatus.PROCESSING.value
            session.commit()

            return events
        finally:
            session.close()

    def _process_event(self, event: FileEvent) -> None:
        """Process a single event.

        Args:
            event: The FileEvent to process
        """
        try:
            operation = json.loads(event.operation)
            event_type = FileEventType(event.event_type)

            logger.debug(f"Processing {event_type.value} event {event.id} for notebook {self.notebook_id}")

            match event_type:
                case FileEventType.CREATE:
                    self._handle_create(operation)
                case FileEventType.UPDATE:
                    self._handle_update(operation)
                case FileEventType.MOVE:
                    self._handle_move(operation)
                case FileEventType.DELETE:
                    self._handle_delete(operation)
                case FileEventType.SYNC:
                    self._handle_sync(operation)

            # Mark completed
            self._mark_completed(event)
            self._processed_count += 1

        except Exception as e:
            self._handle_event_error(event, e)

    def _handle_create(self, operation: dict) -> None:
        """Handle file creation.

        Args:
            operation: Operation details with path, content, and optional metadata
        """
        path = operation["path"]
        content = operation.get("content", "")
        metadata = operation.get("metadata", {})
        is_binary = operation.get("is_binary", False)

        full_path = self.notebook_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        if is_binary:
            # Content is base64 encoded for binary files
            import base64
            binary_content = base64.b64decode(content)
            full_path.write_bytes(binary_content)
        else:
            full_path.write_text(content)

        # Create/update metadata record
        self._update_file_metadata(path, metadata)

        # Add to git batch
        self.git_batcher.add_path(self.notebook_id, str(self.notebook_path), path)

    def _handle_update(self, operation: dict) -> None:
        """Handle file update.

        Args:
            operation: Operation details with path, content, and optional metadata
        """
        path = operation["path"]
        content = operation.get("content")
        metadata = operation.get("metadata", {})
        is_binary = operation.get("is_binary", False)

        full_path = self.notebook_path / path

        # Update content if provided
        if content is not None:
            if is_binary:
                import base64
                binary_content = base64.b64decode(content)
                full_path.write_bytes(binary_content)
            else:
                full_path.write_text(content)

        # Update metadata record
        self._update_file_metadata(path, metadata)

        # Add to git batch
        self.git_batcher.add_path(self.notebook_id, str(self.notebook_path), path)

    def _handle_move(self, operation: dict) -> None:
        """Handle file/folder move.

        Args:
            operation: Operation details with source_path and dest_path
        """
        source_path = operation["source_path"]
        dest_path = operation["dest_path"]

        source_full = self.notebook_path / source_path
        dest_full = self.notebook_path / dest_path

        # Create destination directory
        dest_full.parent.mkdir(parents=True, exist_ok=True)

        # Move file/folder
        shutil.move(str(source_full), str(dest_full))

        # Update metadata
        nb_session = get_notebook_session(str(self.notebook_path))
        try:
            if dest_full.is_dir():
                # Update all files with matching path prefix
                result = nb_session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == self.notebook_id,
                        FileMetadata.path.startswith(source_path + "/"),
                    )
                )
                files = result.scalars().all()

                for f in files:
                    old_path = f.path
                    f.path = f.path.replace(source_path, dest_path, 1)
                    f.filename = os.path.basename(f.path)
                    self.git_batcher.add_deleted_path(self.notebook_id, str(self.notebook_path), old_path)
                    self.git_batcher.add_path(self.notebook_id, str(self.notebook_path), f.path)
            else:
                result = nb_session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == self.notebook_id,
                        FileMetadata.path == source_path,
                    )
                )
                file_meta = result.scalar_one_or_none()

                if file_meta:
                    file_meta.path = dest_path
                    file_meta.filename = os.path.basename(dest_path)

                # Add to git batch
                self.git_batcher.add_deleted_path(self.notebook_id, str(self.notebook_path), source_path)
                self.git_batcher.add_path(self.notebook_id, str(self.notebook_path), dest_path)

            nb_session.commit()
        finally:
            nb_session.close()

    def _handle_delete(self, operation: dict) -> None:
        """Handle file/folder deletion.

        Args:
            operation: Operation details with path and optional is_directory flag
        """
        path = operation["path"]
        is_directory = operation.get("is_directory", False)

        full_path = self.notebook_path / path

        # Delete from filesystem
        if full_path.exists():
            if is_directory or full_path.is_dir():
                shutil.rmtree(str(full_path))
            else:
                full_path.unlink()

        # Delete metadata
        nb_session = get_notebook_session(str(self.notebook_path))
        try:
            if is_directory:
                # Delete all files with matching path prefix
                result = nb_session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == self.notebook_id,
                        FileMetadata.path.startswith(path + "/"),
                    )
                )
                files = result.scalars().all()
                for f in files:
                    nb_session.delete(f)
                    self.git_batcher.add_deleted_path(self.notebook_id, str(self.notebook_path), f.path)
            else:
                result = nb_session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == self.notebook_id,
                        FileMetadata.path == path,
                    )
                )
                file_meta = result.scalar_one_or_none()
                if file_meta:
                    nb_session.delete(file_meta)

            nb_session.commit()
        finally:
            nb_session.close()

        # Add to git batch
        self.git_batcher.add_deleted_path(self.notebook_id, str(self.notebook_path), path)

    def _handle_sync(self, operation: dict) -> None:
        """Handle sync event from watcher.

        Args:
            operation: Operation details with path and event type
        """
        path = operation["path"]
        event = operation.get("event", "modified")

        full_path = self.notebook_path / path

        if event == "deleted":
            # File was deleted externally
            nb_session = get_notebook_session(str(self.notebook_path))
            try:
                result = nb_session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == self.notebook_id,
                        FileMetadata.path == path,
                    )
                )
                file_meta = result.scalar_one_or_none()
                if file_meta:
                    nb_session.delete(file_meta)
                    nb_session.commit()
            finally:
                nb_session.close()
        else:
            # File was created or modified externally
            if full_path.exists() and not full_path.is_dir():
                self._update_file_metadata(path, {})
                self.git_batcher.add_path(self.notebook_id, str(self.notebook_path), path)

    def _update_file_metadata(self, path: str, extra_metadata: dict) -> FileMetadata:
        """Update or create file metadata in the notebook database.

        Args:
            path: Relative path of the file
            extra_metadata: Additional metadata to set

        Returns:
            The updated or created FileMetadata instance
        """
        full_path = self.notebook_path / path
        filename = os.path.basename(path)

        nb_session = get_notebook_session(str(self.notebook_path))
        try:
            # Check if file exists in database
            result = nb_session.execute(
                select(FileMetadata).where(
                    FileMetadata.notebook_id == self.notebook_id,
                    FileMetadata.path == path,
                )
            )
            file_meta = result.scalar_one_or_none()

            # Get file stats and metadata
            file_stats = full_path.stat()
            file_hash = calculate_file_hash(str(full_path))
            content_type = get_content_type(str(full_path))
            is_binary = is_binary_file(str(full_path))

            # Parse metadata from frontmatter/sidecar
            filepath, sidecar = MetadataParser.resolve_sidecar(str(full_path))
            parsed_metadata = MetadataParser.extract_all_metadata(str(full_path))

            # Merge with extra metadata
            metadata = {**parsed_metadata, **extra_metadata}

            if file_meta:
                # Update existing
                file_meta.size = file_stats.st_size
                file_meta.hash = file_hash
                file_meta.content_type = content_type
                file_meta.updated_at = datetime.now(UTC)
                file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)
                file_meta.properties = json.dumps(metadata)

                if sidecar:
                    file_meta.sidecar_path = os.path.relpath(sidecar, str(self.notebook_path))

                if "title" in metadata:
                    file_meta.title = metadata["title"]
                if "description" in metadata:
                    file_meta.description = metadata["description"]
                if "type" in metadata:
                    file_meta.file_type = metadata["type"]
            else:
                # Create new
                file_meta = FileMetadata(
                    notebook_id=self.notebook_id,
                    path=path,
                    filename=filename,
                    content_type=content_type,
                    size=file_stats.st_size,
                    hash=file_hash,
                    git_tracked=not is_binary,
                    properties=json.dumps(metadata),
                    sidecar_path=os.path.relpath(sidecar, str(self.notebook_path)) if sidecar else None,
                    file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                    file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
                )

                if "title" in metadata:
                    file_meta.title = metadata["title"]
                if "description" in metadata:
                    file_meta.description = metadata["description"]
                if "type" in metadata:
                    file_meta.file_type = metadata["type"]

                nb_session.add(file_meta)

            nb_session.commit()
            nb_session.refresh(file_meta)
            return file_meta
        finally:
            nb_session.close()

    def _mark_completed(self, event: FileEvent) -> None:
        """Mark an event as completed.

        Args:
            event: The event to mark as completed
        """
        session = get_system_session_sync()
        try:
            db_event = session.get(FileEvent, event.id)
            if db_event:
                db_event.status = FileEventStatus.COMPLETED.value
                db_event.processed_at = datetime.now(UTC)
                session.commit()
        finally:
            session.close()

    def _handle_event_error(self, event: FileEvent, error: Exception) -> None:
        """Handle an error processing an event.

        Args:
            event: The event that failed
            error: The exception that occurred
        """
        self._error_count += 1
        logger.error(f"Error processing event {event.id}: {error}", exc_info=True)

        session = get_system_session_sync()
        try:
            db_event = session.get(FileEvent, event.id)
            if db_event:
                db_event.retry_count += 1
                db_event.error_message = str(error)

                if db_event.retry_count >= self.max_retries:
                    db_event.status = FileEventStatus.FAILED.value
                    db_event.processed_at = datetime.now(UTC)
                    logger.error(f"Event {event.id} failed permanently after {self.max_retries} retries")
                else:
                    db_event.status = FileEventStatus.PENDING.value  # Will be retried
                    logger.warning(f"Event {event.id} failed, will retry ({db_event.retry_count}/{self.max_retries})")

                session.commit()
        finally:
            session.close()

    def get_stats(self) -> dict:
        """Get statistics about this worker.

        Returns:
            Dictionary with worker statistics
        """
        return {
            "notebook_id": self.notebook_id,
            "running": self._running,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
        }


class EventWorkerManager:
    """Manages event workers for all notebooks."""

    def __init__(
        self,
        git_batch_interval: float = 5.0,
        poll_interval: float = 0.1,
    ):
        """Initialize the worker manager.

        Args:
            git_batch_interval: Seconds between git commits
            poll_interval: Seconds between polling for events
        """
        self.git_batcher = GitBatcher(interval=git_batch_interval)
        self.poll_interval = poll_interval
        self._workers: dict[int, EventWorker] = {}
        self._lock = threading.Lock()

    def start_worker(self, notebook_id: int, notebook_path: str) -> EventWorker:
        """Start a worker for a notebook.

        Args:
            notebook_id: ID of the notebook
            notebook_path: Filesystem path to the notebook

        Returns:
            The started EventWorker instance
        """
        with self._lock:
            if notebook_id in self._workers:
                return self._workers[notebook_id]

            worker = EventWorker(
                notebook_id=notebook_id,
                notebook_path=notebook_path,
                git_batcher=self.git_batcher,
                poll_interval=self.poll_interval,
            )
            worker.start()
            self._workers[notebook_id] = worker
            return worker

    def stop_worker(self, notebook_id: int, timeout: float = 10.0) -> None:
        """Stop a worker for a notebook.

        Args:
            notebook_id: ID of the notebook
            timeout: Seconds to wait for worker to stop
        """
        with self._lock:
            worker = self._workers.pop(notebook_id, None)
            if worker:
                worker.stop(timeout=timeout)

    def stop_all(self, timeout: float = 10.0) -> None:
        """Stop all workers.

        Args:
            timeout: Seconds to wait for each worker to stop
        """
        # First, commit all pending git changes
        self.git_batcher.commit_all()

        # Then stop all workers
        with self._lock:
            for worker in self._workers.values():
                worker.stop(timeout=timeout)
            self._workers.clear()

    def get_worker(self, notebook_id: int) -> EventWorker | None:
        """Get the worker for a notebook.

        Args:
            notebook_id: ID of the notebook

        Returns:
            The EventWorker if running, None otherwise
        """
        with self._lock:
            return self._workers.get(notebook_id)

    def get_all_stats(self) -> dict:
        """Get statistics for all workers.

        Returns:
            Dictionary with stats for all workers
        """
        with self._lock:
            return {
                "workers": {nb_id: w.get_stats() for nb_id, w in self._workers.items()},
                "git_batcher": self.git_batcher.get_stats(),
            }

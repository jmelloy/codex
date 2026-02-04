"""Event queue worker for processing file system operations.

This module provides an event queue worker that batches and processes file system
events every 5 seconds. This helps reduce race conditions and timing issues around
file moves and deletes by providing proper isolation and sequencing of operations.

Batching Strategy:
- Move/Delete operations are queued to prevent race conditions with the file watcher
- Create operations remain synchronous because they need to return file IDs immediately
- Git commits are batched per processing cycle for efficiency
"""

import logging
import os
import shutil
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import select

from codex.core.git_manager import GitManager
from codex.core.metadata import MetadataParser
from codex.db.database import get_notebook_session
from codex.db.models import FileMetadata, FileSystemEvent

logger = logging.getLogger(__name__)


class EventQueueWorker:
    """Worker that processes file system events in batches."""

    def __init__(self, notebook_path: str, notebook_id: int, batch_interval: float = 5.0):
        """Initialize the event queue worker.
        
        Args:
            notebook_path: Path to the notebook directory
            notebook_id: ID of the notebook
            batch_interval: Seconds between batch processing (default: 5.0)
        """
        self.notebook_path = notebook_path
        self.notebook_id = notebook_id
        self.batch_interval = batch_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self):
        """Start the worker thread."""
        if self._running:
            logger.warning(f"Queue worker already running for notebook {self.notebook_id}")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._process_loop,
            name=f"queue-worker-{self.notebook_id}",
            daemon=True
        )
        self._thread.start()
        logger.info(f"Started queue worker for notebook {self.notebook_id} at {self.notebook_path}")

    def stop(self, timeout: float = 10.0):
        """Stop the worker thread.
        
        Args:
            timeout: Maximum time to wait for worker to finish (seconds)
        """
        if not self._running:
            return
        
        logger.info(f"Stopping queue worker for notebook {self.notebook_id}")
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(f"Queue worker for notebook {self.notebook_id} did not stop within timeout")

    def _process_loop(self):
        """Main processing loop that runs in a separate thread."""
        logger.info(f"Queue worker loop started for notebook {self.notebook_id}")
        
        while self._running:
            try:
                self._process_batch()
            except Exception as e:
                logger.error(f"Error processing batch for notebook {self.notebook_id}: {e}", exc_info=True)
            
            # Sleep for the batch interval
            time.sleep(self.batch_interval)
        
        # Process any remaining events before exiting
        try:
            self._process_batch()
        except Exception as e:
            logger.error(f"Error processing final batch for notebook {self.notebook_id}: {e}", exc_info=True)
        
        logger.info(f"Queue worker loop stopped for notebook {self.notebook_id}")

    def _process_batch(self):
        """Process a batch of pending events.

        Events are processed sequentially, then all git changes are committed
        together at the end of the batch for efficiency.
        """
        session = None
        try:
            session = get_notebook_session(self.notebook_path)

            # Get pending events ordered by creation time
            result = session.execute(
                select(FileSystemEvent)
                .where(
                    FileSystemEvent.notebook_id == self.notebook_id,
                    FileSystemEvent.status == "pending"
                )
                .order_by(FileSystemEvent.created_at)
            )
            events = result.scalars().all()

            if not events:
                return

            logger.info(f"Processing batch of {len(events)} events for notebook {self.notebook_id}")

            # Track files changed for batched git commit
            git_changes: list[tuple[str, str]] = []  # (action, path)

            # Process events with proper locking
            with self._lock:
                for event in events:
                    changes = self._process_event(event, session)
                    if changes:
                        git_changes.extend(changes)

            session.commit()

            # Batch git commit for all changes
            if git_changes:
                self._commit_batch(git_changes)

        except Exception as e:
            logger.error(f"Error in batch processing: {e}", exc_info=True)
            if session:
                session.rollback()
        finally:
            if session:
                session.close()

    def _commit_batch(self, changes: list[tuple[str, str]]):
        """Commit all changes from a batch in a single git commit.

        Args:
            changes: List of (action, path) tuples describing what changed
        """
        if not changes:
            return

        try:
            git_manager = GitManager(self.notebook_path)

            # Build commit message summarizing all changes
            if len(changes) == 1:
                action, path = changes[0]
                message = f"{action.capitalize()} {os.path.basename(path)}"
            else:
                # Group by action type
                actions = {}
                for action, path in changes:
                    actions.setdefault(action, []).append(os.path.basename(path))

                parts = []
                for action, files in actions.items():
                    if len(files) == 1:
                        parts.append(f"{action} {files[0]}")
                    else:
                        parts.append(f"{action} {len(files)} files")
                message = "Batch: " + ", ".join(parts)

            # Stage all changes and commit (commit without files uses git add -A)
            git_manager.commit(message)
            logger.debug(f"Committed batch: {message}")

        except Exception as e:
            logger.warning(f"Failed to commit batch to git: {e}")

    def _process_event(self, event: FileSystemEvent, session) -> list[tuple[str, str]] | None:
        """Process a single file system event.

        Args:
            event: The event to process
            session: Database session

        Returns:
            List of (action, path) tuples for git commit, or None if failed
        """
        try:
            logger.debug(f"Processing {event.event_type} event for {event.file_path}")

            # Mark event as processing
            event.status = "processing"
            session.commit()

            # Process based on event type
            git_changes: list[tuple[str, str]] = []

            if event.event_type == "move":
                git_changes = self._handle_move(event, session)
            elif event.event_type == "delete":
                git_changes = self._handle_delete(event, session)
            elif event.event_type == "create":
                self._handle_create(event, session)
            elif event.event_type == "modify":
                self._handle_modify(event, session)
            else:
                raise ValueError(f"Unknown event type: {event.event_type}")

            # Mark event as completed
            event.status = "completed"
            event.processed_at = datetime.now(UTC)

            return git_changes

        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}", exc_info=True)
            event.status = "failed"
            event.error_message = str(e)
            event.processed_at = datetime.now(UTC)
            return None

    def _handle_move(self, event: FileSystemEvent, session) -> list[tuple[str, str]]:
        """Handle a move/rename operation.

        Returns:
            List of (action, path) tuples for git commit
        """
        if not event.new_path:
            raise ValueError("Move event requires new_path")

        old_path = Path(self.notebook_path) / event.file_path
        new_path = Path(self.notebook_path) / event.new_path

        # Check if source exists
        if not old_path.exists():
            logger.warning(f"Source file does not exist for move: {old_path}")
            return []

        # Check if target already exists
        if new_path.exists():
            raise FileExistsError(f"Target path already exists: {new_path}")

        # Create parent directories if needed
        new_path.parent.mkdir(parents=True, exist_ok=True)

        # Move the file on disk
        shutil.move(str(old_path), str(new_path))
        logger.debug(f"Moved file from {event.file_path} to {event.new_path}")

        # Update database metadata
        result = session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == self.notebook_id,
                FileMetadata.path == event.file_path
            )
        )
        file_meta = result.scalar_one_or_none()

        if file_meta:
            file_meta.path = event.new_path
            file_meta.filename = os.path.basename(event.new_path)
            file_meta.updated_at = datetime.now(UTC)

            # Handle sidecar file if it exists
            if file_meta.sidecar_path:
                old_sidecar = Path(self.notebook_path) / file_meta.sidecar_path
                if old_sidecar.exists():
                    new_sidecar = new_path.parent / Path(file_meta.sidecar_path).name
                    shutil.move(str(old_sidecar), str(new_sidecar))
                    file_meta.sidecar_path = os.path.relpath(new_sidecar, self.notebook_path)

        return [("move", event.new_path)]

    def _handle_delete(self, event: FileSystemEvent, session) -> list[tuple[str, str]]:
        """Handle a delete operation.

        Returns:
            List of (action, path) tuples for git commit
        """
        file_path = Path(self.notebook_path) / event.file_path

        # Delete the file from disk if it exists
        if file_path.exists():
            if file_path.is_file():
                os.remove(file_path)
                logger.debug(f"Deleted file: {event.file_path}")
            elif file_path.is_dir():
                shutil.rmtree(file_path)
                logger.debug(f"Deleted directory: {event.file_path}")
        else:
            logger.warning(f"File does not exist for delete: {file_path}")

        # Delete sidecar file if it exists
        _, sidecar = MetadataParser.resolve_sidecar(str(file_path))
        if sidecar and Path(sidecar).exists():
            os.remove(sidecar)
            logger.debug(f"Deleted sidecar file: {sidecar}")

        # Delete from database
        result = session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == self.notebook_id,
                FileMetadata.path == event.file_path
            )
        )
        file_meta = result.scalar_one_or_none()

        if file_meta:
            session.delete(file_meta)

        return [("delete", event.file_path)]

    def _handle_create(self, event: FileSystemEvent, session):
        """Handle a create operation."""
        # Parse metadata from event
        metadata = {}
        if event.event_metadata:
            try:
                metadata = json.loads(event.event_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse event metadata: {event.event_metadata}")
        
        # The file should already exist on disk (created by the API endpoint)
        # This handler just ensures the database is updated
        file_path = Path(self.notebook_path) / event.file_path
        
        if not file_path.exists():
            logger.warning(f"File does not exist for create event: {file_path}")
            return
        
        # Import the watcher's update method to reuse logic
        from codex.core.watcher import NotebookFileHandler
        handler = NotebookFileHandler(self.notebook_path, self.notebook_id)
        handler._update_file_metadata(str(file_path), "created")

    def _handle_modify(self, event: FileSystemEvent, session):
        """Handle a modify operation."""
        # Similar to create, ensure the file is indexed
        file_path = Path(self.notebook_path) / event.file_path
        
        if not file_path.exists():
            logger.warning(f"File does not exist for modify event: {file_path}")
            return
        
        # Import the watcher's update method to reuse logic
        from codex.core.watcher import NotebookFileHandler
        handler = NotebookFileHandler(self.notebook_path, self.notebook_id)
        handler._update_file_metadata(str(file_path), "modified")

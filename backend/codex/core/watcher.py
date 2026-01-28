"""File system watcher for monitoring changes."""

import hashlib
import json
import logging
import os
import threading
from collections.abc import Callable
from datetime import UTC
from pathlib import Path

from sqlmodel import select
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from codex.core.metadata import MetadataParser
from codex.db.database import get_notebook_session
from codex.db.models import FileMetadata

logger = logging.getLogger(__name__)


def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


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

    def __init__(self, notebook_path: str, notebook_id: int, callback: Callable | None = None):
        self.notebook_path = notebook_path
        self.notebook_id = notebook_id
        self.callback = callback
        super().__init__()

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        ignore_patterns = [".codex", ".git", "__pycache__", ".DS_Store", "node_modules"]
        return any(pattern in path for pattern in ignore_patterns)

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

            # Check if file exists in database
            result = session.execute(
                select(FileMetadata).where(FileMetadata.notebook_id == self.notebook_id, FileMetadata.path == rel_path)
            )
            file_meta = result.scalar_one_or_none()

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
                            # Re-query and update instead
                            result = session.execute(
                                select(FileMetadata).where(
                                    FileMetadata.notebook_id == self.notebook_id, FileMetadata.path == rel_path
                                )
                            )
                            file_meta = result.scalar_one_or_none()
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
            logger.error(f"Error updating metadata for {filepath}: {e}", exc_info=True)
        finally:
            if session:
                session.close()

    def on_created(self, event):
        """Called when a file or directory is created."""
        if not event.is_directory:
            src_path = str(event.src_path)
            self._update_file_metadata(src_path, "created")

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if not event.is_directory:
            src_path = str(event.src_path)
            self._update_file_metadata(src_path, "modified")

    def on_deleted(self, event):
        """Called when a file or directory is deleted."""
        if not event.is_directory:
            src_path = str(event.src_path)
            self._update_file_metadata(src_path, "deleted")

    def on_moved(self, event):
        """Called when a file or directory is moved."""
        if not event.is_directory:
            dest_path = str(event.dest_path)
            src_path = str(event.src_path)
            self._update_file_metadata(src_path, "deleted")
            self._update_file_metadata(dest_path, "created")


class NotebookWatcher:
    """Watcher for monitoring notebook filesystem changes."""

    def __init__(self, notebook_path: str, notebook_id: int, callback: Callable | None = None):
        self.notebook_path = notebook_path
        self.notebook_id = notebook_id
        self.callback = callback
        self.observer = Observer()
        self.handler = NotebookFileHandler(notebook_path, notebook_id, callback)
        self._indexing_status = "not_started"  # not_started, in_progress, completed, error
        self._indexing_thread: threading.Thread | None = None

    def start(self):
        """Start watching the notebook directory."""
        logger.info(f"Starting watcher for notebook at {self.notebook_path}")
        self.observer.schedule(self.handler, self.notebook_path, recursive=True)
        self.observer.start()

        # Start indexing in a background thread
        self._start_background_indexing()

    def stop(self):
        """Stop watching the notebook directory."""
        self.observer.stop()
        self.observer.join()

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
                        file_mtime = datetime.fromtimestamp(file_stats.st_mtime)
                        file_size = file_stats.st_size
                    except OSError:
                        # File may have been deleted between walk and stat
                        continue

                    if existing and not is_sidecar:
                        # Compare size first (cheap check)
                        if existing.size != file_size:
                            files_to_process.add(abs_filepath)
                        # Compare modification time (allow 1 second tolerance for filesystem precision)
                        elif existing.file_modified_at:
                            if file_mtime > existing.updated_at or file_mtime > existing.file_modified_at:
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

            for filepath in files_to_process:
                self.handler._update_file_metadata(filepath, "scanned")
                updated_count += 1

            # Find deleted files (in database but not on disk)
            deleted_paths = set(existing_files.keys()) - seen_paths
            for rel_path in deleted_paths:
                filepath = os.path.join(self.notebook_path, rel_path)
                self.handler._update_file_metadata(filepath, "deleted")

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

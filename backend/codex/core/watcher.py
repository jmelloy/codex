"""File system watcher for monitoring changes."""

import json
import os
import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Optional, Callable
import logging
from codex.core.metadata import MetadataParser
from codex.db.database import get_notebook_session
from codex.db.models import FileMetadata, Notebook
from sqlmodel import select

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

    def __init__(self, notebook_path: str, notebook_id: int, callback: Optional[Callable] = None):
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
                        from datetime import datetime, timezone

                        file_meta.updated_at = datetime.now(timezone.utc)
                        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)
                        file_meta.properties = json.dumps(metadata)

                        if sidecar:
                            file_meta.sidecar_path = sidecar
                        
                        if "title" in metadata:
                            file_meta.title = metadata["title"]
                        if "description" in metadata:
                            file_meta.description = metadata["description"]

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
                            sidecar_path=sidecar,
                            file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                            file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
                        )
                        if "title" in metadata:
                            file_meta.title = metadata["title"]
                        if "description" in metadata:
                            file_meta.description = metadata["description"]
                        
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
                                select(FileMetadata).where(FileMetadata.notebook_id == self.notebook_id, FileMetadata.path == rel_path)
                            )
                            file_meta = result.scalar_one_or_none()
                            if file_meta:
                                file_meta.size = file_stats.st_size
                                file_meta.hash = file_hash
                                file_meta.content_type = content_type
                                from datetime import datetime, timezone

                                file_meta.updated_at = datetime.now(timezone.utc)
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

    def __init__(self, notebook_path: str, notebook_id: int, callback: Optional[Callable] = None):
        self.notebook_path = notebook_path
        self.notebook_id = notebook_id
        self.callback = callback
        self.observer = Observer()
        self.handler = NotebookFileHandler(notebook_path, notebook_id, callback)

    def start(self):
        """Start watching the notebook directory."""
        logger.info(f"Starting watcher for notebook at {self.notebook_path}")
        self.observer.schedule(self.handler, self.notebook_path, recursive=True)
        self.observer.start()

        self.scan_existing_files()

    def stop(self):
        """Stop watching the notebook directory."""
        self.observer.stop()
        self.observer.join()

    def scan_existing_files(self):
        """Scan and index existing files in the notebook, skipping unchanged files."""
        from datetime import datetime

        session = get_notebook_session(self.notebook_path)

        try:
            # Get all existing file records from database
            result = session.execute(select(FileMetadata).where(FileMetadata.notebook_id == self.notebook_id))
            existing_files = {}
            sidecar_files = {}
            for f in result.scalars().all():
                logger.debug(f"Existing file in DB: {f.path}")
                existing_files[f.path] = f
                if f.sidecar_path:
                    sidecar_files[f.sidecar_path] = f

            # Track which paths we've seen on disk
            seen_paths = set()
            updated_count = 0

            files_to_process = set()

            for root, dirs, files in os.walk(self.notebook_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if not self.handler._should_ignore(os.path.join(root, d))]

                for filename in files:
                    filepath = os.path.join(root, filename)
                    if self.handler._should_ignore(filepath):
                        continue

                    rel_path = os.path.relpath(filepath, self.notebook_path)
                    seen_paths.add(rel_path)

                    try:
                        file_stats = os.stat(filepath)
                    except OSError:
                        # File may have been deleted between walk and stat
                        continue

                    file_mtime = datetime.fromtimestamp(file_stats.st_mtime)
                    file_size = file_stats.st_size

                    if existing := existing_files.get(rel_path):
                        # Compare size first (cheap check)
                        if existing.size != file_size:
                            files_to_process.add(filepath)
                        # Compare modification time (allow 1 second tolerance for filesystem precision)
                        elif existing.file_modified_at:
                            time_diff = abs((file_mtime - existing.file_modified_at).total_seconds())
                            if time_diff > 1:
                                files_to_process.add(filepath)
                        else:
                            # No mtime recorded, need to update
                            files_to_process.add(filepath)

                    elif filepath in sidecar_files:
                        time_diff = abs((file_mtime - sidecar_files[filepath].file_modified_at).total_seconds())
                        if time_diff > 1:
                            # Sidecar file exists in database - update metadata
                            files_to_process.add(sidecar_files[filepath].path)
                    else:
                        # New file not in database
                        files_to_process.add(filepath)

            for filepath in files_to_process:
                self.handler._update_file_metadata(filepath, "scanned")
                updated_count += 1

            # Find deleted files (in database but not on disk)
            deleted_paths = set(existing_files.keys()) - seen_paths
            for rel_path in deleted_paths:
                filepath = os.path.join(self.notebook_path, rel_path)
                self.handler._update_file_metadata(filepath, "deleted")

            # Log scan summary
            new_count = len(seen_paths - set(existing_files.keys()))
            deleted_count = len(deleted_paths)
            unchanged_count = len(seen_paths) - new_count - updated_count
            logger.info(f"Scan complete: {len(seen_paths)} files on disk, {len(existing_files)} in database")
            logger.info(
                f"  New: {new_count}, Updated: {updated_count}, Deleted: {deleted_count}, Unchanged: {unchanged_count}"
            )

        except Exception as e:
            logger.error(f"Error during file scan: {e}", exc_info=True)
        finally:
            session.close()

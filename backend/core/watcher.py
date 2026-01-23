"""File system watcher for monitoring changes."""

import os
import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Optional, Callable
from backend.db.database import get_notebook_session
from backend.db.models import FileMetadata, Notebook
from sqlmodel import select


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

        print(f"Updating metadata for {filepath} due to {event_type} event")
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
                # File created or modified
                if os.path.exists(filepath):
                    file_stats = os.stat(filepath)
                    file_hash = calculate_file_hash(filepath)
                    is_binary = is_binary_file(filepath)

                    file_type = "binary" if is_binary else "text"
                    if filepath.endswith(".md"):
                        file_type = "markdown"
                    elif filepath.endswith(".json"):
                        file_type = "json"
                    elif filepath.endswith(".xml"):
                        file_type = "xml"

                    if file_meta:
                        # Update existing
                        file_meta.size = file_stats.st_size
                        file_meta.hash = file_hash
                        file_meta.file_type = file_type
                        from datetime import datetime, timezone

                        file_meta.updated_at = datetime.now(timezone.utc)
                        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)
                    else:
                        # Create new
                        from datetime import datetime

                        file_meta = FileMetadata(
                            notebook_id=self.notebook_id,
                            path=rel_path,
                            filename=filename,
                            file_type=file_type,
                            size=file_stats.st_size,
                            hash=file_hash,
                            git_tracked=not is_binary,
                            file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                            file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
                        )
                        session.add(file_meta)

                    # Auto-commit to git if file should be tracked
                    if not is_binary:
                        try:
                            from backend.core.git_manager import GitManager

                            git_manager = GitManager(self.notebook_path)
                            commit_hash = git_manager.auto_commit_on_change(filepath)
                            if commit_hash:
                                file_meta.last_commit_hash = commit_hash
                        except Exception as e:
                            print(f"Warning: Could not commit file to git: {e}")

                    session.commit()

            if self.callback:
                self.callback(filepath, event_type)

        except Exception as e:
            print(f"Error updating metadata for {filepath}: {e}")
        finally:
            session.close()

    def on_created(self, event):
        """Called when a file or directory is created."""
        if not event.is_directory:
            self._update_file_metadata(event.src_path, "created")

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if not event.is_directory:
            self._update_file_metadata(event.src_path, "modified")

    def on_deleted(self, event):
        """Called when a file or directory is deleted."""
        if not event.is_directory:
            self._update_file_metadata(event.src_path, "deleted")

    def on_moved(self, event):
        """Called when a file or directory is moved."""
        if not event.is_directory:
            self._update_file_metadata(event.src_path, "deleted")
            self._update_file_metadata(event.dest_path, "created")


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
        print(f"Starting watcher for notebook at {self.notebook_path}")
        self.observer.schedule(self.handler, self.notebook_path, recursive=True)
        self.observer.start()

        self.scan_existing_files()

    def stop(self):
        """Stop watching the notebook directory."""
        self.observer.stop()
        self.observer.join()

    def scan_existing_files(self):
        """Scan and index all existing files in the notebook."""
        for root, dirs, files in os.walk(self.notebook_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not self.handler._should_ignore(os.path.join(root, d))]

            for filename in files:
                filepath = os.path.join(root, filename)
                if not self.handler._should_ignore(filepath):
                    self.handler._update_file_metadata(filepath, "created")

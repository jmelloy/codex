"""File system watcher for monitoring changes."""

import os
import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Optional, Callable
import logging
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

        logger.debug(f"Updating metadata for {filepath} due to {event_type} event")
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
                    filepath_lower = filepath.lower()
                    filename_lower = os.path.basename(filepath).lower()

                    if filepath.endswith(".md"):
                        file_type = "markdown"
                    elif filepath.endswith(".cdx"):
                        file_type = "view"
                    elif filepath.endswith(".json"):
                        file_type = "json"
                    elif filepath.endswith(".xml"):
                        file_type = "xml"
                    elif filepath_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg")):
                        file_type = "image"
                    elif filepath_lower.endswith(".pdf"):
                        file_type = "pdf"
                    elif filepath_lower.endswith((".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")):
                        file_type = "audio"
                    elif filepath_lower.endswith((".mp4", ".webm", ".ogv", ".mov", ".avi")):
                        file_type = "video"
                    elif filepath_lower.endswith((".html", ".htm")):
                        file_type = "html"
                    # Code file types
                    elif filepath_lower.endswith((".py", ".pyw", ".pyx")):
                        file_type = "code"
                    elif filepath_lower.endswith((".js", ".jsx", ".mjs", ".cjs")):
                        file_type = "code"
                    elif filepath_lower.endswith((".ts", ".tsx")):
                        file_type = "code"
                    elif filepath_lower.endswith((".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx")):
                        file_type = "code"
                    elif filepath_lower.endswith((".java", ".kt", ".kts", ".scala")):
                        file_type = "code"
                    elif filepath_lower.endswith((".go", ".rs", ".swift")):
                        file_type = "code"
                    elif filepath_lower.endswith((".rb", ".php", ".pl", ".pm", ".lua")):
                        file_type = "code"
                    elif filepath_lower.endswith((".cs", ".fs", ".fsx")):
                        file_type = "code"
                    elif filepath_lower.endswith((".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd")):
                        file_type = "code"
                    elif filepath_lower.endswith((".css", ".scss", ".sass", ".less")):
                        file_type = "code"
                    elif filepath_lower.endswith((".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg")):
                        file_type = "code"
                    elif filepath_lower.endswith((".sql", ".graphql", ".gql")):
                        file_type = "code"
                    elif filepath_lower.endswith((".r", ".R", ".hs", ".ml", ".clj", ".cljs", ".ex", ".exs", ".erl")):
                        file_type = "code"
                    elif filepath_lower.endswith((".vue", ".svelte")):
                        file_type = "code"
                    elif filepath_lower.endswith((".diff", ".patch")):
                        file_type = "code"
                    elif filename_lower in ("dockerfile", "makefile", "gnumakefile", "cmakelists.txt"):
                        file_type = "code"

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
                            from codex.core.git_manager import GitManager

                            git_manager = GitManager(self.notebook_path)
                            commit_hash = git_manager.auto_commit_on_change(filepath)
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
                            file_meta = get_existing()
                            if file_meta:
                                file_meta.size = file_stats.st_size
                                file_meta.hash = file_hash
                                file_meta.file_type = file_type
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
            result = session.execute(
                select(FileMetadata).where(FileMetadata.notebook_id == self.notebook_id)
            )
            existing_files = {f.path: f for f in result.scalars().all()}

            # Track which paths we've seen on disk
            seen_paths = set()
            updated_count = 0

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

                    existing = existing_files.get(rel_path)

                    if existing:
                        # File exists in database - check if it needs updating
                        needs_update = False

                        # Compare size first (cheap check)
                        if existing.size != file_size:
                            needs_update = True
                        # Compare modification time (allow 1 second tolerance for filesystem precision)
                        elif existing.file_modified_at:
                            time_diff = abs((file_mtime - existing.file_modified_at).total_seconds())
                            if time_diff > 1:
                                needs_update = True
                        else:
                            # No mtime recorded, need to update
                            needs_update = True

                        if needs_update:
                            self.handler._update_file_metadata(filepath, "modified")
                            updated_count += 1
                    else:
                        # New file not in database
                        self.handler._update_file_metadata(filepath, "created")

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
            logger.info(f"  New: {new_count}, Updated: {updated_count}, Deleted: {deleted_count}, Unchanged: {unchanged_count}")

        except Exception as e:
            logger.error(f"Error during file scan: {e}", exc_info=True)
        finally:
            session.close()

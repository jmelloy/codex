"""Git batcher for batched commits.

This module provides the GitBatcher class which collects file changes and
commits them to git in batches instead of per-operation. This significantly
reduces git overhead for bulk operations.
"""

import logging
import threading
import time
from pathlib import Path

from codex.core.git_lock_manager import git_lock_manager

logger = logging.getLogger(__name__)


class GitBatcher:
    """Batches git commits across multiple file changes.

    Instead of committing every file change immediately, this class collects
    paths and commits them periodically (default: every 5 seconds).
    """

    def __init__(self, interval: float = 5.0, max_files: int = 100):
        """Initialize the git batcher.

        Args:
            interval: Seconds between batch commits (default: 5.0)
            max_files: Force commit when this many files are pending (default: 100)
        """
        self.interval = interval
        self.max_files = max_files
        self._pending: dict[int, dict[str, set[str]]] = {}  # notebook_id -> {notebook_path: paths}
        self._notebook_paths: dict[int, str] = {}  # notebook_id -> notebook_path
        self._last_commit: dict[int, float] = {}  # notebook_id -> timestamp
        self._lock = threading.RLock()

    def add_path(self, notebook_id: int, notebook_path: str, path: str) -> None:
        """Add a path to the pending commit batch.

        Args:
            notebook_id: ID of the notebook
            notebook_path: Filesystem path to the notebook
            path: Relative path of the file within the notebook
        """
        with self._lock:
            if notebook_id not in self._pending:
                self._pending[notebook_id] = set()
                self._notebook_paths[notebook_id] = notebook_path

            self._pending[notebook_id].add(path)

            # Check if we should force commit due to file count
            if len(self._pending[notebook_id]) >= self.max_files:
                logger.info(f"Force committing {len(self._pending[notebook_id])} files for notebook {notebook_id}")
                self._commit_notebook(notebook_id)

    def add_deleted_path(self, notebook_id: int, notebook_path: str, path: str) -> None:
        """Add a deleted path to the pending commit batch.

        Args:
            notebook_id: ID of the notebook
            notebook_path: Filesystem path to the notebook
            path: Relative path of the deleted file
        """
        # Deleted files are tracked the same way - git add -A will handle them
        self.add_path(notebook_id, notebook_path, path)

    def should_commit(self, notebook_id: int) -> bool:
        """Check if it's time to commit for a notebook.

        Args:
            notebook_id: ID of the notebook to check

        Returns:
            True if the notebook has pending changes and enough time has passed
        """
        with self._lock:
            if notebook_id not in self._pending:
                return False
            if not self._pending[notebook_id]:
                return False

            last = self._last_commit.get(notebook_id, 0)
            return time.time() - last >= self.interval

    def commit(self, notebook_id: int) -> int:
        """Perform batch git commit for a notebook.

        Args:
            notebook_id: ID of the notebook to commit

        Returns:
            Number of files committed
        """
        with self._lock:
            return self._commit_notebook(notebook_id)

    def _commit_notebook(self, notebook_id: int) -> int:
        """Internal method to commit a notebook's pending changes.

        Must be called with self._lock held.

        Args:
            notebook_id: ID of the notebook

        Returns:
            Number of files committed
        """
        paths = self._pending.pop(notebook_id, set())
        if not paths:
            return 0

        notebook_path = self._notebook_paths.get(notebook_id)
        if not notebook_path:
            logger.error(f"No notebook path found for notebook {notebook_id}")
            return 0

        self._last_commit[notebook_id] = time.time()

        # Perform git operations outside the lock
        return self._do_git_commit(notebook_id, notebook_path, paths)

    def _do_git_commit(self, notebook_id: int, notebook_path: str, paths: set[str]) -> int:
        """Perform the actual git commit.

        Args:
            notebook_id: ID of the notebook
            notebook_path: Filesystem path to the notebook
            paths: Set of relative file paths to commit

        Returns:
            Number of files committed
        """
        from git import InvalidGitRepositoryError, Repo

        try:
            with git_lock_manager.lock(notebook_path):
                try:
                    repo = Repo(notebook_path)
                except InvalidGitRepositoryError:
                    logger.warning(f"Not a git repository: {notebook_path}")
                    return 0

                notebook_path_obj = Path(notebook_path)

                # Separate existing and deleted files
                existing_paths = []
                deleted_paths = []

                for path in paths:
                    full_path = notebook_path_obj / path
                    if full_path.exists():
                        # Check if it's a binary file (skip those)
                        if not self._is_binary_file(str(full_path)):
                            existing_paths.append(path)
                    else:
                        deleted_paths.append(path)

                # Stage existing files
                if existing_paths:
                    try:
                        repo.index.add(existing_paths)
                    except Exception as e:
                        logger.warning(f"Error adding files to git: {e}")

                # Stage deleted files
                for path in deleted_paths:
                    try:
                        repo.index.remove([path], working_tree=False)
                    except Exception:
                        # File might not be tracked
                        pass

                # Check if there are staged changes
                if not repo.index.diff("HEAD") and repo.head.is_valid():
                    logger.debug(f"No changes to commit for notebook {notebook_id}")
                    return 0

                # Commit with summary message
                total_files = len(existing_paths) + len(deleted_paths)
                if total_files == 1:
                    path = existing_paths[0] if existing_paths else deleted_paths[0]
                    action = "Delete" if path in deleted_paths else "Update"
                    msg = f"{action} {path}"
                else:
                    msg = f"Batch update: {total_files} files"

                repo.index.commit(msg)
                logger.info(f"Committed {total_files} files for notebook {notebook_id}: {msg}")
                return total_files

        except Exception as e:
            logger.error(f"Error committing to git for notebook {notebook_id}: {e}")
            return 0

    def _is_binary_file(self, filepath: str) -> bool:
        """Check if a file is binary.

        Args:
            filepath: Path to the file

        Returns:
            True if the file appears to be binary
        """
        try:
            with open(filepath, "rb") as f:
                chunk = f.read(8192)
                return b"\0" in chunk
        except Exception:
            return False

    def commit_all(self) -> int:
        """Commit all pending changes for all notebooks.

        Useful for graceful shutdown.

        Returns:
            Total number of files committed
        """
        with self._lock:
            notebook_ids = list(self._pending.keys())

        total = 0
        for notebook_id in notebook_ids:
            total += self.commit(notebook_id)

        return total

    def get_pending_count(self, notebook_id: int | None = None) -> int:
        """Get count of pending files.

        Args:
            notebook_id: Optional notebook ID to filter by

        Returns:
            Number of pending files
        """
        with self._lock:
            if notebook_id is not None:
                return len(self._pending.get(notebook_id, set()))
            return sum(len(paths) for paths in self._pending.values())

    def get_stats(self) -> dict:
        """Get statistics about the batcher.

        Returns:
            Dictionary with stats about pending files and last commits
        """
        with self._lock:
            return {
                "pending_notebooks": len(self._pending),
                "pending_files": sum(len(paths) for paths in self._pending.values()),
                "notebooks": {
                    nb_id: {
                        "pending": len(paths),
                        "last_commit": self._last_commit.get(nb_id),
                    }
                    for nb_id, paths in self._pending.items()
                },
            }

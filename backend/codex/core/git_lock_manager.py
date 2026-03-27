"""Lock manager for git operations to prevent conflicts."""

import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

# Maximum age (seconds) for a .git/index.lock file before it's considered stale
STALE_LOCK_SECONDS = 60


def _clean_stale_index_lock(notebook_path: str) -> None:
    """Remove .git/index.lock if it exists and is older than STALE_LOCK_SECONDS."""
    lock_file = Path(notebook_path) / ".git" / "index.lock"
    if not lock_file.exists():
        return
    try:
        age = time.time() - lock_file.stat().st_mtime
        if age > STALE_LOCK_SECONDS:
            lock_file.unlink(missing_ok=True)
            logger.warning(
                f"Removed stale git index.lock ({age:.0f}s old): {lock_file}"
            )
        else:
            logger.debug(
                f"Git index.lock exists but is recent ({age:.0f}s old), leaving it: {lock_file}"
            )
    except FileNotFoundError:
        pass  # Race: file was removed between exists() and stat()/unlink()
    except Exception as e:
        logger.error(f"Error checking git index.lock: {e}")


class GitLockManager:
    """Manager for locking git operations per notebook path to prevent conflicts.

    Uses a single threading.RLock per notebook path that protects all git
    operations regardless of whether they originate from sync threads (file
    watcher) or async tasks (API routes).  The async_lock() context manager
    acquires the *same* underlying RLock via run_in_executor so that sync
    and async callers are properly serialised.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure a single lock manager instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the lock manager."""
        if self._initialized:
            return

        # Single set of locks used by both sync and async paths
        self._locks: dict[str, threading.RLock] = {}
        self._locks_lock = threading.Lock()

        self._initialized = True
        logger.info("GitLockManager initialized")

    def _get_lock(self, notebook_path: str) -> threading.RLock:
        """Get or create a lock for the given notebook path."""
        with self._locks_lock:
            if notebook_path not in self._locks:
                self._locks[notebook_path] = threading.RLock()
                logger.debug(f"Created lock for notebook: {notebook_path}")
            return self._locks[notebook_path]

    @contextmanager
    def lock(self, notebook_path: str, timeout: float = 30.0):
        """Context manager for synchronous git operations.

        Args:
            notebook_path: The path to the notebook repository
            timeout: Maximum seconds to wait for the lock (default 30)

        Raises:
            TimeoutError: If the lock cannot be acquired within timeout
        """
        # Clean up stale git index.lock before trying to acquire
        _clean_stale_index_lock(notebook_path)

        rlock = self._get_lock(notebook_path)
        acquired = rlock.acquire(timeout=timeout)
        if not acquired:
            # Last resort: check if the index.lock is stale and force-clean
            _clean_stale_index_lock(notebook_path)
            acquired = rlock.acquire(timeout=5)
            if not acquired:
                logger.error(f"Timeout acquiring git lock for: {notebook_path}")
                raise TimeoutError(f"Could not acquire git lock for {notebook_path} within {timeout}s")

        try:
            yield
        finally:
            rlock.release()
            # Clean up any index.lock left behind by a crashed git process
            _clean_stale_index_lock(notebook_path)

    def clear_locks(self, notebook_path: str = None):
        """Clear locks for a specific notebook or all notebooks.

        This is primarily useful for testing and cleanup.

        Args:
            notebook_path: Optional path to clear locks for. If None, clears all locks.
        """
        with self._locks_lock:
            if notebook_path:
                self._locks.pop(notebook_path, None)
                logger.debug(f"Cleared lock for: {notebook_path}")
            else:
                self._locks.clear()
                logger.debug("Cleared all locks")


# Global singleton instance
git_lock_manager = GitLockManager()

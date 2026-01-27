"""Lock manager for git operations to prevent conflicts."""

import asyncio
import threading
from typing import Dict
from contextlib import contextmanager, asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class GitLockManager:
    """Manager for locking git operations per notebook path to prevent conflicts.
    
    This class provides both synchronous and asynchronous locking mechanisms
    to ensure that git operations on the same repository don't conflict with
    each other when called from multiple threads or async tasks.
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
        
        # Threading locks for synchronous operations
        self._sync_locks: Dict[str, threading.RLock] = {}
        self._sync_locks_lock = threading.Lock()
        
        # Asyncio locks for asynchronous operations
        self._async_locks: Dict[str, asyncio.Lock] = {}
        self._async_locks_lock = threading.Lock()
        
        self._initialized = True
        logger.info("GitLockManager initialized")

    def _get_sync_lock(self, notebook_path: str) -> threading.RLock:
        """Get or create a threading lock for the given notebook path.
        
        Args:
            notebook_path: The path to the notebook repository
            
        Returns:
            A threading.RLock for the notebook
        """
        with self._sync_locks_lock:
            if notebook_path not in self._sync_locks:
                self._sync_locks[notebook_path] = threading.RLock()
                logger.debug(f"Created sync lock for notebook: {notebook_path}")
            return self._sync_locks[notebook_path]

    def _get_async_lock(self, notebook_path: str) -> asyncio.Lock:
        """Get or create an asyncio lock for the given notebook path.
        
        Args:
            notebook_path: The path to the notebook repository
            
        Returns:
            An asyncio.Lock for the notebook
        """
        with self._async_locks_lock:
            if notebook_path not in self._async_locks:
                self._async_locks[notebook_path] = asyncio.Lock()
                logger.debug(f"Created async lock for notebook: {notebook_path}")
            return self._async_locks[notebook_path]

    @contextmanager
    def lock(self, notebook_path: str):
        """Context manager for synchronous git operations.
        
        Args:
            notebook_path: The path to the notebook repository
            
        Yields:
            None
            
        Example:
            with git_lock_manager.lock(notebook_path):
                # Perform git operations here
                git_manager.commit("message")
        """
        lock = self._get_sync_lock(notebook_path)
        # logger.debug(f"Acquiring sync lock for: {notebook_path}")
        lock.acquire()
        try:
            # logger.debug(f"Acquired sync lock for: {notebook_path}")
            yield
        finally:
            lock.release()
            # logger.debug(f"Released sync lock for: {notebook_path}")
            
    @asynccontextmanager
    async def async_lock(self, notebook_path: str):
        """Context manager for asynchronous git operations.
        
        Args:
            notebook_path: The path to the notebook repository
            
        Yields:
            None
            
        Example:
            async with git_lock_manager.async_lock(notebook_path):
                # Perform git operations here
                git_manager.commit("message")
        """
        lock = self._get_async_lock(notebook_path)
        logger.debug(f"Acquiring async lock for: {notebook_path}")
        await lock.acquire()
        try:
            logger.debug(f"Acquired async lock for: {notebook_path}")
            yield
        finally:
            lock.release()
            logger.debug(f"Released async lock for: {notebook_path}")

    def clear_locks(self, notebook_path: str = None):
        """Clear locks for a specific notebook or all notebooks.
        
        This is primarily useful for testing and cleanup.
        
        Args:
            notebook_path: Optional path to clear locks for. If None, clears all locks.
        """
        with self._sync_locks_lock:
            if notebook_path:
                self._sync_locks.pop(notebook_path, None)
                logger.debug(f"Cleared sync lock for: {notebook_path}")
            else:
                self._sync_locks.clear()
                logger.debug("Cleared all sync locks")
        
        with self._async_locks_lock:
            if notebook_path:
                self._async_locks.pop(notebook_path, None)
                logger.debug(f"Cleared async lock for: {notebook_path}")
            else:
                self._async_locks.clear()
                logger.debug("Cleared all async locks")


# Global singleton instance
git_lock_manager = GitLockManager()

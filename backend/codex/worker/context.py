"""Worker lifecycle hooks — startup and shutdown."""

import logging

from taskiq import TaskiqState

logger = logging.getLogger(__name__)


async def startup(state: TaskiqState) -> None:
    """Initialize database connections when the worker starts."""
    from codex.db.database import async_session_maker, init_system_db

    logger.info("Worker starting up — initializing system database")
    await init_system_db()
    state.session_maker = async_session_maker
    logger.info("Worker startup complete")


async def shutdown(state: TaskiqState) -> None:
    """Cleanup when the worker stops."""
    logger.info("Worker shutting down")

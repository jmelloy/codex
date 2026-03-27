"""Worker lifecycle hooks — startup and shutdown."""

import logging

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Initialize database connections when the worker starts."""
    from codex.db.database import async_session_maker, init_system_db

    logger.info("Worker starting up — initializing system database")
    await init_system_db()
    ctx["session_maker"] = async_session_maker
    logger.info("Worker startup complete")


async def shutdown(ctx: dict) -> None:
    """Cleanup when the worker stops."""
    logger.info("Worker shutting down")

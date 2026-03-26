"""ARQ worker settings and Redis configuration."""

import os
from urllib.parse import urlparse

from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis_settings() -> RedisSettings:
    """Parse REDIS_URL environment variable into ARQ RedisSettings."""
    parsed = urlparse(REDIS_URL)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


async def _on_startup(ctx):
    """Initialize database on worker start."""
    from codex.worker.context import startup

    await startup(ctx)


async def _on_shutdown(ctx):
    """Cleanup on worker stop."""
    from codex.worker.context import shutdown

    await shutdown(ctx)


class WorkerSettings:
    """ARQ worker configuration.

    Start the worker with: arq codex.worker.settings.WorkerSettings
    """

    from codex.worker.tasks import execute_agent_task, run_job

    functions = [execute_agent_task, run_job]
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 600  # 10 minutes

    on_startup = _on_startup
    on_shutdown = _on_shutdown

"""Taskiq broker and Redis configuration.

Start the worker with: taskiq worker codex.worker.settings:broker codex.worker.tasks
"""

import os

from taskiq import TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

broker = ListQueueBroker(REDIS_URL).with_result_backend(RedisAsyncResultBackend(REDIS_URL))


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_startup(state: TaskiqState) -> None:
    """Initialize database on worker start."""
    from codex.worker.context import startup

    await startup(state)


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_shutdown(state: TaskiqState) -> None:
    """Cleanup on worker stop."""
    from codex.worker.context import shutdown

    await shutdown(state)

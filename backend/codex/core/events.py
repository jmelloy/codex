"""Event outbox helpers (issue #530).

Routes append an `Event` row in the same DB transaction as the domain change
it describes, then — once that transaction is committed — enqueue an ARQ job
to fan it out into `Notification` rows off the request path. If the task queue
is unavailable the event is still durably recorded; only the (best-effort)
live fanout is skipped.
"""

import logging

from fastapi import Request

from codex.db.models import Event

logger = logging.getLogger(__name__)


def build_event(workspace_id: int, actor_id: int | None, kind: str, subject: dict) -> Event:
    """Construct an `Event` row. Caller is responsible for `session.add` + commit."""
    return Event(workspace_id=workspace_id, actor_id=actor_id, kind=kind, subject=subject)


async def enqueue_fanout(request: Request, event_id: int) -> None:
    """Enqueue async notification fanout for a committed event.

    Must be called after the event's transaction has committed, so the worker
    (a separate process) is guaranteed to see the row when it picks up the job.
    """
    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is None:
        logger.warning("Skipping notification fanout for event %s — task queue unavailable", event_id)
        return
    try:
        await arq_pool.enqueue_job("fanout_event", event_id)
    except Exception:
        logger.exception("Failed to enqueue fanout job for event %s", event_id)

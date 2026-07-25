"""Notification serialization and live WebSocket push (issue #531).

Shared by the notifications API routes (for serializing REST responses) and
the `fanout_event` ARQ job (for pushing newly created notifications to the
recipient's `principal:{id}` channel as soon as they're created).
"""

from codex.core.websocket import connection_manager, principal_channel
from codex.db.models import Event, Notification


def serialize_notification(notification: Notification, event: Event) -> dict:
    """Denormalize a Notification + its Event into a JSON-safe payload."""
    return {
        "id": notification.id,
        "event_id": event.id,
        "kind": event.kind,
        "workspace_id": event.workspace_id,
        "actor_id": event.actor_id,
        "subject": event.subject,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "created_at": notification.created_at.isoformat(),
    }


async def push_notification(recipient_id: int, payload: dict) -> None:
    """Push a notification payload to the recipient's WebSocket channel.

    A no-op if the recipient has no open connections subscribed to
    `principal:{recipient_id}` — the row already persisted via the REST API
    regardless of live delivery.
    """
    await connection_manager.broadcast(principal_channel(recipient_id), {"type": "notification", "data": payload})

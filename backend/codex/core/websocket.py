"""WebSocket manager for broadcasting file change events.

Connections are organized by channel rather than by bare notebook/workspace id:

- ``workspace:{workspace_id}`` - file change events for everything in that workspace.
- ``principal:{user_id}`` - events addressed to a specific connected user.

A socket can be subscribed to multiple channels at once; subscriptions are only
granted by callers (see `codex.api.routes.ws`) after checking the connecting
principal's effective permission level.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

WORKSPACE_CHANNEL_PREFIX = "workspace:"
PRINCIPAL_CHANNEL_PREFIX = "principal:"


def workspace_channel(workspace_id: int) -> str:
    return f"{WORKSPACE_CHANNEL_PREFIX}{workspace_id}"


def principal_channel(user_id: int) -> str:
    return f"{PRINCIPAL_CHANNEL_PREFIX}{user_id}"


@dataclass
class FileChangeEvent:
    """Represents a file change event to broadcast."""

    notebook_id: int
    event_type: str  # "created", "modified", "deleted", "moved"
    path: str
    old_path: str | None = None  # For move events
    timestamp: str | None = None
    block_id: str | None = None  # Block ID if known
    title: str | None = None
    block_type: str | None = None
    properties: dict | None = None
    workspace_id: int | None = None  # Routing target; resolved lazily if not given
    actor_principal_id: int | None = None  # User whose action triggered this event

    def to_dict(self) -> dict:
        result = {
            "type": "file_change",
            "notebook_id": self.notebook_id,
            "event_type": self.event_type,
            "path": self.path,
            "old_path": self.old_path,
            "timestamp": self.timestamp or datetime.now(UTC).isoformat(),
        }
        if self.block_id:
            result["block_id"] = self.block_id
        if self.title is not None:
            result["title"] = self.title
        if self.block_type is not None:
            result["block_type"] = self.block_type
        if self.properties is not None:
            result["properties"] = self.properties
        if self.actor_principal_id is not None:
            result["actor_principal_id"] = self.actor_principal_id
        return result


def _lookup_workspace_id_sync(notebook_id: int) -> int | None:
    """Blocking lookup of a notebook's workspace id, for use in a worker thread."""
    from codex.db.database import get_system_session_sync
    from codex.db.models import Notebook

    session = get_system_session_sync()
    try:
        notebook = session.get(Notebook, notebook_id)
        return notebook.workspace_id if notebook else None
    finally:
        session.close()


class ConnectionManager:
    """Manages WebSocket connections and their channel subscriptions."""

    def __init__(self):
        # Map of channel -> set of connected WebSockets
        self._channels: dict[str, set[WebSocket]] = {}
        # Map of WebSocket -> set of channels it is subscribed to (for cleanup)
        self._socket_channels: dict[WebSocket, set[str]] = {}
        # Event queue for broadcasting from sync threads
        self._event_queue: asyncio.Queue[FileChangeEvent] | None = None
        self._broadcast_task: asyncio.Task | None = None
        # Cache of notebook_id -> workspace_id for events that don't carry it
        self._notebook_workspace_cache: dict[int, int] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection. Subscribe it to channels separately."""
        await websocket.accept()
        self._socket_channels[websocket] = set()

    def subscribe(self, websocket: WebSocket, channel: str) -> None:
        """Subscribe an already-connected socket to a channel.

        Callers are responsible for checking that the connecting principal is
        authorized for `channel` before calling this.
        """
        self._channels.setdefault(channel, set()).add(websocket)
        self._socket_channels.setdefault(websocket, set()).add(channel)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from all channels it was subscribed to."""
        channels = self._socket_channels.pop(websocket, set())
        for channel in channels:
            connections = self._channels.get(channel)
            if connections is not None:
                connections.discard(websocket)
                if not connections:
                    del self._channels[channel]
        if channels:
            logger.info(f"WebSocket disconnected from channels: {sorted(channels)}")

    async def broadcast(self, channel: str, message: dict) -> None:
        """Broadcast a message to all connections subscribed to a channel."""
        connections = self._channels.get(channel)
        if not connections:
            return

        dead_connections = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                dead_connections.append(websocket)

        for websocket in dead_connections:
            connections.discard(websocket)

    def queue_event(self, event: FileChangeEvent):
        """Queue an event for async broadcasting (thread-safe)."""
        if self._event_queue is not None:
            try:
                self._event_queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event queue full, dropping file change event")

    async def start_broadcast_loop(self):
        """Start the async broadcast loop."""
        self._event_queue = asyncio.Queue(maxsize=1000)
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("WebSocket broadcast loop started")

    async def stop_broadcast_loop(self):
        """Stop the broadcast loop."""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        self._event_queue = None
        logger.info("WebSocket broadcast loop stopped")

    async def _resolve_workspace_id(self, notebook_id: int) -> int | None:
        if notebook_id in self._notebook_workspace_cache:
            return self._notebook_workspace_cache[notebook_id]

        workspace_id = await asyncio.to_thread(_lookup_workspace_id_sync, notebook_id)
        if workspace_id is not None:
            self._notebook_workspace_cache[notebook_id] = workspace_id
        return workspace_id

    async def _broadcast_loop(self):
        """Process events from the queue and broadcast them."""
        while True:
            try:
                event = await self._event_queue.get()
                workspace_id = event.workspace_id
                if workspace_id is None:
                    workspace_id = await self._resolve_workspace_id(event.notebook_id)
                if workspace_id is None:
                    logger.warning(f"Could not resolve workspace for notebook {event.notebook_id}, dropping event")
                    continue
                await self.broadcast(workspace_channel(workspace_id), event.to_dict())
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}", exc_info=True)


# Global connection manager instance
connection_manager = ConnectionManager()


def notify_file_change(
    notebook_id: int,
    event_type: str,
    path: str,
    old_path: str | None = None,
    block_id: str | None = None,
    title: str | None = None,
    block_type: str | None = None,
    properties: dict | None = None,
    workspace_id: int | None = None,
    actor_principal_id: int | None = None,
):
    """Notify connected clients about a file change.

    This function is thread-safe and can be called from the watcher threads.
    `workspace_id`/`actor_principal_id` are optional: callers with a request context
    (e.g. API routes) should pass them; the watcher (a background thread with no
    request context) omits them and the broadcast loop resolves workspace_id lazily.
    """
    event = FileChangeEvent(
        notebook_id=notebook_id,
        event_type=event_type,
        path=path,
        old_path=old_path,
        block_id=block_id,
        title=title,
        block_type=block_type,
        properties=properties,
        workspace_id=workspace_id,
        actor_principal_id=actor_principal_id,
    )
    connection_manager.queue_event(event)

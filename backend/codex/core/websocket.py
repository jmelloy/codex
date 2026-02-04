"""WebSocket manager for broadcasting file change events."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class FileChangeEvent:
    """Represents a file change event to broadcast."""

    notebook_id: int
    event_type: str  # "created", "modified", "deleted", "moved"
    path: str
    old_path: str | None = None  # For move events
    timestamp: str | None = None

    def to_dict(self) -> dict:
        return {
            "type": "file_change",
            "notebook_id": self.notebook_id,
            "event_type": self.event_type,
            "path": self.path,
            "old_path": self.old_path,
            "timestamp": self.timestamp or datetime.now(UTC).isoformat(),
        }


class ConnectionManager:
    """Manages WebSocket connections for file change notifications."""

    def __init__(self):
        # Map of notebook_id -> set of connected WebSockets
        self._connections: dict[int, set[WebSocket]] = {}
        # Event queue for broadcasting from sync threads
        self._event_queue: asyncio.Queue[FileChangeEvent] | None = None
        self._broadcast_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, notebook_id: int):
        """Accept a new WebSocket connection for a notebook."""
        await websocket.accept()
        if notebook_id not in self._connections:
            self._connections[notebook_id] = set()
        self._connections[notebook_id].add(websocket)
        logger.info(f"WebSocket connected for notebook {notebook_id}. Total connections: {len(self._connections[notebook_id])}")

    def disconnect(self, websocket: WebSocket, notebook_id: int):
        """Remove a WebSocket connection."""
        if notebook_id in self._connections:
            self._connections[notebook_id].discard(websocket)
            if not self._connections[notebook_id]:
                del self._connections[notebook_id]
            logger.info(f"WebSocket disconnected for notebook {notebook_id}")

    async def broadcast_to_notebook(self, notebook_id: int, message: dict):
        """Broadcast a message to all connections for a notebook."""
        if notebook_id not in self._connections:
            return

        dead_connections = []
        for websocket in self._connections[notebook_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                dead_connections.append(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            self._connections[notebook_id].discard(ws)

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

    async def _broadcast_loop(self):
        """Process events from the queue and broadcast them."""
        while True:
            try:
                event = await self._event_queue.get()
                await self.broadcast_to_notebook(event.notebook_id, event.to_dict())
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
):
    """Notify connected clients about a file change.

    This function is thread-safe and can be called from the watcher threads.
    """
    event = FileChangeEvent(
        notebook_id=notebook_id,
        event_type=event_type,
        path=path,
        old_path=old_path,
    )
    connection_manager.queue_event(event)

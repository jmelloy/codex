"""WebSocket routes for real-time file change notifications."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from codex.core.websocket import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/notebooks/{notebook_id}")
async def notebook_websocket(websocket: WebSocket, notebook_id: int):
    """WebSocket endpoint for receiving file change notifications for a notebook.

    Clients connect to this endpoint to receive real-time updates when files
    in the notebook are created, modified, deleted, or moved.

    Message format:
    {
        "type": "file_change",
        "notebook_id": 123,
        "event_type": "created" | "modified" | "deleted" | "moved",
        "path": "relative/path/to/file.md",
        "old_path": "old/path/if/moved.md",  // only for moved events
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    await connection_manager.connect(websocket, notebook_id)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "notebook_id": notebook_id,
            "message": "Connected to file change notifications",
        })

        # Keep connection alive and handle any client messages
        while True:
            # Wait for messages (ping/pong or disconnect)
            data = await websocket.receive_text()
            # Handle ping messages
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for notebook {notebook_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for notebook {notebook_id}: {e}")
    finally:
        connection_manager.disconnect(websocket, notebook_id)

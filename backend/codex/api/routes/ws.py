"""WebSocket routes for real-time file change notifications."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select

from codex.api.auth import get_user_from_token
from codex.core.permissions import PermissionLevel, effective_level
from codex.core.websocket import connection_manager, principal_channel, workspace_channel
from codex.db.database import async_session_maker
from codex.db.models import Notebook, User, Workspace

logger = logging.getLogger(__name__)

router = APIRouter()

# RFC 6455 "Policy Violation" - used for both authentication and authorization failures
# so we don't leak which one occurred to an unauthenticated caller.
WS_POLICY_VIOLATION = 1008

# How long to wait for a first-message auth payload when no token was on the query string.
AUTH_MESSAGE_TIMEOUT_SECONDS = 10.0


async def _deny(websocket: WebSocket) -> None:
    """Close a connection that failed authentication/authorization, tolerating a client
    that has already disconnected on its own.

    Always closes with the same generic reason - the specific cause (missing auth,
    unknown notebook, or insufficient permission) is deliberately not disclosed, so an
    unauthenticated caller can't use the close reason to probe what exists.
    """
    try:
        await websocket.close(code=WS_POLICY_VIOLATION, reason="Forbidden")
    except Exception:
        pass
    connection_manager.disconnect(websocket)


async def _resolve_principal(websocket: WebSocket, token: str | None, session) -> User | None:
    """Resolve the connecting principal from a query-param token or a first auth message.

    Supports two handshake styles:
    - `?token=...` on the connection URL.
    - No token on the URL: the client's first message must be
      `{"type": "auth", "token": "..."}`.
    """
    if token:
        return await get_user_from_token(token, session)

    try:
        data = await asyncio.wait_for(websocket.receive_json(), timeout=AUTH_MESSAGE_TIMEOUT_SECONDS)
    except Exception:
        return None

    if not isinstance(data, dict) or data.get("type") != "auth":
        return None

    return await get_user_from_token(data.get("token") or "", session)


@router.websocket("/notebooks/{notebook_id}")
async def notebook_websocket(websocket: WebSocket, notebook_id: int, token: str | None = None):
    """WebSocket endpoint for receiving file change notifications for a notebook.

    Clients must authenticate at handshake time, either via a `token` query param or
    by sending `{"type": "auth", "token": "..."}` as their first message. The connection
    is closed with a policy-violation code if authentication fails or the resolved
    principal lacks at least read access to the notebook's workspace.

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
    await connection_manager.connect(websocket)

    try:
        async with async_session_maker() as session:
            user = await _resolve_principal(websocket, token, session)
            if user is None:
                await _deny(websocket)
                return

            result = await session.execute(
                select(Notebook, Workspace)
                .join(Workspace, Notebook.workspace_id == Workspace.id)
                .where(Notebook.id == notebook_id)
            )
            row = result.first()
            if row is None:
                await _deny(websocket)
                return
            notebook, workspace = row

            level = await effective_level(user, workspace, session)
            if level is None or level < PermissionLevel.READ:
                await _deny(websocket)
                return

        connection_manager.subscribe(websocket, workspace_channel(workspace.id))
        connection_manager.subscribe(websocket, principal_channel(user.id))
    except Exception:
        # Any unexpected failure during auth/authorization (DB error, etc.) must still
        # untrack the socket - otherwise it lingers in connection_manager forever.
        logger.exception(f"WebSocket handshake failed for notebook {notebook_id}")
        await _deny(websocket)
        return

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "notebook_id": notebook_id,
                "message": "Connected to file change notifications",
            }
        )

        # Keep connection alive and handle any client messages
        while True:
            # Wait for messages (ping/pong or disconnect)
            data = await websocket.receive_text()
            # Handle ping messages
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for notebook {notebook_id} (user={user.id})")
    except Exception as e:
        logger.warning(f"WebSocket error for notebook {notebook_id}: {e}")
    finally:
        connection_manager.disconnect(websocket)

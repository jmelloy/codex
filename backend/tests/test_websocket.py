"""Tests for WebSocket file change notifications."""

import time

from starlette.websockets import WebSocketDisconnect

from codex.core.websocket import (
    ConnectionManager,
    FileChangeEvent,
    notify_file_change,
)


class TestFileChangeEvent:
    """Tests for FileChangeEvent dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        event = FileChangeEvent(
            notebook_id=1,
            event_type="created",
            path="test/file.md",
            timestamp="2024-01-15T10:30:00Z",
        )
        result = event.to_dict()

        assert result["type"] == "file_change"
        assert result["notebook_id"] == 1
        assert result["event_type"] == "created"
        assert result["path"] == "test/file.md"
        assert result["old_path"] is None
        assert result["timestamp"] == "2024-01-15T10:30:00Z"

    def test_to_dict_with_old_path(self):
        """Test conversion with old_path for move events."""
        event = FileChangeEvent(
            notebook_id=1,
            event_type="moved",
            path="new/path.md",
            old_path="old/path.md",
        )
        result = event.to_dict()

        assert result["event_type"] == "moved"
        assert result["path"] == "new/path.md"
        assert result["old_path"] == "old/path.md"


class TestConnectionManager:
    """Tests for ConnectionManager."""

    def test_queue_event_without_loop(self):
        """Test that queue_event handles no event loop gracefully."""
        manager = ConnectionManager()
        # Should not raise even without event loop started
        event = FileChangeEvent(
            notebook_id=1,
            event_type="created",
            path="test.md",
        )
        # This should be a no-op since _event_queue is None
        manager.queue_event(event)


class TestWebSocketEndpoint:
    """Tests for the WebSocket endpoint."""

    def test_websocket_connection(self, test_client, auth_headers, workspace_and_notebook):
        """Test WebSocket connection establishment with a token query param."""
        _, notebook = workspace_and_notebook
        token = auth_headers[0]["Authorization"].removeprefix("Bearer ")

        with test_client.websocket_connect(f"/api/v1/ws/notebooks/{notebook['id']}?token={token}") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["notebook_id"] == notebook["id"]

    def test_websocket_ping_pong(self, test_client, auth_headers, workspace_and_notebook):
        """Test WebSocket ping/pong."""
        _, notebook = workspace_and_notebook
        token = auth_headers[0]["Authorization"].removeprefix("Bearer ")

        with test_client.websocket_connect(f"/api/v1/ws/notebooks/{notebook['id']}?token={token}") as websocket:
            # Consume the connection message
            websocket.receive_json()

            # Send ping
            websocket.send_text("ping")

            # Should receive pong
            response = websocket.receive_text()
            assert response == "pong"

    def test_websocket_connection_via_first_message_auth(self, test_client, auth_headers, workspace_and_notebook):
        """Test authenticating via a first `{"type": "auth", ...}` message instead of a query param."""
        _, notebook = workspace_and_notebook
        token = auth_headers[0]["Authorization"].removeprefix("Bearer ")

        with test_client.websocket_connect(f"/api/v1/ws/notebooks/{notebook['id']}") as websocket:
            websocket.send_json({"type": "auth", "token": token})
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["notebook_id"] == notebook["id"]

    def test_websocket_rejects_unauthenticated_connection(self, test_client, workspace_and_notebook):
        """An unauthenticated connection (no token, no auth message) is closed with a policy code."""
        _, notebook = workspace_and_notebook

        with test_client.websocket_connect(f"/api/v1/ws/notebooks/{notebook['id']}") as websocket:
            try:
                websocket.receive_json()
                assert False, "expected the connection to be closed"
            except WebSocketDisconnect as exc:
                assert exc.code == 1008

    def test_websocket_rejects_invalid_token(self, test_client, workspace_and_notebook):
        """A connection with a bogus token is closed with a policy code."""
        _, notebook = workspace_and_notebook

        with test_client.websocket_connect(
            f"/api/v1/ws/notebooks/{notebook['id']}?token=not-a-real-token"
        ) as websocket:
            try:
                websocket.receive_json()
                assert False, "expected the connection to be closed"
            except WebSocketDisconnect as exc:
                assert exc.code == 1008

    def test_websocket_rejects_user_without_access(self, test_client, workspace_and_notebook):
        """A user with no permission on the workspace cannot subscribe to its events."""
        _, notebook = workspace_and_notebook

        stranger_username = f"ws_stranger_{int(time.time() * 1_000_000)}"
        test_client.post(
            "/api/v1/users/register",
            json={
                "username": stranger_username,
                "email": f"{stranger_username}@example.com",
                "password": "testpass123",
            },
        )
        login_response = test_client.post(
            "/api/v1/users/token", data={"username": stranger_username, "password": "testpass123"}
        )
        assert login_response.status_code == 200
        stranger_token = login_response.json()["access_token"]

        with test_client.websocket_connect(
            f"/api/v1/ws/notebooks/{notebook['id']}?token={stranger_token}"
        ) as websocket:
            try:
                websocket.receive_json()
                assert False, "expected the connection to be closed"
            except WebSocketDisconnect as exc:
                assert exc.code == 1008


class TestNotifyFileChange:
    """Tests for the notify_file_change function."""

    def test_notify_file_change(self):
        """Test that notify_file_change queues an event."""
        # This should not raise even if no clients are connected
        notify_file_change(
            notebook_id=1,
            event_type="modified",
            path="test/file.md",
        )

    def test_notify_file_change_with_old_path(self):
        """Test notify_file_change for move events."""
        notify_file_change(
            notebook_id=1,
            event_type="moved",
            path="new/path.md",
            old_path="old/path.md",
        )

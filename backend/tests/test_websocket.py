"""Tests for WebSocket file change notifications."""

import pytest
from fastapi.testclient import TestClient

from codex.core.websocket import (
    ConnectionManager,
    FileChangeEvent,
    connection_manager,
    notify_file_change,
)
from codex.main import app


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

    def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/notebooks/1") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["notebook_id"] == 1

    def test_websocket_ping_pong(self):
        """Test WebSocket ping/pong."""
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/notebooks/1") as websocket:
            # Consume the connection message
            websocket.receive_json()

            # Send ping
            websocket.send_text("ping")

            # Should receive pong
            response = websocket.receive_text()
            assert response == "pong"


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

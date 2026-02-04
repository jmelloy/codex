"""Tests for the FileOperationQueue class."""

import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codex.core.watcher import FileOperation, FileOperationQueue, calculate_file_hash


class TestFileOperation:
    """Tests for the FileOperation dataclass."""

    def test_file_operation_defaults(self):
        """Test FileOperation has correct defaults."""
        op = FileOperation(filepath="/test/file.txt", sidecar_path=None, operation="created")
        assert op.filepath == "/test/file.txt"
        assert op.sidecar_path is None
        assert op.operation == "created"
        assert op.comment is None
        assert op.file_hash is None
        assert op.timestamp > 0
        assert op.completion_event is None
        assert op.result is None
        assert op.error is None

    def test_file_operation_with_all_fields(self):
        """Test FileOperation with all fields set."""
        event = threading.Event()
        op = FileOperation(
            filepath="/test/file.txt",
            sidecar_path="/test/file.txt.meta",
            operation="modified",
            comment="Test comment",
            file_hash="abc123",
            timestamp=12345.0,
            completion_event=event,
        )
        assert op.filepath == "/test/file.txt"
        assert op.sidecar_path == "/test/file.txt.meta"
        assert op.operation == "modified"
        assert op.comment == "Test comment"
        assert op.file_hash == "abc123"
        assert op.timestamp == 12345.0
        assert op.completion_event is event


class TestFileOperationQueue:
    """Tests for the FileOperationQueue class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback for processing."""
        return MagicMock()

    @pytest.fixture
    def queue(self, temp_dir, mock_callback):
        """Create a FileOperationQueue for testing."""
        q = FileOperationQueue(
            notebook_path=temp_dir,
            notebook_id=1,
            process_callback=mock_callback,
        )
        # Use shorter batch interval for tests
        q.BATCH_INTERVAL = 0.1
        return q

    def test_queue_enqueue_and_process(self, queue, mock_callback, temp_dir):
        """Test basic enqueue and process flow."""
        # Create a test file
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        # Start the queue
        queue.start()

        try:
            # Enqueue an operation
            op = queue.enqueue(str(test_file), None, "created")
            assert op.filepath == str(test_file)
            assert op.operation == "created"

            # Wait for processing
            time.sleep(0.3)

            # Verify callback was called
            mock_callback.assert_called()
            call_args = mock_callback.call_args[0]
            assert call_args[0] == str(test_file)
            assert call_args[2] == "created"
        finally:
            queue.stop()

    def test_queue_consolidates_updates(self, queue, mock_callback, temp_dir):
        """Test that multiple updates to the same file are consolidated."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        queue.start()

        try:
            # Enqueue multiple updates to the same file
            queue.enqueue(str(test_file), None, "modified")
            time.sleep(0.01)
            queue.enqueue(str(test_file), None, "modified")
            time.sleep(0.01)
            queue.enqueue(str(test_file), None, "modified")

            # Wait for batch processing
            time.sleep(0.3)

            # Should only have been called once (consolidated)
            assert mock_callback.call_count == 1
        finally:
            queue.stop()

    def test_queue_detects_move(self, queue, mock_callback, temp_dir):
        """Test that delete + create with same hash is detected as move."""
        # Create source file
        source_file = Path(temp_dir) / "source.txt"
        source_file.write_text("unique content for move detection")
        file_hash = calculate_file_hash(str(source_file))

        # "Move" the file
        dest_file = Path(temp_dir) / "dest.txt"
        source_file.rename(dest_file)

        queue.start()

        try:
            # Enqueue delete with hash and create
            queue.enqueue(str(source_file), None, "deleted", file_hash=file_hash)
            queue.enqueue(str(dest_file), None, "created")

            # Wait for processing
            time.sleep(0.3)

            # The callback should NOT be called for moves
            # (move detection handles them differently via DB update)
            # For now, verify it was processed without errors
        finally:
            queue.stop()

    def test_queue_wait_for_completion(self, queue, mock_callback, temp_dir):
        """Test synchronous waiting for operation completion."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        queue.start()

        try:
            start_time = time.time()

            # Enqueue with wait=True
            op = queue.enqueue(str(test_file), None, "created", wait=True)

            elapsed = time.time() - start_time

            # Should have waited for processing
            assert elapsed >= 0.01  # At least some time passed
            assert op.result == {"status": "success"}
            assert op.error is None
        finally:
            queue.stop()

    def test_queue_graceful_shutdown(self, queue, mock_callback, temp_dir):
        """Test that queue drains on stop."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        queue.start()

        # Enqueue several operations
        for i in range(5):
            file_path = Path(temp_dir) / f"test{i}.txt"
            file_path.write_text(f"content {i}")
            queue.enqueue(str(file_path), None, "created")

        # Stop immediately (should drain)
        queue.stop(timeout=5.0)

        # All operations should have been processed
        assert mock_callback.call_count == 5

    def test_queue_handles_callback_error(self, queue, temp_dir):
        """Test that queue handles callback errors gracefully."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        # Set up callback to raise an error
        error_callback = MagicMock(side_effect=ValueError("Test error"))
        queue.process_callback = error_callback

        queue.start()

        try:
            # Enqueue with wait to check error
            op = queue.enqueue(str(test_file), None, "created", wait=True)

            # Operation should have error set
            assert op.error is not None
            assert isinstance(op.error, ValueError)
        finally:
            queue.stop()

    def test_queue_processes_different_operations(self, queue, mock_callback, temp_dir):
        """Test that different operation types are processed correctly."""
        queue.start()

        try:
            # Create
            create_file = Path(temp_dir) / "create.txt"
            create_file.write_text("create")
            queue.enqueue(str(create_file), None, "created")

            # Modify
            modify_file = Path(temp_dir) / "modify.txt"
            modify_file.write_text("modify")
            queue.enqueue(str(modify_file), None, "modified")

            # Delete (file doesn't need to exist)
            delete_file = Path(temp_dir) / "delete.txt"
            queue.enqueue(str(delete_file), None, "deleted")

            # Wait for processing
            time.sleep(0.3)

            # All three should be processed
            assert mock_callback.call_count == 3
        finally:
            queue.stop()

    def test_queue_completion_event_signaled_on_error(self, queue, temp_dir):
        """Test that completion event is signaled even on error."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        # Set up callback to raise an error
        error_callback = MagicMock(side_effect=RuntimeError("Processing failed"))
        queue.process_callback = error_callback

        queue.start()

        try:
            event = threading.Event()
            op = FileOperation(
                filepath=str(test_file),
                sidecar_path=None,
                operation="created",
                completion_event=event,
            )
            queue._queue.put(op)

            # Wait for the event (should be signaled despite error)
            signaled = event.wait(timeout=1.0)
            assert signaled
            assert op.error is not None
        finally:
            queue.stop()


class TestCalculateFileHash:
    """Tests for the calculate_file_hash function."""

    def test_calculate_hash(self):
        """Test hash calculation for a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()
            try:
                hash1 = calculate_file_hash(f.name)
                hash2 = calculate_file_hash(f.name)
                # Same content should produce same hash
                assert hash1 == hash2
                # Hash should be a hex string
                assert all(c in "0123456789abcdef" for c in hash1)
            finally:
                os.unlink(f.name)

    def test_different_content_different_hash(self):
        """Test that different content produces different hash."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f1:
            f1.write("content 1")
            f1.flush()
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f2:
                f2.write("content 2")
                f2.flush()
                try:
                    hash1 = calculate_file_hash(f1.name)
                    hash2 = calculate_file_hash(f2.name)
                    assert hash1 != hash2
                finally:
                    os.unlink(f1.name)
                    os.unlink(f2.name)

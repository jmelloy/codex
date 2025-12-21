"""Tests for agent sandbox system."""

import tempfile
from pathlib import Path

import pytest

from core.sandbox import (
    AgentSandbox,
    ChangeType,
    FileChange,
    SandboxManager,
)


class TestFileChange:
    """Test FileChange class."""

    def test_create_file_change(self):
        """Test creating a file change."""
        change = FileChange(
            path="test.txt",
            change_type=ChangeType.CREATE,
            new_content=b"content",
            new_hash="abc123",
        )
        assert change.path == "test.txt"
        assert change.change_type == ChangeType.CREATE
        assert change.new_content == b"content"

    def test_file_change_to_dict(self):
        """Test converting file change to dictionary."""
        change = FileChange(
            path="test.txt", change_type=ChangeType.MODIFY, new_hash="def456"
        )
        data = change.to_dict()
        assert data["path"] == "test.txt"
        assert data["change_type"] == "modify"
        assert "timestamp" in data

    def test_file_change_from_dict(self):
        """Test creating file change from dictionary."""
        data = {
            "path": "test.txt",
            "change_type": "delete",
            "original_hash": "abc123",
            "new_hash": None,
            "timestamp": "2024-01-01T00:00:00",
        }
        change = FileChange.from_dict(data)
        assert change.path == "test.txt"
        assert change.change_type == ChangeType.DELETE


class TestAgentSandbox:
    """Test AgentSandbox class."""

    def test_create_sandbox(self):
        """Test creating a sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("content")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            assert sandbox.exists()
            assert (sandbox / "test.txt").exists()

    def test_create_file_in_sandbox(self):
        """Test creating a file in sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.create_file("new.txt", b"new content")

            assert (sandbox / "new.txt").exists()
            assert (sandbox / "new.txt").read_bytes() == b"new content"
            assert len(agent_sandbox.changes) == 1
            assert agent_sandbox.changes[0].change_type == ChangeType.CREATE

    def test_create_file_that_exists_raises_error(self):
        """Test creating a file that already exists raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "existing.txt").write_text("content")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            with pytest.raises(FileExistsError):
                agent_sandbox.create_file("existing.txt", b"new content")

    def test_modify_file_in_sandbox(self):
        """Test modifying a file in sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("original")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.modify_file("test.txt", b"modified")

            assert (sandbox / "test.txt").read_bytes() == b"modified"
            assert len(agent_sandbox.changes) == 1
            assert agent_sandbox.changes[0].change_type == ChangeType.MODIFY

    def test_modify_nonexistent_file_raises_error(self):
        """Test modifying a nonexistent file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            with pytest.raises(FileNotFoundError):
                agent_sandbox.modify_file("nonexistent.txt", b"content")

    def test_delete_file_in_sandbox(self):
        """Test deleting a file in sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("content")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.delete_file("test.txt")

            assert not (sandbox / "test.txt").exists()
            assert len(agent_sandbox.changes) == 1
            assert agent_sandbox.changes[0].change_type == ChangeType.DELETE

    def test_get_diff_summary(self):
        """Test getting diff summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "modify.txt").write_text("original")
            (source / "delete.txt").write_text("delete me")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.create_file("new.txt", b"new")
            agent_sandbox.modify_file("modify.txt", b"modified")
            agent_sandbox.delete_file("delete.txt")

            summary = agent_sandbox.get_diff_summary()
            assert summary["total_changes"] == 3
            assert summary["created"] == 1
            assert summary["modified"] == 1
            assert summary["deleted"] == 1

    def test_verify_changes_safe(self):
        """Test verifying safe changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("content")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.modify_file("test.txt", b"modified")

            verification = agent_sandbox.verify_changes()
            assert verification["safe"] is True
            assert len(verification["errors"]) == 0

    def test_verify_changes_unsafe(self):
        """Test verifying unsafe changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.create_file("new.txt", b"content")

            # Create the same file in source to make it unsafe
            (source / "new.txt").write_text("conflict")

            verification = agent_sandbox.verify_changes()
            assert verification["safe"] is False
            assert len(verification["errors"]) > 0

    def test_apply_changes(self):
        """Test applying changes to source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("original")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.modify_file("test.txt", b"modified")
            agent_sandbox.create_file("new.txt", b"new content")

            result = agent_sandbox.apply_changes()

            assert result["success"] is True
            assert (source / "test.txt").read_bytes() == b"modified"
            assert (source / "new.txt").read_bytes() == b"new content"

    def test_apply_unsafe_changes_fails(self):
        """Test applying unsafe changes fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.create_file("new.txt", b"content")
            (source / "new.txt").write_text("conflict")

            result = agent_sandbox.apply_changes(force=False)
            assert result["success"] is False

    def test_rollback_changes(self):
        """Test rolling back changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("original")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.modify_file("test.txt", b"modified")
            agent_sandbox.create_file("new.txt", b"new")

            agent_sandbox.rollback()

            assert (sandbox / "test.txt").read_bytes() == b"original"
            assert not (sandbox / "new.txt").exists()
            assert len(agent_sandbox.changes) == 0

    def test_save_and_load_changes(self):
        """Test saving and loading changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("content")

            sandbox = Path(tmpdir) / "sandbox"
            agent_sandbox = AgentSandbox(source, sandbox)
            agent_sandbox.setup()

            agent_sandbox.create_file("new.txt", b"new")
            agent_sandbox.save_changes()

            # Load in new instance
            agent_sandbox2 = AgentSandbox(source, sandbox)
            agent_sandbox2.load_changes()

            assert len(agent_sandbox2.changes) == 1
            assert agent_sandbox2.changes[0].path == "new.txt"


class TestSandboxManager:
    """Test SandboxManager class."""

    def test_create_sandbox_manager(self):
        """Test creating a sandbox manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SandboxManager(Path(tmpdir))
            assert manager.sandboxes_root.exists()

    def test_create_and_delete_sandbox(self):
        """Test creating and deleting a sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()
            (source / "test.txt").write_text("content")

            manager = SandboxManager(Path(tmpdir) / "sandboxes")
            sandbox = manager.create_sandbox("test-sandbox", source)

            assert sandbox.sandbox_path.exists()

            result = manager.delete_sandbox("test-sandbox")
            assert result is True
            assert not sandbox.sandbox_path.exists()

    def test_delete_nonexistent_sandbox(self):
        """Test deleting a nonexistent sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SandboxManager(Path(tmpdir))
            result = manager.delete_sandbox("nonexistent")
            assert result is False

    def test_list_sandboxes(self):
        """Test listing sandboxes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()

            manager = SandboxManager(Path(tmpdir) / "sandboxes")
            manager.create_sandbox("sandbox1", source)
            manager.create_sandbox("sandbox2", source)

            sandboxes = manager.list_sandboxes()
            assert "sandbox1" in sandboxes
            assert "sandbox2" in sandboxes

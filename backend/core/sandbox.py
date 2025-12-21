"""Agent sandbox environment for safe execution.

This module provides a sandboxed environment for agents to operate on
a clone of the filesystem with verify/apply/rollback capabilities.
"""

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChangeType(Enum):
    """Type of filesystem change."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


@dataclass
class FileChange:
    """Represents a change to a file."""

    path: str
    change_type: ChangeType
    original_content: Optional[bytes] = None
    new_content: Optional[bytes] = None
    original_hash: Optional[str] = None
    new_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "change_type": self.change_type.value,
            "original_hash": self.original_hash,
            "new_hash": self.new_hash,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileChange":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            change_type=ChangeType(data["change_type"]),
            original_hash=data.get("original_hash"),
            new_hash=data.get("new_hash"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class AgentSandbox:
    """Sandbox environment for agent operations."""

    def __init__(self, source_path: Path, sandbox_path: Path):
        """Initialize sandbox.

        Args:
            source_path: Path to original filesystem
            sandbox_path: Path to sandbox directory
        """
        self.source_path = Path(source_path).resolve()
        self.sandbox_path = Path(sandbox_path).resolve()
        self.changes: List[FileChange] = []
        self._tracked_files: Set[str] = set()
        self._backup_path = self.sandbox_path / ".sandbox_backup"
        self._changes_file = self.sandbox_path / ".sandbox_changes.json"

    def setup(self) -> None:
        """Setup the sandbox by cloning the source."""
        if self.sandbox_path.exists():
            shutil.rmtree(self.sandbox_path)

        # Clone source to sandbox
        shutil.copytree(
            self.source_path,
            self.sandbox_path,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )

        # Create backup directory
        self._backup_path.mkdir(exist_ok=True)

    def track_file(self, relative_path: str) -> None:
        """Start tracking a file for changes.

        Args:
            relative_path: Path relative to sandbox root
        """
        self._tracked_files.add(relative_path)
        file_path = self.sandbox_path / relative_path

        if file_path.exists():
            # Backup original content
            backup_file = self._backup_path / relative_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_file)

    def create_file(self, relative_path: str, content: bytes) -> None:
        """Create a new file in the sandbox.

        Args:
            relative_path: Path relative to sandbox root
            content: File content
        """
        file_path = self.sandbox_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            raise FileExistsError(f"File already exists: {relative_path}")

        file_path.write_bytes(content)

        change = FileChange(
            path=relative_path,
            change_type=ChangeType.CREATE,
            new_content=content,
            new_hash=self._hash_content(content),
        )
        self.changes.append(change)

    def modify_file(self, relative_path: str, new_content: bytes) -> None:
        """Modify an existing file in the sandbox.

        Args:
            relative_path: Path relative to sandbox root
            new_content: New file content
        """
        file_path = self.sandbox_path / relative_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        # Track if not already tracked
        if relative_path not in self._tracked_files:
            self.track_file(relative_path)

        # Read original content
        original_content = file_path.read_bytes()

        # Write new content
        file_path.write_bytes(new_content)

        change = FileChange(
            path=relative_path,
            change_type=ChangeType.MODIFY,
            original_content=original_content,
            new_content=new_content,
            original_hash=self._hash_content(original_content),
            new_hash=self._hash_content(new_content),
        )
        self.changes.append(change)

    def delete_file(self, relative_path: str) -> None:
        """Delete a file in the sandbox.

        Args:
            relative_path: Path relative to sandbox root
        """
        file_path = self.sandbox_path / relative_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        # Track if not already tracked
        if relative_path not in self._tracked_files:
            self.track_file(relative_path)

        # Read original content
        original_content = file_path.read_bytes()

        # Delete file
        file_path.unlink()

        change = FileChange(
            path=relative_path,
            change_type=ChangeType.DELETE,
            original_content=original_content,
            original_hash=self._hash_content(original_content),
        )
        self.changes.append(change)

    def get_changes(self) -> List[FileChange]:
        """Get list of all changes.

        Returns:
            List of FileChange objects
        """
        return self.changes.copy()

    def get_diff_summary(self) -> Dict[str, Any]:
        """Get a summary of changes.

        Returns:
            Dictionary with change statistics
        """
        summary = {
            "total_changes": len(self.changes),
            "created": 0,
            "modified": 0,
            "deleted": 0,
            "files": [],
        }

        for change in self.changes:
            if change.change_type == ChangeType.CREATE:
                summary["created"] += 1
            elif change.change_type == ChangeType.MODIFY:
                summary["modified"] += 1
            elif change.change_type == ChangeType.DELETE:
                summary["deleted"] += 1

            summary["files"].append(
                {
                    "path": change.path,
                    "type": change.change_type.value,
                    "timestamp": change.timestamp.isoformat(),
                }
            )

        return summary

    def verify_changes(self) -> Dict[str, Any]:
        """Verify that changes are safe to apply.

        Returns:
            Dictionary with verification results
        """
        results = {
            "safe": True,
            "warnings": [],
            "errors": [],
        }

        for change in self.changes:
            source_file = self.source_path / change.path

            if change.change_type == ChangeType.CREATE:
                # Check if file already exists in source
                if source_file.exists():
                    results["errors"].append(
                        f"Cannot create {change.path}: file already exists in source"
                    )
                    results["safe"] = False

            elif change.change_type == ChangeType.MODIFY:
                # Check if file exists and hasn't been modified
                if not source_file.exists():
                    results["errors"].append(
                        f"Cannot modify {change.path}: file doesn't exist in source"
                    )
                    results["safe"] = False
                elif change.original_hash:
                    current_hash = self._hash_file(source_file)
                    if current_hash != change.original_hash:
                        results["warnings"].append(
                            f"File {change.path} has been modified since sandbox creation"
                        )

            elif change.change_type == ChangeType.DELETE:
                # Check if file still exists
                if not source_file.exists():
                    results["warnings"].append(
                        f"File {change.path} already deleted in source"
                    )

        return results

    def apply_changes(self, force: bool = False) -> Dict[str, Any]:
        """Apply changes to the source filesystem.

        Args:
            force: Apply changes even if verification fails

        Returns:
            Dictionary with application results
        """
        # Verify first
        verification = self.verify_changes()

        if not verification["safe"] and not force:
            return {
                "success": False,
                "message": "Changes are not safe to apply",
                "verification": verification,
            }

        applied = []
        failed = []

        for change in self.changes:
            try:
                target_file = self.source_path / change.path

                if change.change_type == ChangeType.CREATE:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_bytes(change.new_content)
                    applied.append(change.path)

                elif change.change_type == ChangeType.MODIFY:
                    target_file.write_bytes(change.new_content)
                    applied.append(change.path)

                elif change.change_type == ChangeType.DELETE:
                    target_file.unlink()
                    applied.append(change.path)

            except Exception as e:
                failed.append({"path": change.path, "error": str(e)})

        return {
            "success": len(failed) == 0,
            "applied": applied,
            "failed": failed,
            "verification": verification,
        }

    def rollback(self) -> None:
        """Rollback all changes in the sandbox."""
        for change in reversed(self.changes):
            file_path = self.sandbox_path / change.path
            backup_file = self._backup_path / change.path

            try:
                if change.change_type == ChangeType.CREATE:
                    # Remove created file
                    if file_path.exists():
                        file_path.unlink()

                elif change.change_type == ChangeType.MODIFY:
                    # Restore from backup
                    if backup_file.exists():
                        shutil.copy2(backup_file, file_path)

                elif change.change_type == ChangeType.DELETE:
                    # Restore from backup
                    if backup_file.exists():
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup_file, file_path)

            except Exception:
                # Continue rolling back other changes
                pass

        self.changes.clear()

    def cleanup(self) -> None:
        """Clean up sandbox and remove all files."""
        if self.sandbox_path.exists():
            shutil.rmtree(self.sandbox_path)

    def save_changes(self) -> None:
        """Save changes to disk for persistence."""
        data = {"changes": [change.to_dict() for change in self.changes]}
        with open(self._changes_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_changes(self) -> None:
        """Load changes from disk."""
        if self._changes_file.exists():
            with open(self._changes_file, "r") as f:
                data = json.load(f)
                self.changes = [FileChange.from_dict(c) for c in data.get("changes", [])]

    def _hash_content(self, content: bytes) -> str:
        """Calculate hash of content.

        Args:
            content: Content bytes

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(content).hexdigest()

    def _hash_file(self, file_path: Path) -> str:
        """Calculate hash of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash
        """
        return self._hash_content(file_path.read_bytes())


class SandboxManager:
    """Manager for agent sandboxes."""

    def __init__(self, sandboxes_root: Path):
        """Initialize sandbox manager.

        Args:
            sandboxes_root: Root directory for all sandboxes
        """
        self.sandboxes_root = Path(sandboxes_root)
        self.sandboxes_root.mkdir(parents=True, exist_ok=True)

    def create_sandbox(self, sandbox_id: str, source_path: Path) -> AgentSandbox:
        """Create a new sandbox.

        Args:
            sandbox_id: Unique sandbox identifier
            source_path: Path to clone

        Returns:
            AgentSandbox instance
        """
        sandbox_path = self.sandboxes_root / sandbox_id
        sandbox = AgentSandbox(source_path, sandbox_path)
        sandbox.setup()
        return sandbox

    def get_sandbox(self, sandbox_id: str) -> Optional[AgentSandbox]:
        """Get an existing sandbox.

        Args:
            sandbox_id: Sandbox identifier

        Returns:
            AgentSandbox or None if not found
        """
        sandbox_path = self.sandboxes_root / sandbox_id
        if not sandbox_path.exists():
            return None

        # We need the source path - this is a limitation
        # In practice, we'd store metadata about sandboxes
        return None  # Placeholder

    def delete_sandbox(self, sandbox_id: str) -> bool:
        """Delete a sandbox.

        Args:
            sandbox_id: Sandbox identifier

        Returns:
            True if deleted, False if not found
        """
        sandbox_path = self.sandboxes_root / sandbox_id
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
            return True
        return False

    def list_sandboxes(self) -> List[str]:
        """List all sandbox IDs.

        Returns:
            List of sandbox IDs
        """
        return [d.name for d in self.sandboxes_root.iterdir() if d.is_dir()]

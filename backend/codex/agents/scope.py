"""Scope guard for enforcing agent access boundaries."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import PurePath
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from codex.db.models import Agent

ActionType = Literal["read", "write", "create", "delete", "execute"]


class ScopeViolation(Exception):
    """Raised when an agent attempts an out-of-scope action."""

    def __init__(self, action: ActionType, target: str, reason: str):
        self.action = action
        self.target = target
        self.reason = reason
        super().__init__(reason)


class ScopeGuard:
    """Enforces agent access boundaries.

    All agent operations pass through the ScopeGuard before execution.
    It checks notebook access, path patterns, file type restrictions,
    and capability flags.
    """

    def __init__(self, agent: Agent, notebook_id: int | None = None):
        self.agent = agent
        self.scope = agent.scope or {}
        self.notebook_id = notebook_id

    def check_notebook_access(self, notebook_slug: str) -> bool:
        """Verify agent can access this notebook."""
        allowed = self.scope.get("notebooks", ["*"])
        if "*" in allowed:
            return True
        return notebook_slug in allowed

    def check_path_access(self, path: str, action: ActionType) -> bool:
        """Verify agent can perform action on this path."""
        # Check action permission
        action_map: dict[str, bool] = {
            "read": self.agent.can_read,
            "write": self.agent.can_write,
            "create": self.agent.can_create,
            "delete": self.agent.can_delete,
            "execute": self.agent.can_execute_code,
        }
        if not action_map.get(action, False):
            return False

        # Prevent path traversal
        path_obj = PurePath(path)
        if ".." in path_obj.parts:
            return False

        # Check path against folder patterns
        folders = self.scope.get("folders", ["*"])
        if "*" not in folders:
            matched = False
            for pattern in folders:
                if fnmatch(str(path_obj), pattern) or fnmatch(str(path_obj.parent), pattern):
                    matched = True
                    break
            if not matched:
                return False

        # Check file type restrictions
        file_types = self.scope.get("file_types", ["*"])
        if "*" not in file_types:
            if not any(fnmatch(path_obj.name, ft) for ft in file_types):
                return False

        return True

    def validate_or_raise(self, action: ActionType, target: str) -> None:
        """Validate action or raise ScopeViolation."""
        if not self.check_path_access(target, action):
            raise ScopeViolation(
                action=action,
                target=target,
                reason=f"Agent '{self.agent.name}' not permitted to {action} '{target}'",
            )

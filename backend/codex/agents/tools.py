"""Tool router for mapping agent intentions to Codex operations."""

from __future__ import annotations

import logging
import os
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .scope import ScopeGuard, ScopeViolation

if TYPE_CHECKING:
    from codex.db.models import AgentSession

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """Schema for a tool available to agents."""

    name: str
    description: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False


class ToolRouter:
    """Routes agent tool calls to Codex operations.

    All tool calls pass through the ScopeGuard for permission checks
    before executing the underlying file/search operations.
    """

    def __init__(
        self,
        scope_guard: ScopeGuard,
        session: AgentSession,
        notebook_path: str,
    ):
        self.scope_guard = scope_guard
        self.session = session
        self.notebook_path = notebook_path
        self._action_logs: list[dict[str, Any]] = []

    def get_tool_definitions(self) -> list[ToolDefinition]:
        """Return tools available based on agent scope."""
        tools: list[ToolDefinition] = []

        if self.scope_guard.agent.can_read:
            tools.extend([
                ToolDefinition(
                    name="read_file",
                    description="Read the contents of a file in the notebook",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to notebook root"},
                        },
                        "required": ["path"],
                    },
                ),
                ToolDefinition(
                    name="list_files",
                    description="List files in a directory within the notebook",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path relative to notebook root",
                                "default": "/",
                            },
                            "pattern": {"type": "string", "description": "Glob pattern filter (e.g. '*.md')"},
                        },
                    },
                ),
                ToolDefinition(
                    name="search_content",
                    description="Search for text content across files in the notebook",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query text"},
                        },
                        "required": ["query"],
                    },
                ),
                ToolDefinition(
                    name="get_file_metadata",
                    description="Get metadata (size, modified time, properties) for a file",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to notebook root"},
                        },
                        "required": ["path"],
                    },
                ),
            ])

        if self.scope_guard.agent.can_write:
            tools.append(
                ToolDefinition(
                    name="write_file",
                    description="Write or update the contents of a file",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to notebook root"},
                            "content": {"type": "string", "description": "The content to write"},
                        },
                        "required": ["path", "content"],
                    },
                    requires_confirmation=True,
                )
            )

        if self.scope_guard.agent.can_create:
            tools.append(
                ToolDefinition(
                    name="create_file",
                    description="Create a new file in the notebook",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to notebook root"},
                            "content": {"type": "string", "description": "Initial file content", "default": ""},
                        },
                        "required": ["path"],
                    },
                    requires_confirmation=True,
                )
            )

        if self.scope_guard.agent.can_delete:
            tools.append(
                ToolDefinition(
                    name="delete_file",
                    description="Delete a file from the notebook",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to notebook root"},
                        },
                        "required": ["path"],
                    },
                    requires_confirmation=True,
                )
            )

        return tools

    def get_tool_definitions_for_litellm(self) -> list[dict[str, Any]]:
        """Return tool definitions in OpenAI function-calling format for LiteLLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.get_tool_definitions()
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Execute a tool call with scope validation."""
        tool_map = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "list_files": self._list_files,
            "search_content": self._search_content,
            "get_file_metadata": self._get_file_metadata,
            "create_file": self._create_file,
            "delete_file": self._delete_file,
        }

        if tool_name not in tool_map:
            return {"error": f"Unknown tool: {tool_name}"}

        # Check confirmation for tools that require it
        tool_def = next((t for t in self.get_tool_definitions() if t.name == tool_name), None)
        if tool_def and tool_def.requires_confirmation and not confirmed:
            return {
                "requires_confirmation": True,
                "action": tool_name,
                "arguments": arguments,
            }

        start_time = time.monotonic()
        try:
            result = await tool_map[tool_name](**arguments)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            self._action_logs.append({
                "action_type": tool_name,
                "target_path": arguments.get("path"),
                "input_summary": str(arguments)[:500],
                "output_summary": str(result)[:500],
                "was_allowed": True,
                "execution_time_ms": elapsed_ms,
            })
            return result
        except ScopeViolation as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            self._action_logs.append({
                "action_type": tool_name,
                "target_path": arguments.get("path"),
                "input_summary": str(arguments)[:500],
                "output_summary": str(e),
                "was_allowed": False,
                "execution_time_ms": elapsed_ms,
            })
            return {"error": str(e), "scope_violation": True}
        except Exception as e:
            logger.exception(f"Tool execution error: {tool_name}")
            return {"error": str(e)}

    def get_action_logs(self) -> list[dict[str, Any]]:
        """Return accumulated action logs for persistence."""
        return list(self._action_logs)

    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path to an absolute path within the notebook."""
        # Strip leading slash for joining
        clean = path.lstrip("/")
        resolved = (Path(self.notebook_path) / clean).resolve()
        # Ensure the resolved path is within the notebook directory
        notebook_resolved = Path(self.notebook_path).resolve()
        if not str(resolved).startswith(str(notebook_resolved)):
            raise ScopeViolation(
                action="read",
                target=path,
                reason=f"Path '{path}' resolves outside notebook directory",
            )
        return resolved

    async def _read_file(self, path: str) -> dict[str, Any]:
        self.scope_guard.validate_or_raise("read", path)
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return {"error": f"File not found: {path}"}
        if not resolved.is_file():
            return {"error": f"Not a file: {path}"}
        try:
            content = resolved.read_text(encoding="utf-8")
            return {"path": path, "content": content, "size": len(content)}
        except UnicodeDecodeError:
            return {"error": f"Cannot read binary file: {path}"}

    async def _write_file(self, path: str, content: str) -> dict[str, Any]:
        self.scope_guard.validate_or_raise("write", path)
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return {"error": f"File not found: {path}. Use create_file to make new files."}
        resolved.write_text(content, encoding="utf-8")
        # Track modified files on the session
        if hasattr(self.session, "files_modified") and self.session.files_modified is not None:
            if path not in self.session.files_modified:
                self.session.files_modified = [*self.session.files_modified, path]
        return {"path": path, "written": len(content)}

    async def _create_file(self, path: str, content: str = "") -> dict[str, Any]:
        self.scope_guard.validate_or_raise("create", path)
        resolved = self._resolve_path(path)
        if resolved.exists():
            return {"error": f"File already exists: {path}. Use write_file to update."}
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        if hasattr(self.session, "files_modified") and self.session.files_modified is not None:
            if path not in self.session.files_modified:
                self.session.files_modified = [*self.session.files_modified, path]
        return {"path": path, "created": True, "size": len(content)}

    async def _delete_file(self, path: str) -> dict[str, Any]:
        self.scope_guard.validate_or_raise("delete", path)
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return {"error": f"File not found: {path}"}
        resolved.unlink()
        return {"path": path, "deleted": True}

    async def _list_files(self, path: str = "/", pattern: str | None = None) -> dict[str, Any]:
        self.scope_guard.validate_or_raise("read", path)
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return {"error": f"Directory not found: {path}"}
        if not resolved.is_dir():
            return {"error": f"Not a directory: {path}"}

        files: list[dict[str, Any]] = []
        notebook_root = Path(self.notebook_path).resolve()
        for entry in sorted(resolved.iterdir()):
            # Skip hidden files/dirs
            if entry.name.startswith("."):
                continue
            rel_path = str(entry.relative_to(notebook_root))
            if pattern and not fnmatch(entry.name, pattern):
                continue
            files.append({
                "name": entry.name,
                "path": rel_path,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
            })
        return {"path": path, "files": files}

    async def _search_content(self, query: str) -> dict[str, Any]:
        """Simple file content search within the notebook."""
        self.scope_guard.validate_or_raise("read", "/")
        notebook_root = Path(self.notebook_path).resolve()
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for root, dirs, filenames in os.walk(notebook_root):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in filenames:
                if fname.startswith("."):
                    continue
                fpath = Path(root) / fname
                rel_path = str(fpath.relative_to(notebook_root))
                try:
                    content = fpath.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        # Find matching lines
                        matches = []
                        for i, line in enumerate(content.splitlines(), 1):
                            if query_lower in line.lower():
                                matches.append({"line": i, "text": line.strip()[:200]})
                                if len(matches) >= 5:
                                    break
                        results.append({"path": rel_path, "matches": matches})
                        if len(results) >= 20:
                            break
                except (UnicodeDecodeError, PermissionError):
                    continue
            if len(results) >= 20:
                break

        return {"query": query, "results": results, "total": len(results)}

    async def _get_file_metadata(self, path: str) -> dict[str, Any]:
        self.scope_guard.validate_or_raise("read", path)
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return {"error": f"File not found: {path}"}
        stat = resolved.stat()
        return {
            "path": path,
            "name": resolved.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_dir": resolved.is_dir(),
            "suffix": resolved.suffix,
        }

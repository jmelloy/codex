"""Database models for Codex.

This module re-exports all models from submodules for backward compatibility.
Models are organized into two categories:

System models (backend/db/models/system.py):
  - User, Workspace, WorkspacePermission, Task, Notebook
  - Plugin, PluginConfig, PluginSecret, PluginAPILog
  - Stored in the system database (codex_system.db)

Notebook models (backend/db/models/notebook.py):
  - FileMetadata, Tag, FileTag, SearchIndex
  - Stored in per-notebook databases (notebook.db)
"""

# Re-export shared utilities
from .base import utc_now

# Re-export notebook models
from .notebook import (
    FileMetadata,
    FileTag,
    SearchIndex,
    Tag,
)

# Re-export system models
from .system import (
    Notebook,
    Plugin,
    PluginAPILog,
    PluginConfig,
    PluginSecret,
    Task,
    User,
    Workspace,
    WorkspacePermission,
)

__all__ = [
    # Utilities
    "utc_now",
    # System models
    "User",
    "Workspace",
    "WorkspacePermission",
    "Task",
    "Notebook",
    "Plugin",
    "PluginConfig",
    "PluginSecret",
    "PluginAPILog",
    # Notebook models
    "FileMetadata",
    "Tag",
    "FileTag",
    "SearchIndex",
]

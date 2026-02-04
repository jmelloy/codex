"""System database models.

These models are stored in the system database (codex_system.db):
- User: User accounts for authentication
- Workspace: Workspaces for organizing notebooks
- WorkspacePermission: Permission mapping between users and workspaces
- Task: Tasks for agent work
- Notebook: Notebook metadata
- Plugin: Plugin registry
- PluginConfig: Plugin configurations per workspace
- PluginSecret: Secure plugin secrets (encrypted)
- PluginAPILog: Plugin API request logs
- FileEvent: Event queue for file operations
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Index, Text, UniqueConstraint
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from .base import utc_now


class FileEventType(str, Enum):
    """Types of file events."""

    CREATE = "create"
    UPDATE = "update"
    MOVE = "move"
    DELETE = "delete"
    SYNC = "sync"  # Watcher-detected external change


class FileEventStatus(str, Enum):
    """Status of file events."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"  # Replaced by newer event


class User(SQLModel, table=True):
    """User accounts for authentication."""

    __tablename__ = "users"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    theme_setting: str | None = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    workspaces: list["Workspace"] = Relationship(back_populates="owner")


class Workspace(SQLModel, table=True):
    """Workspace for organizing notebooks and files."""

    __tablename__ = "workspaces"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("owner_id", "slug", name="uq_workspaces_owner_slug"),
        {"sqlite_autoincrement": True},
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(index=True)  # URL-safe identifier, unique per owner
    path: str = Field(unique=True)  # Filesystem path
    owner_id: int = Field(foreign_key="users.id")
    theme_setting: str | None = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    permissions: list["WorkspacePermission"] = Relationship(back_populates="workspace")
    notebooks: list["Notebook"] = Relationship(back_populates="workspace")


class WorkspacePermission(SQLModel, table=True):
    """Permission mapping between users and workspaces."""

    __tablename__ = "workspace_permissions"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    user_id: int = Field(foreign_key="users.id")
    permission_level: str = Field(default="read")  # read, write, admin
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    workspace: Workspace = Relationship(back_populates="permissions")


class Task(SQLModel, table=True):
    """Tasks for agent work."""

    __tablename__ = "tasks"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    title: str
    description: str | None = None
    status: str = Field(default="pending")  # pending, in_progress, completed, failed
    assigned_to: str | None = None  # Agent identifier
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class Notebook(SQLModel, table=True):
    """Notebook metadata (stored in system database)."""

    __tablename__ = "notebooks"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    name: str = Field(index=True)
    slug: str = Field(index=True)  # URL-safe identifier (unique per workspace)
    path: str = Field(index=True)  # Relative path from workspace
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    workspace: Workspace = Relationship(back_populates="notebooks")


class Plugin(SQLModel, table=True):
    """Plugin registry table."""

    __tablename__ = "plugins"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    plugin_id: str = Field(unique=True, index=True)
    name: str
    version: str
    type: str  # 'view', 'theme', 'integration'
    enabled: bool = Field(default=True)
    installed_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    manifest: dict = Field(default={}, sa_column=Column(JSON))  # Full plugin manifest

    # Relationships
    configs: list["PluginConfig"] = Relationship(back_populates="plugin")


class PluginConfig(SQLModel, table=True):
    """Plugin configurations per workspace."""

    __tablename__ = "plugin_configs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    enabled: bool = Field(default=True)  # Workspace-level enable/disable
    config: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    plugin: Plugin = Relationship(back_populates="configs")


class NotebookPluginConfig(SQLModel, table=True):
    """Plugin configurations per notebook (overrides workspace settings)."""

    __tablename__ = "notebook_plugin_configs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    notebook_id: int = Field(foreign_key="notebooks.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    enabled: bool = Field(default=True)  # Notebook-level enable/disable (overrides workspace)
    config: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PluginSecret(SQLModel, table=True):
    """Secure plugin secrets (encrypted)."""

    __tablename__ = "plugin_secrets"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    key: str
    encrypted_value: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PluginAPILog(SQLModel, table=True):
    """Plugin API request logs (for rate limiting and debugging)."""

    __tablename__ = "plugin_api_logs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    endpoint_id: str
    timestamp: datetime = Field(default_factory=utc_now, index=True)
    status_code: int | None = None
    error: str | None = None


class IntegrationArtifact(SQLModel, table=True):
    """Cached API responses for integration blocks.

    This table stores metadata for cached integration API responses. The actual
    data is stored in the filesystem at the artifact_path location. This allows
    for more scalable storage of large API responses.

    Files are stored at: {workspace_path}/.codex/artifacts/{plugin_id}/{hash}.{ext}
    where ext is determined by content_type (json, html, txt, bin, etc.)
    """

    __tablename__ = "integration_artifacts"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    block_type: str = Field(index=True)  # e.g., "weather", "github-issue"
    parameters_hash: str = Field(index=True)  # Hash of request parameters for cache key
    artifact_path: str  # Relative path to artifact file within workspace
    content_type: str = Field(default="application/json")  # MIME type of the artifact
    fetched_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None  # Optional expiration time for cache


class FileEvent(SQLModel, table=True):
    """Event queue for file operations.

    This table stores file operation events for async processing by workers.
    Events are processed in order by notebook, enabling batched git commits
    and eliminating race conditions between API endpoints and watchers.
    """

    __tablename__ = "file_events"  # type: ignore[assignment]
    __table_args__ = (
        Index("ix_file_events_notebook_status", "notebook_id", "status"),
        Index("ix_file_events_correlation", "correlation_id"),
        Index("ix_file_events_created_at", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    notebook_id: int = Field(foreign_key="notebooks.id", index=True)

    # Event type and status
    event_type: str = Field(index=True)  # FileEventType value
    status: str = Field(default=FileEventStatus.PENDING.value)  # FileEventStatus value

    # Operation details (JSON serialized)
    # Examples:
    # CREATE: {"path": "/notes/foo.md", "content": "...", "metadata": {...}}
    # UPDATE: {"path": "/notes/foo.md", "content": "...", "metadata": {...}}
    # MOVE:   {"source_path": "/notes/foo.md", "dest_path": "/archive/foo.md"}
    # DELETE: {"path": "/notes/foo.md", "is_directory": false}
    # SYNC:   {"path": "/notes/foo.md", "event": "modified"}
    operation: str = Field(sa_column=Column(Text))

    # Correlation for multi-event operations (e.g., folder move)
    correlation_id: str | None = Field(default=None, index=True)
    sequence: int = Field(default=0)  # Order within correlation group

    # Tracking
    created_at: datetime = Field(default_factory=utc_now)
    processed_at: datetime | None = None

    # Error handling
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    retry_count: int = Field(default=0)

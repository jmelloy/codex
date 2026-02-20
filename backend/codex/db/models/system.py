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
"""

from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from .base import utc_now

# All datetime columns must use timezone=True so PostgreSQL uses TIMESTAMPTZ
TZDateTime = DateTime(timezone=True)


class User(SQLModel, table=True):
    """User accounts for authentication."""

    __tablename__ = "users"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    theme_setting: str | None = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

    # Relationships
    workspaces: list["Workspace"] = Relationship(back_populates="owner")


class Workspace(SQLModel, table=True):
    """Workspace for organizing notebooks and files."""

    __tablename__ = "workspaces"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("owner_id", "slug", name="uq_workspaces_owner_slug"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(index=True)  # URL-safe identifier, unique per owner
    path: str = Field(unique=True)  # Filesystem path
    owner_id: int = Field(foreign_key="users.id")
    theme_setting: str | None = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    permissions: list["WorkspacePermission"] = Relationship(back_populates="workspace")
    notebooks: list["Notebook"] = Relationship(back_populates="workspace")
    agents: list["Agent"] = Relationship(back_populates="workspace")


class WorkspacePermission(SQLModel, table=True):
    """Permission mapping between users and workspaces."""

    __tablename__ = "workspace_permissions"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    user_id: int = Field(foreign_key="users.id")
    permission_level: str = Field(default="read")  # read, write, admin
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

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
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    completed_at: datetime | None = Field(default=None, sa_type=TZDateTime)


class Notebook(SQLModel, table=True):
    """Notebook metadata (stored in system database)."""

    __tablename__ = "notebooks"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    name: str = Field(index=True)
    slug: str = Field(index=True)  # URL-safe identifier (unique per workspace)
    path: str = Field(index=True)  # Relative path from workspace
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

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
    installed_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
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
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

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
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)


class PluginSecret(SQLModel, table=True):
    """Secure plugin secrets (encrypted)."""

    __tablename__ = "plugin_secrets"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    key: str
    encrypted_value: str
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)


class PluginAPILog(SQLModel, table=True):
    """Plugin API request logs (for rate limiting and debugging)."""

    __tablename__ = "plugin_api_logs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    endpoint_id: str
    timestamp: datetime = Field(default_factory=utc_now, index=True, sa_type=TZDateTime)
    status_code: int | None = None
    error: str | None = None


class Agent(SQLModel, table=True):
    """AI agent configuration for a workspace."""

    __tablename__ = "agents"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    name: str = Field(max_length=100)
    description: str | None = None
    provider: str  # "openai", "anthropic", "ollama", or any litellm provider
    model: str  # e.g. "gpt-4o", "claude-sonnet-4-20250514", "ollama/llama3"

    # Scope configuration (JSON)
    scope: dict = Field(default={}, sa_column=Column(JSON))
    # Example: {
    #   "notebooks": ["*"] or ["notebook-slug-1"],
    #   "folders": ["/experiments/*", "/drafts"],
    #   "file_types": ["*.md", "*.py"],
    #   "operations": ["read", "write", "create", "delete"]
    # }

    # Capability flags
    can_read: bool = Field(default=True)
    can_write: bool = Field(default=False)
    can_create: bool = Field(default=False)
    can_delete: bool = Field(default=False)
    can_execute_code: bool = Field(default=False)
    can_access_integrations: bool = Field(default=False)

    # Rate limiting
    max_requests_per_hour: int = Field(default=100)
    max_tokens_per_request: int = Field(default=4000)

    # Status
    is_active: bool = Field(default=True)
    system_prompt: str | None = None
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

    # Relationships
    workspace: Workspace = Relationship(back_populates="agents")
    credentials: list["AgentCredential"] = Relationship(back_populates="agent")
    sessions: list["AgentSession"] = Relationship(back_populates="agent")


class AgentCredential(SQLModel, table=True):
    """Encrypted storage for agent API keys."""

    __tablename__ = "agent_credentials"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    key_name: str  # "api_key", "organization_id", etc.
    encrypted_value: str  # Fernet-encrypted
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

    # Relationships
    agent: Agent = Relationship(back_populates="credentials")


class AgentSession(SQLModel, table=True):
    """Active or historical agent execution session."""

    __tablename__ = "agent_sessions"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    task_id: int | None = Field(default=None, foreign_key="tasks.id")
    user_id: int = Field(foreign_key="users.id")

    status: str = Field(default="pending")  # pending, running, completed, failed, cancelled
    context: dict = Field(default={}, sa_column=Column(JSON))  # Conversation state

    # Metrics
    tokens_used: int = Field(default=0)
    api_calls_made: int = Field(default=0)
    files_modified: list = Field(default=[], sa_column=Column(JSON))

    started_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    completed_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    error_message: str | None = None

    # Relationships
    agent: Agent = Relationship(back_populates="sessions")


class AgentActionLog(SQLModel, table=True):
    """Audit log for all agent actions."""

    __tablename__ = "agent_action_logs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="agent_sessions.id", index=True)

    action_type: str  # "file_read", "file_write", "api_call", etc.
    target_path: str | None = None  # File/folder path if applicable
    input_summary: str | None = None  # Truncated input
    output_summary: str | None = None  # Truncated output

    was_allowed: bool = Field(default=True)  # Did scope guard permit this?
    execution_time_ms: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)


class PersonalAccessToken(SQLModel, table=True):
    """Personal access tokens for API authentication.

    Tokens are prefixed with 'cdx_' for identification. The token_hash stores
    a SHA-256 hash of the full token; the plain token is only shown at creation.
    """

    __tablename__ = "personal_access_tokens"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str  # Human-readable label, e.g. "pre-commit hook"
    token_hash: str = Field(unique=True, index=True)  # SHA-256 of the full token
    token_prefix: str  # First 8 chars of the token for identification
    scopes: str | None = None  # Comma-separated scopes, e.g. "snippets:write"
    workspace_id: int | None = Field(default=None, foreign_key="workspaces.id")  # Optional scope to workspace
    notebook_id: int | None = Field(default=None, foreign_key="notebooks.id")  # Optional scope to notebook
    last_used_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    expires_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

    # Relationships
    user: User = Relationship()


class OAuthConnection(SQLModel, table=True):
    """OAuth connections linking users to external providers (e.g., Google).

    Stores encrypted access/refresh tokens for each provider connection.
    """

    __tablename__ = "oauth_connections"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    provider: str = Field(index=True)  # "google", etc.
    provider_user_id: str | None = None  # External user ID from provider
    provider_email: str | None = None  # Email from the provider
    access_token: str  # Encrypted access token
    refresh_token: str | None = None  # Encrypted refresh token
    token_expires_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    scopes: str | None = None  # Comma-separated OAuth scopes granted
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)

    # Relationships
    user: User = Relationship()


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
    fetched_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    expires_at: datetime | None = Field(default=None, sa_type=TZDateTime)  # Optional expiration time for cache

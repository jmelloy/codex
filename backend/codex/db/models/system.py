"""System database models.

These models are stored in the system database (codex_system.db):
- User: User accounts for authentication
- Workspace: Workspaces for organizing notebooks
- WorkspacePermission: Permission mapping between users and workspaces
- Organization: An organization grouping principals via OrgMembership
- OrgMembership: Role-based membership of a principal (human or bot) in an org
- Task: Tasks for agent work
- Notebook: Notebook metadata
- Comment: Threaded comments anchored to a block ULID
- CommentMention: @handle mentions parsed from a comment at post time
- Event: Append-only event outbox for notification fanout
- Notification: Per-recipient delivery record for an Event
- WorkspaceWatch: Per-user opt-in/mute notification preference for a workspace
- Plugin: Plugin registry
- PluginConfig: Plugin configurations per workspace
- PluginSecret: Secure plugin secrets (encrypted)
- PluginAPILog: Plugin API request logs
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from pydantic import model_validator
from sqlalchemy import DateTime, Index, UniqueConstraint, text
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from .base import utc_now

# Use timezone-aware datetime columns for consistent UTC timestamp handling.
TZDateTime = DateTime(timezone=True)


class UserKind(StrEnum):
    """Distinguishes human users from bot service accounts (issue #533)."""

    HUMAN = "human"
    BOT = "bot"


class User(SQLModel, table=True):
    """User accounts for authentication.

    A user is either a human (authenticates via password + JWT) or a bot
    service account (authenticates exclusively via PAT, no password). Both
    kinds are "principals": grantable in `WorkspacePermission` and rendered
    anywhere a human is, with `is_bot` driving the bot badge (issue #533).
    """

    __tablename__ = "users"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str | None = None  # Null for bots: they never have a password.
    kind: str = Field(default=UserKind.HUMAN.value, index=True)  # "human" | "bot"
    display_name: str | None = None
    avatar_url: str | None = None
    # Null for humans. Once orgs land, this points at the owning org; there's no
    # orgs table yet so it isn't a FK (issue #533: "org admin once orgs land").
    bot_owner_org_id: str | None = None
    is_active: bool = Field(default=True)
    theme_setting: str | None = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    workspaces: list["Workspace"] = Relationship(back_populates="owner")
    agents: list["Agent"] = Relationship(back_populates="principal")

    @property
    def is_bot(self) -> bool:
        return self.kind == UserKind.BOT.value

    @model_validator(mode="after")
    def _enforce_bot_has_no_password(self) -> "User":
        if self.kind == UserKind.BOT.value and self.hashed_password:
            raise ValueError("Bot accounts cannot have a password hash; they authenticate via PAT only")
        return self


class Workspace(SQLModel, table=True):
    """Workspace for organizing notebooks and files.

    `org_id` is null for personal workspaces (today's behavior, unchanged); when set,
    the workspace belongs to that org and slug uniqueness scopes to (org_id, slug)
    instead of (owner_id, slug) (issue #538, design doc §2.2/§2.3). Both partial
    unique indexes below live on the same `slug` column, split by whether org_id is
    null, so personal and org workspaces never contend for the same uniqueness scope.
    """

    __tablename__ = "workspaces"  # type: ignore[assignment]
    __table_args__ = (
        Index(
            "uq_workspaces_owner_slug",
            "owner_id",
            "slug",
            unique=True,
            sqlite_where=text("org_id IS NULL"),
            postgresql_where=text("org_id IS NULL"),
        ),
        Index(
            "uq_workspaces_org_slug",
            "org_id",
            "slug",
            unique=True,
            sqlite_where=text("org_id IS NOT NULL"),
            postgresql_where=text("org_id IS NOT NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(index=True)  # URL-safe identifier, unique per owner (personal) or per org
    path: str = Field(unique=True)  # Filesystem path
    owner_id: int = Field(foreign_key="users.id")
    # Null = personal workspace. Set = org workspace; slug uniqueness moves to (org_id, slug).
    org_id: int | None = Field(default=None, foreign_key="organizations.id", index=True)
    # Effective permission level for an org "member" role with no explicit grant (issue #538,
    # design doc §2.3: "workspace default (configurable, default read)"). Irrelevant for
    # personal workspaces. Org owner/admin always get admin; guest always needs an explicit grant.
    org_member_default_level: str = Field(default="read")
    theme_setting: str | None = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    organization: Optional["Organization"] = Relationship(back_populates="workspaces")
    permissions: list["WorkspacePermission"] = Relationship(back_populates="workspace")
    notebooks: list["Notebook"] = Relationship(back_populates="workspace")
    agents: list["Agent"] = Relationship(back_populates="workspace")


class WorkspacePermission(SQLModel, table=True):
    """Permission mapping between users and workspaces."""

    __tablename__ = "workspace_permissions"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    user_id: int = Field(foreign_key="users.id")
    permission_level: str = Field(default="read")  # read, comment, write, admin
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    workspace: Workspace = Relationship(back_populates="permissions")


class OrgRole(StrEnum):
    """Role a principal holds within an organization (issue #537, design doc §2.2).

    Ranked lowest to highest: guest < member < admin < owner. Role-gated
    membership management lives in `codex.core.org_permissions`, not here.
    """

    GUEST = "guest"
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


class Organization(SQLModel, table=True):
    """An organization grouping principals (humans and bots) via `OrgMembership`."""

    __tablename__ = "organizations"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    memberships: list["OrgMembership"] = Relationship(back_populates="organization")
    workspaces: list["Workspace"] = Relationship(back_populates="organization")


class OrgMembership(SQLModel, table=True):
    """A principal's (human or bot) role-based membership in an organization."""

    __tablename__ = "org_memberships"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("org_id", "principal_id", name="uq_org_memberships_org_principal"),)

    id: int | None = Field(default=None, primary_key=True)
    org_id: int = Field(foreign_key="organizations.id", index=True)
    principal_id: int = Field(foreign_key="users.id", index=True)
    role: str = Field(default=OrgRole.MEMBER.value)  # "owner" | "admin" | "member" | "guest"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    organization: Organization = Relationship(back_populates="memberships")
    principal: User = Relationship()


class Task(SQLModel, table=True):
    """Tasks for agent work."""

    __tablename__ = "tasks"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    title: str
    description: str | None = None
    status: str = Field(default="pending")  # pending, in_progress, completed, failed
    task_type: str | None = None  # e.g. "zip_import"
    assigned_to: str | None = None  # Agent identifier
    job_id: str | None = None  # ARQ job identifier for background execution
    job_type: str = Field(default="agent")  # Job type for generic dispatch
    task_metadata: str | None = None  # JSON-encoded task-specific context
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class Notebook(SQLModel, table=True):
    """Notebook metadata (stored in system database)."""

    __tablename__ = "notebooks"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    name: str = Field(index=True)
    slug: str = Field(index=True)  # URL-safe identifier (unique per workspace)
    path: str = Field(index=True)  # Relative path from workspace
    description: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

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
    installed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    manifest: dict = Field(default={}, sa_column=Column(JSON))  # Full plugin manifest

    # Relationships
    configs: list["PluginConfig"] = Relationship(back_populates="plugin")


class PluginConfig(SQLModel, table=True):
    """Plugin configurations per workspace."""

    __tablename__ = "plugin_configs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    version: str | None = Field(default=None)  # Pinned plugin version (None = latest)
    enabled: bool = Field(default=True)  # Workspace-level enable/disable
    config: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    plugin: Plugin = Relationship(back_populates="configs")


class NotebookPluginConfig(SQLModel, table=True):
    """Plugin configurations per notebook (overrides workspace settings)."""

    __tablename__ = "notebook_plugin_configs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    notebook_id: int = Field(foreign_key="notebooks.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    version: str | None = Field(default=None)  # Pinned plugin version (None = latest)
    enabled: bool = Field(default=True)  # Notebook-level enable/disable (overrides workspace)
    config: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )


class PluginSecret(SQLModel, table=True):
    """Secure plugin secrets (encrypted)."""

    __tablename__ = "plugin_secrets"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    key: str
    encrypted_value: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )


class PluginAPILog(SQLModel, table=True):
    """Plugin API request logs (for rate limiting and debugging)."""

    __tablename__ = "plugin_api_logs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    plugin_id: str = Field(foreign_key="plugins.plugin_id", index=True)
    endpoint_id: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    status_code: int | None = None
    error: str | None = None


class Agent(SQLModel, table=True):
    """AI agent configuration for a workspace.

    `kind` distinguishes agents Codex executes itself ("hosted", via the existing
    engine) from agents that represent an externally-driven bot ("external", e.g. a
    Claude Code session woken by webhook) — see docs/design/multi-user-multi-org.md
    §2.1 and §8 phase 3 (issue #533). `principal_id` links the config to the bot's
    `User` row (the "identity"); it is required for external agents and null for
    hosted agents, which run as the system rather than as a distinct principal.
    """

    __tablename__ = "agents"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("principal_id", name="uq_agents_principal_id"),)

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    name: str = Field(max_length=100)
    description: str | None = None
    provider: str  # "openai", "anthropic", "ollama", or any OpenAI-compatible provider
    model: str  # e.g. "gpt-4o", "claude-sonnet-4-20250514", "ollama/llama3"

    kind: str = Field(default="hosted")  # "hosted" (Codex-run) | "external" (bot-driven)
    # Bot principal (users.id) this agent config belongs to; one Agent per principal
    # (uniqueness enforced by uq_agents_principal_id above).
    principal_id: int | None = Field(default=None, foreign_key="users.id", index=True)

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

    # Webhook delivery config for external bots (issue #536, design doc §2.1 /
    # §8 phase 3). Only meaningful when kind == "external": a mention wakes the
    # bot with a signed POST to webhook_url instead of the ARQ agent-execution
    # pipeline used for hosted agents. webhook_secret_encrypted is Fernet-
    # encrypted at rest, the same as AgentCredential.encrypted_value.
    webhook_url: str | None = None
    webhook_secret_encrypted: str | None = None
    webhook_max_retries: int = Field(default=5)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    workspace: Workspace = Relationship(back_populates="agents")
    principal: User | None = Relationship(back_populates="agents")
    credentials: list["AgentCredential"] = Relationship(back_populates="agent")
    sessions: list["AgentSession"] = Relationship(back_populates="agent")

    @property
    def webhook_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_secret_encrypted)


class AgentCredential(SQLModel, table=True):
    """Encrypted storage for agent API keys."""

    __tablename__ = "agent_credentials"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    key_name: str  # "api_key", "organization_id", etc.
    encrypted_value: str  # Fernet-encrypted
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

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

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )


class AgentWebhookDelivery(SQLModel, table=True):
    """Audit record for one webhook delivery attempt to an external bot (issue #536).

    One row per attempt, not per event: a mention that needs several tries
    because of exponential backoff leaves a full trail, mirroring how
    `AgentActionLog` audits hosted-agent tool calls.
    """

    __tablename__ = "agent_webhook_deliveries"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    event_id: int = Field(foreign_key="events.id", index=True)

    attempt: int = Field(default=1)
    status: str = Field(default="pending")  # pending, delivered, failed
    response_status_code: int | None = None
    error: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )


class PasswordResetToken(SQLModel, table=True):
    """Tokens for password reset requests.

    Tokens are hashed with SHA-256 before storage. The plain token is only
    shown once (or delivered via email/CLI). Tokens expire after 1 hour.
    """

    __tablename__ = "password_reset_tokens"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)  # SHA-256 of the plain token
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    used_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    user: User = Relationship()


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
    # List of formal scopes (see PermissionScope in api/auth.py), e.g. ["workspace:write"].
    # A null/empty list means the token carries no scopes and every scope-gated route rejects it.
    scopes: list[str] | None = Field(default=None, sa_column=Column(JSON))
    workspace_id: int | None = Field(default=None, foreign_key="workspaces.id")  # Optional scope to workspace
    notebook_id: int | None = Field(default=None, foreign_key="notebooks.id")  # Optional scope to notebook
    last_used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    expires_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    user: User = Relationship()


class RefreshToken(SQLModel, table=True):
    """Refresh tokens for obtaining new access tokens without re-authenticating.

    Tokens are hashed with SHA-256 before storage; the plain token is only
    returned at issuance. Each refresh consumes (revokes) the old token and
    issues a new one, so a stolen-but-unused token has a limited window.
    """

    __tablename__ = "refresh_tokens"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)  # SHA-256 of the full token
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

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
    token_expires_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    scopes: str | None = None  # Comma-separated OAuth scopes granted
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

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
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    expires_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )  # Optional expiration time for cache


class Comment(SQLModel, table=True):
    """Threaded comment anchored to a block's stable ULID (issue #529, design doc §4).

    Anchored to `Block.block_id` (not the notebook-local numeric id) so a thread
    survives the block's file being renamed or moved. `thread_id` is null for a
    root comment and points at the root comment's id for replies (threads are
    flattened one level deep, not arbitrarily nested).
    """

    __tablename__ = "comments"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    notebook_id: int = Field(foreign_key="notebooks.id", index=True)
    block_id: str = Field(index=True)  # ULID; Block.block_id in the notebook db
    thread_id: int | None = Field(default=None, foreign_key="comments.id", index=True)
    author_id: int = Field(foreign_key="users.id")
    body: str
    resolved_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    resolved_by_id: int | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    mentions: list["CommentMention"] = Relationship(back_populates="comment")


class CommentMention(SQLModel, table=True):
    """@handle mention parsed from a comment body at post time.

    Mentions are resolved against workspace-visible principals when the comment
    is created and never re-parsed on read, so editing a user's handle later
    does not retroactively change historical mentions.
    """

    __tablename__ = "comment_mentions"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    comment_id: int = Field(foreign_key="comments.id", index=True)
    mentioned_principal_id: int = Field(foreign_key="users.id", index=True)
    handle: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

    # Relationships
    comment: Comment = Relationship(back_populates="mentions")


class Event(SQLModel, table=True):
    """Append-only event outbox (issue #530).

    Every notification-worthy action in a workspace writes one `Event` row here
    (never updated or deleted). The ARQ `fanout_event` job reads new events and
    fans them out into `Notification` rows for the relevant recipients, decoupling
    "what happened" (recorded synchronously, in the request's DB transaction) from
    "who should be told" (resolved asynchronously, off the request path).
    """

    __tablename__ = "events"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    # Nullable: some future event kinds may originate from the system rather than a user action.
    actor_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    # comment.created, comment.mention, comment.resolved, permission.granted, ...
    kind: str = Field(index=True)
    subject: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )


class Notification(SQLModel, table=True):
    """A single recipient's delivery record for an `Event` (issue #530).

    One row per (event, recipient) — enforced by a unique constraint so the async
    fanout job can be retried freely without creating duplicate notifications.
    """

    __tablename__ = "notifications"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("event_id", "recipient_id", name="uq_notifications_event_recipient"),)

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True)
    recipient_id: int = Field(foreign_key="users.id", index=True)
    read_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    delivered_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )


class WorkspaceWatch(SQLModel, table=True):
    """A user's opt-in/mute notification preference for a workspace (issue #530).

    A row's presence means the user has opted in to being treated as a
    "workspace watcher" for fanout purposes; `muted=True` suppresses the
    watcher-derived notifications for that user without deleting the opt-in
    (mentions and thread-participant notifications are unaffected by mute —
    only the blanket workspace-watcher path is suppressed).
    """

    __tablename__ = "workspace_watches"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_watches_workspace_user"),)

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    muted: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

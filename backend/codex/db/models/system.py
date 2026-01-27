"""System database models.

These models are stored in the system database (codex_system.db):
- User: User accounts for authentication
- Workspace: Workspaces for organizing notebooks
- WorkspacePermission: Permission mapping between users and workspaces
- Task: Tasks for agent work
- Notebook: Notebook metadata
"""

from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from .base import utc_now


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

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
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
    path: str = Field(index=True)  # Relative path from workspace
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    workspace: Workspace = Relationship(back_populates="notebooks")

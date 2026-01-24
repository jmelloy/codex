"""System database models.

These models are stored in the system database (codex_system.db):
- User: User accounts for authentication
- Workspace: Workspaces for organizing notebooks
- WorkspacePermission: Permission mapping between users and workspaces
- Task: Tasks for agent work
- Notebook: Notebook metadata
"""

from datetime import datetime
from typing import Optional, List

from sqlmodel import Field, SQLModel, Relationship

from .base import utc_now


class User(SQLModel, table=True):
    """User accounts for authentication."""

    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    theme_setting: Optional[str] = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    workspaces: List["Workspace"] = Relationship(back_populates="owner")


class Workspace(SQLModel, table=True):
    """Workspace for organizing notebooks and files."""

    __tablename__ = "workspaces"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    path: str = Field(unique=True)  # Filesystem path
    owner_id: int = Field(foreign_key="users.id")
    theme_setting: Optional[str] = Field(default="cream")  # User's preferred theme
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    permissions: List["WorkspacePermission"] = Relationship(back_populates="workspace")
    notebooks: List["Notebook"] = Relationship(back_populates="workspace")


class WorkspacePermission(SQLModel, table=True):
    """Permission mapping between users and workspaces."""

    __tablename__ = "workspace_permissions"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    user_id: int = Field(foreign_key="users.id")
    permission_level: str = Field(default="read")  # read, write, admin
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    workspace: Workspace = Relationship(back_populates="permissions")


class Task(SQLModel, table=True):
    """Tasks for agent work."""

    __tablename__ = "tasks"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    title: str
    description: Optional[str] = None
    status: str = Field(default="pending")  # pending, in_progress, completed, failed
    assigned_to: Optional[str] = None  # Agent identifier
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None


class Notebook(SQLModel, table=True):
    """Notebook metadata (stored in system database)."""

    __tablename__ = "notebooks"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id", index=True)
    name: str = Field(index=True)
    path: str = Field(index=True)  # Relative path from workspace
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    workspace: Workspace = Relationship(back_populates="notebooks")

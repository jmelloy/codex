"""Database models for Codex."""

from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# Link tables (must be defined before they are referenced)
# NotebookTag link table removed: Notebooks are now in the system database, 
# while tags remain in per-notebook databases. Tags can still be applied to notebooks
# by referencing the notebook_id, but there's no direct SQLAlchemy relationship.


class FileTag(SQLModel, table=True):
    """Link table for file tags."""

    __tablename__ = "file_tags"  # type: ignore[assignment]

    file_id: int = Field(foreign_key="file_metadata.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)


# System-level models (main database)
class User(SQLModel, table=True):
    """User accounts for authentication."""

    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
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


# Per-notebook database models (FileMetadata, Tags, SearchIndex)
# Note: notebook_id is stored as an integer reference to the system database
class FileMetadata(SQLModel, table=True):
    """Metadata for files in a notebook."""

    __tablename__ = "file_metadata"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    notebook_id: int  # Reference to notebook in system database (not a foreign key)
    path: str = Field(index=True)  # Relative path from notebook
    filename: str = Field(index=True)
    file_type: str  # markdown, json, xml, binary, etc.
    size: int
    hash: Optional[str] = None  # For detecting changes

    # Metadata - properties from frontmatter (source of truth is file)
    # title and description are indexed fields extracted from properties for search
    title: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[str] = None  # JSON-encoded dict from frontmatter
    sidecar_path: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    file_created_at: Optional[datetime] = None
    file_modified_at: Optional[datetime] = None

    # Git tracking
    git_tracked: bool = Field(default=True)
    last_commit_hash: Optional[str] = None

    # Relationships
    tags: List["Tag"] = Relationship(back_populates="files", link_model=FileTag)


class Tag(SQLModel, table=True):
    """Tags for organizing content."""

    __tablename__ = "tags"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    notebook_id: int  # Reference to notebook in system database (not a foreign key)
    name: str = Field(index=True)
    color: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    files: List["FileMetadata"] = Relationship(back_populates="tags", link_model=FileTag)


class SearchIndex(SQLModel, table=True):
    """Full-text search index for file content."""

    __tablename__ = "search_index"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="file_metadata.id", index=True)
    content: str  # Full text content for searching
    updated_at: datetime = Field(default_factory=utc_now)

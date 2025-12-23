"""Database models for Codex."""

from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


# System-level models (main database)
class User(SQLModel, table=True):
    """User accounts for authentication."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    workspaces: List["Workspace"] = Relationship(back_populates="owner")


class Workspace(SQLModel, table=True):
    """Workspace for organizing notebooks and files."""
    __tablename__ = "workspaces"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    path: str = Field(unique=True)  # Filesystem path
    owner_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    permissions: List["WorkspacePermission"] = Relationship(back_populates="workspace")


class WorkspacePermission(SQLModel, table=True):
    """Permission mapping between users and workspaces."""
    __tablename__ = "workspace_permissions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    user_id: int = Field(foreign_key="users.id")
    permission_level: str = Field(default="read")  # read, write, admin
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    workspace: Workspace = Relationship(back_populates="permissions")


class Task(SQLModel, table=True):
    """Tasks for agent work."""
    __tablename__ = "tasks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="workspaces.id")
    title: str
    description: Optional[str] = None
    status: str = Field(default="pending")  # pending, in_progress, completed, failed
    assigned_to: Optional[str] = None  # Agent identifier
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# Notebook-level models (per-notebook SQLite database)
class Notebook(SQLModel, table=True):
    """Notebook metadata."""
    __tablename__ = "notebooks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    path: str = Field(unique=True)  # Relative path from workspace
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    files: List["FileMetadata"] = Relationship(back_populates="notebook")
    tags: List["Tag"] = Relationship(back_populates="notebook", link_model="NotebookTag")


class FileMetadata(SQLModel, table=True):
    """Metadata for files in a notebook."""
    __tablename__ = "file_metadata"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    notebook_id: int = Field(foreign_key="notebooks.id")
    path: str = Field(index=True)  # Relative path from notebook
    filename: str = Field(index=True)
    file_type: str  # markdown, json, xml, binary, etc.
    size: int
    hash: Optional[str] = None  # For detecting changes
    
    # Metadata
    title: Optional[str] = None
    description: Optional[str] = None
    frontmatter: Optional[str] = None  # JSON-encoded frontmatter
    sidecar_path: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    file_created_at: Optional[datetime] = None
    file_modified_at: Optional[datetime] = None
    
    # Git tracking
    git_tracked: bool = Field(default=True)
    last_commit_hash: Optional[str] = None
    
    # Relationships
    notebook: Notebook = Relationship(back_populates="files")
    tags: List["Tag"] = Relationship(back_populates="files", link_model="FileTag")


class Tag(SQLModel, table=True):
    """Tags for organizing content."""
    __tablename__ = "tags"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    notebook_id: int = Field(foreign_key="notebooks.id")
    name: str = Field(index=True)
    color: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    notebook: Notebook = Relationship(back_populates="tags")
    files: List["FileMetadata"] = Relationship(back_populates="tags", link_model="FileTag")


class NotebookTag(SQLModel, table=True):
    """Link table for notebook tags."""
    __tablename__ = "notebook_tags"
    
    notebook_id: int = Field(foreign_key="notebooks.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)


class FileTag(SQLModel, table=True):
    """Link table for file tags."""
    __tablename__ = "file_tags"
    
    file_id: int = Field(foreign_key="file_metadata.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)


class SearchIndex(SQLModel, table=True):
    """Full-text search index for file content."""
    __tablename__ = "search_index"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="file_metadata.id", index=True)
    content: str  # Full text content for searching
    updated_at: datetime = Field(default_factory=datetime.utcnow)

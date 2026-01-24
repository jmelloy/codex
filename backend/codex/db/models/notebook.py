"""Per-notebook database models.

These models are stored in per-notebook databases (notebook.db):
- FileMetadata: Metadata for files in a notebook
- Tag: Tags for organizing content
- FileTag: Link table for file tags
- SearchIndex: Full-text search index for file content

Note: notebook_id in these models is stored as an integer reference
to the system database (not a foreign key, since it's in a different database).
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel, Relationship

from .base import utc_now


class FileTag(SQLModel, table=True):
    """Link table for file tags."""

    __tablename__ = "file_tags"  # type: ignore[assignment]

    file_id: int = Field(foreign_key="file_metadata.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)


class FileMetadata(SQLModel, table=True):
    """Metadata for files in a notebook."""

    __tablename__ = "file_metadata"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("notebook_id", "path", name="uq_file_metadata_notebook_path"),
        {"sqlite_autoincrement": True},
    )

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

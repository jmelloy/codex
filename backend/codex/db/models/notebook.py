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

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

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

    id: int | None = Field(default=None, primary_key=True)
    notebook_id: int  # Reference to notebook in system database (not a foreign key)
    path: str = Field(index=True)  # Relative path from notebook
    filename: str = Field(index=True)
    content_type: str  # MIME type (e.g., text/markdown, image/jpeg)
    size: int
    hash: str | None = None  # For detecting changes

    # Metadata - properties from frontmatter (source of truth is file)
    # title and description are indexed fields extracted from properties for search
    title: str | None = None
    description: str | None = None
    properties: str | None = None  # JSON-encoded dict from frontmatter
    sidecar_path: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    file_created_at: datetime | None = None
    file_modified_at: datetime | None = None

    # Git tracking
    git_tracked: bool = Field(default=True)
    last_commit_hash: str | None = None

    # Relationships
    tags: list["Tag"] = Relationship(back_populates="files", link_model=FileTag)


class Tag(SQLModel, table=True):
    """Tags for organizing content."""

    __tablename__ = "tags"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    notebook_id: int  # Reference to notebook in system database (not a foreign key)
    name: str = Field(index=True)
    color: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    files: list[FileMetadata] = Relationship(back_populates="tags", link_model=FileTag)


class SearchIndex(SQLModel, table=True):
    """Full-text search index for file content."""

    __tablename__ = "search_index"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="file_metadata.id", index=True)
    content: str  # Full text content for searching
    updated_at: datetime = Field(default_factory=utc_now)

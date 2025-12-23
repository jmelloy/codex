"""Notebook database models for per-notebook data.

This module contains models for per-notebook databases that store
pages, tags, and markdown file indexes specific to each notebook.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from db.models import Base as BaseWithCRUD


class NotebookBase(DeclarativeBase):
    """Base class for notebook database models."""
    pass


# Add CRUD methods to NotebookBase
for attr_name in dir(BaseWithCRUD):
    if not attr_name.startswith('_') and attr_name not in ['metadata', 'registry']:
        attr = getattr(BaseWithCRUD, attr_name)
        if callable(attr) and not isinstance(attr, type):
            setattr(NotebookBase, attr_name, attr)


class Page(NotebookBase):
    """Page model (stored in notebook database)."""

    __tablename__ = "pages"

    id = Column(String, primary_key=True)
    notebook_id = Column(String, nullable=False)  # Denormalized reference
    title = Column(String, nullable=False)
    date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    narrative = Column(Text, nullable=True)  # JSON string
    metadata_ = Column("metadata", Text, nullable=True)  # JSON string

    tags = relationship("PageTag", back_populates="page", cascade="all, delete-orphan")


Index("idx_notebook_pages_notebook", Page.notebook_id)
Index("idx_notebook_pages_date", Page.date.desc())


class Tag(NotebookBase):
    """Tag model (stored in notebook database)."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    color = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PageTag(NotebookBase):
    """Page-tag relationship (stored in notebook database)."""

    __tablename__ = "page_tags"

    page_id = Column(
        String, ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    page = relationship("Page", back_populates="tags")
    tag = relationship("Tag")


class MarkdownFile(NotebookBase):
    """Indexed markdown file (stored in notebook database)."""

    __tablename__ = "markdown_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False)
    relative_path = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=True)
    file_hash = Column(String, nullable=False)
    frontmatter = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    file_modified = Column(DateTime, nullable=True)
    indexed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_notebook_markdown_files_path", "path"),
        Index("idx_notebook_markdown_files_relative_path", "relative_path", unique=True),
        Index("idx_notebook_markdown_files_title", "title"),
        Index("idx_notebook_markdown_files_file_hash", "file_hash"),
    )


def get_notebook_engine(db_path: str):
    """Create a notebook database engine."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_notebook_session(engine):
    """Create a notebook database session."""
    Session = sessionmaker(bind=engine)
    return Session()


def init_notebook_db(db_path: str):
    """Initialize a notebook database schema."""
    engine = get_notebook_engine(db_path)
    NotebookBase.metadata.create_all(engine)
    return engine

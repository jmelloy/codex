"""SQLAlchemy models for Lab Notebook."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Notebook(Base):
    """Notebook model - a collection of related work."""

    __tablename__ = "notebooks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    settings = Column(Text, nullable=True)  # JSON string
    metadata_ = Column("metadata", Text, nullable=True)  # JSON string

    pages = relationship(
        "Page", back_populates="notebook", cascade="all, delete-orphan"
    )
    tags = relationship(
        "NotebookTag", back_populates="notebook", cascade="all, delete-orphan"
    )


Index("idx_notebooks_created", Notebook.created_at.desc())


class Page(Base):
    """Page model - a focused work session or investigation thread."""

    __tablename__ = "pages"

    id = Column(String, primary_key=True)
    notebook_id = Column(
        String, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    narrative = Column(Text, nullable=True)  # JSON string
    metadata_ = Column("metadata", Text, nullable=True)  # JSON string

    notebook = relationship("Notebook", back_populates="pages")
    entries = relationship("Entry", back_populates="page", cascade="all, delete-orphan")
    tags = relationship("PageTag", back_populates="page", cascade="all, delete-orphan")


Index("idx_pages_notebook", Page.notebook_id)
Index("idx_pages_date", Page.date.desc())


class Entry(Base):
    """Entry model - a single executable unit."""

    __tablename__ = "entries"

    id = Column(String, primary_key=True)
    page_id = Column(String, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    entry_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String, nullable=False, default="created")

    parent_id = Column(String, ForeignKey("entries.id"), nullable=True)

    inputs = Column(Text, nullable=False)  # JSON string
    outputs = Column(Text, nullable=True)  # JSON string
    execution = Column(Text, nullable=True)  # JSON string
    metrics = Column(Text, nullable=True)  # JSON string
    metadata_ = Column("metadata", Text, nullable=True)  # JSON string

    page = relationship("Page", back_populates="entries")
    parent = relationship("Entry", remote_side=[id], backref="children")
    artifacts = relationship(
        "Artifact", back_populates="entry", cascade="all, delete-orphan"
    )
    tags = relationship(
        "EntryTag", back_populates="entry", cascade="all, delete-orphan"
    )


Index("idx_entries_page", Entry.page_id)
Index("idx_entries_parent", Entry.parent_id)
Index("idx_entries_created", Entry.created_at.desc())
Index("idx_entries_type", Entry.entry_type)


class Artifact(Base):
    """Artifact model - stored output files."""

    __tablename__ = "artifacts"

    id = Column(String, primary_key=True)
    entry_id = Column(
        String, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(String, nullable=False)
    hash = Column(String, nullable=False, unique=True)
    size_bytes = Column(Integer, nullable=False)
    path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    archived = Column(Boolean, default=False)
    archive_strategy = Column(String, nullable=True)
    original_size_bytes = Column(Integer, nullable=True)

    metadata_ = Column("metadata", Text, nullable=True)  # JSON string

    entry = relationship("Entry", back_populates="artifacts")


Index("idx_artifacts_entry", Artifact.entry_id)
Index("idx_artifacts_hash", Artifact.hash)


class EntryLineage(Base):
    """Entry lineage graph - parent-child relationships."""

    __tablename__ = "entry_lineage"

    parent_id = Column(
        String, ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True
    )
    child_id = Column(
        String, ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type = Column(String, default="derives_from")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Tag(Base):
    """Tag model."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    color = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class NotebookTag(Base):
    """Notebook-tag relationship."""

    __tablename__ = "notebook_tags"

    notebook_id = Column(
        String, ForeignKey("notebooks.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    notebook = relationship("Notebook", back_populates="tags")
    tag = relationship("Tag")


class PageTag(Base):
    """Page-tag relationship."""

    __tablename__ = "page_tags"

    page_id = Column(
        String, ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    page = relationship("Page", back_populates="tags")
    tag = relationship("Tag")


class EntryTag(Base):
    """Entry-tag relationship."""

    __tablename__ = "entry_tags"

    entry_id = Column(
        String, ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    entry = relationship("Entry", back_populates="tags")
    tag = relationship("Tag")


class IntegrationVariable(Base):
    """Integration variable model - stores default values for integrations.

    This allows plugins that call APIs to store variables for default values,
    like server addresses, headers, or database connection strings.
    """

    __tablename__ = "integration_variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    integration_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    value = Column(Text, nullable=False)  # JSON-encoded value for complex types
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)  # Flag for sensitive data
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


Index(
    "idx_integration_variables_type_name",
    IntegrationVariable.integration_type,
    IntegrationVariable.name,
    unique=True,
)


def get_engine(db_path: str):
    """Create a database engine."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(engine):
    """Create a session factory."""
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(db_path: str, use_migrations: bool = True):
    """Initialize the database schema.

    Args:
        db_path: Path to the SQLite database file.
        use_migrations: If True, use Alembic migrations. If False, use create_all().
                       Defaults to True.

    Returns:
        SQLAlchemy engine instance.
    """
    engine = get_engine(db_path)

    if use_migrations:
        from codex.db.migrate import initialize_migrations

        initialize_migrations(db_path)
    else:
        Base.metadata.create_all(engine)

    return engine

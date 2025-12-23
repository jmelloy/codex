"""SQLAlchemy models for Lab Notebook."""

from datetime import datetime, timezone
from typing import Any, ClassVar, Optional, TypeVar

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
    inspect,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

T = TypeVar("T", bound="Base")


class Base(DeclarativeBase):
    """Base class for all models with CRUD operations that return typed instances."""

    # Class-level cache for foreign key info
    _fk_cache: ClassVar[dict[str, dict[str, tuple[str, str]]]] = {}

    @classmethod
    def get_foreign_keys(cls) -> dict[str, tuple[str, str]]:
        """Get foreign key information for this model.

        Returns a dict mapping column names to (table_name, column_name) tuples.
        """
        table_name = cls.__tablename__
        if table_name not in cls._fk_cache:
            fk_info = {}
            mapper = inspect(cls)
            for column in mapper.columns:
                for fk in column.foreign_keys:
                    # fk.target_fullname is 'table.column'
                    target_table, target_column = fk.target_fullname.split(".")
                    fk_info[column.name] = (target_table, target_column)
            cls._fk_cache[table_name] = fk_info
        return cls._fk_cache[table_name]

    @classmethod
    def validate_foreign_keys(
        cls, session: Session, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate that foreign key references exist.

        Args:
            session: SQLAlchemy session
            data: Dictionary of column values to validate

        Returns:
            Dictionary with foreign key info (referenced objects exist)

        Raises:
            ValueError: If a foreign key reference doesn't exist
        """
        fk_info = cls.get_foreign_keys()
        fk_status = {}

        for col_name, (target_table, target_column) in fk_info.items():
            if col_name in data and data[col_name] is not None:
                # Find the target model class
                target_cls = None
                for mapper in Base.registry.mappers:
                    if hasattr(mapper.class_, "__tablename__"):
                        if mapper.class_.__tablename__ == target_table:
                            target_cls = mapper.class_
                            break

                if target_cls is not None:
                    # Check if referenced record exists
                    ref_value = data[col_name]
                    exists = (
                        session.query(target_cls)
                        .filter(getattr(target_cls, target_column) == ref_value)
                        .first()
                    )
                    if exists is None:
                        raise ValueError(
                            f"Foreign key constraint failed: {col_name}='{ref_value}' "
                            f"references non-existent {target_table}.{target_column}"
                        )
                    fk_status[col_name] = {"exists": True, "table": target_table}

        return fk_status

    @classmethod
    def create(
        cls: type[T], session: Session, validate_fk: bool = True, **kwargs: Any
    ) -> T:
        """Create a new instance and add it to the session.

        Args:
            session: SQLAlchemy session
            validate_fk: Whether to validate foreign key references
            **kwargs: Column values for the new instance

        Returns:
            The created instance of the model type
        """
        if validate_fk:
            cls.validate_foreign_keys(session, kwargs)

        instance = cls(**kwargs)
        session.add(instance)
        session.flush()
        return instance

    @classmethod
    def get_by_id(cls: type[T], session: Session, id_value: Any) -> Optional[T]:
        """Get a single instance by its primary key.

        Args:
            session: SQLAlchemy session
            id_value: The primary key value (for single PK) or tuple of values (for composite PK)

        Returns:
            The instance if found, None otherwise

        Raises:
            ValueError: If id_value format doesn't match the primary key structure
        """
        mapper = inspect(cls)
        pk_columns = mapper.primary_key

        if len(pk_columns) == 1:
            return session.query(cls).filter(pk_columns[0] == id_value).first()
        elif len(pk_columns) > 1:
            # Composite primary key - id_value should be a tuple
            if not isinstance(id_value, (tuple, list)):
                raise ValueError(
                    f"{cls.__name__} has a composite primary key with {len(pk_columns)} columns. "
                    f"id_value must be a tuple/list of values, got {type(id_value).__name__}"
                )
            if len(id_value) != len(pk_columns):
                raise ValueError(
                    f"{cls.__name__} has {len(pk_columns)} primary key columns, "
                    f"but {len(id_value)} values were provided"
                )
            query = session.query(cls)
            for pk_col, val in zip(pk_columns, id_value):
                query = query.filter(pk_col == val)
            return query.first()
        return None

    @classmethod
    def get_all(cls: type[T], session: Session) -> list[T]:
        """Get all instances of this model.

        Args:
            session: SQLAlchemy session

        Returns:
            List of all instances
        """
        return session.query(cls).all()

    @classmethod
    def find_by(cls: type[T], session: Session, **filters: Any) -> list[T]:
        """Find instances matching the given filters.

        Args:
            session: SQLAlchemy session
            **filters: Column filters (column_name=value)

        Returns:
            List of matching instances
        """
        query = session.query(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query.all()

    @classmethod
    def find_one_by(cls: type[T], session: Session, **filters: Any) -> Optional[T]:
        """Find a single instance matching the given filters.

        Args:
            session: SQLAlchemy session
            **filters: Column filters (column_name=value)

        Returns:
            The first matching instance, or None
        """
        query = session.query(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query.first()

    def update(self: T, session: Session, validate_fk: bool = True, **kwargs: Any) -> T:
        """Update this instance with new values.

        Args:
            session: SQLAlchemy session
            validate_fk: Whether to validate foreign key references
            **kwargs: Column values to update

        Returns:
            The updated instance (self)
        """
        if validate_fk:
            self.__class__.validate_foreign_keys(session, kwargs)

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        session.flush()
        return self

    def delete(self: T, session: Session) -> bool:
        """Delete this instance from the database.

        Args:
            session: SQLAlchemy session

        Returns:
            True if deleted successfully
        """
        session.delete(self)
        session.flush()
        return True

    @classmethod
    def delete_by_id(cls: type[T], session: Session, id_value: Any) -> bool:
        """Delete an instance by its primary key.

        Args:
            session: SQLAlchemy session
            id_value: The primary key value (for single PK) or tuple of values (for composite PK)

        Returns:
            True if found and deleted, False otherwise

        Raises:
            ValueError: If id_value format doesn't match the primary key structure
        """
        instance = cls.get_by_id(session, id_value)
        if instance:
            session.delete(instance)
            session.flush()
            return True
        return False


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    workspace_path = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


Index("idx_users_username", User.username)
Index("idx_users_email", User.email)


class RefreshToken(Base):
    """Refresh token model for token refresh mechanism."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    revoked = Column(Boolean, default=False, nullable=False)

    # Relationship
    user = relationship("User", backref="refresh_tokens")


Index("idx_refresh_tokens_token", RefreshToken.token)
Index("idx_refresh_tokens_user_id", RefreshToken.user_id)


class Notebook(Base):
    """Notebook model - a collection of related work."""

    __tablename__ = "notebooks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
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
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    narrative = Column(Text, nullable=True)  # JSON string
    metadata_ = Column("metadata", Text, nullable=True)  # JSON string

    notebook = relationship("Notebook", back_populates="pages")
    tags = relationship("PageTag", back_populates="page", cascade="all, delete-orphan")


Index("idx_pages_notebook", Page.notebook_id)
Index("idx_pages_date", Page.date.desc())


class Tag(Base):
    """Tag model."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    color = Column(String, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


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


class MarkdownFile(Base):
    """Indexed markdown file with frontmatter metadata."""

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
        Index("idx_markdown_files_path", "path"),
        Index("idx_markdown_files_relative_path", "relative_path", unique=True),
        Index("idx_markdown_files_title", "title"),
        Index("idx_markdown_files_file_hash", "file_hash"),
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
        from db.migrate import initialize_migrations

        initialize_migrations(db_path)
    else:
        Base.metadata.create_all(engine)

    return engine

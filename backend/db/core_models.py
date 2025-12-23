"""Core database models for user authentication.

This module contains models for the core database that stores
user authentication data across all workspaces.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from db.crud_mixin import CRUDMixin


class CoreBase(CRUDMixin, DeclarativeBase):
    """Base class for core database models."""
    pass


class User(CoreBase):
    """User model for authentication (stored in core database)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    workspace_path = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


Index("idx_core_users_username", User.username)
Index("idx_core_users_email", User.email)


class RefreshToken(CoreBase):
    """Refresh token model (stored in core database)."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="refresh_tokens")


Index("idx_core_refresh_tokens_token", RefreshToken.token)
Index("idx_core_refresh_tokens_user_id", RefreshToken.user_id)


def get_core_engine(db_path: str):
    """Create a core database engine."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_core_session(engine):
    """Create a core database session."""
    Session = sessionmaker(bind=engine)
    return Session()


def init_core_db(db_path: str):
    """Initialize the core database schema."""
    engine = get_core_engine(db_path)
    CoreBase.metadata.create_all(engine)
    return engine

"""Workspace database models for notebook registry.

This module contains models for the workspace database that stores
a registry of notebooks within a workspace.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from db.crud_mixin import CRUDMixin


class WorkspaceBase(CRUDMixin, DeclarativeBase):
    """Base class for workspace database models."""
    pass


class Notebook(WorkspaceBase):
    """Notebook registry entry (stored in workspace database)."""

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
    db_path = Column(String, nullable=False)  # Path to notebook's database


Index("idx_workspace_notebooks_created", Notebook.created_at.desc())


def get_workspace_engine(db_path: str):
    """Create a workspace database engine."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_workspace_session(engine):
    """Create a workspace database session."""
    Session = sessionmaker(bind=engine)
    return Session()


def init_workspace_db(db_path: str):
    """Initialize the workspace database schema."""
    engine = get_workspace_engine(db_path)
    WorkspaceBase.metadata.create_all(engine)
    return engine

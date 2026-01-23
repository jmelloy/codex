"""Database connection and session management."""

import os
from pathlib import Path
from typing import AsyncGenerator

from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# System database (users, workspaces, permissions, tasks)
SYSTEM_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codex_system.db")

# Data directory for workspaces (derived from database path or env var)
_default_data_dir = os.path.dirname(SYSTEM_DATABASE_URL.replace("sqlite:///", "")) or "./data"
DATA_DIRECTORY = os.getenv("DATA_DIRECTORY", _default_data_dir)
SYSTEM_DATABASE_URL_ASYNC = SYSTEM_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

system_engine = create_async_engine(SYSTEM_DATABASE_URL_ASYNC, echo=True, connect_args={"check_same_thread": False})

async_session_maker = sessionmaker(system_engine, class_=AsyncSession, expire_on_commit=False)


async def get_system_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for system database."""
    async with async_session_maker() as session:
        yield session


def run_alembic_migrations():
    """Run Alembic migrations for system database.

    This function runs migrations programmatically, which is useful for
    application startup and Docker containers.
    """
    from alembic.config import Config
    from alembic import command

    # Find alembic.ini relative to this file
    backend_dir = Path(__file__).parent.parent
    alembic_ini = backend_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    # Create Alembic config and run migrations
    alembic_cfg = Config(str(alembic_ini))

    # Set the script location relative to alembic.ini
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")


async def init_system_db():
    """Initialize system database tables using Alembic migrations.

    This function runs Alembic migrations to set up or upgrade the system database.
    For new databases, this creates all tables. For existing databases, this applies
    any pending migrations.
    """
    # Ensure data directory exists
    db_path = SYSTEM_DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Run Alembic migrations
    run_alembic_migrations()


def get_notebook_engine(notebook_path: str):
    """Get database engine for a specific notebook."""
    db_path = os.path.join(notebook_path, ".codex", "notebook.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_notebook_db(notebook_path: str):
    """Initialize notebook database tables."""
    engine = get_notebook_engine(notebook_path)
    SQLModel.metadata.create_all(engine)

    # Run migrations on this notebook database
    from backend.db.migrations import migrate_frontmatter_to_properties

    db_path = os.path.join(notebook_path, ".codex", "notebook.db")
    migrate_frontmatter_to_properties(db_path)

    return engine


def get_notebook_session(notebook_path: str):
    """Get database session for a specific notebook."""
    engine = get_notebook_engine(notebook_path)
    return Session(engine)

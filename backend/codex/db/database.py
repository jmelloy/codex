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

system_engine = create_async_engine(SYSTEM_DATABASE_URL_ASYNC, echo=False, connect_args={"check_same_thread": False})

# Synchronous engine for use in thread pools (e.g., notebook watchers)
system_engine_sync = create_engine(SYSTEM_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

async_session_maker = sessionmaker(system_engine, class_=AsyncSession, expire_on_commit=False)


async def get_system_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for system database."""
    async with async_session_maker() as session:
        yield session


def get_system_session_sync() -> Session:
    """Get synchronous database session for system database (for use in thread pools)."""
    return Session(system_engine_sync)


def run_alembic_migrations():
    """Run Alembic migrations for system database.

    This function runs migrations programmatically, which is useful for
    application startup and Docker containers.
    """
    from alembic.config import Config
    from alembic import command

    # Find alembic.ini relative to this file - now it's in backend/ not backend/codex/
    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini = backend_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    # Create Alembic config and run migrations
    alembic_cfg = Config(str(alembic_ini))

    # Set the script location relative to alembic.ini
    alembic_cfg.set_main_option("script_location", str(backend_dir / "codex" / "alembic"))

    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")


def run_notebook_alembic_migrations(notebook_path: str):
    """Run Alembic migrations for a specific notebook database.

    This function runs migrations programmatically on per-notebook databases.
    It handles both fresh databases and existing databases that predate Alembic.

    Args:
        notebook_path: Path to the notebook directory (where .codex/notebook.db resides)
    """
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import inspect, create_engine
    from alembic.runtime.migration import MigrationContext

    # Find notebook_alembic.ini relative to this file - now it's in backend/ not backend/codex/
    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini = backend_dir / "notebook_alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"notebook_alembic.ini not found at {alembic_ini}")

    # Get the notebook database path
    db_path = os.path.join(notebook_path, ".codex", "notebook.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Create Alembic config
    alembic_cfg = Config(str(alembic_ini))

    # Set the script location relative to alembic.ini
    alembic_cfg.set_main_option("script_location", str(backend_dir / "codex" / "notebook_alembic"))

    # Set the database URL for this specific notebook
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    # Check if this is an existing database that needs to be stamped
    # (has tables but no alembic_version)
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Check current revision
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()

    engine.dispose()

    if current_rev is None and "file_metadata" in tables:
        # Database has tables but no alembic_version - this is a pre-Alembic database
        # Check if it has the old 'frontmatter' column or new 'properties' column
        file_metadata_columns = {col["name"] for col in inspector.get_columns("file_metadata")}

        if "frontmatter" in file_metadata_columns:
            # Old database with frontmatter - stamp at revision 001
            # (migration 002 will then rename it to properties)
            command.stamp(alembic_cfg, "001")
        else:
            # Database already has 'properties' column - stamp at head
            command.stamp(alembic_cfg, "head")

    # Now run any pending migrations
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
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except FileExistsError:
            pass

    # Run Alembic migrations
    run_alembic_migrations()


def get_notebook_engine(notebook_path: str):
    """Get database engine for a specific notebook."""
    db_path = os.path.join(notebook_path, ".codex", "notebook.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_notebook_db(notebook_path: str):
    """Initialize notebook database tables using Alembic migrations.

    This function runs Alembic migrations to set up or upgrade the notebook database.
    For new databases, this creates all tables. For existing databases, this applies
    any pending migrations.

    Args:
        notebook_path: Path to the notebook directory

    Returns:
        SQLAlchemy engine for the notebook database
    """
    # Ensure .codex directory exists
    codex_dir = os.path.join(notebook_path, ".codex")
    os.makedirs(codex_dir, exist_ok=True)

    # Run Alembic migrations for this notebook
    run_notebook_alembic_migrations(notebook_path)

    # Return engine for immediate use
    return get_notebook_engine(notebook_path)


def get_notebook_session(notebook_path: str):
    """Get database session for a specific notebook."""
    engine = get_notebook_engine(notebook_path)
    return Session(engine)

"""Database connection and session management."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

# System database (users, workspaces, permissions, tasks)
SYSTEM_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/codex_system.db")

if not SYSTEM_DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("Codex requires a SQLite DATABASE_URL (sqlite:///...)")

SYSTEM_DATABASE_URL_ASYNC = SYSTEM_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
_connect_args = {"check_same_thread": False}
# Data directory derived from SQLite database path
_default_data_dir = os.path.dirname(SYSTEM_DATABASE_URL.replace("sqlite:///", "")) or "./data"

DATA_DIRECTORY = os.getenv("DATA_DIRECTORY", _default_data_dir)

system_engine = create_async_engine(SYSTEM_DATABASE_URL_ASYNC, echo=False, connect_args=_connect_args)

# Synchronous engine for use in thread pools (e.g., notebook watchers)
system_engine_sync = create_engine(SYSTEM_DATABASE_URL, echo=False, connect_args=_connect_args)

async_session_maker = sessionmaker(system_engine, class_=AsyncSession, expire_on_commit=False)


async def get_system_session() -> AsyncGenerator[AsyncSession]:
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
    from alembic import command
    from alembic.config import Config

    # Find alembic.ini relative to this file - now it's in backend/ not backend/codex/
    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini = backend_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    # Create Alembic config for workspace migrations using the workspace section
    alembic_cfg = Config(str(alembic_ini), ini_section="alembic:workspace")

    # Set the script location relative to alembic.ini
    alembic_cfg.set_main_option("script_location", str(backend_dir / "codex" / "migrations" / "workspace"))

    # Override the database URL so Alembic uses the same URL as the app
    alembic_cfg.set_main_option("sqlalchemy.url", SYSTEM_DATABASE_URL)

    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")


def run_notebook_alembic_migrations(notebook_path: str):
    """Run Alembic migrations for a specific notebook database.

    Args:
        notebook_path: Path to the notebook directory (where .codex/notebook.db resides)
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini = backend_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    db_path = os.path.join(notebook_path, ".codex", "notebook.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    alembic_cfg = Config(str(alembic_ini), ini_section="alembic:notebook")
    alembic_cfg.attributes["configure_logger"] = False
    alembic_cfg.set_main_option("script_location", str(backend_dir / "codex" / "migrations" / "notebook"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    # Stamp pre-Alembic databases that already have the initial schema so that
    # migration 001 (which creates file_metadata) is not re-applied on top of
    # an existing table, which would raise "table already exists".
    import sqlite3

    if os.path.exists(db_path):
        con = sqlite3.connect(db_path)
        try:
            cur = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cur.fetchall()}
        finally:
            con.close()

        has_version = "alembic_version" in existing_tables
        has_initial_schema = "file_metadata" in existing_tables or "blocks" in existing_tables

        if not has_version and has_initial_schema:
            # Database was created without Alembic; stamp at revision 001 so
            # Alembic knows the initial schema is already applied.
            command.stamp(alembic_cfg, "001")

    command.upgrade(alembic_cfg, "head")


async def init_system_db():
    """Initialize system database tables using Alembic migrations.

    This function runs Alembic migrations to set up or upgrade the system database.
    For new databases, this creates all tables. For existing databases, this applies
    any pending migrations.
    """
    # Ensure data directory exists for SQLite
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
    """Get database engine for a specific notebook.

    The .codex directory must already exist (created by init_notebook_db).
    This function intentionally does NOT create directories so that
    background threads cannot resurrect a deleted notebook's directory.
    """
    db_path = os.path.join(notebook_path, ".codex", "notebook.db")
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

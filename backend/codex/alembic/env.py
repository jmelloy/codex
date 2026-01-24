"""Alembic migration environment for Codex system database."""

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

# Add backend directory to path for imports when running alembic CLI
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir.parent) not in sys.path:
    sys.path.insert(0, str(backend_dir.parent))

# Import only system models (not notebook models which are in separate databases)
from codex.db.models.system import (Notebook, Task, User, Workspace,
                                    WorkspacePermission)
# Import SQLModel to ensure metadata is populated
from sqlmodel import SQLModel

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
# Only include system model tables
target_metadata = SQLModel.metadata

# Get database URL from environment or use default
# Must match the default in backend/db/database.py
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codex_system.db")


def get_url():
    """Get database URL, preferring environment variable."""
    return DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Uses synchronous SQLAlchemy engine for compatibility with all contexts,
    including being called from within async code.
    """
    url = get_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

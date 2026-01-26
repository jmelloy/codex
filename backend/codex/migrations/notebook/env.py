"""Alembic migration environment for Codex per-notebook databases."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool, create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.engine import Connection

from alembic import context

# Add backend directory to path for imports when running alembic CLI
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir.parent) not in sys.path:
    sys.path.insert(0, str(backend_dir.parent))

# Alembic Config object
config = context.config

# Set up logging from notebook_alembic.ini
# Only configure file-based logging if explicitly running alembic CLI (not programmatically)
# This prevents wiping out the application's logging configuration
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Create target metadata for notebook tables only
# We define this explicitly to avoid pulling in system models
target_metadata = MetaData()


def get_url():
    """Get database URL from config or environment variable."""
    # Try to get from config first (set by database.py when calling programmatically)
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    # Fall back to environment variable
    return os.getenv("NOTEBOOK_DATABASE_URL", "sqlite:///./notebook.db")


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

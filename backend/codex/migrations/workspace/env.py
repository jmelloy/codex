"""Alembic migration environment for Codex system database."""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

# Add backend/ (not backend/codex) to sys.path so `import codex...` works when
# running the alembic CLI directly - this file lives at
# backend/codex/migrations/workspace/env.py, so backend/ is four levels up.
backend_dir = Path(__file__).resolve().parents[3]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import only system models (not notebook models which are in separate databases)

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
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/codex_system.db")

try:
    from codex.db.url import connect_args_for, to_sync_url
except ImportError:
    # backend/ is on sys.path (see above), so this should not normally happen;
    # fall back to inlined equivalents so migrations still work standalone if
    # codex.db.url is unimportable for some other reason (e.g. broken install).
    from sqlalchemy.engine import make_url

    _SUPPORTED_BACKENDS = ("sqlite", "postgresql")

    def _get_backend_name(url: str) -> str:
        backend = make_url(url).get_backend_name()
        if backend not in _SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unsupported database backend {backend!r} in DATABASE_URL; "
                f"Codex supports: {', '.join(_SUPPORTED_BACKENDS)}"
            )
        return backend

    def to_sync_url(url: str) -> str:
        parsed = make_url(url)
        driver = "sqlite" if _get_backend_name(url) == "sqlite" else "postgresql+psycopg2"
        return parsed.set(drivername=driver).render_as_string(hide_password=False)

    def connect_args_for(url: str) -> dict:
        return {"check_same_thread": False} if _get_backend_name(url) == "sqlite" else {}


def get_url():
    """Get database URL (sync driver), preferring environment variable."""
    return to_sync_url(DATABASE_URL)


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
        connect_args=connect_args_for(DATABASE_URL),
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

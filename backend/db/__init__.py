"""Database module initialization."""

from db.migrate import (
    get_current_revision,
    get_head_revision,
    get_migration_history,
    get_pending_migrations,
    initialize_migrations,
    is_up_to_date,
    needs_migration,
    run_migrations,
    stamp_revision,
)
from db.models import Base, get_engine, get_session, init_db
from db.operations import DatabaseManager

# New split database managers
from db.core_operations import CoreDatabaseManager
from db.workspace_operations import WorkspaceDatabaseManager
from db.notebook_operations import NotebookDatabaseManager

__all__ = [
    "Base",
    "DatabaseManager",
    "get_current_revision",
    "get_engine",
    "get_head_revision",
    "get_migration_history",
    "get_pending_migrations",
    "get_session",
    "init_db",
    "initialize_migrations",
    "is_up_to_date",
    "needs_migration",
    "run_migrations",
    "stamp_revision",
    # New split database managers
    "CoreDatabaseManager",
    "WorkspaceDatabaseManager",
    "NotebookDatabaseManager",
]

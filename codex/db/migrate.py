"""Database migration runner.

This module provides utilities for running Alembic migrations
programmatically within the Codex application.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect


def get_alembic_config(db_path: str | Path) -> Config:
    """Create an Alembic configuration for the given database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Configured Alembic Config object.
    """
    # Get the migrations directory (same directory as this file)
    migrations_dir = Path(__file__).parent / "migrations"

    # Create Alembic config
    config = Config()
    config.set_main_option("script_location", str(migrations_dir))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    return config


def get_current_revision(db_path: str | Path) -> str | None:
    """Get the current migration revision of the database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Current revision string, or None if no migrations applied.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def get_head_revision(db_path: str | Path) -> str | None:
    """Get the latest available migration revision.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Head revision string, or None if no migrations available.
    """
    config = get_alembic_config(db_path)
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def is_up_to_date(db_path: str | Path) -> bool:
    """Check if the database is up to date with migrations.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        True if database is at the latest migration.
    """
    current = get_current_revision(db_path)
    head = get_head_revision(db_path)
    return current == head


def needs_migration(db_path: str | Path) -> bool:
    """Check if the database needs migration.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        True if there are pending migrations.
    """
    return not is_up_to_date(db_path)


def run_migrations(db_path: str | Path, revision: str = "head") -> None:
    """Run database migrations up to the specified revision.

    Args:
        db_path: Path to the SQLite database file.
        revision: Target revision (default: "head" for latest).
    """
    config = get_alembic_config(db_path)
    command.upgrade(config, revision)


def downgrade(db_path: str | Path, revision: str) -> None:
    """Downgrade database to the specified revision.

    Args:
        db_path: Path to the SQLite database file.
        revision: Target revision to downgrade to.
    """
    config = get_alembic_config(db_path)
    command.downgrade(config, revision)


def stamp_revision(db_path: str | Path, revision: str = "head") -> None:
    """Stamp the database with a specific revision without running migrations.

    This is useful for marking an existing database as being at a specific
    migration version, typically used when initializing a new database
    that already has the schema from create_all().

    Args:
        db_path: Path to the SQLite database file.
        revision: Revision to stamp (default: "head" for latest).
    """
    config = get_alembic_config(db_path)
    command.stamp(config, revision)


def get_pending_migrations(db_path: str | Path) -> list[str]:
    """Get list of pending migrations.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        List of pending revision IDs.
    """
    config = get_alembic_config(db_path)
    script = ScriptDirectory.from_config(config)
    current = get_current_revision(db_path)

    pending = []
    for revision in script.walk_revisions():
        if current is None or revision.revision != current:
            pending.append(revision.revision)
            if revision.down_revision == current:
                break
        else:
            break

    return list(reversed(pending))


def get_migration_history(db_path: str | Path) -> list[dict]:
    """Get the history of available migrations.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        List of migration info dictionaries.
    """
    config = get_alembic_config(db_path)
    script = ScriptDirectory.from_config(config)
    current = get_current_revision(db_path)

    history = []
    for revision in script.walk_revisions():
        history.append(
            {
                "revision": revision.revision,
                "down_revision": revision.down_revision,
                "description": revision.doc,
                "is_current": revision.revision == current,
                "is_applied": _is_revision_applied(revision.revision, current, script),
            }
        )

    return list(reversed(history))


def _is_revision_applied(revision: str, current: str | None, script: ScriptDirectory) -> bool:
    """Check if a revision has been applied.

    Args:
        revision: Revision to check.
        current: Current database revision.
        script: Alembic script directory.

    Returns:
        True if the revision has been applied.
    """
    if current is None:
        return False

    if revision == current:
        return True

    # Walk from current back to base to see if revision is in ancestry
    for rev in script.walk_revisions(current, "base"):
        if rev.revision == revision:
            return True

    return False


def database_exists_with_tables(db_path: str | Path) -> bool:
    """Check if database exists and has tables.

    This helps determine if we're dealing with an existing database
    that was created with create_all() but not stamped with a revision.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        True if database exists and has user tables.
    """
    if not Path(db_path).exists():
        return False

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Check for our core tables (exclude alembic_version)
    core_tables = {"notebooks", "pages", "entries", "artifacts"}
    return bool(core_tables.intersection(set(tables)))


def initialize_migrations(db_path: str | Path) -> None:
    """Initialize migration tracking for a database.

    For new databases, this runs all migrations.
    For existing databases created with create_all(),
    this stamps them at head without running migrations.

    Args:
        db_path: Path to the SQLite database file.
    """
    current = get_current_revision(db_path)

    if current is not None:
        # Already has migration tracking, just upgrade
        run_migrations(db_path)
    elif database_exists_with_tables(db_path):
        # Existing database without migration tracking - stamp it
        stamp_revision(db_path, "head")
    else:
        # New database - run migrations
        run_migrations(db_path)

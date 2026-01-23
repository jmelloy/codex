"""Database migration utilities.

DEPRECATED: This module contains legacy migration functions that have been
replaced by Alembic migrations. New notebook databases use Alembic for schema
management (see backend/notebook_alembic/).

For historical reference and backward compatibility only.

This module handles schema migrations for the Codex database.
SQLite doesn't natively support column renaming in older versions,
so we use table recreation for structural changes.
"""

import sqlite3
from pathlib import Path


def migrate_frontmatter_to_properties(db_path: str) -> bool:
    """DEPRECATED: Use Alembic migrations instead (backend/notebook_alembic/).
    
    Migrate the frontmatter column to properties in file_metadata table.

    This migration renames the 'frontmatter' column to 'properties' to
    reflect the unified properties system where frontmatter is the source
    of truth.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        True if migration was performed, False if already migrated or no table exists
        
    Note:
        This function is kept for backward compatibility but is no longer used
        by init_notebook_db(). Alembic migration 002 handles this migration.
    """
    if not Path(db_path).exists():
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if file_metadata table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_metadata'")
        if not cursor.fetchone():
            return False

        # Check current column names
        cursor.execute("PRAGMA table_info(file_metadata)")
        columns = {row[1] for row in cursor.fetchall()}

        # If properties already exists, no migration needed
        if "properties" in columns:
            return False

        # If frontmatter doesn't exist, no migration needed
        if "frontmatter" not in columns:
            return False

        # Perform migration: rename frontmatter to properties
        # SQLite 3.25.0+ supports ALTER TABLE RENAME COLUMN
        try:
            cursor.execute("ALTER TABLE file_metadata RENAME COLUMN frontmatter TO properties")
            conn.commit()
            return True
        except sqlite3.OperationalError:
            # Fallback for older SQLite versions: recreate table
            # Get the full schema
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='file_metadata'")
            old_schema = cursor.fetchone()[0]

            # Create new schema with properties instead of frontmatter
            new_schema = old_schema.replace("frontmatter", "properties")
            new_schema = new_schema.replace("file_metadata", "file_metadata_new")

            # Create new table
            cursor.execute(new_schema)

            # Get column names for the copy
            cursor.execute("PRAGMA table_info(file_metadata)")
            all_columns = [row[1] for row in cursor.fetchall()]
            old_columns = ", ".join(all_columns)
            new_columns = ", ".join("properties" if c == "frontmatter" else c for c in all_columns)

            # Copy data
            cursor.execute(f"INSERT INTO file_metadata_new ({new_columns}) SELECT {old_columns} FROM file_metadata")

            # Drop old table and rename new one
            cursor.execute("DROP TABLE file_metadata")
            cursor.execute("ALTER TABLE file_metadata_new RENAME TO file_metadata")

            conn.commit()
            return True

    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise
    finally:
        conn.close()


def run_all_migrations(data_directory: str) -> int:
    """Run all migrations on all notebook databases.

    Args:
        data_directory: Base directory containing workspace/notebook directories

    Returns:
        Number of databases migrated
    """
    migrated_count = 0
    data_path = Path(data_directory)

    if not data_path.exists():
        return 0

    # Find all notebook.db files
    for db_path in data_path.rglob("*/.codex/notebook.db"):
        if migrate_frontmatter_to_properties(str(db_path)):
            print(f"Migrated: {db_path}")
            migrated_count += 1

    return migrated_count


if __name__ == "__main__":
    import sys
    from backend.db.database import DATA_DIRECTORY

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = DATA_DIRECTORY

    count = run_all_migrations(data_dir)
    print(f"Migration complete. {count} database(s) migrated.")

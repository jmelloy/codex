"""Migration to add notebooks table to system database."""

import sqlite3
from pathlib import Path


def migrate_system_db(db_path: str = "./codex_system.db"):
    """Add notebooks table to system database if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if notebooks table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notebooks'")
        if cursor.fetchone():
            print(f"notebooks table already exists in {db_path}")
            return

        # Create notebooks table
        cursor.execute("""
            CREATE TABLE notebooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX ix_notebooks_workspace_id ON notebooks (workspace_id)")
        cursor.execute("CREATE INDEX ix_notebooks_name ON notebooks (name)")
        cursor.execute("CREATE INDEX ix_notebooks_path ON notebooks (path)")

        conn.commit()
        print(f"Added notebooks table to {db_path}")

    except Exception as e:
        print(f"Error migrating database: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "./codex_system.db"
    migrate_system_db(db_path)

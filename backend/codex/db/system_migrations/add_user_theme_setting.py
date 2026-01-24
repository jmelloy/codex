"""Migration to add theme_setting column to users table."""

import sqlite3


def migrate_system_db(db_path: str = "./codex_system.db"):
    """Add theme_setting column to users table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if "theme_setting" not in columns:
            # Add the column with default value
            cursor.execute("ALTER TABLE users ADD COLUMN theme_setting TEXT DEFAULT 'cream'")
            conn.commit()
            print(f"Added theme_setting column to users table in {db_path}")
        else:
            print(f"theme_setting column already exists in users table in {db_path}")

    except Exception as e:
        print(f"Error migrating database: {e}")
        conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "./codex_system.db"
    migrate_system_db(db_path)

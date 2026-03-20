"""Test notebook Alembic migrations."""

import pytest
from sqlalchemy import inspect, text

from codex.db.database import init_notebook_db


class TestNotebookMigrations:
    """Test Alembic migrations for notebook databases."""

    def test_init_fresh_notebook_db(self, tmp_path):
        """Test initializing a fresh notebook database."""
        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()

        # Initialize the database
        engine = init_notebook_db(str(notebook_path))

        # Verify all tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "blocks" in tables
        assert "tags" in tables
        assert "block_tags" in tables
        assert "search_index" in tables
        # file_metadata should no longer exist after migration 010
        assert "file_metadata" not in tables

        # Verify the alembic_version table exists (confirms Alembic was used)
        assert "alembic_version" in tables

        # Verify blocks has merged fields from file_metadata
        columns = {col["name"] for col in inspector.get_columns("blocks")}
        assert "filename" in columns
        assert "hash" in columns
        assert "git_tracked" in columns
        assert "s3_key" in columns
        # file_id should be gone
        assert "file_id" not in columns

    def test_migrate_existing_notebook_with_frontmatter(self, tmp_path):
        """Test migrating an existing database with frontmatter column to properties."""
        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()
        codex_dir = notebook_path / ".codex"
        codex_dir.mkdir()

        # Create an old-style database with frontmatter column
        db_path = codex_dir / "notebook.db"
        from sqlalchemy import create_engine

        old_engine = create_engine(f"sqlite:///{db_path}")

        # Create old schema with frontmatter
        with old_engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE file_metadata (
                    id INTEGER PRIMARY KEY,
                    notebook_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    hash TEXT,
                    title TEXT,
                    description TEXT,
                    frontmatter TEXT,
                    sidecar_path TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    file_created_at TIMESTAMP,
                    file_modified_at TIMESTAMP,
                    git_tracked BOOLEAN NOT NULL,
                    last_commit_hash TEXT
                )
            """))
            conn.commit()

            # Insert test data
            conn.execute(text("""
                INSERT INTO file_metadata (
                    id, notebook_id, path, filename, file_type, size,
                    frontmatter, created_at, updated_at, git_tracked
                )
                VALUES (
                    1, 1, 'test.md', 'test.md', 'markdown', 100,
                    '{"title": "Test"}', '2025-01-23 00:00:00', '2025-01-23 00:00:00', 1
                )
            """))
            conn.commit()

        old_engine.dispose()

        # Run migrations
        engine = init_notebook_db(str(notebook_path))

        # Verify file_metadata is gone after all migrations
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "file_metadata" not in tables
        assert "blocks" in tables

        engine.dispose()

    def test_idempotent_migrations(self, tmp_path):
        """Test that running migrations multiple times is safe."""
        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()

        # Initialize database
        engine1 = init_notebook_db(str(notebook_path))
        engine1.dispose()

        # Run migrations again - should be idempotent
        engine2 = init_notebook_db(str(notebook_path))

        # Verify tables still exist and are correct
        inspector = inspect(engine2)
        tables = inspector.get_table_names()

        assert "blocks" in tables
        assert "tags" in tables
        assert "block_tags" in tables
        assert "search_index" in tables

        engine2.dispose()

    def test_notebook_alembic_version(self, tmp_path):
        """Test that the correct Alembic version is applied."""
        import os

        from alembic.config import Config
        from alembic.script import ScriptDirectory

        # Determine expected head revision from the migration scripts on disk
        ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        cfg = Config(os.path.abspath(ini_path), ini_section="alembic:notebook")
        expected_head = ScriptDirectory.from_config(cfg).get_current_head()

        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()

        # Initialize database
        engine = init_notebook_db(str(notebook_path))

        # Check Alembic version table
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            assert version == expected_head

        engine.dispose()

    def test_unique_constraint_on_notebook_path(self, tmp_path):
        """Test that unique constraint on (notebook_id, path) is enforced on blocks."""
        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()

        engine = init_notebook_db(str(notebook_path))

        # Verify the unique constraint exists on blocks
        inspector = inspect(engine)
        constraints = inspector.get_unique_constraints("blocks")
        constraint_columns = [tuple(c["column_names"]) for c in constraints]
        assert ("notebook_id", "path") in constraint_columns

        engine.dispose()

    def test_migration_deduplicates_existing_rows(self, tmp_path):
        """Test that migration 005 cleans up duplicate rows before adding constraint."""
        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()
        codex_dir = notebook_path / ".codex"
        codex_dir.mkdir()

        from sqlalchemy import create_engine

        db_path = codex_dir / "notebook.db"
        old_engine = create_engine(f"sqlite:///{db_path}")

        # Create a table matching the schema at migration 004 (has properties, content_type,
        # file_type but NO unique constraint on notebook_id+path). Stamp at 004 so
        # init_notebook_db will run migration 005.
        with old_engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE file_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notebook_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    hash TEXT,
                    title TEXT,
                    description TEXT,
                    file_type TEXT,
                    properties TEXT,
                    sidecar_path TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    file_created_at TIMESTAMP,
                    file_modified_at TIMESTAMP,
                    git_tracked BOOLEAN NOT NULL DEFAULT 0,
                    last_commit_hash TEXT
                )
            """))
            conn.execute(text("CREATE INDEX ix_file_metadata_path ON file_metadata (path)"))
            conn.execute(
                text(
                    "CREATE TABLE tags (id INTEGER PRIMARY KEY, notebook_id INTEGER, name TEXT, color TEXT, created_at TIMESTAMP)"
                )
            )
            conn.execute(
                text("CREATE TABLE file_tags (file_id INTEGER, tag_id INTEGER, PRIMARY KEY (file_id, tag_id))")
            )
            conn.execute(
                text(
                    "CREATE TABLE search_index (id INTEGER PRIMARY KEY, file_id INTEGER, content TEXT, updated_at TIMESTAMP)"
                )
            )
            # Stamp as migration 004 so init_notebook_db runs migration 005
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('004')"))
            conn.commit()

            # Insert duplicate rows (same notebook_id + path)
            for i in range(3):
                conn.execute(text(f"""
                    INSERT INTO file_metadata (
                        notebook_id, path, filename, content_type, size
                    )
                    VALUES (1, 'duplicate.md', 'duplicate.md', 'text/markdown', {100 + i})
                """))
            conn.commit()

            # Confirm duplicates exist
            result = conn.execute(text("SELECT COUNT(*) FROM file_metadata WHERE path = 'duplicate.md'"))
            assert result.scalar() == 3

        old_engine.dispose()

        # Run migrations — should run 005 which deduplicates and adds constraint,
        # then later migrations merge file_metadata into blocks
        engine = init_notebook_db(str(notebook_path))

        with engine.connect() as conn:
            # file_metadata should be gone after migration 010
            inspector = inspect(engine)
            assert "file_metadata" not in inspector.get_table_names()

        engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

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

        assert "file_metadata" in tables
        assert "tags" in tables
        assert "file_tags" in tables
        assert "search_index" in tables

        # Verify the alembic_version table exists (confirms Alembic was used)
        assert "alembic_version" in tables

        # Verify file_metadata has 'properties' column (not 'frontmatter')
        columns = {col["name"] for col in inspector.get_columns("file_metadata")}
        assert "properties" in columns
        assert "frontmatter" not in columns

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

        # Verify migration was applied
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("file_metadata")}

        # Should now have 'properties' instead of 'frontmatter'
        assert "properties" in columns
        assert "frontmatter" not in columns

        # Verify data was preserved
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, properties FROM file_metadata WHERE id = 1"))
            row = result.fetchone()
            assert row is not None
            assert row[0] == 1
            assert row[1] == '{"title": "Test"}'

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

        assert "file_metadata" in tables
        assert "tags" in tables
        assert "file_tags" in tables
        assert "search_index" in tables

        engine2.dispose()

    def test_notebook_alembic_version(self, tmp_path):
        """Test that the correct Alembic version is applied."""
        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()

        # Initialize database
        engine = init_notebook_db(str(notebook_path))

        # Check Alembic version table
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            # Should be at the latest migration (004)
            assert version == "004"

        engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

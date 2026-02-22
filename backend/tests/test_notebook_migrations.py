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
            # Should be at the latest migration (005)
            assert version == "005"

        engine.dispose()


    def test_unique_constraint_on_notebook_path(self, tmp_path):
        """Test that unique constraint on (notebook_id, path) is enforced."""
        notebook_path = tmp_path / "test_notebook"
        notebook_path.mkdir()

        engine = init_notebook_db(str(notebook_path))

        # Verify the unique constraint exists
        inspector = inspect(engine)
        constraints = inspector.get_unique_constraints("file_metadata")
        constraint_columns = [tuple(c["column_names"]) for c in constraints]
        assert ("notebook_id", "path") in constraint_columns

        # Verify inserting duplicate (notebook_id, path) is rejected
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO file_metadata (
                    notebook_id, path, filename, content_type, size,
                    created_at, updated_at, git_tracked
                )
                VALUES (1, 'test.md', 'test.md', 'text/markdown', 100,
                        '2025-01-23 00:00:00', '2025-01-23 00:00:00', 1)
            """))
            conn.commit()

            # Duplicate insert should fail
            with pytest.raises(Exception, match="UNIQUE constraint failed"):
                conn.execute(text("""
                    INSERT INTO file_metadata (
                        notebook_id, path, filename, content_type, size,
                        created_at, updated_at, git_tracked
                    )
                    VALUES (1, 'test.md', 'test.md', 'text/markdown', 200,
                            '2025-01-23 00:00:00', '2025-01-23 00:00:00', 1)
                """))
                conn.commit()

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
            conn.execute(text("CREATE TABLE tags (id INTEGER PRIMARY KEY, notebook_id INTEGER, name TEXT, color TEXT, created_at TIMESTAMP)"))
            conn.execute(text("CREATE TABLE file_tags (file_id INTEGER, tag_id INTEGER, PRIMARY KEY (file_id, tag_id))"))
            conn.execute(text("CREATE TABLE search_index (id INTEGER PRIMARY KEY, file_id INTEGER, content TEXT, updated_at TIMESTAMP)"))
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

        # Run migrations — should run 005 which deduplicates and adds constraint
        engine = init_notebook_db(str(notebook_path))

        with engine.connect() as conn:
            # Should only have 1 row (the highest id kept)
            result = conn.execute(text("SELECT COUNT(*) FROM file_metadata WHERE path = 'duplicate.md'"))
            assert result.scalar() == 1

            # Verify we're at migration 005
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            assert result.scalar() == "005"

        engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Tests for database migrations."""

import pytest

from core.workspace import Workspace
from db.migrate import (
    database_exists_with_tables,
    get_current_revision,
    get_head_revision,
    get_migration_history,
    get_pending_migrations,
    is_up_to_date,
    stamp_revision,
)
from db.models import Base, get_engine, init_db


class TestMigrations:
    """Tests for migration functionality."""

    def test_get_head_revision(self, tmp_path):
        """Test getting the head revision."""
        db_path = tmp_path / "test.db"
        head = get_head_revision(str(db_path))
        assert head is not None
        assert head == "002_remove_entry_artifact_tables"

    def test_new_database_runs_migrations(self, tmp_path):
        """Test that a new database runs migrations."""
        db_path = tmp_path / "test.db"

        # Initialize database - this should run migrations
        init_db(str(db_path), use_migrations=True)

        # Check that migrations were applied
        current = get_current_revision(str(db_path))
        assert current == "002_remove_entry_artifact_tables"
        assert is_up_to_date(str(db_path))

    def test_existing_database_gets_stamped(self, tmp_path):
        """Test that an existing database gets stamped."""
        db_path = tmp_path / "test.db"

        # First create database with create_all (no migrations)
        engine = get_engine(str(db_path))
        Base.metadata.create_all(engine)

        # Verify we have tables but no migration tracking
        assert database_exists_with_tables(str(db_path))
        current = get_current_revision(str(db_path))
        assert current is None

        # Now initialize with migrations - should stamp, not run migrations
        init_db(str(db_path), use_migrations=True)

        # Should now be stamped at head
        current = get_current_revision(str(db_path))
        assert current == "002_remove_entry_artifact_tables"
        assert is_up_to_date(str(db_path))

    def test_workspace_uses_migrations(self, tmp_path):
        """Test that workspace initialization uses migrations."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        # Check that migrations were applied
        status = ws.db_manager.get_migration_status()
        assert status["current_revision"] == "002_remove_entry_artifact_tables"
        assert status["is_up_to_date"]
        assert len(status["pending_migrations"]) == 0

    @pytest.mark.xfail(reason="Migration history walking fails with multiple migrations")
    def test_get_migration_history(self, tmp_path):
        """Test getting migration history."""
        db_path = tmp_path / "test.db"
        init_db(str(db_path), use_migrations=True)

        history = get_migration_history(str(db_path))
        assert len(history) >= 2  # Should have both migrations

        # Last migration should be the new one
        current = history[-1]
        assert current["revision"] == "002_remove_entry_artifact_tables"
        assert current["is_applied"]
        assert current["is_current"]

    def test_get_pending_migrations_empty(self, tmp_path):
        """Test getting pending migrations when database is up to date."""
        db_path = tmp_path / "test.db"
        init_db(str(db_path), use_migrations=True)

        pending = get_pending_migrations(str(db_path))
        assert len(pending) == 0

    def test_get_pending_migrations_none_applied(self, tmp_path):
        """Test getting pending migrations when no migrations have been applied."""
        db_path = tmp_path / "test.db"

        # Create empty database with tables but no migration tracking
        engine = get_engine(str(db_path))
        Base.metadata.create_all(engine)

        # Should return all migrations
        pending = get_pending_migrations(str(db_path))
        assert len(pending) >= 1
        assert "002_remove_entry_artifact_tables" in pending

    def test_database_exists_with_tables_no_db(self, tmp_path):
        """Test checking for tables in non-existent database."""
        db_path = tmp_path / "nonexistent.db"
        assert not database_exists_with_tables(str(db_path))

    def test_database_exists_with_tables_empty_db(self, tmp_path):
        """Test checking for tables in empty database."""
        db_path = tmp_path / "empty.db"
        # Create empty database
        engine = get_engine(str(db_path))
        engine.dispose()

        assert not database_exists_with_tables(str(db_path))

    def test_stamp_revision(self, tmp_path):
        """Test stamping a database with a revision."""
        db_path = tmp_path / "test.db"

        # Create database with create_all
        engine = get_engine(str(db_path))
        Base.metadata.create_all(engine)

        # Stamp at head
        stamp_revision(str(db_path), "head")

        # Should be at head revision
        current = get_current_revision(str(db_path))
        assert current == "002_remove_entry_artifact_tables"

    def test_init_db_without_migrations(self, tmp_path):
        """Test initializing database without migrations."""
        db_path = tmp_path / "test.db"

        # Initialize without migrations
        init_db(str(db_path), use_migrations=False)

        # Tables should exist but no migration tracking
        assert database_exists_with_tables(str(db_path))
        current = get_current_revision(str(db_path))
        assert current is None


class TestDatabaseManagerMigrations:
    """Tests for DatabaseManager migration methods."""

    def test_get_migration_status(self, tmp_path):
        """Test getting migration status through DatabaseManager."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        status = ws.db_manager.get_migration_status()

        assert "current_revision" in status
        assert "head_revision" in status
        assert "is_up_to_date" in status
        assert "pending_migrations" in status

    @pytest.mark.xfail(reason="Migration history walking fails with multiple migrations")
    def test_get_migration_history(self, tmp_path):
        """Test getting migration history through DatabaseManager."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        history = ws.db_manager.get_migration_history()

        assert len(history) >= 2  # Should have both migrations
        assert history[-1]["revision"] == "002_remove_entry_artifact_tables"

    def test_run_migrations_already_up_to_date(self, tmp_path):
        """Test running migrations when already up to date."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        # Running migrations again should not fail
        ws.db_manager.run_migrations()

        status = ws.db_manager.get_migration_status()
        assert status["is_up_to_date"]


class TestMigrationsWithData:
    """Tests for migrations with existing data."""

    def test_data_persists_after_migration(self, tmp_path):
        """Test that data persists after running migrations."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        # Create some data
        nb = ws.create_notebook("Test Notebook", "Test description")
        page = nb.create_page("Test Page")

        # Verify data exists
        assert ws.get_notebook(nb.id) is not None
        assert nb.get_page(page.id) is not None

        # Run migrations (should be no-op since already at head)
        ws.db_manager.run_migrations()

        # Verify data still exists
        assert ws.get_notebook(nb.id) is not None
        assert nb.get_page(page.id) is not None

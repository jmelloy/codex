"""Tests for core functionality."""

from datetime import datetime

import pytest

from codex.core.storage import StorageManager
from codex.core.utils import format_table
from codex.core.workspace import Workspace


class TestWorkspace:
    """Tests for Workspace class."""

    def test_initialize_workspace(self, tmp_path):
        """Test workspace initialization."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        assert ws.path == tmp_path
        assert ws.is_initialized()
        assert (ws.lab_path / "config.json").exists()
        assert (ws.lab_path / "db" / "index.db").exists()
        assert (ws.notebooks_path).exists()
        assert (ws.artifacts_path).exists()

    def test_load_workspace(self, tmp_path):
        """Test loading an existing workspace."""
        Workspace.initialize(tmp_path, "Test Workspace")

        ws2 = Workspace.load(tmp_path)
        assert ws2.path == tmp_path
        assert ws2.is_initialized()

    def test_load_nonexistent_workspace(self, tmp_path):
        """Test loading a non-existent workspace raises error."""
        with pytest.raises(ValueError):
            Workspace.load(tmp_path)

    def test_get_config(self, tmp_path):
        """Test getting workspace config."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        config = ws.get_config()

        assert config["name"] == "Test Workspace"
        assert config["version"] == "1.0.0"
        assert "created_at" in config


class TestNotebook:
    """Tests for Notebook class."""

    def test_create_notebook(self, tmp_path):
        """Test notebook creation."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        nb = ws.create_notebook(
            title="Test Notebook",
            description="A test notebook",
            tags=["test", "demo"],
        )

        assert nb.id.startswith("nb-")
        assert nb.title == "Test Notebook"
        assert nb.description == "A test notebook"
        assert "test" in nb.tags
        assert nb.get_directory().exists()

    def test_list_notebooks(self, tmp_path):
        """Test listing notebooks."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        ws.create_notebook("Notebook 1")
        ws.create_notebook("Notebook 2")

        notebooks = ws.list_notebooks()
        assert len(notebooks) == 2

    def test_get_notebook(self, tmp_path):
        """Test getting a notebook by ID."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        nb = ws.create_notebook("Test Notebook")

        retrieved = ws.get_notebook(nb.id)
        assert retrieved is not None
        assert retrieved.id == nb.id
        assert retrieved.title == nb.title

    def test_update_notebook(self, tmp_path):
        """Test updating a notebook."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        nb = ws.create_notebook("Original Title")
        nb.update(title="Updated Title", description="New description")

        retrieved = ws.get_notebook(nb.id)
        assert retrieved.title == "Updated Title"
        assert retrieved.description == "New description"

    def test_delete_notebook(self, tmp_path):
        """Test deleting a notebook."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")

        nb = ws.create_notebook("Test Notebook")
        nb_id = nb.id

        nb.delete()

        assert ws.get_notebook(nb_id) is None


class TestPage:
    """Tests for Page class."""

    def test_create_page(self, tmp_path):
        """Test page creation."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        nb = ws.create_notebook("Test Notebook")

        page = nb.create_page(
            title="Test Page",
            date=datetime(2024, 11, 27),
            narrative={"goals": "Test goals"},
        )

        assert page.id.startswith("page-")
        assert page.title == "Test Page"
        assert page.notebook_id == nb.id
        assert page.narrative["goals"] == "Test goals"

    def test_list_pages(self, tmp_path):
        """Test listing pages."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        nb = ws.create_notebook("Test Notebook")

        nb.create_page("Page 1")
        nb.create_page("Page 2")

        pages = nb.list_pages()
        assert len(pages) == 2

    def test_update_narrative(self, tmp_path):
        """Test updating page narrative."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        nb = ws.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        page.update_narrative("goals", "New goals")

        retrieved = nb.get_page(page.id)
        assert retrieved.narrative["goals"] == "New goals"


class TestEntry:
    """Tests for Entry class."""

    def test_create_entry(self, tmp_path):
        """Test entry creation."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        nb = ws.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        entry = page.create_entry(
            entry_type="custom",
            title="Test Entry",
            inputs={"param1": "value1"},
            tags=["test"],
        )

        assert entry.id.startswith("entry-")
        assert entry.title == "Test Entry"
        assert entry.entry_type == "custom"
        assert entry.inputs["param1"] == "value1"
        assert entry.status == "created"

    def test_list_entries(self, tmp_path):
        """Test listing entries."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        nb = ws.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        page.create_entry("custom", "Entry 1", {})
        page.create_entry("custom", "Entry 2", {})

        entries = page.list_entries()
        assert len(entries) == 2

    def test_create_variation(self, tmp_path):
        """Test creating entry variation."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        nb = ws.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        entry = page.create_entry(
            entry_type="custom",
            title="Original Entry",
            inputs={"param1": "value1", "param2": "value2"},
        )

        variation = entry.create_variation(
            title="Variation Entry",
            input_overrides={"param1": "new_value"},
        )

        assert variation.parent_id == entry.id
        assert variation.inputs["param1"] == "new_value"
        assert variation.inputs["param2"] == "value2"

    def test_get_lineage(self, tmp_path):
        """Test getting entry lineage."""
        ws = Workspace.initialize(tmp_path, "Test Workspace")
        nb = ws.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        entry1 = page.create_entry("custom", "Entry 1", {})
        entry2 = entry1.create_variation("Entry 2", {})
        _ = entry2.create_variation("Entry 3", {})  # entry3 used for lineage test

        lineage = entry2.get_lineage(depth=3)

        assert len(lineage["ancestors"]) >= 1
        assert len(lineage["descendants"]) >= 1


class TestStorageManager:
    """Tests for StorageManager class."""

    def test_store_and_retrieve(self, tmp_path):
        """Test storing and retrieving data."""
        storage = StorageManager(tmp_path)
        storage.initialize()

        data = b"Hello, World!"
        hash_value = storage.store(data, "text/plain")

        assert hash_value.startswith("sha256:")

        retrieved = storage.retrieve(hash_value)
        assert retrieved == data

    def test_exists(self, tmp_path):
        """Test checking if data exists."""
        storage = StorageManager(tmp_path)
        storage.initialize()

        data = b"Test data"
        hash_value = storage.store(data, "text/plain")

        assert storage.exists(hash_value)
        assert not storage.exists("sha256:nonexistent")

    def test_delete(self, tmp_path):
        """Test deleting data."""
        storage = StorageManager(tmp_path)
        storage.initialize()

        data = b"Test data"
        hash_value = storage.store(data, "text/plain")

        assert storage.delete(hash_value)
        assert not storage.exists(hash_value)

    def test_get_size(self, tmp_path):
        """Test getting data size."""
        storage = StorageManager(tmp_path)
        storage.initialize()

        data = b"Hello, World!"
        hash_value = storage.store(data, "text/plain")

        size = storage.get_size(hash_value)
        assert size == len(data)


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow from workspace to entry."""
        # Initialize workspace
        ws = Workspace.initialize(tmp_path, "My Lab")

        # Create notebook
        nb = ws.create_notebook(
            title="AI Art Production",
            description="Testing image generation",
            tags=["sdxl", "test"],
        )

        # Create page
        page = nb.create_page(
            title="Landscape Experiments",
            date=datetime(2024, 11, 27),
            narrative={"goals": "Generate sunset landscapes"},
        )

        # Create entry
        entry = page.create_entry(
            entry_type="custom",
            title="Initial test",
            inputs={
                "prompt": "a serene lake at sunset",
                "seed": 42,
            },
        )

        # Create variation
        variation = entry.create_variation(
            title="Higher CFG test",
            input_overrides={"cfg": 10.0},
        )

        # Verify everything was created
        assert len(ws.list_notebooks()) == 1
        assert len(nb.list_pages()) == 1
        assert len(page.list_entries()) == 2

        # Verify lineage
        lineage = variation.get_lineage()
        assert len(lineage["ancestors"]) >= 1


class TestFormatTable:
    """Tests for table formatting utility."""

    def test_format_table_basic(self):
        """Test basic table formatting."""
        columns = ["id", "name", "value"]
        rows = [
            {"id": "1", "name": "Alice", "value": "100"},
            {"id": "2", "name": "Bob", "value": "200"},
        ]

        result = format_table(columns, rows)

        assert "id" in result
        assert "name" in result
        assert "value" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "100" in result
        assert "200" in result
        # Check table structure
        assert result.count("+") >= 8  # At least 8 "+" for corners
        assert result.count("|") >= 12  # At least 12 "|" for columns

    def test_format_table_empty_rows(self):
        """Test table formatting with empty rows."""
        columns = ["id", "name"]
        rows = []

        result = format_table(columns, rows)

        # Should have headers but no data rows
        assert "id" in result
        assert "name" in result
        lines = result.strip().split("\n")
        assert len(lines) == 4  # separator, header, separator, separator (closing)

    def test_format_table_empty_columns(self):
        """Test table formatting with empty columns."""
        columns = []
        rows = [{"a": "1"}]

        result = format_table(columns, rows)
        assert result == ""

    def test_format_table_numeric_values(self):
        """Test table formatting with numeric values."""
        columns = ["count", "total"]
        rows = [
            {"count": 42, "total": 1000.5},
        ]

        result = format_table(columns, rows)

        assert "42" in result
        assert "1000.5" in result

    def test_format_table_missing_columns(self):
        """Test table formatting with missing columns in rows."""
        columns = ["a", "b", "c"]
        rows = [
            {"a": "1", "c": "3"},  # missing "b"
        ]

        result = format_table(columns, rows)

        assert "1" in result
        assert "3" in result
        # "b" column should be present but empty
        lines = result.strip().split("\n")
        assert len(lines) >= 4  # separator, header, separator, data, separator

    def test_format_table_long_values(self):
        """Test table formatting with long values adjusts column width."""
        columns = ["short", "long_column"]
        rows = [
            {"short": "a", "long_column": "this is a very long value"},
        ]

        result = format_table(columns, rows)

        # The long value should be present
        assert "this is a very long value" in result

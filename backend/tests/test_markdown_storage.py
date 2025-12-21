"""Tests for markdown-based storage."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from core.markdown_storage import (
    MarkdownNotebook,
    MarkdownPage,
    MarkdownWorkspace,
)


class TestMarkdownWorkspace:
    """Test markdown workspace."""

    def test_initialize_workspace(self):
        """Test initializing a new workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = MarkdownWorkspace.initialize(Path(tmpdir), "Test Workspace")
            
            assert ws.path.exists()
            assert ws.notebooks_path.exists()
            assert ws.artifacts_path.exists()
            assert ws.config_file.exists()
            
            # Check config content
            import yaml
            with open(ws.config_file) as f:
                config = yaml.safe_load(f)
            assert config["name"] == "Test Workspace"
            assert config["storage_type"] == "markdown"

    def test_create_notebook(self):
        """Test creating a notebook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = MarkdownWorkspace.initialize(Path(tmpdir), "Test Workspace")
            
            notebook = ws.create_notebook(
                "Test Notebook",
                "This is a test notebook",
                tags=["test", "example"]
            )
            
            assert notebook.id.startswith("nb-")
            assert notebook.title == "Test Notebook"
            assert notebook.description == "This is a test notebook"
            assert notebook.tags == ["test", "example"]
            assert notebook.path.exists()
            assert notebook.index_file.exists()

    def test_list_notebooks(self):
        """Test listing notebooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = MarkdownWorkspace.initialize(Path(tmpdir), "Test Workspace")
            
            # Create notebooks
            nb1 = ws.create_notebook("Notebook 1")
            nb2 = ws.create_notebook("Notebook 2")
            
            # List notebooks
            notebooks = ws.list_notebooks()
            assert len(notebooks) == 2
            
            notebook_ids = [nb.id for nb in notebooks]
            assert nb1.id in notebook_ids
            assert nb2.id in notebook_ids

    def test_get_notebook(self):
        """Test getting a notebook by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = MarkdownWorkspace.initialize(Path(tmpdir), "Test Workspace")
            
            nb = ws.create_notebook("Test Notebook")
            
            # Get notebook
            retrieved = ws.get_notebook(nb.id)
            assert retrieved is not None
            assert retrieved.id == nb.id
            assert retrieved.title == nb.title


class TestMarkdownNotebook:
    """Test markdown notebook."""

    def test_create_notebook(self):
        """Test creating a notebook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "My Notebook",
                "Description here",
                tags=["tag1", "tag2"]
            )
            
            assert notebook.id.startswith("nb-")
            assert notebook.title == "My Notebook"
            assert notebook.description == "Description here"
            assert notebook.tags == ["tag1", "tag2"]
            assert notebook.path.exists()
            assert notebook.index_file.exists()

    def test_save_and_load(self):
        """Test saving and loading a notebook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and save
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Test description"
            )
            original_id = notebook.id
            
            # Load from file
            loaded = MarkdownNotebook(notebook.path)
            assert loaded.id == original_id
            assert loaded.title == "Test Notebook"
            assert loaded.description == "Test description"

    def test_create_page(self):
        """Test creating a page in a notebook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            page = notebook.create_page(
                "Test Page",
                narrative={"goals": "Test goals"}
            )
            
            assert page.id.startswith("page-")
            assert page.title == "Test Page"
            assert page.notebook_id == notebook.id
            assert page.narrative["goals"] == "Test goals"
            assert page.path.exists()

    def test_list_pages(self):
        """Test listing pages in a notebook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            # Create pages
            page1 = notebook.create_page("Page 1")
            page2 = notebook.create_page("Page 2")
            
            # List pages
            pages = notebook.list_pages()
            assert len(pages) == 2

    def test_get_page(self):
        """Test getting a page by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            page = notebook.create_page("Test Page")
            
            # Get page
            retrieved = notebook.get_page(page.id)
            assert retrieved is not None
            assert retrieved.id == page.id
            assert retrieved.title == page.title

    def test_to_dict(self):
        """Test converting notebook to dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description",
                tags=["tag1"]
            )
            
            data = notebook.to_dict()
            assert data["id"] == notebook.id
            assert data["title"] == "Test Notebook"
            assert data["description"] == "Description"
            assert data["tags"] == ["tag1"]


class TestMarkdownPage:
    """Test markdown page."""

    def test_create_page(self):
        """Test creating a page."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            page = MarkdownPage.create(
                notebook,
                "My Page",
                narrative={
                    "goals": "Test goals",
                    "hypothesis": "Test hypothesis"
                }
            )
            
            assert page.id.startswith("page-")
            assert page.title == "My Page"
            assert page.notebook_id == notebook.id
            assert page.narrative["goals"] == "Test goals"
            assert page.narrative["hypothesis"] == "Test hypothesis"
            assert page.path.exists()

    def test_save_and_load(self):
        """Test saving and loading a page."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            # Create and save
            page = MarkdownPage.create(
                notebook,
                "Test Page",
                narrative={"goals": "Test goals"}
            )
            original_id = page.id
            
            # Load from file
            loaded = MarkdownPage(page.path)
            assert loaded.id == original_id
            assert loaded.title == "Test Page"
            assert loaded.narrative["goals"] == "Test goals"

    def test_update_narrative(self):
        """Test updating narrative fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            page = MarkdownPage.create(notebook, "Test Page")
            
            # Update narrative
            page.update_narrative("goals", "Updated goals")
            page.update_narrative("observations", "New observations")
            
            # Reload and check
            reloaded = MarkdownPage(page.path)
            assert reloaded.narrative["goals"] == "Updated goals"
            assert reloaded.narrative["observations"] == "New observations"

    def test_add_entry(self):
        """Test adding an entry to a page."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            page = MarkdownPage.create(notebook, "Test Page")
            
            # Add entry
            entry_data = {
                "id": "entry-123",
                "title": "Test Entry",
                "entry_type": "custom",
                "created_at": datetime.utcnow().isoformat(),
                "status": "completed",
                "inputs": {"param": "value"},
                "outputs": {"result": "success"},
            }
            page.add_entry(entry_data)
            
            # Reload and check
            reloaded = MarkdownPage(page.path)
            assert len(reloaded.entries) == 1
            assert reloaded.entries[0]["id"] == "entry-123"
            assert reloaded.entries[0]["title"] == "Test Entry"

    def test_to_dict(self):
        """Test converting page to dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notebook = MarkdownNotebook.create(
                Path(tmpdir),
                "Test Notebook",
                "Description"
            )
            
            page = MarkdownPage.create(
                notebook,
                "Test Page",
                narrative={"goals": "Test goals"}
            )
            
            data = page.to_dict()
            assert data["id"] == page.id
            assert data["title"] == "Test Page"
            assert data["notebook_id"] == notebook.id
            assert data["narrative"]["goals"] == "Test goals"


class TestMarkdownIntegration:
    """Integration tests for markdown storage."""

    def test_complete_workflow(self):
        """Test complete workflow: workspace -> notebook -> page -> entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize workspace
            ws = MarkdownWorkspace.initialize(Path(tmpdir), "Test Workspace")
            
            # Create notebook
            notebook = ws.create_notebook(
                "Project Alpha",
                "Research project",
                tags=["research", "alpha"]
            )
            
            # Create page
            page = notebook.create_page(
                "Day 1 Experiments",
                narrative={
                    "goals": "Test initial hypothesis",
                    "hypothesis": "Parameter X affects output Y",
                }
            )
            
            # Add entry
            entry_data = {
                "id": "entry-001",
                "title": "Experiment 1",
                "entry_type": "api_call",
                "created_at": datetime.utcnow().isoformat(),
                "status": "completed",
                "inputs": {"url": "https://api.example.com", "method": "GET"},
                "outputs": {"status_code": 200, "body": "Success"},
                "artifacts": [
                    {"type": "application/json", "path": "artifacts/response.json"}
                ],
            }
            page.add_entry(entry_data)
            
            # Verify everything is saved
            assert notebook.path.exists()
            assert notebook.index_file.exists()
            assert page.path.exists()
            
            # Reload from disk
            ws2 = MarkdownWorkspace(Path(tmpdir))
            notebooks = ws2.list_notebooks()
            assert len(notebooks) == 1
            
            nb2 = notebooks[0]
            assert nb2.title == "Project Alpha"
            
            pages = nb2.list_pages()
            assert len(pages) == 1
            
            page2 = MarkdownPage(pages[0])
            assert page2.title == "Day 1 Experiments"
            assert len(page2.entries) == 1
            assert page2.entries[0]["title"] == "Experiment 1"

    def test_multiple_notebooks_and_pages(self):
        """Test handling multiple notebooks and pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = MarkdownWorkspace.initialize(Path(tmpdir), "Test Workspace")
            
            # Create multiple notebooks
            nb1 = ws.create_notebook("Notebook 1")
            nb2 = ws.create_notebook("Notebook 2")
            
            # Create pages in each notebook
            page1_1 = nb1.create_page("Page 1.1")
            page1_2 = nb1.create_page("Page 1.2")
            page2_1 = nb2.create_page("Page 2.1")
            
            # Verify structure
            assert len(ws.list_notebooks()) == 2
            assert len(nb1.list_pages()) == 2
            assert len(nb2.list_pages()) == 1

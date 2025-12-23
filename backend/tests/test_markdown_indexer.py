"""Tests for markdown file indexing."""

import json
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.markdown_indexer import (
    compute_file_hash,
    index_directory,
    index_markdown_file,
    remove_stale_entries,
    search_markdown_files,
)
from db.models import Base, MarkdownFile


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        notebooks = workspace / "notebooks"
        notebooks.mkdir()
        yield workspace


@pytest.fixture
def db_session(temp_workspace):
    """Create a test database session."""
    db_path = temp_workspace / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_compute_file_hash(temp_workspace):
    """Test file hash computation."""
    test_file = temp_workspace / "test.txt"
    test_file.write_text("hello world")
    
    hash1 = compute_file_hash(test_file)
    hash2 = compute_file_hash(test_file)
    
    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex string
    
    # Different content should produce different hash
    test_file.write_text("different content")
    hash3 = compute_file_hash(test_file)
    assert hash1 != hash3


def test_index_markdown_file(temp_workspace, db_session):
    """Test indexing a single markdown file."""
    notebooks = temp_workspace / "notebooks"
    test_file = notebooks / "test.md"
    test_file.write_text("""---
title: Test Document
author: Test Author
tags:
  - test
  - markdown
---

# Test Content

This is a test markdown file.
""")
    
    result = index_markdown_file(db_session, test_file, notebooks)
    
    assert result is not None
    assert result.title == "Test Document"
    assert result.relative_path == "test.md"
    assert result.file_size > 0
    
    # Check frontmatter is stored as JSON
    frontmatter = json.loads(result.frontmatter)
    assert frontmatter["title"] == "Test Document"
    assert frontmatter["author"] == "Test Author"
    assert "test" in frontmatter["tags"]


def test_index_markdown_file_no_frontmatter(temp_workspace, db_session):
    """Test indexing a markdown file without frontmatter."""
    notebooks = temp_workspace / "notebooks"
    test_file = notebooks / "simple.md"
    test_file.write_text("# Simple Document\n\nJust some content.")
    
    result = index_markdown_file(db_session, test_file, notebooks)
    
    assert result is not None
    assert result.title == "simple"  # Falls back to filename
    assert result.frontmatter == "{}"  # Empty frontmatter


def test_index_markdown_file_updates(temp_workspace, db_session):
    """Test that updating a file triggers re-indexing."""
    notebooks = temp_workspace / "notebooks"
    test_file = notebooks / "update-test.md"
    test_file.write_text("""---
title: Original Title
---

Original content.
""")
    
    # Index first version
    result1 = index_markdown_file(db_session, test_file, notebooks)
    original_hash = result1.file_hash
    
    # Modify file
    test_file.write_text("""---
title: Updated Title
---

Updated content.
""")
    
    # Index again
    result2 = index_markdown_file(db_session, test_file, notebooks)
    
    assert result2.id == result1.id  # Same record
    assert result2.title == "Updated Title"
    assert result2.file_hash != original_hash  # Hash changed


def test_index_directory(temp_workspace, db_session):
    """Test indexing a directory of markdown files."""
    notebooks = temp_workspace / "notebooks"
    
    # Create multiple files
    (notebooks / "file1.md").write_text("---\ntitle: File 1\n---\n# File 1")
    (notebooks / "file2.md").write_text("---\ntitle: File 2\n---\n# File 2")
    (notebooks / "file3.txt").write_text("Not a markdown file")
    
    # Create subdirectory with more files
    subdir = notebooks / "subdir"
    subdir.mkdir()
    (subdir / "file4.md").write_text("---\ntitle: File 4\n---\n# File 4")
    
    # Index directory
    count = index_directory(db_session, notebooks, notebooks, recursive=True)
    
    assert count == 3  # Only markdown files
    
    # Verify all files are indexed
    all_files = db_session.query(MarkdownFile).all()
    assert len(all_files) == 3
    
    titles = {f.title for f in all_files}
    assert titles == {"File 1", "File 2", "File 4"}


def test_index_directory_non_recursive(temp_workspace, db_session):
    """Test non-recursive directory indexing."""
    notebooks = temp_workspace / "notebooks"
    
    (notebooks / "root.md").write_text("---\ntitle: Root\n---\n# Root")
    
    subdir = notebooks / "subdir"
    subdir.mkdir()
    (subdir / "nested.md").write_text("---\ntitle: Nested\n---\n# Nested")
    
    # Index non-recursively
    count = index_directory(db_session, notebooks, notebooks, recursive=False)
    
    assert count == 1  # Only root file
    
    all_files = db_session.query(MarkdownFile).all()
    assert len(all_files) == 1
    assert all_files[0].title == "Root"


def test_search_markdown_files(temp_workspace, db_session):
    """Test searching indexed markdown files."""
    notebooks = temp_workspace / "notebooks"
    
    # Create files with different content
    (notebooks / "python.md").write_text("---\ntitle: Python Guide\ntags: [python, programming]\n---\n# Python")
    (notebooks / "javascript.md").write_text("---\ntitle: JavaScript Guide\ntags: [javascript, programming]\n---\n# JS")
    (notebooks / "readme.md").write_text("---\ntitle: README\n---\n# Project")
    
    # Index all files
    index_directory(db_session, notebooks, notebooks)
    
    # Search by title
    results = search_markdown_files(db_session, query="python")
    assert len(results) == 1
    assert results[0]["title"] == "Python Guide"
    
    # Search by tag
    results = search_markdown_files(db_session, query="programming")
    assert len(results) == 2
    
    # Search with no query returns all
    results = search_markdown_files(db_session, query=None, limit=100)
    assert len(results) == 3


def test_remove_stale_entries(temp_workspace, db_session):
    """Test removing index entries for deleted files."""
    notebooks = temp_workspace / "notebooks"
    
    # Create and index a file
    test_file = notebooks / "temp.md"
    test_file.write_text("---\ntitle: Temporary\n---\n# Temp")
    index_markdown_file(db_session, test_file, notebooks)
    
    # Verify it's indexed
    assert db_session.query(MarkdownFile).count() == 1
    
    # Delete the file
    test_file.unlink()
    
    # Remove stale entries
    removed = remove_stale_entries(db_session, notebooks)
    
    assert removed == 1
    assert db_session.query(MarkdownFile).count() == 0


def test_index_skips_hidden_files(temp_workspace, db_session):
    """Test that hidden files are not indexed."""
    notebooks = temp_workspace / "notebooks"
    
    (notebooks / "visible.md").write_text("---\ntitle: Visible\n---\n# Visible")
    (notebooks / ".hidden.md").write_text("---\ntitle: Hidden\n---\n# Hidden")
    
    count = index_directory(db_session, notebooks, notebooks)
    
    assert count == 1  # Only visible file
    
    all_files = db_session.query(MarkdownFile).all()
    assert len(all_files) == 1
    assert all_files[0].title == "Visible"

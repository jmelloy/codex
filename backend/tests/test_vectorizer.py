"""Tests for page vectorization and search."""

import json
import os
import sqlite3
import tempfile

import pytest
from sqlmodel import Session, create_engine, select

from codex.core.vectorizer import (
    _serialize_f32,
    _deserialize_f32,
    build_page_text,
    ensure_search_tables,
    index_page_fts,
    delete_page_fts,
    search_by_fts,
)
from codex.db.models.notebook import Block


@pytest.fixture
def notebook_dir():
    """Create a temporary notebook directory with a .codex database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        codex_dir = os.path.join(tmpdir, ".codex")
        os.makedirs(codex_dir)
        db_path = os.path.join(codex_dir, "notebook.db")
        engine = create_engine(f"sqlite:///{db_path}")

        # Create tables
        from sqlmodel import SQLModel
        from codex.db.models.notebook import Block, Tag, BlockTag, SearchIndex

        SQLModel.metadata.create_all(engine)

        yield tmpdir, engine, db_path


def test_serialize_deserialize_f32():
    """Test vector serialization roundtrip."""
    original = [0.1, 0.2, 0.3, 0.4, 0.5]
    serialized = _serialize_f32(original)
    deserialized = _deserialize_f32(serialized)
    assert len(deserialized) == len(original)
    for a, b in zip(deserialized, original):
        assert abs(a - b) < 1e-6


def test_serialize_list_roundtrip():
    """Test serialization of a float list."""
    values = [1.0, 2.0, 3.0]
    serialized = _serialize_f32(values)
    deserialized = _deserialize_f32(serialized)
    assert deserialized == values


def test_ensure_search_tables(notebook_dir):
    """Test that FTS5 and vec0 tables are created."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'shadow')"
            ).fetchall()
        }
        # FTS5 creates shadow tables
        assert "pages_fts" in tables
        # vec0 table
        assert "page_embeddings" in tables
    finally:
        conn.close()


def test_ensure_search_tables_idempotent(notebook_dir):
    """Test that calling ensure_search_tables twice doesn't fail."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)
    ensure_search_tables(engine)  # Should not raise


def test_index_page_fts(notebook_dir):
    """Test FTS indexing of a page."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    session = Session(engine)
    block = Block(
        notebook_id=1,
        block_id="test-block-1",
        path="my-page",
        block_type="page",
        title="Test Page Title",
        description="A description about quantum computing",
        properties=json.dumps({"status": "draft", "author": "Alice"}),
    )
    session.add(block)
    session.commit()

    index_page_fts(engine, block, "Full content of the page about quantum computing")

    # Verify FTS index
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT block_id, title FROM pages_fts WHERE pages_fts MATCH 'quantum'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "test-block-1"
    finally:
        conn.close()
    session.close()


def test_search_by_fts_title(notebook_dir):
    """Test FTS search matches on title."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    session = Session(engine)
    block = Block(
        notebook_id=1,
        block_id="block-title-1",
        path="page-1",
        block_type="page",
        title="Machine Learning Experiments",
        description="Training neural networks",
    )
    session.add(block)
    session.commit()

    index_page_fts(engine, block, "Training neural networks with PyTorch")

    results = search_by_fts(engine, "machine learning")
    assert len(results) >= 1
    assert results[0][0] == "block-title-1"
    session.close()


def test_search_by_fts_properties(notebook_dir):
    """Test FTS search matches on properties."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    session = Session(engine)
    block = Block(
        notebook_id=1,
        block_id="block-props-1",
        path="page-2",
        block_type="page",
        title="My Experiment",
        properties=json.dumps({"category": "biology", "organism": "drosophila"}),
    )
    session.add(block)
    session.commit()

    index_page_fts(engine, block, "Studying fruit fly genetics")

    results = search_by_fts(engine, "drosophila")
    assert len(results) >= 1
    assert results[0][0] == "block-props-1"
    session.close()


def test_search_by_fts_content(notebook_dir):
    """Test FTS search matches on child content."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    session = Session(engine)
    block = Block(
        notebook_id=1,
        block_id="block-content-1",
        path="page-3",
        block_type="page",
        title="Notes",
    )
    session.add(block)
    session.commit()

    index_page_fts(engine, block, "The mitochondria is the powerhouse of the cell")

    results = search_by_fts(engine, "mitochondria")
    assert len(results) >= 1
    assert results[0][0] == "block-content-1"
    session.close()


def test_delete_page_fts(notebook_dir):
    """Test deletion from FTS index."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    session = Session(engine)
    block = Block(
        notebook_id=1,
        block_id="block-del-1",
        path="page-4",
        block_type="page",
        title="Deletable Page",
    )
    session.add(block)
    session.commit()

    index_page_fts(engine, block, "Some searchable content")
    results = search_by_fts(engine, "deletable")
    assert len(results) >= 1

    delete_page_fts(engine, "block-del-1")
    results = search_by_fts(engine, "deletable")
    assert len(results) == 0
    session.close()


def test_build_page_text(notebook_dir):
    """Test text assembly for a page."""
    tmpdir, engine, db_path = notebook_dir

    session = Session(engine)
    page = Block(
        notebook_id=1,
        block_id="page-text-1",
        path="my-page",
        block_type="page",
        title="My Research",
        description="Important findings",
        properties=json.dumps({"status": "published", "tags": ["science", "research"]}),
    )
    session.add(page)

    # Create a child text block with a file on disk
    child = Block(
        notebook_id=1,
        block_id="child-text-1",
        parent_block_id="page-text-1",
        path="my-page/notes.md",
        block_type="text",
        content_type="text/markdown",
    )
    session.add(child)
    session.commit()

    # Create the file on disk
    page_dir = os.path.join(tmpdir, "my-page")
    os.makedirs(page_dir, exist_ok=True)
    with open(os.path.join(page_dir, "notes.md"), "w") as f:
        f.write("# Detailed notes\nThese are my detailed research notes.")

    text = build_page_text(page, tmpdir, session)

    assert "My Research" in text
    assert "Important findings" in text
    assert "published" in text
    assert "Detailed notes" in text
    session.close()


def test_fts_update_reindex(notebook_dir):
    """Test that re-indexing a page updates FTS."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    session = Session(engine)
    block = Block(
        notebook_id=1,
        block_id="block-reindex-1",
        path="page-5",
        block_type="page",
        title="Original Title",
    )
    session.add(block)
    session.commit()

    index_page_fts(engine, block, "Original content")
    results = search_by_fts(engine, "original")
    assert len(results) >= 1

    # Update and reindex
    block.title = "Updated Title"
    session.commit()
    index_page_fts(engine, block, "Updated content about physics")

    results = search_by_fts(engine, "physics")
    assert len(results) >= 1
    assert results[0][0] == "block-reindex-1"

    # Old content should no longer match
    results = search_by_fts(engine, "original")
    assert len(results) == 0
    session.close()


def test_multiple_pages_ranked(notebook_dir):
    """Test that FTS returns multiple results ranked by relevance."""
    tmpdir, engine, db_path = notebook_dir
    ensure_search_tables(engine)

    session = Session(engine)
    blocks = []
    for i in range(3):
        b = Block(
            notebook_id=1,
            block_id=f"ranked-{i}",
            path=f"page-ranked-{i}",
            block_type="page",
            title=f"Page {i}",
        )
        session.add(b)
        blocks.append(b)
    session.commit()

    # First page mentions "python" many times
    index_page_fts(engine, blocks[0], "Python programming. Python is great. Python python python.")
    # Second page mentions it once
    index_page_fts(engine, blocks[1], "I once used Python for a script.")
    # Third page doesn't mention it
    index_page_fts(engine, blocks[2], "JavaScript and TypeScript are fun.")

    results = search_by_fts(engine, "python")
    assert len(results) >= 2
    # Block IDs that matched
    matched_ids = [r[0] for r in results]
    assert "ranked-0" in matched_ids
    assert "ranked-1" in matched_ids
    assert "ranked-2" not in matched_ids
    session.close()

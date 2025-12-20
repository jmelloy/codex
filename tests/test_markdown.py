"""Tests for markdown format utilities."""

import tempfile
from pathlib import Path

import pytest

from codex.core.markdown import (
    MarkdownDocument,
    parse_markdown_file,
    write_markdown_file,
)


class TestMarkdownDocument:
    """Test MarkdownDocument class."""

    def test_parse_empty_document(self):
        """Test parsing an empty document."""
        doc = MarkdownDocument.parse("")
        assert doc.frontmatter == {}
        assert doc.blocks == []
        assert doc.content == ""

    def test_parse_frontmatter_only(self):
        """Test parsing a document with only frontmatter."""
        text = """---
title: Test Document
author: Test Author
tags:
  - test
  - markdown
---
"""
        doc = MarkdownDocument.parse(text)
        assert doc.frontmatter["title"] == "Test Document"
        assert doc.frontmatter["author"] == "Test Author"
        assert doc.frontmatter["tags"] == ["test", "markdown"]
        assert doc.content == ""
        assert doc.blocks == []

    def test_parse_content_only(self):
        """Test parsing a document with only content."""
        text = "This is some markdown content.\n\n## Heading\n\nMore content."
        doc = MarkdownDocument.parse(text)
        assert doc.frontmatter == {}
        assert doc.blocks == []
        assert "This is some markdown content" in doc.content

    def test_parse_blocks_only(self):
        """Test parsing a document with only blocks."""
        text = """
::: information
This is an information block.
:::

::: warning
This is a warning block.
:::
"""
        doc = MarkdownDocument.parse(text)
        assert len(doc.blocks) == 2
        assert doc.blocks[0]["type"] == "information"
        assert "information block" in doc.blocks[0]["content"]
        assert doc.blocks[1]["type"] == "warning"
        assert "warning block" in doc.blocks[1]["content"]

    def test_parse_complete_document(self):
        """Test parsing a complete document with all elements."""
        text = """---
title: Complete Document
version: 1.0
---

# Main Content

This is the main markdown content.

::: note
This is a note block.
:::

More content here.

::: code
print("Hello, World!")
:::
"""
        doc = MarkdownDocument.parse(text)
        assert doc.frontmatter["title"] == "Complete Document"
        assert doc.frontmatter["version"] == 1.0
        assert "Main Content" in doc.content
        assert len(doc.blocks) == 2
        assert doc.blocks[0]["type"] == "note"
        assert doc.blocks[1]["type"] == "code"

    def test_to_markdown_empty(self):
        """Test converting empty document to markdown."""
        doc = MarkdownDocument()
        result = doc.to_markdown()
        assert result == "\n"

    def test_to_markdown_frontmatter(self):
        """Test converting document with frontmatter to markdown."""
        doc = MarkdownDocument(frontmatter={"title": "Test", "count": 42})
        result = doc.to_markdown()
        assert "---" in result
        assert "title: Test" in result
        assert "count: 42" in result

    def test_to_markdown_content(self):
        """Test converting document with content to markdown."""
        doc = MarkdownDocument(content="# Heading\n\nContent here.")
        result = doc.to_markdown()
        assert "# Heading" in result
        assert "Content here." in result

    def test_to_markdown_blocks(self):
        """Test converting document with blocks to markdown."""
        doc = MarkdownDocument(
            blocks=[
                {"type": "info", "content": "Information here"},
                {"type": "warning", "content": "Warning here"},
            ]
        )
        result = doc.to_markdown()
        assert "::: info" in result
        assert "Information here" in result
        assert "::: warning" in result
        assert "Warning here" in result
        assert result.count(":::") == 4  # 2 opening, 2 closing

    def test_to_markdown_complete(self):
        """Test converting a complete document to markdown."""
        doc = MarkdownDocument(
            frontmatter={"title": "Test Doc"},
            content="# Content",
            blocks=[{"type": "note", "content": "A note"}],
        )
        result = doc.to_markdown()
        assert "---" in result
        assert "title: Test Doc" in result
        assert "# Content" in result
        assert "::: note" in result
        assert "A note" in result

    def test_roundtrip_parsing(self):
        """Test that parsing and converting back produces equivalent document."""
        original_text = """---
title: Roundtrip Test
version: 1.0
---

# Main Content

This is some content.

::: note
A note block.
:::

More content.

::: code
Some code here.
:::
"""
        # Parse original
        doc = MarkdownDocument.parse(original_text)
        
        # Convert back to markdown
        result = doc.to_markdown()
        
        # Parse again
        doc2 = MarkdownDocument.parse(result)
        
        # Compare
        assert doc.frontmatter == doc2.frontmatter
        assert len(doc.blocks) == len(doc2.blocks)
        for b1, b2 in zip(doc.blocks, doc2.blocks):
            assert b1["type"] == b2["type"]
            assert b1["content"].strip() == b2["content"].strip()

    def test_get_block(self):
        """Test getting a specific block."""
        doc = MarkdownDocument(
            blocks=[
                {"type": "info", "content": "Info content"},
                {"type": "warning", "content": "Warning content"},
            ]
        )
        assert doc.get_block("info") == "Info content"
        assert doc.get_block("warning") == "Warning content"
        assert doc.get_block("nonexistent") is None

    def test_get_all_blocks(self):
        """Test getting all blocks of a type."""
        doc = MarkdownDocument(
            blocks=[
                {"type": "note", "content": "Note 1"},
                {"type": "info", "content": "Info 1"},
                {"type": "note", "content": "Note 2"},
            ]
        )
        notes = doc.get_all_blocks("note")
        assert len(notes) == 2
        assert "Note 1" in notes
        assert "Note 2" in notes
        
        info = doc.get_all_blocks("info")
        assert len(info) == 1
        assert "Info 1" in info

    def test_add_block(self):
        """Test adding a block to a document."""
        doc = MarkdownDocument()
        doc.add_block("note", "A new note")
        assert len(doc.blocks) == 1
        assert doc.blocks[0]["type"] == "note"
        assert doc.blocks[0]["content"] == "A new note"

    def test_set_frontmatter(self):
        """Test setting frontmatter properties."""
        doc = MarkdownDocument()
        doc.set_frontmatter("title", "New Title")
        doc.set_frontmatter("version", 2.0)
        assert doc.frontmatter["title"] == "New Title"
        assert doc.frontmatter["version"] == 2.0

    def test_get_frontmatter(self):
        """Test getting frontmatter properties."""
        doc = MarkdownDocument(frontmatter={"title": "Test", "count": 5})
        assert doc.get_frontmatter("title") == "Test"
        assert doc.get_frontmatter("count") == 5
        assert doc.get_frontmatter("nonexistent") is None
        assert doc.get_frontmatter("nonexistent", "default") == "default"


class TestMarkdownFileOperations:
    """Test file operations."""

    def test_parse_markdown_file(self):
        """Test parsing a markdown file from disk."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\ntitle: Test\n---\n\n# Content\n\n::: note\nA note\n:::")
            temp_path = f.name

        try:
            doc = parse_markdown_file(temp_path)
            assert doc.frontmatter["title"] == "Test"
            assert "# Content" in doc.content
            assert len(doc.blocks) == 1
            assert doc.blocks[0]["type"] == "note"
        finally:
            Path(temp_path).unlink()

    def test_write_markdown_file(self):
        """Test writing a markdown document to a file."""
        doc = MarkdownDocument(
            frontmatter={"title": "Write Test"},
            content="# Content here",
            blocks=[{"type": "info", "content": "Info block"}],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = f.name

        try:
            write_markdown_file(temp_path, doc)
            
            # Read back and verify
            with open(temp_path, "r") as f:
                content = f.read()
            
            assert "title: Write Test" in content
            assert "# Content here" in content
            assert "::: info" in content
            assert "Info block" in content
        finally:
            Path(temp_path).unlink()

    def test_file_roundtrip(self):
        """Test writing and reading back a file."""
        original_doc = MarkdownDocument(
            frontmatter={"title": "Roundtrip", "version": 1},
            content="# Test Content\n\nSome text.",
            blocks=[{"type": "note", "content": "Note content"}],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = f.name

        try:
            write_markdown_file(temp_path, original_doc)
            loaded_doc = parse_markdown_file(temp_path)
            
            assert original_doc.frontmatter == loaded_doc.frontmatter
            assert original_doc.content.strip() == loaded_doc.content.strip()
            assert len(original_doc.blocks) == len(loaded_doc.blocks)
        finally:
            Path(temp_path).unlink()

"""Test for /content and /text endpoints with frontmatter handling."""

import pytest
from codex.core.metadata import MetadataParser


def test_frontmatter_parsing():
    """Test that MetadataParser.parse_frontmatter strips frontmatter correctly."""
    
    # Test with frontmatter
    markdown_with_frontmatter = """---
title: Test Document
author: Test Author
tags: [test, example]
---

# Main Content

This is the actual content of the markdown file.
"""
    
    metadata, content = MetadataParser.parse_frontmatter(markdown_with_frontmatter)
    
    assert "title" in metadata
    assert metadata["title"] == "Test Document"
    assert "author" in metadata
    assert metadata["author"] == "Test Author"
    assert "# Main Content" in content
    assert "---" not in content  # Frontmatter should be stripped
    assert "title:" not in content  # YAML keys should be stripped


def test_no_frontmatter_parsing():
    """Test that files without frontmatter are handled correctly."""
    
    markdown_no_frontmatter = """# Main Content

This is content without any frontmatter.
"""
    
    metadata, content = MetadataParser.parse_frontmatter(markdown_no_frontmatter)
    
    assert metadata == {}
    assert "# Main Content" in content
    # Content should be the same (may have slight whitespace differences)
    assert content.strip() == markdown_no_frontmatter.strip()


def test_empty_frontmatter_parsing():
    """Test that empty frontmatter is handled correctly."""
    
    markdown_empty_frontmatter = """---
---

# Main Content

Content after empty frontmatter.
"""
    
    metadata, content = MetadataParser.parse_frontmatter(markdown_empty_frontmatter)
    
    assert metadata == {}
    assert "# Main Content" in content
    assert "---" not in content


def test_complex_frontmatter_parsing():
    """Test parsing complex frontmatter with nested structures."""
    
    markdown_complex = """---
title: Complex Document
metadata:
  author: John Doe
  date: 2024-01-01
tags:
  - python
  - testing
  - yaml
config:
  enabled: true
  timeout: 30
---

# Document Body

Complex frontmatter test.
"""
    
    metadata, content = MetadataParser.parse_frontmatter(markdown_complex)
    
    assert "title" in metadata
    assert metadata["title"] == "Complex Document"
    assert "metadata" in metadata
    assert isinstance(metadata["metadata"], dict)
    assert metadata["metadata"]["author"] == "John Doe"
    assert "tags" in metadata
    assert isinstance(metadata["tags"], list)
    assert len(metadata["tags"]) == 3
    assert "# Document Body" in content
    assert "---" not in content


if __name__ == "__main__":
    # Run tests directly
    test_frontmatter_parsing()
    print("✓ test_frontmatter_parsing passed")
    
    test_no_frontmatter_parsing()
    print("✓ test_no_frontmatter_parsing passed")
    
    test_empty_frontmatter_parsing()
    print("✓ test_empty_frontmatter_parsing passed")
    
    test_complex_frontmatter_parsing()
    print("✓ test_complex_frontmatter_parsing passed")
    
    print("\nAll tests passed!")

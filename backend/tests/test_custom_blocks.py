"""Tests for custom block parser."""

import pytest

from codex.core.custom_blocks import CustomBlock, CustomBlockParser


def test_parse_simple_weather_block():
    """Test parsing a simple weather block."""
    markdown = """
# Test Document

Some content here.

```weather
location: San Francisco
units: imperial
```

More content.
"""

    parser = CustomBlockParser(available_block_types=["weather"])
    blocks = parser.parse(markdown)

    assert len(blocks) == 1
    assert blocks[0].block_type == "weather"
    assert blocks[0].config["location"] == "San Francisco"
    assert blocks[0].config["units"] == "imperial"
    assert "```weather" in blocks[0].raw_content


def test_parse_link_preview_block():
    """Test parsing a link preview block."""
    markdown = """
```link-preview
url: https://example.com
```
"""

    parser = CustomBlockParser(available_block_types=["link-preview"])
    blocks = parser.parse(markdown)

    assert len(blocks) == 1
    assert blocks[0].block_type == "link-preview"
    assert blocks[0].config["url"] == "https://example.com"


def test_ignores_standard_code_blocks():
    """Test that standard code language blocks are ignored."""
    markdown = """
```python
def hello():
    print("world")
```

```javascript
console.log("hello");
```

```weather
location: Tokyo
```
"""

    parser = CustomBlockParser(available_block_types=["weather"])
    blocks = parser.parse(markdown)

    # Should only find the weather block, not python or javascript
    assert len(blocks) == 1
    assert blocks[0].block_type == "weather"


def test_parse_multiple_custom_blocks():
    """Test parsing multiple custom blocks."""
    markdown = """
```weather
location: New York
```

Some text.

```link-preview
url: https://github.com
```

```weather
location: London
units: metric
```
"""

    parser = CustomBlockParser(available_block_types=["weather", "link-preview"])
    blocks = parser.parse(markdown)

    assert len(blocks) == 3
    assert blocks[0].block_type == "weather"
    assert blocks[0].config["location"] == "New York"
    assert blocks[1].block_type == "link-preview"
    assert blocks[2].block_type == "weather"
    assert blocks[2].config["location"] == "London"


def test_parse_empty_config():
    """Test parsing a block with empty config."""
    markdown = """
```weather
```
"""

    parser = CustomBlockParser(available_block_types=["weather"])
    blocks = parser.parse(markdown)

    assert len(blocks) == 1
    assert blocks[0].block_type == "weather"
    assert blocks[0].config == {}


def test_parse_invalid_yaml():
    """Test parsing a block with invalid YAML falls back to plain text."""
    markdown = """
```custom
This is not valid YAML: {[}]
```
"""

    parser = CustomBlockParser(available_block_types=["custom"])
    blocks = parser.parse(markdown)

    assert len(blocks) == 1
    assert blocks[0].block_type == "custom"
    assert "content" in blocks[0].config
    assert "This is not valid YAML" in blocks[0].config["content"]


def test_parse_without_whitelist():
    """Test parsing without specifying available block types."""
    markdown = """
```python
print("hello")
```

```mycustomblock
key: value
```
"""

    # No whitelist - should parse any non-standard language
    parser = CustomBlockParser()
    blocks = parser.parse(markdown)

    # Should find mycustomblock but not python
    assert len(blocks) == 1
    assert blocks[0].block_type == "mycustomblock"


def test_parse_with_whitelist_filters():
    """Test that whitelist filters out unknown block types."""
    markdown = """
```weather
location: Paris
```

```unknownblock
data: value
```
"""

    # Only allow weather blocks
    parser = CustomBlockParser(available_block_types=["weather"])
    blocks = parser.parse(markdown)

    # Should only find weather, not unknownblock
    assert len(blocks) == 1
    assert blocks[0].block_type == "weather"


def test_block_positions():
    """Test that block positions are tracked correctly."""
    markdown = """# Title

```weather
location: Seattle
```

Text"""

    parser = CustomBlockParser(available_block_types=["weather"])
    blocks = parser.parse(markdown)

    assert len(blocks) == 1
    block = blocks[0]
    assert block.start_pos > 0
    assert block.end_pos > block.start_pos
    # Verify we can extract the block using positions
    assert markdown[block.start_pos : block.end_pos] == block.raw_content


def test_replace_blocks():
    """Test replacing blocks with rendered content."""
    markdown = """
# Document

```weather
location: Boston
```

Some text.

```link-preview
url: https://example.com
```
"""

    parser = CustomBlockParser(available_block_types=["weather", "link-preview"])
    blocks = parser.parse(markdown)

    # Create replacements
    replacements = {
        blocks[0].start_pos: '<div class="weather-widget">Weather for Boston</div>',
        blocks[1].start_pos: '<div class="link-preview">Example.com preview</div>',
    }

    result = parser.replace_blocks(markdown, replacements)

    assert "weather-widget" in result
    assert "Weather for Boston" in result
    assert "link-preview" in result
    assert "Example.com preview" in result
    # Original blocks should be gone
    assert "```weather" not in result
    assert "```link-preview" not in result


def test_parse_complex_yaml_config():
    """Test parsing blocks with complex YAML configurations."""
    markdown = """
```github-issue
repository: owner/repo
number: 123
show_comments: true
max_comments: 5
labels:
  - bug
  - urgent
```
"""

    parser = CustomBlockParser(available_block_types=["github-issue"])
    blocks = parser.parse(markdown)

    assert len(blocks) == 1
    assert blocks[0].config["repository"] == "owner/repo"
    assert blocks[0].config["number"] == 123
    assert blocks[0].config["show_comments"] is True
    assert blocks[0].config["max_comments"] == 5
    assert blocks[0].config["labels"] == ["bug", "urgent"]


def test_extract_blocks_with_positions():
    """Test extracting blocks with position information."""
    markdown = """
```weather
location: Miami
```

```link-preview
url: https://test.com
```
"""

    parser = CustomBlockParser(available_block_types=["weather", "link-preview"])
    results = parser.extract_blocks_with_positions(markdown)

    assert len(results) == 2
    block1, start1, end1 = results[0]
    block2, start2, end2 = results[1]

    assert block1.block_type == "weather"
    assert start1 < end1
    assert block2.block_type == "link-preview"
    assert start2 < end2
    assert start2 > end1  # Second block comes after first

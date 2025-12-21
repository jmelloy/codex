"""Markdown format utilities for

This module provides utilities for working with markdown files that follow
the Codex standard format:
- YAML frontmatter enclosed in --- delimiters
- Content blocks enclosed in ::: delimiters
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import yaml


class MarkdownDocument:
    """Represents a markdown document with frontmatter and blocks."""

    def __init__(
        self,
        frontmatter: Optional[Dict[str, Any]] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        content: str = "",
    ):
        """Initialize a markdown document.

        Args:
            frontmatter: Dictionary of frontmatter properties
            blocks: List of content blocks with type and content
            content: Raw markdown content (without blocks/frontmatter)
        """
        self.frontmatter = frontmatter or {}
        self.blocks = blocks or []
        self.content = content

    @classmethod
    def parse(cls, text: str) -> "MarkdownDocument":
        """Parse a markdown document from text.

        Args:
            text: Raw markdown text

        Returns:
            MarkdownDocument instance
        """
        # Extract frontmatter
        frontmatter = {}
        remaining_text = text

        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, text, re.DOTALL)
        if match:
            frontmatter_text = match.group(1)
            try:
                frontmatter = yaml.safe_load(frontmatter_text) or {}
            except yaml.YAMLError:
                frontmatter = {}
            remaining_text = text[match.end() :]

        # Extract blocks
        blocks = []
        block_pattern = r":::\s*(\w+)\s*\n(.*?)\n:::"

        for match in re.finditer(block_pattern, remaining_text, re.DOTALL):
            block_type = match.group(1)
            block_content = match.group(2).strip()
            blocks.append({"type": block_type, "content": block_content})

        # Remove blocks from content to get remaining markdown
        content = re.sub(block_pattern, "", remaining_text, flags=re.DOTALL).strip()

        return cls(frontmatter=frontmatter, blocks=blocks, content=content)

    def to_markdown(self) -> str:
        """Convert document to markdown format.

        Returns:
            Formatted markdown string
        """
        parts = []

        # Add frontmatter
        if self.frontmatter:
            parts.append("---")
            parts.append(yaml.dump(self.frontmatter, default_flow_style=False).strip())
            parts.append("---")
            parts.append("")

        # Add content
        if self.content:
            parts.append(self.content)
            parts.append("")

        # Add blocks
        for block in self.blocks:
            parts.append(f"::: {block['type']}")
            parts.append(block["content"])
            parts.append(":::")
            parts.append("")

        return "\n".join(parts).rstrip() + "\n"

    def get_block(self, block_type: str) -> Optional[str]:
        """Get the content of the first block of a given type.

        Args:
            block_type: Type of block to retrieve

        Returns:
            Block content or None if not found
        """
        for block in self.blocks:
            if block["type"] == block_type:
                return block["content"]
        return None

    def get_all_blocks(self, block_type: str) -> List[str]:
        """Get all blocks of a given type.

        Args:
            block_type: Type of blocks to retrieve

        Returns:
            List of block contents
        """
        return [
            block["content"] for block in self.blocks if block["type"] == block_type
        ]

    def add_block(self, block_type: str, content: str) -> None:
        """Add a new block to the document.

        Args:
            block_type: Type of block
            content: Block content
        """
        self.blocks.append({"type": block_type, "content": content})

    def set_frontmatter(self, key: str, value: Any) -> None:
        """Set a frontmatter property.

        Args:
            key: Property key
            value: Property value
        """
        self.frontmatter[key] = value

    def get_frontmatter(self, key: str, default: Any = None) -> Any:
        """Get a frontmatter property.

        Args:
            key: Property key
            default: Default value if key not found

        Returns:
            Property value
        """
        return self.frontmatter.get(key, default)


def parse_markdown_file(path: str) -> MarkdownDocument:
    """Parse a markdown file.

    Args:
        path: Path to markdown file

    Returns:
        MarkdownDocument instance
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return MarkdownDocument.parse(text)


def write_markdown_file(path: str, doc: MarkdownDocument) -> None:
    """Write a markdown document to a file.

    Args:
        path: Path to write to
        doc: MarkdownDocument instance
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc.to_markdown())

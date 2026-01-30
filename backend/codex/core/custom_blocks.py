"""Custom block parser for markdown with integration support."""

import re
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class CustomBlock:
    """Represents a custom block found in markdown."""

    block_type: str  # e.g., 'weather', 'link-preview'
    config: dict[str, Any]  # YAML config inside the block
    raw_content: str  # Original markdown text
    start_pos: int  # Position in the markdown
    end_pos: int  # End position in the markdown


class CustomBlockParser:
    """Parser for custom code fence blocks in markdown.

    Parses blocks with syntax like:
    ```weather
    location: San Francisco
    units: imperial
    ```

    ```link-preview
    url: https://example.com
    ```
    """

    # Pattern to match code fence blocks with optional language/type
    # Allows alphanumeric, hyphens, and underscores in block type name
    BLOCK_PATTERN = re.compile(r"```([\w-]+)\s*\n(.*?)```", re.MULTILINE | re.DOTALL)

    # Standard code block languages to ignore
    STANDARD_LANGUAGES = {
        "python",
        "javascript",
        "typescript",
        "js",
        "ts",
        "jsx",
        "tsx",
        "java",
        "c",
        "cpp",
        "csharp",
        "go",
        "rust",
        "ruby",
        "php",
        "swift",
        "kotlin",
        "scala",
        "bash",
        "sh",
        "shell",
        "zsh",
        "powershell",
        "sql",
        "html",
        "css",
        "scss",
        "sass",
        "json",
        "yaml",
        "yml",
        "xml",
        "markdown",
        "md",
        "text",
        "txt",
        "diff",
        "patch",
        "dockerfile",
        "makefile",
    }

    def __init__(self, available_block_types: list[str] | None = None):
        """Initialize parser.

        Args:
            available_block_types: List of valid custom block type IDs from integrations.
                                   If None, all non-standard language types are treated as custom blocks.
        """
        self.available_block_types = set(available_block_types or [])

    def parse(self, markdown: str) -> list[CustomBlock]:
        """Parse markdown and extract custom blocks.

        Args:
            markdown: Markdown text to parse

        Returns:
            List of CustomBlock instances found
        """
        blocks = []

        for match in self.BLOCK_PATTERN.finditer(markdown):
            block_type = match.group(1)
            content = match.group(2).strip()

            # Skip standard code languages
            if block_type.lower() in self.STANDARD_LANGUAGES:
                continue

            # If we have a whitelist, only parse known block types
            if self.available_block_types and block_type not in self.available_block_types:
                continue

            # Try to parse content as YAML
            try:
                if content:
                    config = yaml.safe_load(content)
                    # Ensure config is a dict
                    if not isinstance(config, dict):
                        config = {"value": config}
                else:
                    config = {}
            except yaml.YAMLError:
                # If YAML parsing fails, treat as plain text content
                config = {"content": content}

            blocks.append(
                CustomBlock(
                    block_type=block_type,
                    config=config,
                    raw_content=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                )
            )

        return blocks

    def replace_blocks(self, markdown: str, replacements: dict[int, str]) -> str:
        """Replace custom blocks with rendered content.

        Args:
            markdown: Original markdown text
            replacements: Dict mapping block start position to replacement HTML

        Returns:
            Markdown with blocks replaced
        """
        if not replacements:
            return markdown

        # Parse to get block positions
        blocks = self.parse(markdown)

        # Build list of (start, end, replacement) tuples
        to_replace = []
        for block in blocks:
            if block.start_pos in replacements:
                to_replace.append((block.start_pos, block.end_pos, replacements[block.start_pos]))

        # Sort by position (descending) to replace from end to start
        # This prevents position shifts from affecting later replacements
        to_replace.sort(key=lambda x: x[0], reverse=True)

        result = markdown
        for start, end, replacement in to_replace:
            result = result[:start] + replacement + result[end:]

        return result

    def extract_blocks_with_positions(self, markdown: str) -> list[tuple[CustomBlock, int, int]]:
        """Parse markdown and return blocks with their positions.

        Args:
            markdown: Markdown text to parse

        Returns:
            List of tuples (block, start_position, end_position)
        """
        return [(block, block.start_pos, block.end_pos) for block in self.parse(markdown)]

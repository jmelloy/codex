"""Markdown to blocks converter.

Parses a markdown file into structural blocks and creates a page folder
with individual block files and a .codex-page.json metadata file.
"""

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from sqlmodel import Session

from codex.core.blocks import (
    BLOCK_TYPE_CODE,
    BLOCK_TYPE_DIVIDER,
    BLOCK_TYPE_HEADING,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_LIST,
    BLOCK_TYPE_QUOTE,
    BLOCK_TYPE_TEXT,
    write_page_metadata,
)
from codex.core.metadata import MetadataParser

logger = logging.getLogger(__name__)


def _parse_markdown_to_blocks(markdown_content: str) -> list[dict[str, Any]]:
    """Parse markdown content into a list of block descriptors.

    Each block descriptor has:
        - type: block type string
        - content: the raw markdown content for this block
        - language: (for code blocks) the language hint

    Uses regex-based parsing to split markdown into structural blocks.
    """
    blocks: list[dict[str, Any]] = []
    lines = markdown_content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines between blocks
        if not line.strip():
            i += 1
            continue

        # Horizontal rule / divider
        if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line.strip()):
            blocks.append({"type": BLOCK_TYPE_DIVIDER, "content": "---"})
            i += 1
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            blocks.append(
                {
                    "type": BLOCK_TYPE_HEADING,
                    "content": line,
                    "level": level,
                }
            )
            i += 1
            continue

        # Fenced code block
        code_match = re.match(r"^```(\w*)\s*$", line)
        if code_match:
            language = code_match.group(1) or ""
            code_lines = [line]
            i += 1
            while i < len(lines):
                code_lines.append(lines[i])
                if lines[i].strip() == "```":
                    break
                i += 1
            blocks.append(
                {
                    "type": BLOCK_TYPE_CODE,
                    "content": "\n".join(code_lines),
                    "language": language,
                }
            )
            i += 1
            continue

        # Blockquote
        if line.startswith(">"):
            quote_lines = []
            while i < len(lines) and (lines[i].startswith(">") or (lines[i].strip() and quote_lines)):
                if not lines[i].startswith(">") and not lines[i].strip():
                    break
                quote_lines.append(lines[i])
                i += 1
            blocks.append(
                {
                    "type": BLOCK_TYPE_QUOTE,
                    "content": "\n".join(quote_lines),
                }
            )
            continue

        # Unordered list
        if re.match(r"^[\s]*[-*+]\s", line):
            list_lines = []
            while i < len(lines) and (
                re.match(r"^[\s]*[-*+]\s", lines[i]) or (lines[i].startswith("  ") and list_lines)
            ):
                list_lines.append(lines[i])
                i += 1
            blocks.append(
                {
                    "type": BLOCK_TYPE_LIST,
                    "content": "\n".join(list_lines),
                }
            )
            continue

        # Ordered list
        if re.match(r"^[\s]*\d+\.\s", line):
            list_lines = []
            while i < len(lines) and (
                re.match(r"^[\s]*\d+\.\s", lines[i]) or (lines[i].startswith("  ") and list_lines)
            ):
                list_lines.append(lines[i])
                i += 1
            blocks.append(
                {
                    "type": BLOCK_TYPE_LIST,
                    "content": "\n".join(list_lines),
                }
            )
            continue

        # Standalone image
        img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line.strip())
        if img_match:
            blocks.append(
                {
                    "type": BLOCK_TYPE_IMAGE,
                    "content": line.strip(),
                }
            )
            i += 1
            continue

        # Regular paragraph (text)
        para_lines = []
        while i < len(lines) and lines[i].strip():
            # Stop if we hit a new block-level element
            if re.match(r"^#{1,6}\s", lines[i]):
                break
            if re.match(r"^```", lines[i]):
                break
            if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", lines[i].strip()):
                break
            if lines[i].startswith(">"):
                break
            if re.match(r"^[\s]*[-*+]\s", lines[i]) and not para_lines:
                break
            if re.match(r"^[\s]*\d+\.\s", lines[i]) and not para_lines:
                break
            para_lines.append(lines[i])
            i += 1

        if para_lines:
            blocks.append(
                {
                    "type": BLOCK_TYPE_TEXT,
                    "content": "\n".join(para_lines),
                }
            )

    return blocks


def _block_filename(index: int, block: dict[str, Any]) -> str:
    """Generate a filename for a block."""
    block_type = block["type"]
    prefix = f"{index + 1:03d}"

    if block_type == BLOCK_TYPE_CODE:
        language = block.get("language", "")
        # Map common languages to extensions
        lang_ext = {
            "python": ".py",
            "py": ".py",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "rust": ".rs",
            "go": ".go",
            "java": ".java",
            "c": ".c",
            "cpp": ".cpp",
            "html": ".html",
            "css": ".css",
            "sql": ".sql",
            "shell": ".sh",
            "bash": ".sh",
            "yaml": ".yaml",
            "json": ".json",
            "toml": ".toml",
            "xml": ".xml",
        }
        ext = lang_ext.get(language.lower(), ".md")
        return f"{prefix}-code{ext}"

    if block_type == BLOCK_TYPE_HEADING:
        level = block.get("level", 1)
        return f"{prefix}-heading-{level}.md"

    type_slug = block_type.replace("_", "-")
    return f"{prefix}-{type_slug}.md"


def import_markdown_to_page(
    notebook_path: Path,
    notebook_id: int,
    markdown_path: str,
    nb_session: Session | None = None,
) -> dict[str, Any]:
    """Import a markdown file as a page of blocks.

    Reads the markdown file, parses it into blocks, creates a page folder,
    and writes individual block files.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        markdown_path: Relative path to the markdown file from notebook root
        nb_session: Optional database session

    Returns:
        Page metadata dict with block_id, path, title, and blocks list.
    """
    full_md_path = notebook_path / markdown_path

    if not full_md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

    # Read the markdown file
    with open(full_md_path) as f:
        raw_content = f.read()

    # Extract frontmatter as page properties
    frontmatter, body = MetadataParser.parse_frontmatter(raw_content)

    # Use frontmatter title or filename as page title
    title = frontmatter.pop("title", None) or Path(markdown_path).stem

    # Parse body into blocks
    parsed_blocks = _parse_markdown_to_blocks(body)

    if not parsed_blocks:
        # If no blocks parsed, create a single text block with the entire body
        parsed_blocks = [{"type": BLOCK_TYPE_TEXT, "content": body}]

    # Create page folder
    page_folder_name = Path(markdown_path).stem
    parent_dir = str(Path(markdown_path).parent)
    if parent_dir == ".":
        parent_dir = ""

    if parent_dir:
        page_path = f"{parent_dir}/{page_folder_name}"
    else:
        page_path = page_folder_name

    page_full_path = notebook_path / page_path

    # Ensure unique folder name
    if page_full_path.exists():
        counter = 1
        while True:
            candidate = f"{page_folder_name}-{counter}"
            if parent_dir:
                page_path = f"{parent_dir}/{candidate}"
            else:
                page_path = candidate
            page_full_path = notebook_path / page_path
            if not page_full_path.exists():
                break
            counter += 1

    page_full_path.mkdir(parents=True, exist_ok=True)

    # Generate page block_id
    page_block_id = str(uuid.uuid4())

    # Write block files and build metadata
    block_entries = []
    for i, block in enumerate(parsed_blocks):
        block_id = str(uuid.uuid4())
        filename = _block_filename(i, block)

        # Write block content to file
        block_file = page_full_path / filename
        with open(block_file, "w") as f:
            f.write(block["content"])

        block_entries.append(
            {
                "block_id": block_id,
                "type": block["type"],
                "file": filename,
                "order": float(i + 1),
            }
        )

    # Build description from frontmatter
    description = frontmatter.pop("description", None)

    # Write .codex-page.json
    page_metadata = {
        "version": 1,
        "block_id": page_block_id,
        "title": title,
        "description": description,
        "properties": frontmatter,  # Remaining frontmatter becomes properties
        "blocks": block_entries,
    }
    write_page_metadata(page_full_path, page_metadata)

    # Sync to DB if session provided
    if nb_session is not None:
        from codex.core.blocks import sync_page_from_disk

        sync_page_from_disk(notebook_path, page_path, notebook_id, nb_session)

    # Remove original markdown file
    try:
        full_md_path.unlink()
    except OSError as e:
        logger.warning(f"Failed to remove original markdown file {markdown_path}: {e}")

    return {
        "block_id": page_block_id,
        "path": page_path,
        "title": title,
        "description": description,
        "properties": frontmatter,
        "blocks": block_entries,
    }

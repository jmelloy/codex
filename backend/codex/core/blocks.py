"""Core block operations for infinite nested block structure.

Blocks are backed by files on disk. Pages (blocks with children) are folders
containing a .codex-page.json metadata file that tracks ordering and properties.
"""

import json
import logging
import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlmodel import Session, select
from ulid import ULID

from codex.db.models import Block
from codex.db.models.base import utc_now

logger = logging.getLogger(__name__)

PAGE_METADATA_FILE = ".codex-page.json"


def generate_unique_path(file_path: Path) -> Path:
    """Generate a unique file path by appending a numeric suffix if the file already exists."""
    if not file_path.exists():
        return file_path

    stem = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent

    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


# Block types
BLOCK_TYPE_PAGE = "page"
BLOCK_TYPE_TEXT = "text"
BLOCK_TYPE_HEADING = "heading"
BLOCK_TYPE_CODE = "code"
BLOCK_TYPE_IMAGE = "image"
BLOCK_TYPE_LIST = "list"
BLOCK_TYPE_QUOTE = "quote"
BLOCK_TYPE_DIVIDER = "divider"
BLOCK_TYPE_EMBED = "embed"
BLOCK_TYPE_FILE = "file"
BLOCK_TYPE_DATABASE = "database"
BLOCK_TYPE_API = "api"

VALID_BLOCK_TYPES = {
    BLOCK_TYPE_PAGE,
    BLOCK_TYPE_TEXT,
    BLOCK_TYPE_HEADING,
    BLOCK_TYPE_CODE,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_LIST,
    BLOCK_TYPE_QUOTE,
    BLOCK_TYPE_DIVIDER,
    BLOCK_TYPE_EMBED,
    BLOCK_TYPE_FILE,
    BLOCK_TYPE_DATABASE,
    BLOCK_TYPE_API,
}

# Content format mappings
BLOCK_TYPE_TO_EXTENSION = {
    BLOCK_TYPE_TEXT: ".md",
    BLOCK_TYPE_HEADING: ".md",
    BLOCK_TYPE_CODE: ".md",  # Will be overridden by language-specific extension
    BLOCK_TYPE_IMAGE: ".md",  # Reference to image file
    BLOCK_TYPE_LIST: ".md",
    BLOCK_TYPE_QUOTE: ".md",
    BLOCK_TYPE_DIVIDER: ".md",
    BLOCK_TYPE_EMBED: ".json",
    BLOCK_TYPE_FILE: "",  # Keeps original extension
    BLOCK_TYPE_DATABASE: ".json",
    BLOCK_TYPE_API: ".json",
}


def read_page_metadata(folder_path: Path) -> dict[str, Any] | None:
    """Read page metadata from .codex-page.json in the folder."""
    metadata_file = folder_path / PAGE_METADATA_FILE
    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read page metadata from {metadata_file}: {e}")
        return None


def write_page_metadata(folder_path: Path, metadata: dict[str, Any]) -> None:
    """Write page metadata to .codex-page.json in the folder."""
    metadata_file = folder_path / PAGE_METADATA_FILE
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def is_page_folder(folder_path: Path) -> bool:
    """Check if a folder is a page (has .codex-page.json)."""
    return (folder_path / PAGE_METADATA_FILE).exists()


def _next_order_index(metadata: dict[str, Any]) -> float:
    """Get the next order index for a new block in a page."""
    blocks = metadata.get("blocks", [])
    if not blocks:
        return 1.0
    return max(b.get("order", 0) for b in blocks) + 1.0


def _insert_order_index(metadata: dict[str, Any], position: int | None) -> float:
    """Calculate order index for inserting at a specific position.

    Uses fractional indexing: inserting between order 1.0 and 2.0 yields 1.5.
    """
    blocks = metadata.get("blocks", [])
    if not blocks or position is None or position >= len(blocks):
        return _next_order_index(metadata)

    sorted_blocks = sorted(blocks, key=lambda b: b.get("order", 0))

    if position <= 0:
        return sorted_blocks[0].get("order", 1.0) / 2.0

    before = sorted_blocks[position - 1].get("order", 0)
    after = sorted_blocks[position].get("order", 0)
    return (before + after) / 2.0


def _generate_block_filename(block_type: str, block_id: str) -> str:
    """Generate a filename for a block using its block_id."""
    ext = BLOCK_TYPE_TO_EXTENSION.get(block_type, ".md")
    return f"{block_id}{ext}"


def ensure_page_hierarchy(
    notebook_path: Path,
    notebook_id: int,
    file_path: str,
    nb_session: Session,
) -> str | None:
    """Ensure every directory in a file path is a page.

    Given a file path like "photos/vacation/beach.jpg", ensures that
    "photos" and "photos/vacation" are both pages (folders with .codex-page.json).

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        file_path: Relative file path (e.g., "photos/vacation/beach.jpg")
        nb_session: Database session

    Returns:
        The page path of the immediate parent folder, or None if file is at root.
    """
    parts = file_path.split("/")
    if len(parts) <= 1:
        return None  # File is at notebook root, no pages to create

    # Process each directory level (everything except the filename)
    current_path = ""
    parent_path = None

    for part in parts[:-1]:
        current_path = f"{parent_path}/{part}" if parent_path else part
        full_path = notebook_path / current_path

        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)

        if not is_page_folder(full_path):
            # Convert this directory into a page
            create_page(
                notebook_path=notebook_path,
                notebook_id=notebook_id,
                parent_path=parent_path,
                title=part,
                nb_session=nb_session,
            )

        parent_path = current_path

    return parent_path


def add_file_as_block(
    notebook_path: Path,
    notebook_id: int,
    page_path: str,
    file_path: str,
    nb_session: Session,
) -> dict[str, Any]:
    """Add an existing file as a block within a page.

    The file stays where it is on disk. A block entry is created in the
    page's .codex-page.json and in the database pointing to it.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        page_path: Path to the parent page folder
        file_path: Full relative path to the file (e.g., "photos/vacation/beach.jpg")
        nb_session: Database session

    Returns:
        Block metadata dict.
    """
    filename = os.path.basename(file_path)
    full_file = notebook_path / file_path
    if not full_file.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    page_full_path = notebook_path / page_path
    page_meta = read_page_metadata(page_full_path)
    if page_meta is None:
        raise ValueError(f"Not a page folder: {page_path}")

    # Determine block type from file extension
    ext = os.path.splitext(filename)[1].lower()
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp", ".ico"}
    if ext in image_exts:
        block_type = BLOCK_TYPE_IMAGE
    else:
        block_type = BLOCK_TYPE_FILE

    # Calculate order
    order = _next_order_index(page_meta)
    block_id = str(ULID())

    # Add to page metadata
    page_meta.setdefault("blocks", []).append(
        {
            "block_id": block_id,
            "type": block_type,
            "file": filename,
            "order": order,
        }
    )
    write_page_metadata(page_full_path, page_meta)

    # Create Block row
    full_file = notebook_path / file_path
    ct = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    sz = full_file.stat().st_size if full_file.exists() else 0
    block = Block(
        notebook_id=notebook_id,
        block_id=block_id,
        parent_block_id=page_meta.get("block_id"),
        path=file_path,
        block_type=block_type,
        content_format="binary",
        order_index=order,
        title=None,
        filename=os.path.basename(file_path),
        content_type=ct,
        size=sz,
    )
    nb_session.add(block)
    nb_session.commit()

    return {
        "block_id": block_id,
        "type": block_type,
        "file": filename,
        "path": file_path,
        "order": order,
    }


def create_page(
    notebook_path: Path,
    notebook_id: int,
    parent_path: str | None,
    title: str,
    description: str | None = None,
    properties: dict[str, Any] | None = None,
    nb_session: Session | None = None,
) -> dict[str, Any]:
    """Create a new page (folder with .codex-page.json).

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        parent_path: Parent folder path (None for root-level pages)
        title: Page title
        description: Optional description
        properties: Optional custom properties
        nb_session: Optional database session (caller manages lifecycle)

    Returns:
        The page metadata dict including block_id and path.
    """
    # Sanitize title for folder name
    safe_name = _sanitize_folder_name(title)
    if not safe_name:
        safe_name = "untitled"

    # Determine full path
    if parent_path:
        page_path = f"{parent_path}/{safe_name}"
    else:
        page_path = safe_name

    full_path = notebook_path / page_path

    # Ensure unique folder name
    if full_path.exists():
        counter = 1
        while True:
            candidate = f"{safe_name}-{counter}"
            if parent_path:
                page_path = f"{parent_path}/{candidate}"
            else:
                page_path = candidate
            full_path = notebook_path / page_path
            if not full_path.exists():
                break
            counter += 1

    # Create folder
    full_path.mkdir(parents=True, exist_ok=True)

    # Generate block_id
    block_id = str(ULID())

    # Write .codex-page.json
    page_metadata = {
        "version": 1,
        "block_id": block_id,
        "title": title,
        "description": description,
        "properties": properties or {},
        "blocks": [],
    }
    write_page_metadata(full_path, page_metadata)

    # Insert Block row if session provided
    if nb_session is not None:
        # Determine parent_block_id
        parent_block_id = None
        if parent_path:
            parent_meta = read_page_metadata(notebook_path / parent_path)
            if parent_meta:
                parent_block_id = parent_meta.get("block_id")

                # Also add this page as a child block in the parent's metadata
                parent_order = _next_order_index(parent_meta)
                parent_meta["blocks"].append(
                    {
                        "block_id": block_id,
                        "type": BLOCK_TYPE_PAGE,
                        "file": f"{safe_name}/",
                        "order": parent_order,
                    }
                )
                write_page_metadata(notebook_path / parent_path, parent_meta)

        block = Block(
            notebook_id=notebook_id,
            block_id=block_id,
            parent_block_id=parent_block_id,
            path=page_path,
            block_type=BLOCK_TYPE_PAGE,
            content_format="markdown",
            order_index=0.0,  # Pages use their parent's order for them
            title=title,
            description=description,
            properties=json.dumps(properties) if properties else None,
        )
        nb_session.add(block)
        nb_session.commit()

        # Create an initial empty text block so the page isn't blank
        create_block(
            notebook_path=notebook_path,
            notebook_id=notebook_id,
            page_path=page_path,
            block_type=BLOCK_TYPE_TEXT,
            content="",
            nb_session=nb_session,
        )

    return {
        "block_id": block_id,
        "path": page_path,
        "title": title,
        "description": description,
        "properties": properties or {},
    }


def create_block(
    notebook_path: Path,
    notebook_id: int,
    page_path: str,
    block_type: str,
    content: str,
    position: int | None = None,
    content_format: str = "markdown",
    nb_session: Session | None = None,
) -> dict[str, Any]:
    """Create a new block (file) within a page (folder).

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        page_path: Path to the parent page folder
        block_type: Type of block (text, heading, code, etc.)
        content: Block content
        position: Optional position (0-indexed). None = append to end.
        content_format: Content format (markdown, json, binary)
        nb_session: Optional database session

    Returns:
        Block metadata dict.
    """
    if block_type not in VALID_BLOCK_TYPES:
        raise ValueError(f"Invalid block type: {block_type}. Must be one of {VALID_BLOCK_TYPES}")

    if block_type == BLOCK_TYPE_PAGE:
        raise ValueError("Use create_page() to create page blocks")

    page_full_path = notebook_path / page_path

    if not page_full_path.exists() or not page_full_path.is_dir():
        raise FileNotFoundError(f"Page folder not found: {page_path}")

    # Read page metadata
    page_meta = read_page_metadata(page_full_path)
    if page_meta is None:
        raise ValueError(f"Not a page folder (no {PAGE_METADATA_FILE}): {page_path}")

    # Calculate order index
    order = _insert_order_index(page_meta, position)

    # Generate block ID and filename
    block_id = str(ULID())
    filename = _generate_block_filename(block_type, block_id)

    # Ensure unique filename
    while (page_full_path / filename).exists():
        base, ext = os.path.splitext(filename)
        filename = f"{base}-{uuid.uuid4().hex[:4]}{ext}"

    # Write content to file
    file_path = page_full_path / filename
    with open(file_path, "w") as f:
        f.write(content)

    # Update page metadata
    page_meta.setdefault("blocks", []).append(
        {
            "block_id": block_id,
            "type": block_type,
            "file": filename,
            "order": order,
        }
    )
    write_page_metadata(page_full_path, page_meta)

    # Relative path from notebook root
    relative_path = f"{page_path}/{filename}"

    # Insert Block row if session provided
    if nb_session is not None:
        file_full = page_full_path / filename
        ct = mimetypes.guess_type(filename)[0] or "text/plain"
        sz = file_full.stat().st_size if file_full.exists() else len(content.encode())
        block = Block(
            notebook_id=notebook_id,
            block_id=block_id,
            parent_block_id=page_meta.get("block_id"),
            path=relative_path,
            block_type=block_type,
            content_format=content_format,
            order_index=order,
            title=None,
            content_type=ct,
            size=sz,
        )
        nb_session.add(block)
        nb_session.commit()

    return {
        "block_id": block_id,
        "type": block_type,
        "file": filename,
        "path": relative_path,
        "order": order,
        "content": content,
    }


def update_block_content(
    notebook_path: Path,
    notebook_id: int,
    block_id: str,
    content: str,
    block_type: str | None = None,
    nb_session: Session | None = None,
) -> dict[str, Any]:
    """Update the content of a block, optionally changing its type.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        block_id: Block UUID to update
        content: New content
        block_type: Optional new block type
        nb_session: Database session

    Returns:
        Updated block metadata.
    """
    block = nb_session.exec(select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)).first()

    if not block:
        raise FileNotFoundError(f"Block not found: {block_id}")

    file_path = notebook_path / block.path
    if not file_path.exists():
        raise FileNotFoundError(f"Block file not found: {block.path}")

    with open(file_path, "w") as f:
        f.write(content)

    from codex.db.models.base import utc_now

    # Update block type if requested
    if block_type and block_type in VALID_BLOCK_TYPES and block_type != BLOCK_TYPE_PAGE:
        old_type = block.block_type
        if old_type != block_type:
            block.block_type = block_type
            # Also update the page metadata
            parent_path = str(Path(block.path).parent)
            parent_full = notebook_path / parent_path
            parent_meta = read_page_metadata(parent_full)
            if parent_meta:
                for entry in parent_meta.get("blocks", []):
                    if entry.get("block_id") == block_id:
                        entry["type"] = block_type
                        break
                write_page_metadata(parent_full, parent_meta)

    block.updated_at = utc_now()
    nb_session.add(block)
    nb_session.commit()

    return {
        "block_id": block.block_id,
        "type": block.block_type,
        "path": block.path,
        "content": content,
    }


def move_block(
    notebook_path: Path,
    notebook_id: int,
    block_id: str,
    new_parent_block_id: str | None,
    position: int | None,
    nb_session: Session,
) -> dict[str, Any]:
    """Move a block to a new parent page and/or position.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        block_id: Block UUID to move
        new_parent_block_id: Target parent block ID (None for root level)
        position: Position within the new parent (None = append)
        nb_session: Database session

    Returns:
        Updated block metadata.
    """
    block = nb_session.exec(select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)).first()

    if not block:
        raise FileNotFoundError(f"Block not found: {block_id}")

    # Find the current parent page
    old_parent_path = str(Path(block.path).parent)
    old_parent_full = notebook_path / old_parent_path
    old_parent_meta = read_page_metadata(old_parent_full)

    # Find the new parent page
    if new_parent_block_id:
        new_parent_block = nb_session.exec(
            select(Block).where(Block.notebook_id == notebook_id, Block.block_id == new_parent_block_id)
        ).first()
        if not new_parent_block:
            raise FileNotFoundError(f"Target parent block not found: {new_parent_block_id}")
        new_parent_path = new_parent_block.path
    else:
        # Moving to root - use notebook root
        new_parent_path = ""

    new_parent_full = notebook_path / new_parent_path if new_parent_path else notebook_path
    new_parent_meta = read_page_metadata(new_parent_full)

    if not new_parent_meta:
        raise ValueError(f"Target is not a page folder: {new_parent_path}")

    filename = Path(block.path).name

    # Remove from old parent metadata
    if old_parent_meta:
        old_parent_meta["blocks"] = [b for b in old_parent_meta.get("blocks", []) if b.get("block_id") != block_id]
        write_page_metadata(old_parent_full, old_parent_meta)

    # Move file on disk if parent changed
    old_file = notebook_path / block.path
    if new_parent_path:
        new_file_path = f"{new_parent_path}/{filename}"
    else:
        new_file_path = filename
    new_file = notebook_path / new_file_path

    if old_file != new_file:
        if block.block_type == BLOCK_TYPE_PAGE:
            shutil.move(str(old_file), str(new_file))
        else:
            old_file.rename(new_file)

    # Calculate new order
    order = _insert_order_index(new_parent_meta, position)

    # Add to new parent metadata
    entry = {
        "block_id": block_id,
        "type": block.block_type,
        "file": f"{filename}/" if block.block_type == BLOCK_TYPE_PAGE else filename,
        "order": order,
    }
    new_parent_meta.setdefault("blocks", []).append(entry)
    write_page_metadata(new_parent_full, new_parent_meta)

    # Update DB
    from codex.db.models.base import utc_now

    block.path = new_file_path
    block.parent_block_id = new_parent_block_id
    block.order_index = order
    block.updated_at = utc_now()
    nb_session.add(block)
    nb_session.commit()

    return {
        "block_id": block_id,
        "path": new_file_path,
        "parent_block_id": new_parent_block_id,
        "order": order,
    }


def reorder_blocks(
    notebook_path: Path,
    notebook_id: int,
    page_block_id: str,
    block_ids_in_order: list[str],
    nb_session: Session,
) -> list[dict[str, Any]]:
    """Reorder blocks within a page.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        page_block_id: Block ID of the page to reorder
        block_ids_in_order: Block IDs in desired order
        nb_session: Database session

    Returns:
        List of reordered block entries.
    """
    page_block = nb_session.exec(
        select(Block).where(Block.notebook_id == notebook_id, Block.block_id == page_block_id)
    ).first()

    if not page_block:
        raise FileNotFoundError(f"Page block not found: {page_block_id}")

    page_full_path = notebook_path / page_block.path
    page_meta = read_page_metadata(page_full_path)
    if not page_meta:
        raise ValueError(f"Not a page folder: {page_block.path}")

    # Build a map of existing blocks by block_id
    blocks_by_id = {b["block_id"]: b for b in page_meta.get("blocks", [])}

    # Reorder
    reordered = []
    from codex.db.models.base import utc_now

    now = utc_now()
    for i, bid in enumerate(block_ids_in_order):
        if bid in blocks_by_id:
            entry = blocks_by_id[bid]
            entry["order"] = float(i + 1)
            reordered.append(entry)

            # Update DB
            db_block = nb_session.exec(
                select(Block).where(Block.notebook_id == notebook_id, Block.block_id == bid)
            ).first()
            if db_block:
                db_block.order_index = float(i + 1)
                db_block.updated_at = now
                nb_session.add(db_block)

    # Add any blocks not in the reorder list at the end
    for bid, entry in blocks_by_id.items():
        if bid not in block_ids_in_order:
            entry["order"] = float(len(reordered) + 1)
            reordered.append(entry)

    page_meta["blocks"] = reordered
    write_page_metadata(page_full_path, page_meta)
    nb_session.commit()

    return reordered


def delete_block(
    notebook_path: Path,
    notebook_id: int,
    block_id: str,
    nb_session: Session,
) -> None:
    """Delete a block and its backing file.

    For page blocks, recursively deletes all children.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        block_id: Block UUID to delete
        nb_session: Database session
    """
    block = nb_session.exec(select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)).first()

    if not block:
        raise FileNotFoundError(f"Block not found: {block_id}")

    file_path = notebook_path / block.path

    # Remove from parent's .codex-page.json
    parent_path = str(Path(block.path).parent)
    parent_full = notebook_path / parent_path
    parent_meta = read_page_metadata(parent_full)
    if parent_meta:
        parent_meta["blocks"] = [b for b in parent_meta.get("blocks", []) if b.get("block_id") != block_id]
        write_page_metadata(parent_full, parent_meta)

    # Delete from filesystem
    if block.block_type == BLOCK_TYPE_PAGE and file_path.is_dir():
        # Recursively delete child blocks from DB first
        child_blocks = nb_session.exec(
            select(Block).where(Block.notebook_id == notebook_id, Block.parent_block_id == block_id)
        ).all()
        for child in child_blocks:
            nb_session.delete(child)

        shutil.rmtree(file_path, ignore_errors=True)
    elif file_path.exists():
        file_path.unlink()

    # Delete the block itself
    nb_session.delete(block)
    nb_session.commit()


def get_block(
    notebook_id: int,
    block_id: str,
    nb_session: Session,
) -> Block | None:
    """Get a block by its UUID."""
    return nb_session.exec(select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)).first()


def get_block_children(
    notebook_id: int,
    parent_block_id: str,
    nb_session: Session,
) -> list[Block]:
    """Get ordered children of a page block."""
    children = nb_session.exec(
        select(Block).where(
            Block.notebook_id == notebook_id,
            Block.parent_block_id == parent_block_id,
        )
    ).all()
    return sorted(children, key=lambda b: b.order_index)


def get_root_blocks(
    notebook_id: int,
    nb_session: Session,
) -> list[Block]:
    """Get root-level blocks (no parent)."""
    blocks = nb_session.exec(
        select(Block).where(
            Block.notebook_id == notebook_id,
            Block.parent_block_id == None,  # noqa: E711
        )
    ).all()
    return sorted(blocks, key=lambda b: b.order_index)


def sync_page_from_disk(
    notebook_path: Path,
    page_path: str,
    notebook_id: int,
    nb_session: Session,
) -> None:
    """Sync block state from .codex-page.json on disk to the database.

    Reads the page metadata file and ensures the blocks table matches.
    Used by the watcher when .codex-page.json changes on disk.
    """
    full_path = notebook_path / page_path if page_path else notebook_path
    page_meta = read_page_metadata(full_path)
    if not page_meta:
        return

    page_block_id = page_meta.get("block_id")
    if not page_block_id:
        return

    # Ensure page block exists in DB
    page_block = nb_session.exec(
        select(Block).where(Block.notebook_id == notebook_id, Block.block_id == page_block_id)
    ).first()

    if not page_block:
        # Determine parent
        parent_block_id = None
        if page_path:
            parent_folder = str(Path(page_path).parent)
            if parent_folder and parent_folder != ".":
                parent_meta = read_page_metadata(notebook_path / parent_folder)
                if parent_meta:
                    parent_block_id = parent_meta.get("block_id")

        page_block = Block(
            notebook_id=notebook_id,
            block_id=page_block_id,
            parent_block_id=parent_block_id,
            path=page_path or "",
            block_type=BLOCK_TYPE_PAGE,
            content_format="markdown",
            order_index=0.0,
            title=page_meta.get("title"),
        )
        nb_session.add(page_block)
    else:
        page_block.title = page_meta.get("title")

    # Sync child blocks
    existing_children = {
        b.block_id: b
        for b in nb_session.exec(
            select(Block).where(
                Block.notebook_id == notebook_id,
                Block.parent_block_id == page_block_id,
            )
        ).all()
    }

    seen_block_ids = set()
    for entry in page_meta.get("blocks", []):
        bid = entry.get("block_id")
        if not bid:
            continue
        seen_block_ids.add(bid)

        filename = entry.get("file", "")
        block_type = entry.get("type", BLOCK_TYPE_TEXT)
        order = entry.get("order", 0.0)

        # Build relative path
        if filename.endswith("/"):
            rel_path = f"{page_path}/{filename.rstrip('/')}" if page_path else filename.rstrip("/")
        else:
            rel_path = f"{page_path}/{filename}" if page_path else filename

        if bid in existing_children:
            # Update existing
            child = existing_children[bid]
            child.path = rel_path
            child.block_type = block_type
            child.order_index = order
            nb_session.add(child)
        else:
            # Create new
            child = Block(
                notebook_id=notebook_id,
                block_id=bid,
                parent_block_id=page_block_id,
                path=rel_path,
                block_type=block_type,
                content_format="markdown",
                order_index=order,
            )
            nb_session.add(child)

    # Remove blocks no longer in metadata
    for bid, child in existing_children.items():
        if bid not in seen_block_ids:
            nb_session.delete(child)

    nb_session.commit()


def _sanitize_folder_name(name: str) -> str:
    """Sanitize a title for use as a folder name on disk."""
    safe = name.replace("/", "-").replace("\\", "-").replace("\0", "")
    safe = safe.strip().strip(".")
    return safe


# ---------------------------------------------------------------------------
# Unified block functions (Phase 1.3)
# ---------------------------------------------------------------------------


def get_block_tree(
    notebook_path: Path,
    notebook_id: int,
    nb_session: Session,
) -> list[dict[str, Any]]:
    """Build a hierarchical tree of all blocks for sidebar navigation.

    Returns a nested list where page blocks contain their children.
    """
    all_blocks = nb_session.exec(select(Block).where(Block.notebook_id == notebook_id)).all()

    # Index by block_id
    by_id: dict[str, dict[str, Any]] = {}
    for b in all_blocks:
        by_id[b.block_id] = _block_dict(b)

    # Build tree
    roots: list[dict[str, Any]] = []
    for b in all_blocks:
        node = by_id[b.block_id]
        if b.parent_block_id and b.parent_block_id in by_id:
            parent = by_id[b.parent_block_id]
            parent.setdefault("children", []).append(node)
        else:
            roots.append(node)

    # Sort children by order_index recursively
    def _sort(nodes: list[dict[str, Any]]) -> None:
        nodes.sort(key=lambda n: n.get("order_index", 0))
        for n in nodes:
            if "children" in n:
                _sort(n["children"])

    _sort(roots)
    return roots


def _block_dict(block: Block) -> dict[str, Any]:
    """Convert a Block to a dict suitable for API responses."""
    return {
        "id": block.id,
        "block_id": block.block_id,
        "parent_block_id": block.parent_block_id,
        "notebook_id": block.notebook_id,
        "path": block.path,
        "block_type": block.block_type,
        "content_format": block.content_format,
        "order_index": block.order_index,
        "title": block.title,
        "filename": block.filename,
        "content_type": block.content_type,
        "size": block.size,
        "description": block.description,
        "properties": _parse_json(block.properties),
        "created_at": block.created_at.isoformat() if block.created_at else None,
        "updated_at": block.updated_at.isoformat() if block.updated_at else None,
    }


def _parse_json(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def get_block_content(notebook_path: Path, block: Block) -> str | None:
    """Read text content from a block's backing file."""
    file_path = notebook_path / block.path
    if not file_path.exists() or file_path.is_dir():
        return None
    try:
        content = file_path.read_text()
        # Strip frontmatter from markdown files
        if block.path.endswith(".md"):
            from codex.core.metadata import MetadataParser

            _, content = MetadataParser.parse_frontmatter(content)
        return content
    except Exception:
        return None


def serve_block_file(notebook_path: Path, block: Block):
    """Return the path and media type for serving a block's file content."""
    file_path = notebook_path / block.path
    if not file_path.exists() or file_path.is_dir():
        return None, None

    media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    return str(file_path), media_type


def _is_image_file(filename: str) -> bool:
    """Check if a filename has an image extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp", ".ico", ".heic", ".avif", ".tiff", ".tif"}


def _is_sidecar_file(filename: str, siblings: set[str]) -> bool:
    """Check if a file is a sidecar metadata file for another file in the same folder.

    Sidecar patterns: file.ext.json, .file.ext.json, file.ext.xml, .file.ext.xml, file.ext.md, .file.ext.md
    """
    name = filename
    # Dot-prefixed sidecar: .photo.jpg.json -> photo.jpg
    if name.startswith("."):
        name = name[1:]

    for suffix in (".json", ".xml", ".md"):
        if name.endswith(suffix):
            base = name.removesuffix(suffix)
            if base in siblings:
                return True
    return False


def _import_image_as_page(
    notebook_path: Path,
    notebook_id: int,
    parent_path: str,
    image_path: Path,
    nb_session: Session,
) -> dict[str, Any]:
    """Create a page for a single image file with cover_image and sidecar properties.

    Moves the image into a new subfolder, sets cover_image in page properties,
    and merges any sidecar metadata into page properties.
    """
    from codex.core.metadata import MetadataParser

    image_name = image_path.name
    stem = image_path.stem
    title = stem.replace("-", " ").replace("_", " ")

    # Extract sidecar metadata before moving the file
    sidecar_metadata = {}
    _, sidecar_path = MetadataParser.resolve_sidecar(str(image_path))

    if sidecar_path:
        sidecar_metadata = MetadataParser.extract_all_metadata(str(image_path))
        # Remove image dimension metadata from page properties (keep in block)
        for key in ("width", "height", "format", "mode"):
            sidecar_metadata.pop(key, None)

    # Use title from sidecar if available
    if "title" in sidecar_metadata:
        title = sidecar_metadata.pop("title")

    # Build page properties with cover_image and sidecar data
    properties = {"cover_image": image_name}
    properties.update(sidecar_metadata)

    # Create the page (this creates the subfolder and .codex-page.json)
    page_result = create_page(
        notebook_path=notebook_path,
        notebook_id=notebook_id,
        parent_path=parent_path,
        title=title,
        properties=properties,
        nb_session=nb_session,
    )
    page_path = page_result["path"]
    page_folder = notebook_path / page_path

    # Move the image into the new page folder
    dest = page_folder / image_name
    shutil.move(str(image_path), str(dest))

    # Move sidecar file too if it exists
    if sidecar_path:
        sidecar_dest = page_folder / Path(sidecar_path).name
        if Path(sidecar_path).exists():
            shutil.move(sidecar_path, str(sidecar_dest))

    # Add the image as a block within the page
    rel_path = str(dest.relative_to(notebook_path))
    add_file_as_block(
        notebook_path=notebook_path,
        notebook_id=notebook_id,
        page_path=page_path,
        file_path=rel_path,
        nb_session=nb_session,
    )

    return page_result


def import_folder_as_pages(
    notebook_path: Path,
    notebook_id: int,
    folder_path: str,
    nb_session: Session,
) -> dict[str, Any]:
    """Recursively convert a folder tree into pages and blocks.

    Each subfolder becomes a page block. Image files each become their own
    sub-page with cover_image set in properties. Sidecar metadata files
    are merged into the image page's properties. Non-image files become
    leaf blocks.
    """
    full_path = notebook_path / folder_path if folder_path else notebook_path
    if not full_path.exists() or not full_path.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    # Create page for this folder if not already a page
    if not is_page_folder(full_path):
        title = os.path.basename(folder_path) if folder_path else "Root"
        parent_path = str(Path(folder_path).parent) if folder_path and "/" in folder_path else None
        if parent_path == ".":
            parent_path = None
        create_page(
            notebook_path=notebook_path,
            notebook_id=notebook_id,
            parent_path=parent_path,
            title=title,
            nb_session=nb_session,
        )

    page_meta = read_page_metadata(full_path)
    if not page_meta:
        raise ValueError(f"Failed to create page metadata for: {folder_path}")

    # Collect sibling filenames for sidecar detection
    sibling_names = {item.name for item in full_path.iterdir() if item.is_file() and not item.name.startswith(".")}

    # Process children
    created_pages = []
    created_blocks = []
    for item in sorted(full_path.iterdir()):
        if item.name.startswith("."):
            continue

        if item.is_dir():
            child_path = f"{folder_path}/{item.name}" if folder_path else item.name
            result = import_folder_as_pages(notebook_path, notebook_id, child_path, nb_session)
            created_pages.append(result)
        elif item.is_file():
            # Skip sidecar files — they'll be processed with their image
            if _is_sidecar_file(item.name, sibling_names):
                continue

            if _is_image_file(item.name):
                # Each image becomes its own page with cover_image
                try:
                    result = _import_image_as_page(
                        notebook_path=notebook_path,
                        notebook_id=notebook_id,
                        parent_path=folder_path,
                        image_path=item,
                        nb_session=nb_session,
                    )
                    created_pages.append(result)
                except Exception as e:
                    logger.warning(f"Could not create page for image {item}: {e}")
            else:
                rel_path = str(item.relative_to(notebook_path))
                # Check if already a block
                existing = nb_session.exec(
                    select(Block).where(Block.notebook_id == notebook_id, Block.path == rel_path)
                ).first()
                if not existing:
                    try:
                        result = add_file_as_block(
                            notebook_path=notebook_path,
                            notebook_id=notebook_id,
                            page_path=folder_path,
                            file_path=rel_path,
                            nb_session=nb_session,
                        )
                        created_blocks.append(result)
                    except Exception as e:
                        logger.warning(f"Could not add {rel_path} as block: {e}")

    return {
        "path": folder_path,
        "block_id": page_meta.get("block_id"),
        "pages_created": len(created_pages),
        "blocks_created": len(created_blocks),
    }


def upload_to_block(
    notebook_path: Path,
    notebook_id: int,
    page_block_id: str | None,
    filename: str,
    content: bytes,
    nb_session: Session,
) -> dict[str, Any]:
    """Upload a file and create a Block record.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        page_block_id: Parent page block ID (None for root)
        filename: Original filename
        content: File content bytes
        nb_session: Database session

    Returns:
        Block metadata dict.
    """
    import hashlib

    from codex.core.watcher import get_content_type

    # Determine target path
    if page_block_id:
        parent_block = nb_session.exec(
            select(Block).where(Block.notebook_id == notebook_id, Block.block_id == page_block_id)
        ).first()
        if not parent_block:
            raise FileNotFoundError(f"Parent block not found: {page_block_id}")
        if parent_block.block_type != BLOCK_TYPE_PAGE:
            raise ValueError("Parent must be a page block")
        target_dir = parent_block.path
    else:
        target_dir = ""

    file_path = f"{target_dir}/{filename}" if target_dir else filename
    full_path = notebook_path / file_path

    # Ensure unique name
    if full_path.exists():
        stem = full_path.stem
        suffix = full_path.suffix
        counter = 1
        while full_path.exists():
            file_path = f"{target_dir}/{stem}-{counter}{suffix}" if target_dir else f"{stem}-{counter}{suffix}"
            full_path = notebook_path / file_path
            counter += 1

    # Write file to disk
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(content)

    content_type = get_content_type(str(full_path))
    file_hash = hashlib.sha256(content).hexdigest()

    from datetime import datetime

    file_stats = os.stat(full_path)

    # Create Block
    block_id = str(ULID())
    ext = os.path.splitext(filename)[1].lower()
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp", ".ico"}
    block_type = BLOCK_TYPE_IMAGE if ext in image_exts else BLOCK_TYPE_FILE

    page_meta = None
    parent_bid = None
    order = 0.0
    if page_block_id:
        parent_bid = page_block_id
        page_full = notebook_path / target_dir
        page_meta = read_page_metadata(page_full)
        if page_meta:
            order = _next_order_index(page_meta)
            page_meta.setdefault("blocks", []).append(
                {
                    "block_id": block_id,
                    "type": block_type,
                    "file": os.path.basename(file_path),
                    "order": order,
                }
            )
            write_page_metadata(page_full, page_meta)

    block = Block(
        notebook_id=notebook_id,
        block_id=block_id,
        parent_block_id=parent_bid,
        path=file_path,
        block_type=block_type,
        content_format="binary",
        order_index=order,
        filename=os.path.basename(file_path),
        content_type=content_type,
        size=len(content),
        hash=file_hash,
        file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
        file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
    )
    nb_session.add(block)
    nb_session.commit()

    return _block_dict(block)


def update_block_properties(
    notebook_path: Path,
    notebook_id: int,
    block_id: str,
    properties: dict[str, Any],
    nb_session: Session,
) -> dict[str, Any]:
    """Update block properties (denormalized and on-disk)."""
    block = nb_session.exec(select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)).first()
    if not block:
        raise FileNotFoundError(f"Block not found: {block_id}")

    # Merge with existing properties (PATCH semantics)
    existing = {}
    if block.properties:
        try:
            existing = json.loads(block.properties)
        except (json.JSONDecodeError, TypeError):
            pass
    merged = {**existing, **properties}

    # Update denormalized fields
    if "title" in properties:
        block.title = properties["title"]
    if "description" in properties:
        block.description = properties["description"]
    block.properties = json.dumps(merged)
    block.updated_at = utc_now()

    # If it's a page, also update .codex-page.json
    if block.block_type == BLOCK_TYPE_PAGE:
        page_full = notebook_path / block.path
        page_meta = read_page_metadata(page_full)
        if page_meta:
            if "title" in properties:
                page_meta["title"] = properties["title"]
            if "description" in properties:
                page_meta["description"] = properties["description"]
            page_meta["properties"] = merged
            write_page_metadata(page_full, page_meta)

    # Write sidecar or frontmatter to disk
    file_path = notebook_path / block.path
    if file_path.exists() and file_path.is_file():
        from codex.core.metadata import MetadataParser

        if block.content_type == "text/markdown":
            content = file_path.read_text()
            _, body = MetadataParser.parse_frontmatter(content)
            new_content = MetadataParser.write_frontmatter(body, merged)
            file_path.write_text(new_content)
        else:
            MetadataParser.write_sidecar(str(file_path), merged)

    nb_session.add(block)
    nb_session.commit()
    return _block_dict(block)

"""Core block operations for infinite nested block structure.

Blocks are backed by files on disk. Pages (blocks with children) are folders
containing a .codex-page.json metadata file that tracks ordering and properties.
"""

import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from codex.db.models import Block, FileMetadata

logger = logging.getLogger(__name__)

PAGE_METADATA_FILE = ".codex-page.json"

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


def _generate_block_filename(block_type: str, order: float, content: str = "") -> str:
    """Generate a filename for a block based on its type and order."""
    index = int(order)
    prefix = f"{index:03d}"

    ext = BLOCK_TYPE_TO_EXTENSION.get(block_type, ".md")
    type_slug = block_type.replace("_", "-")

    return f"{prefix}-{type_slug}{ext}"


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
    block_id = str(uuid.uuid4())

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
        )
        nb_session.add(block)
        nb_session.commit()

    return {
        "block_id": block_id,
        "path": page_path,
        "title": title,
        "description": description,
        "properties": properties or {},
        "blocks": [],
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
    block_id = str(uuid.uuid4())
    filename = _generate_block_filename(block_type, len(page_meta.get("blocks", [])) + 1, content)

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
        block = Block(
            notebook_id=notebook_id,
            block_id=block_id,
            parent_block_id=page_meta.get("block_id"),
            path=relative_path,
            block_type=block_type,
            content_format=content_format,
            order_index=order,
            title=None,
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
    nb_session: Session,
) -> dict[str, Any]:
    """Update the content of a block.

    Args:
        notebook_path: Root path of the notebook
        notebook_id: Notebook ID
        block_id: Block UUID to update
        content: New content
        nb_session: Database session

    Returns:
        Updated block metadata.
    """
    block = nb_session.exec(
        select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)
    ).first()

    if not block:
        raise FileNotFoundError(f"Block not found: {block_id}")

    file_path = notebook_path / block.path
    if not file_path.exists():
        raise FileNotFoundError(f"Block file not found: {block.path}")

    with open(file_path, "w") as f:
        f.write(content)

    from codex.db.models.base import utc_now

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
    block = nb_session.exec(
        select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)
    ).first()

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
        old_parent_meta["blocks"] = [
            b for b in old_parent_meta.get("blocks", []) if b.get("block_id") != block_id
        ]
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
    block = nb_session.exec(
        select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)
    ).first()

    if not block:
        raise FileNotFoundError(f"Block not found: {block_id}")

    file_path = notebook_path / block.path

    # Remove from parent's .codex-page.json
    parent_path = str(Path(block.path).parent)
    parent_full = notebook_path / parent_path
    parent_meta = read_page_metadata(parent_full)
    if parent_meta:
        parent_meta["blocks"] = [
            b for b in parent_meta.get("blocks", []) if b.get("block_id") != block_id
        ]
        write_page_metadata(parent_full, parent_meta)

    # Delete from filesystem
    if block.block_type == BLOCK_TYPE_PAGE and file_path.is_dir():
        # Recursively delete child blocks from DB first
        child_blocks = nb_session.exec(
            select(Block).where(Block.notebook_id == notebook_id, Block.parent_block_id == block_id)
        ).all()
        for child in child_blocks:
            nb_session.delete(child)

        # Delete child FileMetadata
        prefix = f"{block.path}/"
        child_files = nb_session.exec(
            select(FileMetadata).where(
                FileMetadata.notebook_id == notebook_id,
                FileMetadata.path.startswith(prefix),
            )
        ).all()
        for cf in child_files:
            nb_session.delete(cf)

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
    return nb_session.exec(
        select(Block).where(Block.notebook_id == notebook_id, Block.block_id == block_id)
    ).first()


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

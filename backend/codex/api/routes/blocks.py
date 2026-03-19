"""Block routes for infinite nested block structure.

Provides CRUD operations for blocks and pages, supporting Notion-like
infinite block recursion backed by filesystem folders and files.
"""

import hashlib
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.helpers import get_notebook_path_nested
from codex.core.blocks import (
    BLOCK_TYPE_FILE,
    BLOCK_TYPE_IMAGE,
    PAGE_METADATA_FILE,
    _next_order_index,
    create_block,
    create_page,
    delete_block,
    get_block,
    get_block_children,
    get_root_blocks,
    move_block,
    read_page_metadata,
    reorder_blocks,
    update_block_content,
    write_page_metadata,
)
from codex.core.md_import import import_markdown_to_page
from codex.core.watcher import get_content_type, is_binary_file
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import Block, FileMetadata, User

logger = logging.getLogger(__name__)


# Request/Response models
class CreateBlockRequest(BaseModel):
    """Request to create a new block."""

    parent_block_id: str | None = None
    block_type: str = "text"
    content: str = ""
    position: int | None = None
    content_format: str = "markdown"


class CreatePageRequest(BaseModel):
    """Request to create a new page."""

    parent_path: str | None = None
    title: str
    description: str | None = None
    properties: dict[str, Any] | None = None


class UpdateBlockRequest(BaseModel):
    """Request to update block content."""

    content: str


class MoveBlockRequest(BaseModel):
    """Request to move a block."""

    new_parent_block_id: str | None = None
    position: int | None = None


class ReorderBlocksRequest(BaseModel):
    """Request to reorder blocks within a page."""

    block_ids: list[str]


def _block_to_dict(block: Block, nb_session=None, notebook_path=None) -> dict[str, Any]:
    """Convert a Block model to a response dict.

    When nb_session is provided, enriches the response with content_type and size
    from the linked FileMetadata record (looked up via file_id or path).
    """
    result = {
        "id": block.id,
        "block_id": block.block_id,
        "parent_block_id": block.parent_block_id,
        "notebook_id": block.notebook_id,
        "path": block.path,
        "block_type": block.block_type,
        "content_format": block.content_format,
        "order_index": block.order_index,
        "title": block.title,
        "file_id": block.file_id,
        "created_at": block.created_at.isoformat() if block.created_at else None,
        "updated_at": block.updated_at.isoformat() if block.updated_at else None,
    }

    # Enrich with FileMetadata info when session available
    if nb_session is not None:
        file_meta = None
        if block.file_id:
            file_meta = nb_session.get(FileMetadata, block.file_id)
        if not file_meta and block.path:
            file_meta = nb_session.exec(
                select(FileMetadata).where(
                    FileMetadata.notebook_id == block.notebook_id,
                    FileMetadata.path == block.path,
                )
            ).first()
        if file_meta:
            result["content_type"] = file_meta.content_type
            result["size"] = file_meta.size
        elif notebook_path and block.block_type != "page":
            # Fall back to filesystem detection
            file_path = notebook_path / block.path
            if file_path.exists():
                result["content_type"] = get_content_type(str(file_path))
                result["size"] = file_path.stat().st_size

    return result


def _is_binary_block(block: Block, notebook_path) -> bool:
    """Check if a block's backing file is binary."""
    if block.block_type in (BLOCK_TYPE_IMAGE, BLOCK_TYPE_FILE):
        file_path = notebook_path / block.path
        if file_path.exists():
            return is_binary_file(str(file_path))
    return False


def _read_block_content(block: Block, notebook_path) -> dict[str, Any]:
    """Read content for a leaf block, handling binary files safely.

    Returns a dict with either 'content' (text) or 'is_binary' flag.
    """
    if block.block_type == "page":
        return {}

    file_path = notebook_path / block.path
    if not file_path.exists():
        return {"content": None}

    if is_binary_file(str(file_path)):
        return {"content": None, "is_binary": True}

    try:
        return {"content": file_path.read_text()}
    except Exception:
        return {"content": None}


# Nested router (mounted under workspace/notebook)
nested_router = APIRouter()


@nested_router.get("/")
async def list_root_blocks(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List root-level blocks and pages in the notebook."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        blocks = get_root_blocks(notebook.id, nb_session)
        return {
            "blocks": [_block_to_dict(b, nb_session, notebook_path) for b in blocks],
            "notebook_id": notebook.id,
            "workspace_id": workspace.id,
        }
    finally:
        nb_session.close()


@nested_router.get("/{block_id}")
async def get_block_detail(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a single block with its metadata and content."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = get_block(notebook.id, block_id, nb_session)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")

        result = _block_to_dict(block, nb_session, notebook_path)

        # Include content for leaf blocks (safely handling binary)
        if block.block_type != "page":
            result.update(_read_block_content(block, notebook_path))
        else:
            # For pages, include the page metadata
            page_meta = read_page_metadata(notebook_path / block.path)
            if page_meta:
                result["page_metadata"] = page_meta

        return result
    finally:
        nb_session.close()


@nested_router.get("/{block_id}/children")
async def get_children(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get ordered children of a page block."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Verify parent exists and is a page
        parent = get_block(notebook.id, block_id, nb_session)
        if not parent:
            raise HTTPException(status_code=404, detail="Block not found")
        if parent.block_type != "page":
            raise HTTPException(status_code=400, detail="Block is not a page")

        children = get_block_children(notebook.id, block_id, nb_session)

        # Include content for each child (safely handling binary)
        result = []
        for child in children:
            child_dict = _block_to_dict(child, nb_session, notebook_path)
            if child.block_type != "page":
                child_dict.update(_read_block_content(child, notebook_path))
            result.append(child_dict)

        return {
            "parent_block_id": block_id,
            "children": result,
        }
    finally:
        nb_session.close()


@nested_router.post("/")
async def create_new_block(
    workspace_identifier: str,
    notebook_identifier: str,
    request: CreateBlockRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new block within a page."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Find the parent page path
        if request.parent_block_id:
            parent = get_block(notebook.id, request.parent_block_id, nb_session)
            if not parent:
                raise HTTPException(status_code=404, detail="Parent block not found")
            if parent.block_type != "page":
                raise HTTPException(status_code=400, detail="Parent must be a page block")
            page_path = parent.path
        else:
            raise HTTPException(
                status_code=400,
                detail="parent_block_id is required. Use POST /pages to create root-level pages.",
            )

        result = create_block(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            page_path=page_path,
            block_type=request.block_type,
            content=request.content,
            position=request.position,
            content_format=request.content_format,
            nb_session=nb_session,
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()


@nested_router.post("/pages")
async def create_new_page(
    workspace_identifier: str,
    notebook_identifier: str,
    request: CreatePageRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new page (folder with block structure)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = create_page(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            parent_path=request.parent_path,
            title=request.title,
            description=request.description,
            properties=request.properties,
            nb_session=nb_session,
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.put("/{block_id}")
async def update_block(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    request: UpdateBlockRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update block content."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = update_block_content(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            block_id=block_id,
            content=request.content,
            nb_session=nb_session,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()


@nested_router.patch("/{block_id}/move")
async def move_block_endpoint(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    request: MoveBlockRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Move a block to a new parent and/or position."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = move_block(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            block_id=block_id,
            new_parent_block_id=request.new_parent_block_id,
            position=request.position,
            nb_session=nb_session,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.patch("/{block_id}/reorder")
async def reorder_blocks_endpoint(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    request: ReorderBlocksRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Reorder children of a page block."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = reorder_blocks(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            page_block_id=block_id,
            block_ids_in_order=request.block_ids,
            nb_session=nb_session,
        )
        return {"parent_block_id": block_id, "blocks": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.delete("/{block_id}")
async def delete_block_endpoint(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a block. For pages, recursively deletes all children."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        delete_block(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            block_id=block_id,
            nb_session=nb_session,
        )
        return {"message": "Block deleted successfully"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()


@nested_router.post("/import-markdown")
async def import_markdown(
    workspace_identifier: str,
    notebook_identifier: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Import a markdown file, converting it to a page of blocks."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files can be imported")

    # Save uploaded file temporarily
    temp_path = notebook_path / file.filename
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        nb_session = get_notebook_session(str(notebook_path))
        try:
            result = import_markdown_to_page(
                notebook_path=notebook_path,
                notebook_id=notebook.id,
                markdown_path=file.filename,
                nb_session=nb_session,
            )
            return result
        finally:
            nb_session.close()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Error importing markdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error importing markdown: {str(e)}")


@nested_router.post("/{block_id}/upload")
async def upload_to_block(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    file: UploadFile = File(...),
    position: int | None = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Upload a file into a page block, creating both FileMetadata and Block records.

    The uploaded file is written into the page's folder on disk and atomically
    registered as a block in .codex-page.json. Binary files are offloaded to S3
    when configured.
    """
    import uuid
    from datetime import datetime

    from codex.api.routes.files import generate_unique_path
    from codex.core.git_manager import GitManager
    from codex.core.s3_storage import build_s3_key, is_s3_configured, upload_binary, write_pointer_file

    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Verify the parent block is a page
        parent = get_block(notebook.id, block_id, nb_session)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent block not found")
        if parent.block_type != "page":
            raise HTTPException(status_code=400, detail="Parent must be a page block")

        page_full_path = notebook_path / parent.path
        page_meta = read_page_metadata(page_full_path)
        if page_meta is None:
            raise HTTPException(status_code=400, detail="Parent is not a valid page (no metadata)")

        # Determine filename and write path
        filename = file.filename or "upload"
        file_path = page_full_path / filename
        file_path = generate_unique_path(file_path)
        filename = file_path.name

        # Read file content
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        content_type = get_content_type(str(file_path))
        is_binary = b"\0" in content[:8192]

        # S3 offload for binary files
        s3_meta = None
        rel_path = str(file_path.relative_to(notebook_path))
        if is_binary and is_s3_configured():
            s3_key = build_s3_key(workspace.slug, notebook.slug, rel_path)
            s3_meta = upload_binary(content, s3_key, content_type)

        # Write file to disk
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)

        # Create FileMetadata record
        file_meta = FileMetadata(
            notebook_id=notebook.id,
            path=rel_path,
            filename=filename,
            content_type=content_type,
            size=len(content),
            hash=file_hash,
        )
        if s3_meta:
            file_meta.s3_bucket = s3_meta["bucket"]
            file_meta.s3_key = s3_meta["key"]
            file_meta.s3_version_id = s3_meta["version_id"]

        file_stats = os.stat(file_path)
        file_meta.file_created_at = datetime.fromtimestamp(file_stats.st_ctime)
        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)

        nb_session.add(file_meta)
        nb_session.flush()  # Get the ID without committing yet

        # Determine block type from file extension
        ext = os.path.splitext(filename)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
            block_type = BLOCK_TYPE_IMAGE
        else:
            block_type = BLOCK_TYPE_FILE

        content_format = "binary" if is_binary else "markdown"

        # Create Block record
        new_block_id = str(uuid.uuid4())
        order = _next_order_index(page_meta) if position is None else position

        block = Block(
            notebook_id=notebook.id,
            block_id=new_block_id,
            parent_block_id=page_meta.get("block_id"),
            path=rel_path,
            block_type=block_type,
            content_format=content_format,
            order_index=order,
            title=None,
            file_id=file_meta.id,
        )
        nb_session.add(block)

        # Update .codex-page.json
        page_meta.setdefault("blocks", []).append({
            "block_id": new_block_id,
            "type": block_type,
            "file": filename,
            "order": order,
        })
        write_page_metadata(page_full_path, page_meta)

        # Git commit
        git_manager = GitManager(str(notebook_path))
        if s3_meta:
            pointer_path = write_pointer_file(
                str(file_path),
                bucket=s3_meta["bucket"],
                s3_key=s3_meta["key"],
                version_id=s3_meta["version_id"],
                size=len(content),
                sha256=file_hash,
                content_type=content_type,
            )
            commit_hash = git_manager.commit_s3_upload(
                filepath=str(file_path),
                pointer_path=pointer_path,
                s3_bucket=s3_meta["bucket"],
                s3_key=s3_meta["key"],
                s3_version_id=s3_meta["version_id"],
                file_size=len(content),
            )
        else:
            commit_hash = git_manager.commit(
                f"Upload {filename} to page",
                [str(file_path), str(page_full_path / PAGE_METADATA_FILE)],
            )

        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        nb_session.commit()
        nb_session.refresh(file_meta)
        nb_session.refresh(block)

        result = {
            "block_id": new_block_id,
            "type": block_type,
            "file": filename,
            "path": rel_path,
            "order": order,
            "file_id": file_meta.id,
            "content_type": content_type,
            "size": len(content),
            "is_binary": is_binary,
        }
        if s3_meta:
            result["s3_key"] = s3_meta["key"]

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to block: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        nb_session.close()

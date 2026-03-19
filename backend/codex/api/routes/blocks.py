"""Block routes for infinite nested block structure.

Provides CRUD operations for blocks and pages, supporting Notion-like
infinite block recursion backed by filesystem folders and files.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codex.api.auth import get_current_active_user
from codex.api.routes.helpers import get_notebook_path_nested
from codex.core.blocks import (
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
)
from codex.core.md_import import import_markdown_to_page
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import Block, User

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


class ConvertFileRequest(BaseModel):
    """Request to convert an existing markdown file to a block page."""

    file_id: int | None = None
    path: str | None = None


class ReorderBlocksRequest(BaseModel):
    """Request to reorder blocks within a page."""

    block_ids: list[str]


def _block_to_dict(block: Block) -> dict[str, Any]:
    """Convert a Block model to a response dict."""
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
        "file_id": block.file_id,
        "created_at": block.created_at.isoformat() if block.created_at else None,
        "updated_at": block.updated_at.isoformat() if block.updated_at else None,
    }


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
            "blocks": [_block_to_dict(b) for b in blocks],
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

        result = _block_to_dict(block)

        # Include content for leaf blocks
        if block.block_type != "page":
            file_path = notebook_path / block.path
            if file_path.exists():
                try:
                    result["content"] = file_path.read_text()
                except Exception:
                    result["content"] = None
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

        # Include content for each child
        result = []
        for child in children:
            child_dict = _block_to_dict(child)
            if child.block_type != "page":
                file_path = notebook_path / child.path
                if file_path.exists():
                    try:
                        child_dict["content"] = file_path.read_text()
                    except Exception:
                        child_dict["content"] = None
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


@nested_router.post("/convert-file")
async def convert_file_to_blocks(
    workspace_identifier: str,
    notebook_identifier: str,
    request: ConvertFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Convert an existing markdown file in the notebook to a page of blocks."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Resolve the file path
    if request.file_id:
        nb_session = get_notebook_session(str(notebook_path))
        try:
            from codex.db.models import FileMetadata as FM

            from sqlmodel import select as sel

            file_meta = nb_session.exec(sel(FM).where(FM.notebook_id == notebook.id, FM.id == request.file_id)).first()
            if not file_meta:
                raise HTTPException(status_code=404, detail="File not found")
            md_path = file_meta.path
        finally:
            nb_session.close()
    elif request.path:
        md_path = request.path
    else:
        raise HTTPException(status_code=400, detail="Either file_id or path is required")

    if not md_path.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files can be converted to blocks")

    full_path = notebook_path / md_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {md_path}")

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = import_markdown_to_page(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            markdown_path=md_path,
            nb_session=nb_session,
        )
        return result
    except Exception as e:
        logger.error(f"Error converting file to blocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error converting file: {str(e)}")
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

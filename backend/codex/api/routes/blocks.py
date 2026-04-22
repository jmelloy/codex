"""Block routes for infinite nested block structure.

Provides CRUD operations for blocks and pages, supporting Notion-like
infinite block recursion backed by filesystem folders and files.
"""

import logging
import mimetypes
import os
import shutil
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.helpers import get_notebook_path_nested
from codex.api.schemas import (
    BlockAtCommitResponse,
    BlockChildrenResponse,
    BlockDeleteResponse,
    BlockHistoryResponse,
    BlockReorderResponse,
    BlockResolveLinkResponse,
    BlockResponse,
    BlockTextContentResponse,
    BlockTreeResponse,
    ImportFolderResponse,
    PageAtCommitResponse,
    PageResponse,
    RootBlocksResponse,
    ZipImportResponse,
)
from codex.core.blocks import (
    _block_dict,
    _parse_json,
    create_block,
    create_page,
    delete_block,
    get_block,
    get_block_children,
    get_block_content,
    get_block_tree,
    get_root_blocks,
    import_folder_as_pages,
    move_block,
    read_page_metadata,
    reorder_blocks,
    serve_block_file,
    update_block_content,
    update_block_properties,
    upload_to_block,
)
from codex.core.import_worker import process_zip_import
from codex.core.md_import import import_markdown_to_page
from codex.core.websocket import notify_file_change
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import Block, Task, User

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
    block_type: str | None = None


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


class UpdateBlockPropertiesRequest(BaseModel):
    """Request to update block properties."""

    properties: dict[str, Any]


class ImportFolderRequest(BaseModel):
    """Request to import a folder tree as pages."""

    folder_path: str


class ResolveLinkRequest(BaseModel):
    """Request model for resolving a link."""

    link: str
    current_file_path: str | None = None


def _get_children_with_content(
    notebook_path, notebook_id: int, parent_block_id: str, nb_session
) -> list[dict[str, Any]]:
    """Get all children of a page block with their content."""
    children = get_block_children(notebook_id, parent_block_id, nb_session)
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
    return result


def _block_to_dict(block: Block) -> dict[str, Any]:
    """Convert a Block model to a response dict."""
    return _block_dict(block)


# Nested router (mounted under workspace/notebook)
nested_router = APIRouter()


# ---- Routes with literal path segments MUST be registered before /{block_id} ----


@nested_router.get("/tree", response_model=BlockTreeResponse)
async def get_tree(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get hierarchical block tree for sidebar navigation."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        tree = get_block_tree(notebook_path, notebook.id, nb_session)
        return {"tree": tree, "notebook_id": notebook.id, "workspace_id": workspace.id}
    finally:
        nb_session.close()


@nested_router.get("/path/{path:path}/content")
async def get_block_content_by_path(
    workspace_identifier: str,
    notebook_identifier: str,
    path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Serve content by path (needed for markdown image resolution)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Try direct path on disk first
    file_path = notebook_path / path
    if file_path.exists() and file_path.is_file():
        # Security check
        try:
            if not file_path.resolve().is_relative_to(notebook_path.resolve()):
                raise HTTPException(status_code=403, detail="Access denied")
        except (OSError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid path")

        media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return FileResponse(path=str(file_path), media_type=media_type, filename=file_path.name)

    # Try looking up by filename in DB
    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = nb_session.exec(select(Block).where(Block.notebook_id == notebook.id, Block.path == path)).first()
        if not block and "/" not in path:
            block = nb_session.exec(
                select(Block).where(Block.notebook_id == notebook.id, Block.filename == path)
            ).first()

        if block:
            file_path_str, media_type = serve_block_file(notebook_path, block)
            if file_path_str:
                return FileResponse(path=file_path_str, media_type=media_type, filename=block.path.split("/")[-1])

        raise HTTPException(status_code=404, detail=f"Content not found: {path}")
    finally:
        nb_session.close()


# ---- End literal routes ----


@nested_router.get("/", response_model=RootBlocksResponse)
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


@nested_router.get("/{block_id}", response_model=BlockResponse)
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


@nested_router.get("/{block_id}/children", response_model=BlockChildrenResponse)
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


@nested_router.post("/", response_model=BlockResponse)
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

        notify_file_change(
            notebook_id=notebook.id,
            event_type="created",
            path=result.get("path", page_path),
            block_id=result.get("block_id"),
            block_type=request.block_type,
        )

        # Return created block plus all siblings so frontend doesn't need a refetch
        result["blocks"] = _get_children_with_content(notebook_path, notebook.id, request.parent_block_id, nb_session)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()


@nested_router.post("/pages", response_model=PageResponse)
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
        # Check if a page with this exact path already exists
        from codex.core.blocks import _sanitize_folder_name

        safe_name = _sanitize_folder_name(request.title) or "untitled"
        candidate_path = f"{request.parent_path}/{safe_name}" if request.parent_path else safe_name
        existing = nb_session.execute(
            select(Block).where(
                Block.notebook_id == notebook.id,
                Block.path == candidate_path,
                Block.block_type == "page",
            )
        ).scalar_one_or_none()
        if existing:
            return {
                "block_id": existing.block_id,
                "path": existing.path,
                "title": existing.title or request.title,
                "description": existing.description,
                "properties": existing.properties or {},
            }

        result = create_page(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            parent_path=request.parent_path,
            title=request.title,
            description=request.description,
            properties=request.properties,
            nb_session=nb_session,
        )

        notify_file_change(
            notebook_id=notebook.id,
            event_type="created",
            path=result.get("path", ""),
            block_id=result.get("block_id"),
            title=request.title,
            block_type="page",
            properties=request.properties,
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.put("/{block_id}", response_model=BlockResponse)
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
            block_type=request.block_type,
            nb_session=nb_session,
        )

        notify_file_change(
            notebook_id=notebook.id,
            event_type="modified",
            path=result.get("path", ""),
            block_id=block_id,
            title=result.get("title"),
            block_type=result.get("block_type"),
        )

        # Include updated siblings when type changed (view needs refresh)
        if request.block_type:
            block = get_block(notebook.id, block_id, nb_session)
            if block and block.parent_block_id:
                result["blocks"] = _get_children_with_content(
                    notebook_path, notebook.id, block.parent_block_id, nb_session
                )

        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()


@nested_router.patch("/{block_id}/move", response_model=BlockResponse)
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
        # Get old path before move
        old_block = get_block(notebook.id, block_id, nb_session)
        old_path = old_block.path if old_block else None

        result = move_block(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            block_id=block_id,
            new_parent_block_id=request.new_parent_block_id,
            position=request.position,
            nb_session=nb_session,
        )

        notify_file_change(
            notebook_id=notebook.id,
            event_type="moved",
            path=result.get("path", ""),
            old_path=old_path,
            block_id=block_id,
            title=result.get("title"),
            block_type=result.get("block_type"),
        )

        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.patch("/{block_id}/reorder", response_model=BlockReorderResponse)
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
        reorder_blocks(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            page_block_id=block_id,
            block_ids_in_order=request.block_ids,
            nb_session=nb_session,
        )
        # Return reordered children with content
        blocks = _get_children_with_content(notebook_path, notebook.id, block_id, nb_session)
        return {"parent_block_id": block_id, "blocks": blocks}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.delete("/{block_id}", response_model=BlockDeleteResponse)
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
        # Get block info before deleting so we can notify and return remaining siblings
        block = get_block(notebook.id, block_id, nb_session)
        parent_block_id = block.parent_block_id if block else None
        block_path = block.path if block else ""

        delete_block(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            block_id=block_id,
            nb_session=nb_session,
        )

        notify_file_change(
            notebook_id=notebook.id,
            event_type="deleted",
            path=block_path,
            block_id=block_id,
        )

        result: dict[str, Any] = {"message": "Block deleted successfully"}
        if parent_block_id:
            result["blocks"] = _get_children_with_content(notebook_path, notebook.id, parent_block_id, nb_session)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()


@nested_router.post("/convert-file", response_model=PageResponse)
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
    if request.path:
        md_path = request.path
    elif request.file_id:
        # Legacy support: look up block by integer id
        nb_session = get_notebook_session(str(notebook_path))
        try:
            block_row = nb_session.exec(
                select(Block).where(Block.notebook_id == notebook.id, Block.id == request.file_id)
            ).first()
            if not block_row:
                raise HTTPException(status_code=404, detail="Block not found")
            md_path = block_row.path
        finally:
            nb_session.close()
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


@nested_router.post("/import-markdown", response_model=PageResponse)
async def import_markdown(
    workspace_identifier: str,
    notebook_identifier: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Import a markdown file, converting it to a page of blocks."""
    logger.info(
        "import_markdown: start workspace=%s notebook=%s filename=%s user=%s",
        workspace_identifier,
        notebook_identifier,
        file.filename,
        current_user.username,
    )
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    if not file.filename or not file.filename.endswith(".md"):
        logger.warning("import_markdown: rejected - not a .md file (filename=%s)", file.filename)
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
            logger.info(
                "import_markdown: success filename=%s size=%d",
                file.filename,
                len(content),
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


@nested_router.get("/{block_id}/content")
async def get_block_content_endpoint(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Serve binary content for a block (mirrors files/{id}/content)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = get_block(notebook.id, block_id, nb_session)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")

        file_path_str, media_type = serve_block_file(notebook_path, block)
        if not file_path_str:
            # Check S3 (fields now directly on Block)
            if block.s3_key and block.s3_bucket:
                from fastapi.responses import RedirectResponse

                from codex.core.s3_storage import generate_presigned_url, is_s3_configured

                if is_s3_configured():
                    url = generate_presigned_url(block.s3_key, block.s3_version_id, block.s3_bucket)
                    return RedirectResponse(url=url)
            raise HTTPException(status_code=404, detail="Block content not found")

        return FileResponse(path=file_path_str, media_type=media_type, filename=block.path.split("/")[-1])
    finally:
        nb_session.close()


@nested_router.get("/{block_id}/text", response_model=BlockTextContentResponse)
async def get_block_text_endpoint(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Serve text content for a block, stripping frontmatter."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = get_block(notebook.id, block_id, nb_session)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")

        content = get_block_content(notebook_path, block)
        if content is None:
            raise HTTPException(status_code=404, detail="Block content not found")

        props = _parse_json(block.properties) if block.properties else None
        return {"content": content, "properties": props}
    finally:
        nb_session.close()


@nested_router.post("/upload", response_model=BlockResponse)
async def upload_block(
    workspace_identifier: str,
    notebook_identifier: str,
    file: UploadFile = File(...),
    parent_block_id: str | None = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Upload a file as a block within a page."""
    import time

    start = time.monotonic()
    logger.info(
        "upload_block: start workspace=%s notebook=%s filename=%s content_type=%s parent_block_id=%s user=%s",
        workspace_identifier,
        notebook_identifier,
        file.filename,
        file.content_type,
        parent_block_id,
        current_user.username,
    )
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    if not file.filename:
        logger.warning("upload_block: rejected - no filename provided")
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    logger.info(
        "upload_block: received filename=%s size=%d bytes notebook_path=%s",
        file.filename,
        len(content),
        notebook_path,
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = upload_to_block(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            page_block_id=parent_block_id,
            filename=file.filename,
            content=content,
            nb_session=nb_session,
        )
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "upload_block: success block_id=%s path=%s size=%d duration_ms=%.1f",
            result.get("block_id"),
            result.get("path"),
            len(content),
            duration_ms,
        )
        return result
    except FileNotFoundError as e:
        logger.warning("upload_block: parent page not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.warning("upload_block: validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("upload_block: unexpected error during upload")
        raise
    finally:
        nb_session.close()


@nested_router.post("/upload-folder-zip", response_model=ZipImportResponse)
async def upload_folder_zip(
    workspace_identifier: str,
    notebook_identifier: str,
    file: UploadFile = File(...),
    parent_path: str = Form(""),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Upload a zip file, extract to staging area, and kick off a background import task."""
    import asyncio
    import io
    import uuid
    import zipfile

    logger.info(
        "upload_folder_zip: start workspace=%s notebook=%s filename=%s parent_path=%s user=%s",
        workspace_identifier,
        notebook_identifier,
        file.filename,
        parent_path,
        current_user.username,
    )
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    if not file.filename or not file.filename.endswith(".zip"):
        logger.warning("upload_folder_zip: rejected - not a .zip file (filename=%s)", file.filename)
        raise HTTPException(status_code=400, detail="Must upload a .zip file")

    content = await file.read()
    logger.info("upload_folder_zip: received size=%d bytes", len(content))

    # Stage into .codex/staging/{upload_id}/ which the watcher ignores
    upload_id = str(uuid.uuid4())
    staging_dir = notebook_path / ".codex" / "staging" / upload_id
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            # Security: reject paths with .. or absolute paths
            for member in zf.namelist():
                if member.startswith("/") or ".." in member:
                    logger.warning("upload_folder_zip: invalid path rejected: %s", member)
                    raise HTTPException(status_code=400, detail=f"Invalid path in zip: {member}")

            # Filter out macOS resource fork metadata
            members = [m for m in zf.namelist() if not m.startswith("__MACOSX/") and not m.startswith("._")]

            # Find the top-level folder name from the zip
            top_dirs = {name.split("/")[0] for name in members if "/" in name}
            top_files = {name for name in members if "/" not in name and name}

            logger.info(
                "upload_folder_zip: extracting upload_id=%s members=%d top_dirs=%d top_files=%d",
                upload_id,
                len(members),
                len(top_dirs),
                len(top_files),
            )
            zf.extractall(staging_dir, members=[m for m in zf.infolist() if m.filename in set(members)])
    except zipfile.BadZipFile:
        shutil.rmtree(staging_dir, ignore_errors=True)
        logger.warning("upload_folder_zip: invalid zip file filename=%s", file.filename)
        raise HTTPException(status_code=400, detail="Invalid zip file")

    # Clean up any __MACOSX folder that may have been extracted
    macosx_dir = staging_dir / "__MACOSX"
    if macosx_dir.exists():
        shutil.rmtree(macosx_dir)

    # Determine the import path (relative to staging_dir)
    if len(top_dirs) == 1 and len(top_files) == 0:
        import_path = top_dirs.pop()
    else:
        # Multiple top-level items: wrap in a folder named after the zip
        folder_name = os.path.splitext(file.filename or "upload")[0]
        wrapper_dir = staging_dir / folder_name
        if not wrapper_dir.exists():
            wrapper_dir.mkdir(parents=True)
            for item_name in top_dirs | top_files:
                src = staging_dir / item_name
                if src.exists():
                    shutil.move(str(src), str(wrapper_dir / item_name))
        import_path = folder_name

    # Create a task to track the import
    task = Task(
        workspace_id=workspace.id,
        title=f"Import zip: {file.filename}",
        task_type="zip_import",
        status="pending",
        assigned_to="system",
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    logger.info(
        "upload_folder_zip: task created task_id=%s import_path=%s staging_dir=%s",
        task.id,
        import_path,
        staging_dir,
    )

    # Launch background import
    asyncio.create_task(
        process_zip_import(
            task_id=task.id,
            staging_dir=staging_dir,
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            import_path=import_path,
            parent_path=parent_path,
        )
    )

    return ZipImportResponse(
        task_id=task.id,
        status="pending",
        message=f"Import task created for {file.filename}",
    )


@nested_router.post("/import-folder", response_model=ImportFolderResponse)
async def import_folder(
    workspace_identifier: str,
    notebook_identifier: str,
    request: ImportFolderRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Import a folder tree as nested pages."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = import_folder_as_pages(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            folder_path=request.folder_path,
            nb_session=nb_session,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.get("/{block_id}/history", response_model=BlockHistoryResponse)
async def get_block_history(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get git history for a block's page directory.

    History is always returned at the page level. If the block is a page,
    its directory is used directly. If it is a child block, its parent
    page directory is used instead.
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = get_block(notebook.id, block_id, nb_session)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))

        # Resolve to the page directory
        if block.block_type == "page":
            page_path = notebook_path / block.path
        elif block.parent_block_id:
            parent = get_block(notebook.id, block.parent_block_id, nb_session)
            if parent and parent.block_type == "page":
                page_path = notebook_path / parent.path
            else:
                # Fallback to file-level history
                page_path = notebook_path / block.path
        else:
            # Root-level block with no parent page, use file-level history
            page_path = notebook_path / block.path

        if page_path.is_dir():
            history = git_manager.get_directory_history(str(page_path))
        else:
            history = git_manager.get_file_history(str(page_path))

        return {"block_id": block_id, "path": block.path, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        nb_session.close()


@nested_router.get("/{block_id}/history/{commit_hash}")
async def get_block_at_commit(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    commit_hash: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get page directory changes or block content at a specific commit.

    For page blocks, returns a PageAtCommitResponse with per-file diffs.
    For non-page blocks, returns a BlockAtCommitResponse with file content.
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = get_block(notebook.id, block_id, nb_session)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))

        # Resolve to the page directory
        if block.block_type == "page":
            page_path = notebook_path / block.path
        elif block.parent_block_id:
            parent = get_block(notebook.id, block.parent_block_id, nb_session)
            if parent and parent.block_type == "page":
                page_path = notebook_path / parent.path
            else:
                page_path = notebook_path / block.path
        else:
            page_path = notebook_path / block.path

        if page_path.is_dir():
            files = git_manager.get_directory_at_commit(str(page_path), commit_hash)
            return PageAtCommitResponse(
                block_id=block_id,
                path=block.path,
                commit_hash=commit_hash,
                files=files,
            )
        else:
            content = git_manager.get_file_at_commit(str(page_path), commit_hash)
            if content is None:
                raise HTTPException(status_code=404, detail="Content not found at this commit")
            return BlockAtCommitResponse(
                block_id=block_id,
                path=block.path,
                commit_hash=commit_hash,
                content=content,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        nb_session.close()


@nested_router.post("/resolve-link", response_model=BlockResolveLinkResponse)
async def resolve_link_endpoint(
    workspace_identifier: str,
    notebook_identifier: str,
    request: ResolveLinkRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Resolve a relative link to a block."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    from codex.core.link_resolver import LinkResolver

    try:
        resolved_path = LinkResolver.resolve_link(request.link, request.current_file_path, notebook_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Look up block by path
        block = nb_session.exec(
            select(Block).where(Block.notebook_id == notebook.id, Block.path == resolved_path)
        ).first()
        if not block and "/" not in resolved_path:
            block = nb_session.exec(
                select(Block).where(Block.notebook_id == notebook.id, Block.filename == resolved_path)
            ).first()
        if block:
            return {**_block_to_dict(block), "resolved_path": resolved_path}
        raise HTTPException(status_code=404, detail=f"Not found: {resolved_path}")
    finally:
        nb_session.close()


@nested_router.patch("/{block_id}/properties", response_model=BlockResponse)
async def update_block_properties_endpoint(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    request: UpdateBlockPropertiesRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update block properties."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = update_block_properties(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            block_id=block_id,
            properties=request.properties,
            nb_session=nb_session,
        )

        notify_file_change(
            notebook_id=notebook.id,
            event_type="modified",
            path=result.get("path", ""),
            block_id=block_id,
            title=result.get("title"),
            block_type=result.get("block_type"),
            properties=result.get("properties"),
        )

        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()

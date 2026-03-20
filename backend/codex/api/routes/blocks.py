"""Block routes for infinite nested block structure.

Provides CRUD operations for blocks and pages, supporting Notion-like
infinite block recursion backed by filesystem folders and files.
"""

import json
import logging
import mimetypes
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.helpers import get_notebook_path_nested
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
from codex.core.md_import import import_markdown_to_page
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


@nested_router.get("/tree")
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
        block = nb_session.exec(
            select(Block).where(Block.notebook_id == notebook.id, Block.path == path)
        ).first()
        if not block and "/" not in path:
            fm = nb_session.exec(
                select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.filename == path)
            ).first()
            if fm:
                file_path = notebook_path / fm.path
                if file_path.exists():
                    media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
                    return FileResponse(path=str(file_path), media_type=media_type, filename=fm.filename)

        if block:
            file_path_str, media_type = serve_block_file(notebook_path, block)
            if file_path_str:
                return FileResponse(path=file_path_str, media_type=media_type, filename=block.path.split("/")[-1])

        raise HTTPException(status_code=404, detail=f"Content not found: {path}")
    finally:
        nb_session.close()


# ---- End literal routes ----


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

        # Return created block plus all siblings so frontend doesn't need a refetch
        result["blocks"] = _get_children_with_content(
            notebook_path, notebook.id, request.parent_block_id, nb_session
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
            block_type=request.block_type,
            nb_session=nb_session,
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
        # Get parent before deleting so we can return remaining siblings
        block = get_block(notebook.id, block_id, nb_session)
        parent_block_id = block.parent_block_id if block else None

        delete_block(
            notebook_path=notebook_path,
            notebook_id=notebook.id,
            block_id=block_id,
            nb_session=nb_session,
        )

        result: dict[str, Any] = {"message": "Block deleted successfully"}
        if parent_block_id:
            result["blocks"] = _get_children_with_content(
                notebook_path, notebook.id, parent_block_id, nb_session
            )
        return result
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
            # Check S3
            if block.file_id:
                fm = nb_session.exec(select(FileMetadata).where(FileMetadata.id == block.file_id)).first()
                if fm and fm.s3_key and fm.s3_bucket:
                    from codex.core.s3_storage import generate_presigned_url, is_s3_configured
                    from fastapi.responses import RedirectResponse

                    if is_s3_configured():
                        url = generate_presigned_url(fm.s3_key, fm.s3_version_id, fm.s3_bucket)
                        return RedirectResponse(url=url)
            raise HTTPException(status_code=404, detail="Block content not found")

        return FileResponse(path=file_path_str, media_type=media_type, filename=block.path.split("/")[-1])
    finally:
        nb_session.close()


@nested_router.get("/{block_id}/text")
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


@nested_router.post("/upload")
async def upload_block(
    workspace_identifier: str,
    notebook_identifier: str,
    file: UploadFile = File(...),
    parent_block_id: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Upload a file as a block within a page."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()

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
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        nb_session.close()


@nested_router.post("/import-folder")
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


@nested_router.get("/{block_id}/history")
async def get_block_history(
    workspace_identifier: str,
    notebook_identifier: str,
    block_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get git history for a block's backing file."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )
    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = get_block(notebook.id, block_id, nb_session)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")

        file_path = notebook_path / block.path
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        history = git_manager.get_file_history(str(file_path))
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
    """Get block content at a specific commit."""
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
        content = git_manager.get_file_at_commit(str(notebook_path / block.path), commit_hash)
        if content is None:
            raise HTTPException(status_code=404, detail="Content not found at this commit")
        return {"block_id": block_id, "path": block.path, "commit_hash": commit_hash, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        nb_session.close()


@nested_router.post("/resolve-link")
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
        # Try block lookup first
        block = nb_session.exec(
            select(Block).where(Block.notebook_id == notebook.id, Block.path == resolved_path)
        ).first()
        if block:
            return {**_block_to_dict(block), "resolved_path": resolved_path}

        # Fall back to FileMetadata
        fm = nb_session.exec(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == resolved_path)
        ).first()
        if not fm and "/" not in resolved_path:
            fm = nb_session.exec(
                select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.filename == resolved_path)
            ).first()
        if fm:
            return {
                "id": fm.id,
                "path": fm.path,
                "filename": fm.filename,
                "content_type": fm.content_type,
                "resolved_path": resolved_path,
            }
        raise HTTPException(status_code=404, detail=f"Not found: {resolved_path}")
    finally:
        nb_session.close()


@nested_router.patch("/{block_id}/properties")
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
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        nb_session.close()

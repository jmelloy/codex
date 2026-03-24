"""Snippet posting routes.

Designed for programmatic use from pre-commit hooks, Python scripts,
and other automation tools. Authenticates via personal access tokens.
"""

import hashlib
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.core.blocks import create_page
from codex.core.git_manager import GitManager
from codex.core.metadata import MetadataParser
from codex.core.watcher import get_content_type, get_watcher_for_notebook
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import Block, Notebook, User, Workspace

router = APIRouter()
logger = logging.getLogger(__name__)


class SnippetRequest(BaseModel):
    """Request to post a snippet.

    Minimal required fields: workspace, notebook, and content.
    The endpoint generates a filename with the current date if not provided.
    """

    workspace: str  # Workspace slug or ID
    notebook: str  # Notebook slug or ID
    content: str
    title: str | None = None
    filename: str | None = None  # If omitted, auto-generated from title/date
    folder: str | None = None  # Subfolder within the notebook
    tags: list[str] = Field(default_factory=list)
    file_type: str | None = None  # e.g. "snippet", "note", "log"
    properties: dict | None = None  # Extra frontmatter properties


class SnippetResponse(BaseModel):
    """Response after creating a snippet."""

    id: int
    path: str
    filename: str
    content_type: str
    size: int
    title: str | None = None
    created_at: str
    message: str


def _generate_snippet_filename(title: str | None, extension: str = ".md") -> str:
    """Generate a filename for a snippet based on title and current date."""
    now = datetime.now(UTC)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")

    if title:
        # Sanitize title for use in filename
        safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in title)
        safe_title = safe_title.strip().replace(" ", "-").lower()
        if safe_title:
            return f"{date_str}-{safe_title}{extension}"

    return f"{date_str}-{time_str}-snippet{extension}"


async def _resolve_workspace_and_notebook(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User,
    session: AsyncSession,
) -> tuple[Path, Notebook, Workspace]:
    """Resolve workspace and notebook from slug or ID."""
    # Try slug first, then ID for workspace
    workspace_query = select(Workspace).where(Workspace.owner_id == current_user.id)
    try:
        ws_id = int(workspace_identifier)
        workspace_query = workspace_query.where(Workspace.id == ws_id)
    except ValueError:
        workspace_query = workspace_query.where(Workspace.slug == workspace_identifier)

    result = await session.execute(workspace_query)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_identifier}")

    # Try slug first, then ID for notebook
    notebook_query = select(Notebook).where(Notebook.workspace_id == workspace.id)
    try:
        nb_id = int(notebook_identifier)
        notebook_query = notebook_query.where(Notebook.id == nb_id)
    except ValueError:
        notebook_query = notebook_query.where(Notebook.slug == notebook_identifier)

    result = await session.execute(notebook_query)
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail=f"Notebook not found: {notebook_identifier}")

    workspace_path = Path(workspace.path).resolve()
    notebook_path = workspace_path / notebook.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found on disk")

    return notebook_path, notebook, workspace


@router.post("/", response_model=SnippetResponse, status_code=201)
async def post_snippet(
    request: SnippetRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> SnippetResponse:
    """Post a snippet to a notebook.

    Creates a new markdown file with appropriate frontmatter and dates.
    Designed for use from pre-commit hooks, scripts, and CLI tools.

    Example usage with curl:
        curl -X POST http://localhost:8000/api/v1/snippets/ \\
          -H "Authorization: Bearer cdx_..." \\
          -H "Content-Type: application/json" \\
          -d '{"workspace": "my-workspace", "notebook": "my-notebook",
               "content": "Code snippet here", "title": "My Snippet"}'
    """
    notebook_path, notebook, workspace = await _resolve_workspace_and_notebook(
        request.workspace, request.notebook, current_user, session
    )

    # Generate filename
    filename = request.filename or _generate_snippet_filename(request.title)

    # When no folder is specified, auto-create a parent page so the snippet
    # appears in the sidebar (which only renders page-type blocks).
    auto_create_page = not request.folder
    if request.folder:
        page_folder = request.folder
    else:
        page_folder = os.path.splitext(filename)[0]

    # Create the parent page BEFORE writing the file, since create_page
    # also creates the directory and checks for uniqueness.
    nb_session = get_notebook_session(str(notebook_path))
    parent_block_id = None
    try:
        if auto_create_page:
            parent_page = nb_session.execute(
                select(Block).where(
                    Block.notebook_id == notebook.id,
                    Block.path == page_folder,
                    Block.block_type == "page",
                )
            ).scalar_one_or_none()

            if not parent_page:
                page_result = create_page(
                    notebook_path=notebook_path,
                    notebook_id=notebook.id,
                    parent_path=None,
                    title=request.title or page_folder,
                    nb_session=nb_session,
                )
                nb_session.commit()
                parent_block_id = page_result["block_id"]
                page_folder = page_result["path"]
            else:
                parent_block_id = parent_page.block_id
        else:
            # For explicit folders, look up existing page if any
            parts = page_folder.rstrip("/").split("/")
            for i in range(len(parts), 0, -1):
                candidate = "/".join(parts[:i])
                parent_page = nb_session.execute(
                    select(Block).where(
                        Block.notebook_id == notebook.id,
                        Block.path == candidate,
                        Block.block_type == "page",
                    )
                ).scalar_one_or_none()
                if parent_page:
                    parent_block_id = parent_page.block_id
                    break
    except HTTPException:
        nb_session.close()
        raise
    except Exception as e:
        nb_session.close()
        logger.error(f"Error creating parent page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating snippet: {str(e)}")

    rel_path = os.path.join(page_folder, filename)

    # Build frontmatter properties
    frontmatter_props: dict = {}
    if request.title:
        frontmatter_props["title"] = request.title
    frontmatter_props["date"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if request.tags:
        frontmatter_props["tags"] = request.tags
    if request.file_type:
        frontmatter_props["type"] = request.file_type
    if request.properties:
        frontmatter_props.update(request.properties)

    full_content = MetadataParser.write_frontmatter(request.content, frontmatter_props)

    file_path = notebook_path / rel_path

    # Prevent path traversal
    try:
        resolved = file_path.resolve()
        if not str(resolved).startswith(str(notebook_path.resolve())):
            raise HTTPException(status_code=400, detail="Invalid path")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid path")

    # If file exists, make the name unique
    if file_path.exists():
        base, ext = os.path.splitext(rel_path)
        counter = 1
        while file_path.exists():
            rel_path = f"{base}-{counter}{ext}"
            file_path = notebook_path / rel_path
            counter += 1

    # Create parent directories
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    with open(file_path, "w") as f:
        f.write(full_content)

    # Process through watcher or manually create metadata
    watcher = get_watcher_for_notebook(str(notebook_path))

    if watcher:
        filepath, sidecar = MetadataParser.resolve_sidecar(str(file_path))
        op = watcher.enqueue_operation(
            filepath=filepath,
            sidecar_path=sidecar,
            operation="created",
            comment=f"Snippet: {request.title or filename}",
            wait=True,
        )
        if op.error:
            logger.error(f"Error processing snippet creation: {op.error}")
            raise HTTPException(status_code=500, detail=f"Error creating snippet: {str(op.error)}")

    # Get or create the block record
    try:
        result = nb_session.execute(
            select(Block).where(Block.notebook_id == notebook.id, Block.path == rel_path)
        )
        block = result.scalar_one_or_none()

        if not block:
            from ulid import ULID

            content_type = get_content_type(str(file_path))
            file_stats = os.stat(file_path)

            block = Block(
                notebook_id=notebook.id,
                block_id=str(ULID()),
                parent_block_id=parent_block_id,
                path=rel_path,
                filename=os.path.basename(rel_path),
                block_type="text",
                content_format="markdown",
                order_index=0.0,
                content_type=content_type,
                size=file_stats.st_size,
                hash=hashlib.sha256(full_content.encode()).hexdigest(),
                title=request.title,
                file_type=request.file_type or "snippet",
                file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
            )
            nb_session.add(block)

            # Commit to git if no watcher
            if not watcher:
                git_manager = GitManager(str(notebook_path))
                commit_hash = git_manager.commit(f"Snippet: {request.title or filename}", [str(file_path)])
                if commit_hash:
                    block.last_commit_hash = commit_hash

            nb_session.commit()
            nb_session.refresh(block)

        return SnippetResponse(
            id=block.id,
            path=block.path,
            filename=block.filename or os.path.basename(block.path),
            content_type=block.content_type or "text/markdown",
            size=block.size or 0,
            title=request.title,
            created_at=block.created_at.isoformat() if block.created_at else datetime.now(UTC).isoformat(),
            message="Snippet created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating snippet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating snippet: {str(e)}")
    finally:
        nb_session.close()

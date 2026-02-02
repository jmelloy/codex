"""V2 API routes with hierarchical slug-based URLs.

This module provides clean, hierarchical routes like:
- GET /{workspace}/ - Get workspace by slug
- GET /{workspace}/notebooks - List notebooks
- GET /{workspace}/{notebook}/files - List files
- GET /{workspace}/{notebook}/files/{path:path} - Get file by path
"""

import hashlib
import json
import logging
import mimetypes
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.dependencies import (
    extract_workspace_slug,
    get_notebook_by_slugs,
    get_notebook_path_from_slugs,
    get_workspace_by_slug,
)
from codex.core.metadata import MetadataParser
from codex.core.watcher import NotebookWatcher, get_content_type
from codex.db.database import get_notebook_session, get_system_session, init_notebook_db
from codex.db.models import (
    FileMetadata,
    Notebook,
    NotebookPluginConfig,
    Task,
    User,
    Workspace,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# The metadata file name stored in each folder
FOLDER_METADATA_FILE = ".metadata"
DEFAULT_FOLDER_PAGINATION_LIMIT = 100


# =============================================================================
# Pydantic models for request bodies
# =============================================================================


class NotebookCreate(BaseModel):
    """Request body for creating a notebook."""

    name: str
    description: str | None = None


class CreateFileRequest(BaseModel):
    """Request model for creating a file."""

    path: str
    content: str


class UpdateFileRequest(BaseModel):
    """Request model for updating a file."""

    content: str | None = None
    properties: dict[str, Any] | None = None


class MoveFileRequest(BaseModel):
    """Request model for moving/renaming a file."""

    new_path: str


class ResolveLinkRequest(BaseModel):
    """Request model for resolving a link."""

    link: str
    current_file_path: str | None = None


class UpdateFolderPropertiesRequest(BaseModel):
    """Request model for updating folder properties."""

    properties: dict[str, Any]


class NotebookPluginConfigUpdate(BaseModel):
    """Request body for updating notebook plugin configuration."""

    enabled: bool | None = None
    config: dict | None = None


class ThemeUpdate(BaseModel):
    """Request body for updating theme setting."""

    theme: str


# =============================================================================
# Helper functions
# =============================================================================


def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    import re

    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "notebook"


def read_folder_properties(folder_path: Path) -> dict[str, Any] | None:
    """Read folder properties from .metadata file in the folder."""
    metadata_file = folder_path / FOLDER_METADATA_FILE
    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file) as f:
            content = f.read()
        properties, _ = MetadataParser.parse_frontmatter(content)
        return properties
    except Exception as e:
        logger.warning(f"Failed to read folder properties from {metadata_file}: {e}")
        return None


def write_folder_properties(folder_path: Path, properties: dict[str, Any]) -> None:
    """Write folder properties to .metadata file in the folder."""
    metadata_file = folder_path / FOLDER_METADATA_FILE
    content = MetadataParser.write_frontmatter("", properties)
    with open(metadata_file, "w") as f:
        f.write(content)


def get_folder_files(
    folder_path: str,
    notebook_id: int,
    notebook_path: Path,
    nb_session,
    skip: int = 0,
    limit: int = DEFAULT_FOLDER_PAGINATION_LIMIT,
) -> tuple[list[dict], int]:
    """Get files in a specific folder (not recursive) with pagination."""
    prefix = f"{folder_path}/" if folder_path else ""

    if folder_path:
        files_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook_id, FileMetadata.path.startswith(prefix))
        )
    else:
        files_result = nb_session.execute(select(FileMetadata).where(FileMetadata.notebook_id == notebook_id))

    all_files = files_result.scalars().all()

    folder_files = []
    total_count = 0
    MAX_COUNT_THRESHOLD = 10000

    for f in all_files:
        if f.filename == FOLDER_METADATA_FILE:
            continue

        if folder_path:
            if not f.path.startswith(prefix):
                continue
            relative = f.path[len(prefix) :]
            if "/" in relative:
                continue
        else:
            if "/" in f.path:
                continue

        total_count += 1

        if total_count <= skip:
            continue

        if len(folder_files) >= limit and total_count > skip + limit + 100:
            break

        if total_count > MAX_COUNT_THRESHOLD and len(folder_files) >= limit:
            total_count = MAX_COUNT_THRESHOLD
            break

        if len(folder_files) < limit:
            properties = None
            if f.properties:
                try:
                    properties = json.loads(f.properties)
                except json.JSONDecodeError:
                    properties = None

            folder_files.append(
                {
                    "id": f.id,
                    "notebook_id": f.notebook_id,
                    "path": f.path,
                    "filename": f.filename,
                    "content_type": f.content_type,
                    "size": f.size,
                    "title": f.title,
                    "description": f.description,
                    "properties": properties,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "updated_at": f.updated_at.isoformat() if f.updated_at else None,
                }
            )

    return folder_files, total_count


def get_subfolders(folder_path: str, notebook_path: Path) -> list[dict]:
    """Get immediate subfolders in a folder."""
    full_folder_path = notebook_path / folder_path if folder_path else notebook_path

    subfolders = []
    for item in full_folder_path.iterdir():
        if item.name.startswith("."):
            continue
        if item.is_dir():
            subfolder_path = f"{folder_path}/{item.name}" if folder_path else item.name
            properties = read_folder_properties(item)
            folder_stats = item.stat()

            subfolders.append(
                {
                    "path": subfolder_path,
                    "name": item.name,
                    "title": properties.get("title") if properties else None,
                    "description": properties.get("description") if properties else None,
                    "properties": properties,
                    "created_at": datetime.fromtimestamp(folder_stats.st_ctime, tz=UTC).isoformat(),
                    "updated_at": datetime.fromtimestamp(folder_stats.st_mtime, tz=UTC).isoformat(),
                }
            )

    subfolders.sort(key=lambda x: x["name"].lower())
    return subfolders


def workspace_to_dict(ws: Workspace) -> dict:
    """Convert workspace to dict with slug field."""
    return {
        "id": ws.id,
        "name": ws.name,
        "path": ws.path,
        "slug": extract_workspace_slug(ws),
        "owner_id": ws.owner_id,
        "theme_setting": ws.theme_setting,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
    }


def notebook_to_dict(nb: Notebook) -> dict:
    """Convert notebook to dict."""
    return {
        "id": nb.id,
        "name": nb.name,
        "path": nb.path,
        "slug": nb.path,  # notebook path is already the slug
        "description": nb.description,
        "created_at": nb.created_at.isoformat() if nb.created_at else None,
        "updated_at": nb.updated_at.isoformat() if nb.updated_at else None,
    }


# =============================================================================
# Workspace routes
# =============================================================================


@router.get("/{workspace}/")
async def get_workspace(
    workspace: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get workspace by slug."""
    ws = await get_workspace_by_slug(workspace, current_user, session)
    return workspace_to_dict(ws)


@router.patch("/{workspace}/theme")
async def update_workspace_theme(
    workspace: str,
    body: ThemeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update the theme setting for a workspace."""
    ws = await get_workspace_by_slug(workspace, current_user, session)
    ws.theme_setting = body.theme
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    return workspace_to_dict(ws)


# =============================================================================
# Notebook routes
# =============================================================================


@router.get("/{workspace}/notebooks")
async def list_notebooks(
    workspace: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all notebooks in a workspace."""
    ws = await get_workspace_by_slug(workspace, current_user, session)
    result = await session.execute(select(Notebook).where(Notebook.workspace_id == ws.id))
    notebooks = result.scalars().all()
    return [notebook_to_dict(nb) for nb in notebooks]


@router.post("/{workspace}/notebooks")
async def create_notebook(
    workspace: str,
    body: NotebookCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new notebook in a workspace."""
    ws = await get_workspace_by_slug(workspace, current_user, session)

    workspace_path = Path(ws.path)
    slug = slugify(body.name)
    notebook_path = workspace_path / slug

    counter = 1
    original_slug = slug
    while notebook_path.exists():
        slug = f"{original_slug}-{counter}"
        notebook_path = workspace_path / slug
        counter += 1

    try:
        notebook_path.mkdir(parents=True, exist_ok=False)
        init_notebook_db(str(notebook_path))

        from codex.core.git_manager import GitManager

        GitManager(str(notebook_path))

        notebook = Notebook(workspace_id=ws.id, name=body.name, path=slug, description=body.description)
        session.add(notebook)
        await session.commit()
        await session.refresh(notebook)

        NotebookWatcher(str(notebook_path), notebook.id).start()

        return notebook_to_dict(notebook)

    except Exception as e:
        if notebook_path.exists():
            import shutil

            shutil.rmtree(notebook_path)
        raise HTTPException(status_code=500, detail=f"Error creating notebook: {str(e)}")


# =============================================================================
# Search routes (must come before /{workspace}/{notebook} catch-all)
# =============================================================================


@router.get("/{workspace}/search")
async def search(
    workspace: str,
    q: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files and content in a workspace."""
    ws = await get_workspace_by_slug(workspace, current_user, session)

    return {
        "query": q,
        "workspace_id": ws.id,
        "results": [],
        "message": "Full-text search requires search index population",
    }


@router.get("/{workspace}/search/tags")
async def search_by_tags(
    workspace: str,
    tags: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files by tags."""
    ws = await get_workspace_by_slug(workspace, current_user, session)

    tag_list = [tag.strip() for tag in tags.split(",")]

    return {
        "tags": tag_list,
        "workspace_id": ws.id,
        "results": [],
        "message": "Tag search requires notebook-level database queries",
    }


# =============================================================================
# Task routes (must come before /{workspace}/{notebook} catch-all)
# =============================================================================


@router.get("/{workspace}/tasks")
async def list_tasks(
    workspace: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[Task]:
    """List all tasks for a workspace."""
    ws = await get_workspace_by_slug(workspace, current_user, session)
    result = await session.execute(select(Task).where(Task.workspace_id == ws.id))
    return result.scalars().all()


@router.get("/{workspace}/tasks/{task_id}")
async def get_task(
    workspace: str,
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Get a specific task."""
    ws = await get_workspace_by_slug(workspace, current_user, session)
    result = await session.execute(select(Task).where(Task.id == task_id, Task.workspace_id == ws.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{workspace}/tasks")
async def create_task(
    workspace: str,
    title: str,
    description: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Create a new task."""
    ws = await get_workspace_by_slug(workspace, current_user, session)
    task = Task(workspace_id=ws.id, title=title, description=description)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.put("/{workspace}/tasks/{task_id}")
async def update_task(
    workspace: str,
    task_id: int,
    status: str = None,
    assigned_to: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Update a task."""
    ws = await get_workspace_by_slug(workspace, current_user, session)
    result = await session.execute(select(Task).where(Task.id == task_id, Task.workspace_id == ws.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if status:
        task.status = status
    if assigned_to:
        task.assigned_to = assigned_to

    task.updated_at = datetime.now(UTC)

    if status == "completed":
        task.completed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(task)
    return task


# =============================================================================
# Notebook detail routes (/{workspace}/{notebook} catch-all comes after specific routes)
# =============================================================================


@router.get("/{workspace}/{notebook}")
async def get_notebook(
    workspace: str,
    notebook: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a specific notebook by slug."""
    _, nb = await get_notebook_by_slugs(workspace, notebook, current_user, session)
    return notebook_to_dict(nb)


@router.get("/{workspace}/{notebook}/indexing-status")
async def get_notebook_indexing_status(
    workspace: str,
    notebook: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get the indexing status for a notebook."""
    _, nb = await get_notebook_by_slugs(workspace, notebook, current_user, session)

    from codex.main import get_active_watchers

    for watcher in get_active_watchers():
        if watcher.notebook_id == nb.id:
            return watcher.get_indexing_status()

    return {"notebook_id": nb.id, "status": "not_started", "is_alive": False}


# =============================================================================
# File routes
# =============================================================================


@router.get("/{workspace}/{notebook}/files")
async def list_files(
    workspace: str,
    notebook: str,
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List files in a notebook with pagination."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        from sqlmodel import func

        count_statement = select(func.count(FileMetadata.id)).where(FileMetadata.notebook_id == nb.id)
        count_result = nb_session.execute(count_statement)
        total_count = count_result.scalar_one()

        statement = select(FileMetadata).where(FileMetadata.notebook_id == nb.id).offset(skip).limit(limit)
        files_result = nb_session.execute(statement)
        files = files_result.scalars().all()

        file_list = []
        for f in files:
            properties = None
            if f.properties:
                try:
                    properties = json.loads(f.properties)
                except json.JSONDecodeError:
                    properties = None

            file_list.append(
                {
                    "id": f.id,
                    "notebook_id": f.notebook_id,
                    "path": f.path,
                    "filename": f.filename,
                    "content_type": f.content_type,
                    "size": f.size,
                    "hash": f.hash,
                    "title": f.title,
                    "description": f.description,
                    "file_type": f.file_type,
                    "properties": properties,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "updated_at": f.updated_at.isoformat() if f.updated_at else None,
                    "file_modified_at": f.file_modified_at.isoformat() if f.file_modified_at else None,
                }
            )

        return {
            "files": file_list,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total_count,
                "has_more": skip + len(file_list) < total_count,
            },
        }
    finally:
        nb_session.close()


@router.get("/{workspace}/{notebook}/files/{file_path:path}/text")
async def get_file_text(
    workspace: str,
    notebook: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get text content for a file by path."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        disk_path = notebook_path / file_meta.path

        if not disk_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        if not (
            file_meta.content_type.startswith("text/")
            or file_meta.content_type in ["application/json", "application/xml", "application/x-codex-view"]
        ):
            raise HTTPException(
                status_code=400, detail="File is not a text file. Use /content endpoint for binary files."
            )

        try:
            with open(disk_path) as f:
                raw_content = f.read()
        except Exception as e:
            logger.error(f"Error reading file content: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error reading file content")

        content = raw_content
        properties = None
        if file_meta.content_type in ["text/markdown", "application/x-codex-view"]:
            properties, body_content = MetadataParser.parse_frontmatter(raw_content)
            properties_json = json.dumps(properties) if properties else None
            if file_meta.properties != properties_json:
                file_meta.properties = properties_json
                if properties:
                    if "title" in properties:
                        file_meta.title = properties["title"]
                    if "description" in properties:
                        file_meta.description = properties["description"]
                    if "type" in properties:
                        file_meta.file_type = properties["type"]
                nb_session.commit()
            if file_meta.content_type == "application/x-codex-view":
                content = raw_content
            else:
                content = body_content

        return {
            "id": file_meta.id,
            "content": content,
            "properties": properties,
        }
    finally:
        nb_session.close()


@router.get("/{workspace}/{notebook}/files/{file_path:path}/content")
async def get_file_content(
    workspace: str,
    notebook: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content (serves binary files like images)."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        disk_path = notebook_path / file_meta.path

        try:
            resolved_path = disk_path.resolve()
            resolved_notebook = notebook_path.resolve()
            if not str(resolved_path).startswith(str(resolved_notebook)):
                raise HTTPException(status_code=403, detail="Access denied: Invalid file path")
        except (OSError, ValueError) as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not disk_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        media_type, _ = mimetypes.guess_type(str(disk_path))
        if media_type is None:
            media_type = "application/octet-stream"

        return FileResponse(path=str(disk_path), media_type=media_type, filename=file_meta.filename)
    finally:
        nb_session.close()


@router.get("/{workspace}/{notebook}/files/{file_path:path}/history")
async def get_file_history(
    workspace: str,
    notebook: str,
    file_path: str,
    max_count: int = 20,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get git history for a specific file."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        disk_path = notebook_path / file_meta.path

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        history = git_manager.get_file_history(str(disk_path), max_count=max_count)

        return {"file_id": file_meta.id, "path": file_meta.path, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting file history: {str(e)}")
    finally:
        nb_session.close()


@router.get("/{workspace}/{notebook}/files/{file_path:path}/history/{commit_hash}")
async def get_file_at_commit(
    workspace: str,
    notebook: str,
    file_path: str,
    commit_hash: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content at a specific commit."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        disk_path = notebook_path / file_meta.path

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        content = git_manager.get_file_at_commit(str(disk_path), commit_hash)

        if content is None:
            raise HTTPException(status_code=404, detail="File not found at this commit")

        return {"file_id": file_meta.id, "path": file_meta.path, "commit_hash": commit_hash, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file at commit: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting file at commit: {str(e)}")
    finally:
        nb_session.close()


@router.get("/{workspace}/{notebook}/files/{file_path:path}")
async def get_file(
    workspace: str,
    notebook: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file metadata by path (without content)."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        properties = None
        if file_meta.properties:
            try:
                properties = json.loads(file_meta.properties)
            except json.JSONDecodeError:
                properties = None

        return {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "content_type": file_meta.content_type,
            "size": file_meta.size,
            "hash": file_meta.hash,
            "title": file_meta.title,
            "description": file_meta.description,
            "file_type": file_meta.file_type,
            "properties": properties,
            "created_at": file_meta.created_at.isoformat() if file_meta.created_at else None,
            "updated_at": file_meta.updated_at.isoformat() if file_meta.updated_at else None,
            "file_modified_at": file_meta.file_modified_at.isoformat() if file_meta.file_modified_at else None,
        }
    finally:
        nb_session.close()


@router.post("/{workspace}/{notebook}/files")
async def create_file(
    workspace: str,
    notebook: str,
    request: CreateFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new file."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_path = notebook_path / request.path

        if file_path.exists():
            raise HTTPException(status_code=400, detail="File already exists")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        content_type = get_content_type(str(file_path))

        file_meta = FileMetadata(
            notebook_id=nb.id,
            path=request.path,
            filename=os.path.basename(request.path),
            content_type=content_type,
            size=0,
            hash=hashlib.sha256(request.content.encode()).hexdigest(),
        )

        nb_session.add(file_meta)
        try:
            nb_session.commit()
            nb_session.refresh(file_meta)
        except Exception as commit_error:
            nb_session.rollback()
            if "UNIQUE constraint failed" in str(commit_error):
                existing_result = nb_session.execute(
                    select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == request.path)
                )
                file_meta = existing_result.scalar_one_or_none()
                if not file_meta:
                    raise HTTPException(status_code=500, detail="Race condition: file metadata not found")
            else:
                raise

        with open(file_path, "w") as f:
            f.write(request.content)

        nb_session.refresh(file_meta)

        file_stats = os.stat(file_path)
        file_meta.size = file_stats.st_size
        file_meta.file_created_at = datetime.fromtimestamp(file_stats.st_ctime)
        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        commit_hash = git_manager.commit(f"Create {os.path.basename(request.path)}", [str(file_path)])
        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        nb_session.commit()
        nb_session.refresh(file_meta)

        return {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "content_type": file_meta.content_type,
            "size": file_meta.size,
            "message": "File created successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating file in notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating file: {str(e)}")
    finally:
        nb_session.close()


@router.post("/{workspace}/{notebook}/files/upload")
async def upload_file(
    workspace: str,
    notebook: str,
    file: UploadFile = File(...),
    path: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Upload a binary file."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        target_path = path if path else file.filename
        if not target_path:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_path = notebook_path / target_path

        if file_path.exists():
            raise HTTPException(status_code=400, detail="File already exists")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        content_type = get_content_type(str(file_path))

        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        file_meta = FileMetadata(
            notebook_id=nb.id,
            path=target_path,
            filename=os.path.basename(target_path),
            content_type=content_type,
            size=len(content),
            hash=file_hash,
        )

        nb_session.add(file_meta)
        try:
            nb_session.commit()
            nb_session.refresh(file_meta)
        except Exception as commit_error:
            nb_session.rollback()
            if "UNIQUE constraint failed" in str(commit_error):
                existing_result = nb_session.execute(
                    select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == target_path)
                )
                file_meta = existing_result.scalar_one_or_none()
                if not file_meta:
                    raise HTTPException(status_code=500, detail="Race condition: file metadata not found")
            else:
                raise

        with open(file_path, "wb") as f:
            f.write(content)

        file_stats = os.stat(file_path)
        file_meta.size = file_stats.st_size
        file_meta.file_created_at = datetime.fromtimestamp(file_stats.st_ctime)
        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        commit_hash = git_manager.commit(f"Upload {os.path.basename(target_path)}", [str(file_path)])
        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        nb_session.commit()
        nb_session.refresh(file_meta)

        return {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "content_type": file_meta.content_type,
            "size": file_meta.size,
            "message": "File uploaded successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        nb_session.close()


@router.put("/{workspace}/{notebook}/files/{file_path:path}")
async def update_file(
    workspace: str,
    notebook: str,
    file_path: str,
    request: UpdateFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update a file by path."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        disk_path = notebook_path / file_meta.path

        if not disk_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        content = request.content
        properties = request.properties

        if properties is not None:
            if content and file_meta.content_type in ["text/markdown", "application/x-codex-view"]:
                content = MetadataParser.write_frontmatter(content, properties)
            else:
                MetadataParser.write_sidecar(str(disk_path), properties)

        if content is not None:
            with open(disk_path, "w") as f:
                f.write(content)

        return {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "content_type": file_meta.content_type,
            "size": file_meta.size,
            "hash": file_meta.hash,
            "title": file_meta.title,
            "description": file_meta.description,
            "properties": properties,
            "updated_at": file_meta.updated_at.isoformat() if file_meta.updated_at else None,
            "message": "File updated successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file in notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating file: {str(e)}")
    finally:
        nb_session.close()


@router.patch("/{workspace}/{notebook}/files/{file_path:path}/move")
async def move_file(
    workspace: str,
    notebook: str,
    file_path: str,
    request: MoveFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Move or rename a file."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        old_file_path = notebook_path / file_meta.path
        new_file_path = notebook_path / request.new_path

        if not old_file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        if new_file_path.exists() and old_file_path != new_file_path:
            raise HTTPException(status_code=400, detail="Target path already exists")

        new_file_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.move(str(old_file_path), str(new_file_path))

        old_file_path_str, old_sidecar = MetadataParser.resolve_sidecar(str(old_file_path))
        if old_sidecar:
            old_sidecar_name = os.path.basename(old_sidecar)
            old_filename = os.path.basename(old_file_path)

            if old_sidecar_name.startswith("."):
                sidecar_suffix = old_sidecar_name[len("." + old_filename) :]
                new_sidecar_name = f".{new_file_path.name}{sidecar_suffix}"
                new_sidecar = str(new_file_path.parent / new_sidecar_name)
            else:
                sidecar_suffix = old_sidecar_name[len(old_filename) :]
                new_sidecar = str(new_file_path) + sidecar_suffix

            if Path(old_sidecar).exists():
                shutil.move(old_sidecar, new_sidecar)
                logger.debug(f"Moved sidecar file from {old_sidecar} to {new_sidecar}")

        old_path = file_meta.path
        file_meta.path = request.new_path
        file_meta.filename = os.path.basename(request.new_path)
        file_meta.updated_at = datetime.now(UTC)

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        commit_hash = git_manager.commit(
            f"Move {os.path.basename(old_path)} to {request.new_path}", [str(new_file_path)]
        )
        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        nb_session.commit()
        nb_session.refresh(file_meta)

        return {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "content_type": file_meta.content_type,
            "size": file_meta.size,
            "message": "File moved successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving file in notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error moving file: {str(e)}")
    finally:
        nb_session.close()


@router.delete("/{workspace}/{notebook}/files/{file_path:path}")
async def delete_file(
    workspace: str,
    notebook: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a file by path."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == file_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        disk_path = notebook_path / file_meta.path

        if disk_path.exists():
            os.remove(disk_path)

        _, sidecar = MetadataParser.resolve_sidecar(str(disk_path))
        if sidecar and Path(sidecar).exists():
            os.remove(sidecar)
            logger.debug(f"Deleted sidecar file: {sidecar}")

        nb_session.delete(file_meta)

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        git_manager.commit(f"Delete {file_meta.filename}", [])

        nb_session.commit()

        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
    finally:
        nb_session.close()


@router.post("/{workspace}/{notebook}/files/resolve-link")
async def resolve_link(
    workspace: str,
    notebook: str,
    request: ResolveLinkRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Resolve a link to a file path."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    from codex.core.link_resolver import LinkResolver

    try:
        resolved_path = LinkResolver.resolve_link(request.link, request.current_file_path, notebook_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.path == resolved_path)
        )
        file_meta = file_result.scalar_one_or_none()

        if not file_meta and "/" not in resolved_path:
            file_result = nb_session.execute(
                select(FileMetadata).where(FileMetadata.notebook_id == nb.id, FileMetadata.filename == resolved_path)
            )
            file_meta = file_result.scalars().first()

        if not file_meta:
            raise HTTPException(status_code=404, detail=f"File not found: {resolved_path}")

        properties = None
        if file_meta.properties:
            try:
                properties = json.loads(file_meta.properties)
            except json.JSONDecodeError:
                properties = None

        return {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "content_type": file_meta.content_type,
            "size": file_meta.size,
            "hash": file_meta.hash,
            "title": file_meta.title,
            "description": file_meta.description,
            "file_type": file_meta.file_type,
            "properties": properties,
            "resolved_path": resolved_path,
            "created_at": file_meta.created_at.isoformat() if file_meta.created_at else None,
            "updated_at": file_meta.updated_at.isoformat() if file_meta.updated_at else None,
        }
    finally:
        nb_session.close()


# =============================================================================
# Folder routes
# =============================================================================


@router.get("/{workspace}/{notebook}/folders/{folder_path:path}")
async def get_folder(
    workspace: str,
    notebook: str,
    folder_path: str,
    skip: int = 0,
    limit: int = DEFAULT_FOLDER_PAGINATION_LIMIT,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get folder metadata and its files with pagination."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    full_folder_path = notebook_path / folder_path

    try:
        resolved_path = full_folder_path.resolve()
        resolved_notebook = notebook_path.resolve()
        if not str(resolved_path).startswith(str(resolved_notebook)):
            raise HTTPException(status_code=403, detail="Access denied: Invalid folder path")
    except (OSError, ValueError) as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid folder path")

    if not full_folder_path.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    if not full_folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a folder")

    properties = read_folder_properties(full_folder_path)
    folder_stats = full_folder_path.stat()

    nb_session = get_notebook_session(str(notebook_path))
    try:
        files, total_file_count = get_folder_files(folder_path, nb.id, notebook_path, nb_session, skip, limit)
        subfolders = get_subfolders(folder_path, notebook_path)

        folder_name = os.path.basename(folder_path) if folder_path else ""

        return {
            "path": folder_path,
            "name": folder_name,
            "notebook_id": nb.id,
            "title": properties.get("title") if properties else None,
            "description": properties.get("description") if properties else None,
            "properties": properties,
            "file_count": total_file_count,
            "files": files,
            "subfolders": subfolders,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total_file_count,
                "has_more": skip + len(files) < total_file_count,
            },
            "created_at": datetime.fromtimestamp(folder_stats.st_ctime, tz=UTC).isoformat(),
            "updated_at": datetime.fromtimestamp(folder_stats.st_mtime, tz=UTC).isoformat(),
        }
    finally:
        nb_session.close()


@router.put("/{workspace}/{notebook}/folders/{folder_path:path}")
async def update_folder_properties(
    workspace: str,
    notebook: str,
    folder_path: str,
    request: UpdateFolderPropertiesRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update folder properties."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    full_folder_path = notebook_path / folder_path

    try:
        resolved_path = full_folder_path.resolve()
        resolved_notebook = notebook_path.resolve()
        if not str(resolved_path).startswith(str(resolved_notebook)):
            raise HTTPException(status_code=403, detail="Access denied: Invalid folder path")
    except (OSError, ValueError) as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid folder path")

    if not full_folder_path.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    if not full_folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a folder")

    try:
        write_folder_properties(full_folder_path, request.properties)

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        metadata_file = full_folder_path / FOLDER_METADATA_FILE
        git_manager.commit(f"Update folder properties: {folder_path}", [str(metadata_file)])

        folder_stats = full_folder_path.stat()
        folder_name = os.path.basename(folder_path) if folder_path else ""

        nb_session = get_notebook_session(str(notebook_path))
        try:
            files, file_count = get_folder_files(
                folder_path, nb.id, notebook_path, nb_session, skip=0, limit=DEFAULT_FOLDER_PAGINATION_LIMIT
            )
        finally:
            nb_session.close()

        return {
            "path": folder_path,
            "name": folder_name,
            "notebook_id": nb.id,
            "title": request.properties.get("title"),
            "description": request.properties.get("description"),
            "properties": request.properties,
            "file_count": file_count,
            "created_at": datetime.fromtimestamp(folder_stats.st_ctime, tz=UTC).isoformat(),
            "updated_at": datetime.fromtimestamp(folder_stats.st_mtime, tz=UTC).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating folder properties: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating folder properties: {str(e)}")


@router.delete("/{workspace}/{notebook}/folders/{folder_path:path}")
async def delete_folder(
    workspace: str,
    notebook: str,
    folder_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a folder and all its contents."""
    _, nb, notebook_path = await get_notebook_path_from_slugs(workspace, notebook, current_user, session)

    full_folder_path = notebook_path / folder_path

    try:
        resolved_path = full_folder_path.resolve()
        resolved_notebook = notebook_path.resolve()
        if not str(resolved_path).startswith(str(resolved_notebook)):
            raise HTTPException(status_code=403, detail="Access denied: Invalid folder path")
    except (OSError, ValueError) as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid folder path")

    if not full_folder_path.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    if not full_folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a folder")

    if not folder_path:
        raise HTTPException(status_code=400, detail="Cannot delete root folder")

    nb_session = get_notebook_session(str(notebook_path))
    try:
        prefix = f"{folder_path}/"
        files_result = nb_session.execute(select(FileMetadata).where(FileMetadata.notebook_id == nb.id))
        all_files = files_result.scalars().all()

        for f in all_files:
            if f.path.startswith(prefix) or f.path == folder_path:
                nb_session.delete(f)

        import shutil

        shutil.rmtree(full_folder_path)

        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        git_manager.commit(f"Delete folder: {folder_path}", [])

        nb_session.commit()

        return {"message": "Folder deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting folder: {str(e)}")
    finally:
        nb_session.close()


# =============================================================================
# Plugin routes
# =============================================================================


@router.get("/{workspace}/{notebook}/plugins")
async def list_notebook_plugins(
    workspace: str,
    notebook: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List plugin configurations for a notebook."""
    _, nb = await get_notebook_by_slugs(workspace, notebook, current_user, session)

    stmt = select(NotebookPluginConfig).where(NotebookPluginConfig.notebook_id == nb.id)
    result = await session.execute(stmt)
    configs = result.scalars().all()

    return [
        {
            "plugin_id": config.plugin_id,
            "enabled": config.enabled,
            "config": config.config,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
        for config in configs
    ]


@router.get("/{workspace}/{notebook}/plugins/{plugin_id}")
async def get_notebook_plugin_config(
    workspace: str,
    notebook: str,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get plugin configuration for a notebook."""
    _, nb = await get_notebook_by_slugs(workspace, notebook, current_user, session)

    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == nb.id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        return {
            "plugin_id": plugin_id,
            "enabled": True,
            "config": {},
        }

    return {
        "plugin_id": config.plugin_id,
        "enabled": config.enabled,
        "config": config.config,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


@router.put("/{workspace}/{notebook}/plugins/{plugin_id}")
async def update_notebook_plugin_config(
    workspace: str,
    notebook: str,
    plugin_id: str,
    request_data: NotebookPluginConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update plugin configuration for a notebook."""
    _, nb = await get_notebook_by_slugs(workspace, notebook, current_user, session)

    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == nb.id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        if request_data.enabled is not None:
            config.enabled = request_data.enabled
        if request_data.config is not None:
            config.config = request_data.config
        session.add(config)
        await session.commit()
        await session.refresh(config)
    else:
        config = NotebookPluginConfig(
            notebook_id=nb.id,
            plugin_id=plugin_id,
            enabled=request_data.enabled if request_data.enabled is not None else True,
            config=request_data.config if request_data.config is not None else {},
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)

    return {
        "plugin_id": config.plugin_id,
        "enabled": config.enabled,
        "config": config.config,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


@router.delete("/{workspace}/{notebook}/plugins/{plugin_id}")
async def delete_notebook_plugin_config(
    workspace: str,
    notebook: str,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete plugin configuration for a notebook (revert to workspace defaults)."""
    _, nb = await get_notebook_by_slugs(workspace, notebook, current_user, session)

    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == nb.id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        await session.delete(config)
        await session.commit()

    return {"message": "Plugin configuration deleted successfully"}

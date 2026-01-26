"""Folder routes for folder metadata and properties."""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
import logging
from codex.core.metadata import MetadataParser
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import FileMetadata, Notebook, User, Workspace

router = APIRouter()
logger = logging.getLogger(__name__)

# The metadata file name stored in each folder
FOLDER_METADATA_FILE = ".metadata"


async def get_notebook_path(
    notebook_id: int, workspace_id: int, current_user: User, session: AsyncSession
) -> tuple[Path, Notebook]:
    """Helper to get and verify notebook path."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get notebook from system database
    result = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.workspace_id == workspace_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Get notebook path
    workspace_path = Path(workspace.path)
    notebook_path = workspace_path / notebook.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found")

    return notebook_path, notebook


class UpdateFolderPropertiesRequest(BaseModel):
    """Request model for updating folder properties."""

    properties: dict[str, Any]


def read_folder_properties(folder_path: Path) -> dict[str, Any] | None:
    """Read folder properties from .file in the folder."""
    metadata_file = folder_path / FOLDER_METADATA_FILE
    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file) as f:
            content = f.read()

        # Parse YAML frontmatter
        properties, _ = MetadataParser.parse_frontmatter(content)
        return properties
    except Exception as e:
        logger.warning(f"Failed to read folder properties from {metadata_file}: {e}")
        return None


def write_folder_properties(folder_path: Path, properties: dict[str, Any]) -> None:
    """Write folder properties to .file in the folder."""
    metadata_file = folder_path / FOLDER_METADATA_FILE

    # Write as YAML frontmatter
    content = MetadataParser.write_frontmatter("", properties)

    with open(metadata_file, "w") as f:
        f.write(content)


def get_folder_files(folder_path: str, notebook_id: int, notebook_path: Path, nb_session) -> list[dict]:
    """Get files in a specific folder (not recursive)."""
    # Query files that are directly in this folder
    prefix = f"{folder_path}/" if folder_path else ""

    files_result = nb_session.execute(select(FileMetadata).where(FileMetadata.notebook_id == notebook_id))
    all_files = files_result.scalars().all()

    folder_files = []
    for f in all_files:
        # Skip .file metadata files
        if f.filename == FOLDER_METADATA_FILE:
            continue

        # Check if file is directly in this folder (not in a subfolder)
        if folder_path:
            if not f.path.startswith(prefix):
                continue
            # Get the relative path after the folder prefix
            relative = f.path[len(prefix) :]
            # If there's a / in the relative path, it's in a subfolder
            if "/" in relative:
                continue
        else:
            # Root level files have no / in their path
            if "/" in f.path:
                continue

        # Parse properties JSON if available
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
                "file_type": f.file_type,
                "size": f.size,
                "title": f.title,
                "description": f.description,
                "properties": properties,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None,
            }
        )

    return folder_files


@router.get("/{folder_path:path}")
async def get_folder(
    folder_path: str,
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get folder metadata and its files.

    The folder properties are stored in a .file within the folder.
    """
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Validate folder path
    full_folder_path = notebook_path / folder_path

    # Security check: ensure path is within notebook
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

    # Read folder properties from .file
    properties = read_folder_properties(full_folder_path)

    # Get folder stats
    folder_stats = full_folder_path.stat()

    # Count files in folder (excluding .file)
    nb_session = get_notebook_session(str(notebook_path))
    try:
        files = get_folder_files(folder_path, notebook_id, notebook_path, nb_session)
        file_count = len(files)

        # Build response
        folder_name = os.path.basename(folder_path) if folder_path else ""

        result = {
            "path": folder_path,
            "name": folder_name,
            "notebook_id": notebook_id,
            "title": properties.get("title") if properties else None,
            "description": properties.get("description") if properties else None,
            "properties": properties,
            "file_count": file_count,
            "files": files,
            "created_at": datetime.fromtimestamp(folder_stats.st_ctime, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(folder_stats.st_mtime, tz=timezone.utc).isoformat(),
        }

        return result
    finally:
        nb_session.close()


@router.put("/{folder_path:path}")
async def update_folder_properties(
    folder_path: str,
    notebook_id: int,
    workspace_id: int,
    request: UpdateFolderPropertiesRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update folder properties.

    This updates the .file within the folder.
    """
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Validate folder path
    full_folder_path = notebook_path / folder_path

    # Security check
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
        # Write properties to .file
        write_folder_properties(full_folder_path, request.properties)

        # Commit to git
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        metadata_file = full_folder_path / FOLDER_METADATA_FILE
        git_manager.commit(f"Update folder properties: {folder_path}", [str(metadata_file)])

        # Get folder stats
        folder_stats = full_folder_path.stat()
        folder_name = os.path.basename(folder_path) if folder_path else ""

        # Count files
        nb_session = get_notebook_session(str(notebook_path))
        try:
            files = get_folder_files(folder_path, notebook_id, notebook_path, nb_session)
            file_count = len(files)
        finally:
            nb_session.close()

        result = {
            "path": folder_path,
            "name": folder_name,
            "notebook_id": notebook_id,
            "title": request.properties.get("title"),
            "description": request.properties.get("description"),
            "properties": request.properties,
            "file_count": file_count,
            "created_at": datetime.fromtimestamp(folder_stats.st_ctime, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(folder_stats.st_mtime, tz=timezone.utc).isoformat(),
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating folder properties: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating folder properties: {str(e)}")


@router.delete("/{folder_path:path}")
async def delete_folder(
    folder_path: str,
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a folder and all its contents."""
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Validate folder path
    full_folder_path = notebook_path / folder_path

    # Security check
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

    # Don't allow deleting the root folder
    if not folder_path:
        raise HTTPException(status_code=400, detail="Cannot delete root folder")

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Delete all files in folder from database
        prefix = f"{folder_path}/"
        files_result = nb_session.execute(select(FileMetadata).where(FileMetadata.notebook_id == notebook_id))
        all_files = files_result.scalars().all()

        for f in all_files:
            if f.path.startswith(prefix) or f.path == folder_path:
                nb_session.delete(f)

        # Delete the folder from disk
        shutil.rmtree(full_folder_path)

        # Commit to git
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

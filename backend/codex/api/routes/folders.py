"""Folder routes for folder metadata and properties."""

import json
import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.notebooks import get_notebook_by_slug_or_id
from codex.api.routes.workspaces import get_workspace_by_slug_or_id
from codex.core.metadata import MetadataParser
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import FileMetadata, Notebook, User, Workspace

logger = logging.getLogger(__name__)

# The metadata file name stored in each folder
FOLDER_METADATA_FILE = ".metadata"

# Default pagination limit for folder contents
DEFAULT_FOLDER_PAGINATION_LIMIT = 100


async def get_notebook_path(
    notebook_id: int, workspace_id: int, current_user: User, session: AsyncSession
) -> tuple[Path, Notebook]:
    """Helper to get and verify notebook path (deprecated - use get_notebook_path_nested)."""
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


async def get_notebook_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User,
    session: AsyncSession,
) -> tuple[Path, Notebook, Workspace]:
    """Helper to get and verify notebook path using workspace and notebook identifiers.

    Returns:
        Tuple of (notebook_path, notebook_model, workspace_model)

    Raises:
        HTTPException if workspace or notebook not found
    """
    # Get workspace by slug or ID
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)

    # Get notebook by slug or ID
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    # Get notebook path
    workspace_path = Path(workspace.path)
    notebook_path = workspace_path / notebook.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found")

    return notebook_path, notebook, workspace


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


def get_folder_files(
    folder_path: str,
    notebook_id: int,
    notebook_path: Path,
    nb_session,
    skip: int = 0,
    limit: int = DEFAULT_FOLDER_PAGINATION_LIMIT,
) -> tuple[list[dict], int]:
    """Get files in a specific folder (not recursive) with pagination.

    Note: This implementation filters in Python rather than SQL because we need to:
    1. Check if files are directly in the folder (not in subfolders)
    2. Exclude .metadata files

    For optimal performance with very large folders (>10k files), consider:
    - Adding a parent_folder column to FileMetadata for direct SQL filtering
    - Using an indexed path column for faster queries

    Current implementation provides accurate counts up to a reasonable folder size,
    then estimates for very large folders to avoid processing all files.

    Returns:
        Tuple of (files_list, total_count)
    """
    # Query files that are directly in this folder
    prefix = f"{folder_path}/" if folder_path else ""

    # Optimization: Add LIKE filter to reduce initial result set
    if folder_path:
        # Files in this specific folder start with the prefix
        files_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook_id, FileMetadata.path.startswith(prefix))
        )
    else:
        # Root level: files without any path separator
        files_result = nb_session.execute(select(FileMetadata).where(FileMetadata.notebook_id == notebook_id))

    all_files = files_result.scalars().all()

    folder_files = []
    total_count = 0
    # Stop counting after processing a reasonable number for performance
    # This provides accurate counts for normal folders while avoiding
    # processing tens of thousands of files just for counting
    MAX_COUNT_THRESHOLD = 10000

    for f in all_files:
        # Skip .metadata files
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

        total_count += 1

        # Apply pagination - skip early items
        if total_count <= skip:
            continue

        # Stop processing once we have enough items and counted enough
        if len(folder_files) >= limit and total_count > skip + limit + 100:
            # We have our page and a reasonable count estimate
            break

        # Stop counting beyond threshold (still collect items up to limit)
        if total_count > MAX_COUNT_THRESHOLD and len(folder_files) >= limit:
            # For very large folders, provide an estimated count
            total_count = MAX_COUNT_THRESHOLD  # Indicate "more than 10k"
            break

        # Collect the file if we haven't reached the limit yet
        if len(folder_files) < limit:
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
        # Skip hidden folders (including .codex)
        if item.name.startswith("."):
            continue
        if item.is_dir():
            subfolder_path = f"{folder_path}/{item.name}" if folder_path else item.name
            # Read subfolder properties if available
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

    # Sort by name
    subfolders.sort(key=lambda x: x["name"].lower())
    return subfolders


# New nested router for workspace/notebook-based folder routes
nested_router = APIRouter()


@nested_router.get("/{folder_path:path}")
async def get_folder(
    workspace_identifier: str,
    notebook_identifier: str,
    folder_path: str,
    skip: int = 0,
    limit: int = DEFAULT_FOLDER_PAGINATION_LIMIT,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get folder metadata and its files with pagination.

    The folder properties are stored in a .file within the folder.

    Args:
        workspace_identifier: Workspace slug or ID
        notebook_identifier: Notebook slug or ID
        folder_path: Path to the folder
        skip: Number of files to skip (for pagination)
        limit: Maximum number of files to return (for pagination)
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

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
        files, total_file_count = get_folder_files(folder_path, notebook.id, notebook_path, nb_session, skip, limit)

        # Get subfolders
        subfolders = get_subfolders(folder_path, notebook_path)

        # Build response
        folder_name = os.path.basename(folder_path) if folder_path else ""

        result = {
            "path": folder_path,
            "name": folder_name,
            "notebook_id": notebook.id,
            "notebook_slug": notebook.slug,
            "workspace_id": workspace.id,
            "workspace_slug": workspace.slug,
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

        return result
    finally:
        nb_session.close()


@nested_router.put("/{folder_path:path}")
async def update_folder_properties(
    workspace_identifier: str,
    notebook_identifier: str,
    folder_path: str,
    request: UpdateFolderPropertiesRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update folder properties.

    This updates the .file within the folder.
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

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
            files, file_count = get_folder_files(
                folder_path, notebook.id, notebook_path, nb_session, skip=0, limit=DEFAULT_FOLDER_PAGINATION_LIMIT
            )
        finally:
            nb_session.close()

        result = {
            "path": folder_path,
            "name": folder_name,
            "notebook_id": notebook.id,
            "notebook_slug": notebook.slug,
            "workspace_id": workspace.id,
            "workspace_slug": workspace.slug,
            "title": request.properties.get("title"),
            "description": request.properties.get("description"),
            "properties": request.properties,
            "file_count": file_count,
            "created_at": datetime.fromtimestamp(folder_stats.st_ctime, tz=UTC).isoformat(),
            "updated_at": datetime.fromtimestamp(folder_stats.st_mtime, tz=UTC).isoformat(),
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating folder properties: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating folder properties: {str(e)}")


@nested_router.delete("/{folder_path:path}")
async def delete_folder(
    workspace_identifier: str,
    notebook_identifier: str,
    folder_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a folder and all its contents."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

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
        files_result = nb_session.execute(select(FileMetadata).where(FileMetadata.notebook_id == notebook.id))
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

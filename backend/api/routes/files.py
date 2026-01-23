"""File routes."""

import json
import mimetypes
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.api.auth import get_current_active_user
import logging
from backend.core.metadata import MetadataParser
from backend.db.database import get_notebook_session, get_system_session
from backend.db.models import FileMetadata, Notebook, User, Workspace

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_notebook_path(
    notebook_id: int, workspace_id: int, current_user: User, session: AsyncSession
) -> tuple[Path, Notebook]:
    """Helper to get and verify notebook path.
    
    Returns:
        Tuple of (notebook_path, notebook_model)
    
    Raises:
        HTTPException if workspace or notebook not found
    """
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


class CreateFileRequest(BaseModel):
    """Request model for creating a file."""

    notebook_id: int
    workspace_id: int
    path: str
    content: str


class UpdateFileRequest(BaseModel):
    """Request model for updating a file."""

    content: str
    properties: dict[str, Any] | None = None  # Unified properties from frontmatter


@router.get("/")
async def list_files(
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all files in a notebook."""
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query files from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        files_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook_id)
        )
        files = files_result.scalars().all()

        file_list = []
        for f in files:
            # Parse properties JSON if available
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
                    "file_type": f.file_type,
                    "size": f.size,
                    "hash": f.hash,
                    "title": f.title,
                    "description": f.description,
                    "properties": properties,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "updated_at": f.updated_at.isoformat() if f.updated_at else None,
                    "file_modified_at": f.file_modified_at.isoformat() if f.file_modified_at else None,
                }
            )

        return file_list
    finally:
        nb_session.close()


@router.get("/{file_id}")
async def get_file(
    file_id: int,
    workspace_id: int,
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a specific file."""
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Read file content if it's a text file
        # Note: Binary files like images are excluded - use /content endpoint to download them
        file_path = notebook_path / file_meta.path
        content = None
        raw_content = None
        if file_path.exists() and file_meta.file_type in ["text", "markdown", "view", "json", "xml"]:
            try:
                with open(file_path) as f:
                    raw_content = f.read()
            except Exception as e:
                logger.error(f"Error reading file content: {e}", exc_info=True)

        # Parse frontmatter from file content if it's a markdown or view file
        properties = None
        if raw_content and file_meta.file_type in ["markdown", "view"]:
            properties, content = MetadataParser.parse_frontmatter(raw_content)
            # Sync properties to DB cache if they changed
            properties_json = json.dumps(properties) if properties else None
            if file_meta.properties != properties_json:
                file_meta.properties = properties_json
                # Extract title/description for indexed search
                if properties:
                    if "title" in properties:
                        file_meta.title = properties["title"]
                    if "description" in properties:
                        file_meta.description = properties["description"]
                nb_session.commit()
        else:
            content = raw_content
            # Try to load cached properties from DB
            if file_meta.properties:
                try:
                    properties = json.loads(file_meta.properties)
                except json.JSONDecodeError:
                    properties = None

        result = {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "file_type": file_meta.file_type,
            "size": file_meta.size,
            "hash": file_meta.hash,
            "title": file_meta.title,
            "description": file_meta.description,
            "properties": properties,
            "content": content,
            "created_at": file_meta.created_at.isoformat() if file_meta.created_at else None,
            "updated_at": file_meta.updated_at.isoformat() if file_meta.updated_at else None,
            "file_modified_at": (
                file_meta.file_modified_at.isoformat() if file_meta.file_modified_at else None
            ),
        }

        return result
    finally:
        nb_session.close()


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: int,
    workspace_id: int,
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content (serves binary files like images)."""
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Get file path
        file_path = notebook_path / file_meta.path
        
        # Validate path to prevent directory traversal attacks
        try:
            resolved_path = file_path.resolve()
            resolved_notebook = notebook_path.resolve()
            # Ensure the file is within the notebook directory
            if not str(resolved_path).startswith(str(resolved_notebook)):
                raise HTTPException(status_code=403, detail="Access denied: Invalid file path")
        except (OSError, ValueError) as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Determine media type based on file extension
        media_type, _ = mimetypes.guess_type(str(file_path))
        if media_type is None:
            media_type = "application/octet-stream"
        
        # Return the file
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_meta.filename
        )
    finally:
        nb_session.close()


@router.post("/")
async def create_file(
    request: CreateFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new file."""
    notebook_id = request.notebook_id
    workspace_id = request.workspace_id
    path = request.path
    content = request.content

    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Create the file
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_path = notebook_path / path

        # Check if file already exists
        if file_path.exists():
            raise HTTPException(status_code=400, detail="File already exists")

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine file type before creating file
        file_type = "text"
        if path.endswith(".md"):
            file_type = "markdown"
        elif path.endswith(".cdx"):
            file_type = "view"
        elif path.endswith(".json"):
            file_type = "json"
        elif path.endswith(".xml"):
            file_type = "xml"
        elif path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg")):
            file_type = "image"

        import hashlib
        from datetime import datetime

        # Create metadata record BEFORE writing file to prevent race with watcher
        # Use placeholder values that will be updated after file is written
        file_meta = FileMetadata(
            notebook_id=notebook_id,
            path=path,
            filename=os.path.basename(path),
            file_type=file_type,
            size=0,  # Placeholder, will be updated
            hash=hashlib.sha256(content.encode()).hexdigest(),
        )

        # Add and commit the metadata record first
        nb_session.add(file_meta)
        try:
            nb_session.commit()
            nb_session.refresh(file_meta)
        except Exception as commit_error:
            # Handle race condition: watcher may have created the record
            nb_session.rollback()
            if "UNIQUE constraint failed" in str(commit_error):
                # Query for the existing record created by the watcher
                existing_result = nb_session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == notebook_id,
                        FileMetadata.path == path
                    )
                )
                file_meta = existing_result.scalar_one_or_none()
                if not file_meta:
                    raise HTTPException(status_code=500, detail="Race condition: file metadata not found")
            else:
                raise

        # Now write the file to disk (watcher will update the existing record if needed)
        with open(file_path, "w") as f:
            f.write(content)

        # Refresh to get any updates the watcher may have made
        nb_session.refresh(file_meta)

        # Update metadata with actual file stats (watcher may have already set these)
        file_stats = os.stat(file_path)
        file_meta.size = file_stats.st_size
        file_meta.file_created_at = datetime.fromtimestamp(file_stats.st_ctime)
        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)

        # Commit file to git
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        commit_hash = git_manager.commit(f"Create {os.path.basename(path)}", [str(file_path)])
        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        # Commit the updates
        nb_session.commit()
        nb_session.refresh(file_meta)

        result = {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "file_type": file_meta.file_type,
            "size": file_meta.size,
            "message": "File created successfully",
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating file in notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating file: {str(e)}")
    finally:
        nb_session.close()


@router.put("/{file_id}")
async def update_file(
    file_id: int,
    workspace_id: int,
    notebook_id: int,
    request: UpdateFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update a file."""
    content = request.content

    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Update the file
        file_path = notebook_path / file_meta.path

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Prepare content with frontmatter if properties provided
        final_content = content
        properties = request.properties
        if properties and file_meta.file_type in ["markdown", "view"]:
            # Write frontmatter to file
            final_content = MetadataParser.write_frontmatter(content, properties)

        # Write new content
        with open(file_path, "w") as f:
            f.write(final_content)

        # Update metadata
        import hashlib
        from datetime import datetime, timezone

        file_hash = hashlib.sha256(final_content.encode()).hexdigest()
        file_stats = os.stat(file_path)

        file_meta.size = file_stats.st_size
        file_meta.hash = file_hash
        file_meta.updated_at = datetime.now(timezone.utc)
        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)

        # Update properties cache and indexed fields
        if properties is not None:
            file_meta.properties = json.dumps(properties)
            # Extract title/description for indexed search
            if "title" in properties:
                file_meta.title = properties["title"]
            if "description" in properties:
                file_meta.description = properties["description"]

        # Commit file changes to git
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        commit_hash = git_manager.commit(f"Update {file_meta.filename}", [str(file_path)])
        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        nb_session.commit()
        nb_session.refresh(file_meta)

        # Return updated properties
        result_properties = None
        if file_meta.properties:
            try:
                result_properties = json.loads(file_meta.properties)
            except json.JSONDecodeError:
                result_properties = None

        result = {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "file_type": file_meta.file_type,
            "size": file_meta.size,
            "hash": file_meta.hash,
            "title": file_meta.title,
            "description": file_meta.description,
            "properties": result_properties,
            "updated_at": file_meta.updated_at.isoformat() if file_meta.updated_at else None,
            "message": "File updated successfully",
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file in notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating file: {str(e)}")
    finally:
        nb_session.close()

"""File routes."""

import hashlib
import json
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.helpers import get_notebook_path_nested
from codex.core.git_manager import GitManager
from codex.core.link_resolver import LinkResolver
from codex.core.metadata import MetadataParser
from codex.core.watcher import get_content_type
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import FileMetadata, User
from codex.core.watcher import get_watcher_for_notebook

logger = logging.getLogger(__name__)


def generate_unique_path(file_path: Path) -> Path:
    """Generate a unique file path by appending a numeric suffix if the file already exists.

    If ``file_path`` does not exist on disk, it is returned unchanged.
    Otherwise the function appends ``-1``, ``-2``, … before the file extension
    (or at the end for files without an extension) until a non-existing path is found.

    Examples:
        notes.md  → notes-1.md  → notes-2.md
        image.png → image-1.png → image-2.png
        README    → README-1    → README-2
    """
    if not file_path.exists():
        return file_path

    stem = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent

    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


class ResolveLinkRequest(BaseModel):
    """Request model for resolving a link."""

    link: str
    current_file_path: str | None = None


class MoveFileRequest(BaseModel):
    """Request model for moving/renaming a file."""

    new_path: str


# Nested router for workspace/notebook-based file routes
# Routes follow the pattern: /workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/...
nested_router = APIRouter()


class CreateFileRequestNested(BaseModel):
    """Request model for creating a file (nested routes)."""

    path: str
    content: str


class UpdateFileRequestNested(BaseModel):
    """Request model for updating a file (nested routes)."""

    content: str | None = None
    properties: dict[str, Any] | None = None


@nested_router.get("/")
async def list_files_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List files in a notebook with pagination (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Query files from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Get total count efficiently
        from sqlmodel import func

        count_statement = select(func.count(FileMetadata.id)).where(FileMetadata.notebook_id == notebook.id)
        count_result = nb_session.execute(count_statement)
        total_count = count_result.scalar_one()

        # Get paginated files
        statement = select(FileMetadata).where(FileMetadata.notebook_id == notebook.id).offset(skip).limit(limit)
        files_result = nb_session.execute(statement)
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

            entry = {
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
            if f.s3_key:
                entry["s3_key"] = f.s3_key
                entry["s3_version_id"] = f.s3_version_id
            file_list.append(entry)

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


@nested_router.post("/")
async def create_file_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    request: CreateFileRequestNested,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new file (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    path = request.path
    content = request.content

    file_path = notebook_path / path

    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate a unique path if file already exists
    file_path = generate_unique_path(file_path)
    path = str(file_path.relative_to(notebook_path))

    # Write the file to disk first
    with open(file_path, "w") as f:
        f.write(content)

    # Check if we have an active watcher for this notebook
    watcher = get_watcher_for_notebook(str(notebook_path))

    if watcher:
        # Use the queue system - enqueue and wait for processing
        from codex.core.metadata import MetadataParser

        filepath, sidecar = MetadataParser.resolve_sidecar(str(file_path))
        op = watcher.enqueue_operation(
            filepath=filepath,
            sidecar_path=sidecar,
            operation="created",
            comment=f"Create {os.path.basename(path)}",
            wait=True,
        )

        if op.error:
            logger.error(f"Error processing file creation: {op.error}")
            raise HTTPException(status_code=500, detail=f"Error creating file: {str(op.error)}")

    # Query the file metadata (either created by watcher or we create it now)
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Query the file metadata
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == path)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            # No watcher or watcher didn't create the record - create it manually
            content_type = get_content_type(str(file_path))
            file_stats = os.stat(file_path)

            file_meta = FileMetadata(
                notebook_id=notebook.id,
                path=path,
                filename=os.path.basename(path),
                content_type=content_type,
                size=file_stats.st_size,
                hash=hashlib.sha256(content.encode()).hexdigest(),
                file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
            )
            nb_session.add(file_meta)

            # Commit file to git if no watcher
            if not watcher:
                git_manager = GitManager(str(notebook_path))
                commit_hash = git_manager.commit(f"Create {os.path.basename(path)}", [str(file_path)])
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


@nested_router.get("/path/{filepath:path}/text")
async def get_file_text_by_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    filepath: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file text content by path (nested under workspace/notebook route).

    For markdown files, strips frontmatter and returns only the content body.
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    file_path = notebook_path / filepath

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Strip frontmatter from markdown files
        if filepath.endswith(".md"):
            _, content = MetadataParser.parse_frontmatter(content)

        return {"content": content}
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@nested_router.get("/path/{filepath:path}/content")
async def get_file_content_by_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    filepath: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content by path (serves binary files like images).

    Nested under workspace/notebook route.
    Supports:
    - Exact path match: "path/to/image.png"
    - Filename only: "image.png" (searches for filename in notebook)
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # First try exact path match
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == filepath)
        )
        file_meta = file_result.scalar_one_or_none()

        # If not found and filepath doesn't contain directory separator, try filename match
        if not file_meta and "/" not in filepath:
            file_result = nb_session.execute(
                select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.filename == filepath)
            )
            # Get first match if multiple files have same name
            file_meta = file_result.scalars().first()

        if not file_meta:
            raise HTTPException(status_code=404, detail=f"File not found: {filepath}")

        # Get file path
        file_path = notebook_path / file_meta.path

        # Validate path to prevent directory traversal attacks
        try:
            resolved_path = file_path.resolve()
            resolved_notebook = notebook_path.resolve()
            # Ensure the file is within the notebook directory
            if not resolved_path.is_relative_to(resolved_notebook):
                raise HTTPException(status_code=403, detail="Access denied: Invalid file path")
        except (OSError, ValueError) as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Serve from S3 if the file is stored there
        if file_meta.s3_key and file_meta.s3_bucket:
            from codex.core.s3_storage import generate_presigned_url, is_s3_configured
            from fastapi.responses import RedirectResponse

            if is_s3_configured():
                url = generate_presigned_url(file_meta.s3_key, file_meta.s3_version_id, file_meta.s3_bucket)
                return RedirectResponse(url=url)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Determine media type based on file extension
        media_type, _ = mimetypes.guess_type(str(file_path))
        if media_type is None:
            media_type = "application/octet-stream"

        # Return the file
        return FileResponse(path=str(file_path), media_type=media_type, filename=file_meta.filename)
    finally:
        nb_session.close()


@nested_router.get("/path/{filepath:path}")
async def get_file_by_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    filepath: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file metadata by path (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == filepath)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Parse properties JSON if available
        properties = None
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
        if file_meta.s3_key:
            result["s3_key"] = file_meta.s3_key
            result["s3_version_id"] = file_meta.s3_version_id
        return result
    finally:
        nb_session.close()


@nested_router.get("/{file_id}")
async def get_file_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file metadata by ID (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Parse properties JSON if available
        properties = None
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
        if file_meta.s3_key:
            result["s3_key"] = file_meta.s3_key
            result["s3_version_id"] = file_meta.s3_version_id
        return result
    finally:
        nb_session.close()


@nested_router.get("/{file_id}/content")
async def get_file_content_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content (serves binary files like images).

    Nested under workspace/notebook route.
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
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
            if not resolved_path.is_relative_to(resolved_notebook):
                raise HTTPException(status_code=403, detail="Access denied: Invalid file path")
        except (OSError, ValueError) as e:
            logger.error(f"Path validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Serve from S3 if the file is stored there
        if file_meta.s3_key and file_meta.s3_bucket:
            from codex.core.s3_storage import generate_presigned_url, is_s3_configured
            from fastapi.responses import RedirectResponse

            if is_s3_configured():
                url = generate_presigned_url(file_meta.s3_key, file_meta.s3_version_id, file_meta.s3_bucket)
                return RedirectResponse(url=url)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Determine media type based on file extension
        media_type, _ = mimetypes.guess_type(str(file_path))
        if media_type is None:
            media_type = "application/octet-stream"

        # Return the file
        return FileResponse(path=str(file_path), media_type=media_type, filename=file_meta.filename)
    finally:
        nb_session.close()


@nested_router.get("/{file_id}/text")
async def get_file_text_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file text content by ID (nested under workspace/notebook route).

    For markdown files, strips frontmatter and returns only the content body.
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Get file metadata
    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = notebook_path / file_meta.path

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Strip frontmatter from markdown files
            if file_meta.path.endswith(".md"):
                _, content = MetadataParser.parse_frontmatter(content)

            return {"content": content}
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    finally:
        nb_session.close()


@nested_router.put("/{file_id}")
async def update_file_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    request: UpdateFileRequestNested,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update file content and/or properties (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    content = request.content
    properties = request.properties

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Get file metadata
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = notebook_path / file_meta.path

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Handle properties update
        sidecar_path = None
        if properties is not None:
            if content and file_meta.content_type == "text/markdown":
                # Write frontmatter to file
                content = MetadataParser.write_frontmatter(content, properties)
            else:
                sidecar_path = MetadataParser.write_sidecar(str(file_path), properties)

        # Update content if provided
        if content is not None:
            with open(file_path, "w") as f:
                f.write(content)

        # Notify watcher queue if available
        watcher = get_watcher_for_notebook(str(notebook_path))
        if watcher and (content is not None or properties is not None):
            filepath, resolved_sidecar = MetadataParser.resolve_sidecar(str(file_path))
            watcher.enqueue_operation(
                filepath=filepath,
                sidecar_path=sidecar_path or resolved_sidecar,
                operation="modified",
                comment=f"Update {file_meta.filename}",
                wait=False,  # Don't block - let queue batch it
            )

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
        logger.error(f"Error updating file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating file: {str(e)}")
    finally:
        nb_session.close()


@nested_router.patch("/{file_id}/move")
async def move_file_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    request: MoveFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Move/rename a file (nested under workspace/notebook route)."""
    import shutil
    from codex.core.watcher import calculate_file_hash

    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    new_path = request.new_path

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Get file metadata
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        old_path = notebook_path / file_meta.path
        new_file_path = notebook_path / new_path

        # Check if target already exists
        if new_file_path.exists():
            raise HTTPException(status_code=400, detail="Target path already exists")

        # Create parent directories if needed
        new_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Capture file hash before move (for watcher move detection)
        file_hash = None
        try:
            if old_path.exists():
                file_hash = calculate_file_hash(str(old_path))
        except Exception:
            pass

        # Move the file on disk
        shutil.move(str(old_path), str(new_file_path))

        # Handle sidecar file
        old_sidecar_path = None
        new_sidecar_path = None
        if file_meta.sidecar_path:
            old_sidecar_abs = notebook_path / file_meta.sidecar_path
            if old_sidecar_abs.exists():
                old_sidecar_path = str(old_sidecar_abs)
                new_sidecar_path = new_file_path.parent / Path(file_meta.sidecar_path).name
                shutil.move(old_sidecar_path, str(new_sidecar_path))

        # Check if we have an active watcher
        watcher = get_watcher_for_notebook(str(notebook_path))

        if watcher:
            # Let the queue handle the move detection
            # Enqueue delete (with hash) and create
            watcher.enqueue_operation(
                filepath=str(old_path),
                sidecar_path=old_sidecar_path,
                operation="deleted",
                file_hash=file_hash,
                wait=False,
            )
            dest_filepath, dest_sidecar = MetadataParser.resolve_sidecar(str(new_file_path))
            watcher.enqueue_operation(
                filepath=dest_filepath,
                sidecar_path=str(new_sidecar_path) if new_sidecar_path else dest_sidecar,
                operation="created",
                comment=f"Move {file_meta.filename} to {new_path}",
                wait=True,  # Wait for this one to ensure DB is updated
            )
        else:
            # No watcher - update metadata directly
            file_meta.path = new_path
            file_meta.filename = os.path.basename(new_path)
            if new_sidecar_path:
                file_meta.sidecar_path = os.path.relpath(str(new_sidecar_path), str(notebook_path))
            nb_session.commit()

        # Re-query to get updated metadata
        nb_session.expire_all()
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == new_path)
        )
        updated_meta = result.scalar_one_or_none()

        return {
            "id": updated_meta.id if updated_meta else file_meta.id,
            "path": new_path,
            "filename": os.path.basename(new_path),
            "message": "File moved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error moving file: {str(e)}")
    finally:
        nb_session.close()


@nested_router.delete("/{file_id}")
async def delete_file_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a file (nested under workspace/notebook route)."""
    from sqlalchemy.orm.exc import StaleDataError

    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Get file metadata
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = notebook_path / file_meta.path
        filename = file_meta.filename

        # Delete sidecar file if it exists
        _, sidecar = MetadataParser.resolve_sidecar(str(file_path))
        if sidecar and Path(sidecar).exists():
            os.remove(sidecar)
            logger.debug(f"Deleted sidecar file: {sidecar}")

        # Delete the file from disk
        if file_path.exists():
            os.remove(file_path)

        # Check if we have an active watcher
        watcher = get_watcher_for_notebook(str(notebook_path))

        if watcher:
            # Let the queue handle the deletion
            op = watcher.enqueue_operation(
                filepath=str(file_path),
                sidecar_path=sidecar,
                operation="deleted",
                comment=f"Delete {filename}",
                wait=True,
            )
            if op.error:
                logger.warning(f"Error in watcher delete processing: {op.error}")
        else:
            # No watcher - handle directly
            # Commit deletion to git
            git_manager = GitManager(str(notebook_path))
            git_manager.commit(f"Delete {filename}", [])

            # Delete from database
            nb_session.delete(file_meta)
            try:
                nb_session.commit()
            except StaleDataError:
                nb_session.rollback()

        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
    finally:
        nb_session.close()


@nested_router.get("/{file_id}/versions")
async def get_file_versions_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List S3 versions for a binary file.

    Returns version history from S3 bucket versioning.  Only applicable
    to files stored in S3 (``s3_key`` is set).
    """
    from codex.core.s3_storage import is_s3_configured, list_versions

    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        if not file_meta.s3_key:
            return {"versions": [], "message": "File is not stored in S3"}

        if not is_s3_configured():
            raise HTTPException(status_code=503, detail="S3 storage is not configured")

        versions = list_versions(file_meta.s3_key, file_meta.s3_bucket)
        return {
            "file_id": file_meta.id,
            "path": file_meta.path,
            "s3_key": file_meta.s3_key,
            "current_version_id": file_meta.s3_version_id,
            "versions": versions,
        }
    finally:
        nb_session.close()


@nested_router.post("/resolve-link")
async def resolve_link_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    request: ResolveLinkRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Resolve a link to a file (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Resolve the link
    try:
        resolved_path = LinkResolver.resolve_link(request.link, request.current_file_path, notebook_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Query the resolved file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # First try exact path match
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == resolved_path)
        )
        file_meta = file_result.scalar_one_or_none()

        # If not found and path doesn't contain directory separator, try filename match
        if not file_meta and "/" not in resolved_path:
            file_result = nb_session.execute(
                select(FileMetadata).where(
                    FileMetadata.notebook_id == notebook.id, FileMetadata.filename == resolved_path
                )
            )
            # Get first match if multiple files have same name
            file_meta = file_result.scalars().first()

        if not file_meta:
            raise HTTPException(status_code=404, detail=f"File not found: {resolved_path}")

        # Parse properties if available
        properties = None
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

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving link: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error resolving link: {str(e)}")
    finally:
        nb_session.close()


@nested_router.get("/{file_id}/history")
async def get_file_history_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get git history for a file (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Get file metadata
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = notebook_path / file_meta.path

        # Get git history
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        history = git_manager.get_file_history(str(file_path))

        return {"history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting file history: {str(e)}")
    finally:
        nb_session.close()


@nested_router.get("/{file_id}/history/{commit_hash}")
async def get_file_at_commit_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file_id: int,
    commit_hash: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content at a specific commit (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Get file metadata
        result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.id == file_id, FileMetadata.notebook_id == notebook.id)
        )
        file_meta = result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = notebook_path / file_meta.path

        # Get file content at commit
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        content = git_manager.get_file_at_commit(str(file_path), commit_hash)

        if content is None:
            raise HTTPException(status_code=404, detail="File not found at this commit")

        return {"file_id": file_id, "path": file_meta.path, "commit_hash": commit_hash, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file at commit: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting file at commit: {str(e)}")
    finally:
        nb_session.close()


@nested_router.post("/upload")
async def upload_file_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    file: UploadFile = File(...),
    path: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Upload a file (nested under workspace/notebook route).

    Binary files are automatically offloaded to S3 when ``CODEX_S3_BUCKET``
    is configured.  A lightweight ``.s3ref`` pointer file is committed to
    git so that every version of the binary is tracked.
    """
    from codex.core.s3_storage import (
        build_s3_key,
        is_s3_configured,
        upload_binary,
        write_pointer_file,
    )

    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    # Create the file
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Use provided path or default to filename
        target_path = path if path else file.filename
        if not target_path:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_path = notebook_path / target_path

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate a unique path if file already exists
        file_path = generate_unique_path(file_path)
        target_path = str(file_path.relative_to(notebook_path))

        # Determine content type
        content_type = get_content_type(str(file_path))

        # Read file content
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Detect whether this is a binary file
        is_binary = b"\0" in content[:8192]

        # S3 upload for binary files when configured
        s3_meta = None
        if is_binary and is_s3_configured():
            s3_key = build_s3_key(workspace.slug, notebook.slug, target_path)
            s3_meta = upload_binary(content, s3_key, content_type)

        # Create metadata record
        file_meta = FileMetadata(
            notebook_id=notebook.id,
            path=target_path,
            filename=os.path.basename(target_path),
            content_type=content_type,
            size=len(content),
            hash=file_hash,
        )

        if s3_meta:
            file_meta.s3_bucket = s3_meta["bucket"]
            file_meta.s3_key = s3_meta["key"]
            file_meta.s3_version_id = s3_meta["version_id"]

        # Add and commit the metadata record
        nb_session.add(file_meta)
        try:
            nb_session.commit()
            nb_session.refresh(file_meta)
        except Exception as commit_error:
            nb_session.rollback()
            if "UNIQUE constraint failed" in str(commit_error):
                existing_result = nb_session.execute(
                    select(FileMetadata).where(
                        FileMetadata.notebook_id == notebook.id, FileMetadata.path == target_path
                    )
                )
                file_meta = existing_result.scalar_one_or_none()
                if not file_meta:
                    raise HTTPException(status_code=500, detail="Race condition: file metadata not found")
                # Update existing record with S3 info
                if s3_meta:
                    file_meta.s3_bucket = s3_meta["bucket"]
                    file_meta.s3_key = s3_meta["key"]
                    file_meta.s3_version_id = s3_meta["version_id"]
                    file_meta.hash = file_hash
                    file_meta.size = len(content)
            else:
                raise

        # Write the file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        # Update metadata with actual file stats
        file_stats = os.stat(file_path)
        file_meta.size = file_stats.st_size
        file_meta.file_created_at = datetime.fromtimestamp(file_stats.st_ctime)
        file_meta.file_modified_at = datetime.fromtimestamp(file_stats.st_mtime)

        # Commit to git
        git_manager = GitManager(str(notebook_path))

        if s3_meta:
            # Write an S3 pointer file and commit it (instead of the binary)
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
            commit_hash = git_manager.commit(f"Upload {os.path.basename(target_path)}", [str(file_path)])

        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        nb_session.commit()
        nb_session.refresh(file_meta)

        result = {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "content_type": file_meta.content_type,
            "size": file_meta.size,
            "message": "File uploaded successfully",
        }

        if s3_meta:
            result["s3_version_id"] = s3_meta["version_id"]
            result["s3_key"] = s3_meta["key"]

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        nb_session.close()

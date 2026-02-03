"""File routes."""

import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.notebooks import get_notebook_by_slug_or_id
from codex.api.routes.workspaces import get_workspace_by_slug_or_id
from codex.core.link_resolver import LinkResolver
from codex.core.metadata import MetadataParser
from codex.core.watcher import get_content_type
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import FileMetadata, Notebook, User, Workspace

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
    workspace_path = Path(workspace.path).resolve()  # Convert to absolute path
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


class ResolveLinkRequest(BaseModel):
    """Request model for resolving a link."""

    link: str
    current_file_path: str | None = None


class CreateFromTemplateRequest(BaseModel):
    """Request model for creating a file from a template."""

    notebook_id: int
    workspace_id: int
    template_id: str
    filename: str | None = None  # Optional custom filename, otherwise use template default


def load_default_templates(loader) -> list[dict]:
    """Load default templates from YAML files in the templates directory and from plugins.

    This loads templates from any plugin that provides them, not just view plugins.
    This allows themes, integrations, or any other plugin type to provide templates.
    """
    import yaml

    templates = []

    # Load templates from any plugin that provides them, using capability-based filtering
    try:
        # Get all plugins that have templates (regardless of type)
        plugins_with_templates = loader.get_plugins_with_templates()

        for plugin in plugins_with_templates:
            # Add templates from this plugin
            for template_def in plugin.templates:
                template_file_path = plugin.plugin_dir / template_def.get("file", "")
                if template_file_path.exists():
                    try:
                        with open(template_file_path) as f:
                            template_data = yaml.safe_load(f)
                            if template_data and isinstance(template_data, dict):
                                # Add plugin source information
                                template_data["plugin_id"] = plugin.id
                                templates.append(template_data)
                    except Exception as e:
                        logger.warning(f"Failed to load plugin template {template_file_path}: {e}")
    except Exception as e:
        logger.warning(f"Failed to load plugin templates: {e}")

    return templates


def get_default_templates(loader) -> list[dict]:
    """Get default templates using the plugin loader."""
    return load_default_templates(loader)


def expand_template_pattern(pattern: str, title: str = "untitled") -> str:
    """Expand date patterns and title in a template string.

    Supported patterns:
    - {yyyy}: 4-digit year
    - {yy}: 2-digit year
    - {mm}: 2-digit month
    - {dd}: 2-digit day
    - {month}: Full month name
    - {mon}: Abbreviated month name
    - {title}: The provided title
    """
    from datetime import datetime

    now = datetime.now()

    replacements = {
        "{yyyy}": now.strftime("%Y"),
        "{yy}": now.strftime("%y"),
        "{mm}": now.strftime("%m"),
        "{dd}": now.strftime("%d"),
        "{month}": now.strftime("%B"),
        "{mon}": now.strftime("%b"),
        "{title}": title,
    }

    result = pattern
    for key, value in replacements.items():
        result = result.replace(key, value)

    result = now.strftime(result)

    return result


def add_template_source(templates: list[dict]) -> list[dict]:
    """Add source field to templates based on whether they're from plugins.

    Args:
        templates: List of template dictionaries

    Returns:
        List of templates with source field added
    """
    result = []
    for t in templates:
        template_copy = {**t}
        if "plugin_id" in t:
            template_copy["source"] = "plugin"
        else:
            template_copy["source"] = "default"
        result.append(template_copy)
    return result


@router.post("/from-template")
async def create_from_template(
    req: Request,
    request: CreateFromTemplateRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new file from a template.

    Expands date patterns in filename and content.
    """
    notebook_id = request.notebook_id
    workspace_id = request.workspace_id
    template_id = request.template_id
    custom_filename = request.filename

    # Get notebook path
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Find the template
    template = None

    # First check .templates folder
    templates_dir = notebook_path / ".templates"
    if templates_dir.exists():
        for template_file in templates_dir.iterdir():
            if template_file.stem == template_id:
                try:
                    with open(template_file) as f:
                        content = f.read()
                    properties, body = MetadataParser.parse_frontmatter(content)
                    if properties and properties.get("type") == "template":
                        ext = properties.get("template_for", template_file.suffix)
                        template = {
                            "id": template_id,
                            "file_extension": ext,
                            "default_name": properties.get("default_name", f"{{title}}{ext}"),
                            "content": properties.get("template_content", body),
                        }
                        break
                except Exception:
                    continue

    # Fall back to default templates
    if not template:
        for t in get_default_templates(req.app.state.plugin_loader):
            if t["id"] == template_id:
                template = t
                break

    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    # Determine filename
    if custom_filename:
        # Use custom filename, ensure it has the right extension
        filename = custom_filename
        if not filename.endswith(template["file_extension"]):
            filename += template["file_extension"]
    else:
        # Generate from pattern
        filename = expand_template_pattern(template["default_name"])

    # Extract title from filename for content expansion
    title = os.path.splitext(filename)[0]

    # Expand patterns in content
    content = expand_template_pattern(template["content"], title)

    # Create the file using existing create_file logic
    create_request = CreateFileRequest(
        notebook_id=notebook_id,
        workspace_id=workspace_id,
        path=filename,
        content=content,
    )

    return await create_file(create_request, current_user, session)


@router.get("/by-path/content")
async def get_file_content_by_path(
    path: str,
    workspace_id: int,
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content by path (serves binary files like images).

    Supports:
    - Exact path match: "path/to/image.png"
    - Filename only: "image.png" (searches for filename in notebook)
    """
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # First try exact path match
        file_result = nb_session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == notebook_id, FileMetadata.path == path)
        )
        file_meta = file_result.scalar_one_or_none()

        # If not found and path doesn't contain directory separator, try filename match
        if not file_meta and "/" not in path:
            file_result = nb_session.execute(
                select(FileMetadata).where(FileMetadata.notebook_id == notebook_id, FileMetadata.filename == path)
            )
            # Get first match if multiple files have same name
            file_meta = file_result.scalars().first()

        if not file_meta:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

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
        return FileResponse(path=str(file_path), media_type=media_type, filename=file_meta.filename)
    finally:
        nb_session.close()


@router.get("/{file_id}/history")
async def get_file_history(
    file_id: int,
    workspace_id: int,
    notebook_id: int,
    max_count: int = 20,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get git history for a specific file.

    Returns a list of commits that modified this file, with hash, author, date, and message.
    """
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Get file path on disk
        file_path = notebook_path / file_meta.path

        # Get git history
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        history = git_manager.get_file_history(str(file_path), max_count=max_count)

        return {"file_id": file_id, "path": file_meta.path, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting file history: {str(e)}")
    finally:
        nb_session.close()


@router.get("/{file_id}/history/{commit_hash}")
async def get_file_at_commit(
    file_id: int,
    commit_hash: str,
    workspace_id: int,
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file content at a specific commit.

    Returns the file content as it was at the specified commit.
    """
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        # Get file path on disk
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
        return FileResponse(path=str(file_path), media_type=media_type, filename=file_meta.filename)
    finally:
        nb_session.close()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    notebook_id: int = Form(...),
    workspace_id: int = Form(...),
    path: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Upload a binary file."""
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Create the file
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # Use provided path or default to filename
        target_path = path if path else file.filename
        if not target_path:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_path = notebook_path / target_path

        # Check if file already exists
        if file_path.exists():
            raise HTTPException(status_code=400, detail="File already exists")

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine content type
        content_type = get_content_type(str(file_path))

        import hashlib
        from datetime import datetime

        # Read file content
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Create metadata record
        file_meta = FileMetadata(
            notebook_id=notebook_id,
            path=target_path,
            filename=os.path.basename(target_path),
            content_type=content_type,
            size=len(content),
            hash=file_hash,
        )

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
                        FileMetadata.notebook_id == notebook_id, FileMetadata.path == target_path
                    )
                )
                file_meta = existing_result.scalar_one_or_none()
                if not file_meta:
                    raise HTTPException(status_code=500, detail="Race condition: file metadata not found")
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

        # Commit file to git
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
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

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        nb_session.close()


class MoveFileRequest(BaseModel):
    """Request model for moving/renaming a file."""

    new_path: str


# New nested router for workspace/notebook-based file routes
# These routes follow the pattern: /workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/...
nested_router = APIRouter()


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
    workspace_path = Path(workspace.path).resolve()  # Convert to absolute path
    notebook_path = workspace_path / notebook.path

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook path not found")

    return notebook_path, notebook, workspace


class CreateFileRequestNested(BaseModel):
    """Request model for creating a file (nested routes)."""

    path: str
    content: str


class UpdateFileRequestNested(BaseModel):
    """Request model for updating a file (nested routes)."""

    content: str | None = None
    properties: dict[str, Any] | None = None


@nested_router.get("/templates")
async def list_templates_nested(
    request: Request,
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List available file templates (nested under workspace/notebook route)."""
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    defaults = get_default_templates(request.app.state.plugin_loader)
    defaults_with_source = add_template_source(defaults)

    templates_dir = notebook_path / ".templates"
    # Check if notebook has a .templates folder
    templates = []
    if templates_dir.exists() and templates_dir.is_dir():
        # Load templates from the .templates folder
        for template_file in templates_dir.iterdir():
            if template_file.is_file() and not template_file.name.startswith("."):
                try:
                    with open(template_file) as f:
                        content = f.read()

                    # Parse frontmatter to get template metadata
                    properties, body = MetadataParser.parse_frontmatter(content)

                    # Template must have type: template in frontmatter
                    if properties and properties.get("type") == "template":
                        template_id = template_file.stem
                        ext = properties.get("template_for", template_file.suffix)

                        templates.append(
                            {
                                "id": template_id,
                                "name": properties.get("name", template_id),
                                "description": properties.get("description", ""),
                                "icon": properties.get("icon", "📄"),
                                "file_extension": ext,
                                "default_name": properties.get("default_name", f"{{title}}{ext}"),
                                "content": properties.get("template_content", body),
                                "source": "notebook",
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse template {template_file}: {e}")
                    continue

    return {"templates": defaults_with_source + templates}


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


@nested_router.get("/by-path")
async def get_file_by_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    path: str,
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
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == path)
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


@nested_router.get("/by-path/content")
async def get_file_content_by_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    path: str,
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
            select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == path)
        )
        file_meta = file_result.scalar_one_or_none()

        # If not found and path doesn't contain directory separator, try filename match
        if not file_meta and "/" not in path:
            file_result = nb_session.execute(
                select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.filename == path)
            )
            # Get first match if multiple files have same name
            file_meta = file_result.scalars().first()

        if not file_meta:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

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
        return FileResponse(path=str(file_path), media_type=media_type, filename=file_meta.filename)
    finally:
        nb_session.close()


@nested_router.get("/by-path/text")
async def get_file_text_by_path_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get file text content by path (nested under workspace/notebook route).
    
    For markdown files, strips frontmatter and returns only the content body.
    """
    notebook_path, notebook, workspace = await get_notebook_path_nested(
        workspace_identifier, notebook_identifier, current_user, session
    )

    file_path = notebook_path / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path, "r") as f:
            content = f.read()
        
        # Strip frontmatter from markdown files
        if path.endswith(".md"):
            _, content = MetadataParser.parse_frontmatter(content)
        
        return {"content": content}
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


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

    # Create the file
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_path = notebook_path / path

        # Check if file already exists
        if file_path.exists():
            raise HTTPException(status_code=400, detail="File already exists")

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine content type before creating file
        content_type = get_content_type(str(file_path))

        import hashlib
        from datetime import datetime

        # Create metadata record BEFORE writing file to prevent race with watcher
        file_meta = FileMetadata(
            notebook_id=notebook.id,
            path=path,
            filename=os.path.basename(path),
            content_type=content_type,
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
                    select(FileMetadata).where(FileMetadata.notebook_id == notebook.id, FileMetadata.path == path)
                )
                file_meta = existing_result.scalar_one_or_none()
                if not file_meta:
                    raise HTTPException(status_code=500, detail="Race condition: file metadata not found")
            else:
                raise

        # Now write the file to disk
        with open(file_path, "w") as f:
            f.write(content)

        # Refresh to get any updates the watcher may have made
        nb_session.refresh(file_meta)

        # Update metadata with actual file stats
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
            "content_type": file_meta.content_type,
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
        if properties is not None:
            if content and file_meta.content_type in ["text/markdown", "application/x-codex-view"]:
                # Write frontmatter to file
                content = MetadataParser.write_frontmatter(content, properties)
            else:
                MetadataParser.write_sidecar(str(file_path), properties)

        # Update content if provided
        if content is not None:
            with open(file_path, "w") as f:
                f.write(content)

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
            "properties": properties,
            "updated_at": file_meta.updated_at.isoformat() if file_meta.updated_at else None,
            "message": "File updated successfully",
        }

        return result
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

        # Move the file on disk first
        import shutil
        shutil.move(str(old_path), str(new_file_path))

        # Update metadata to match the new file location
        file_meta.path = new_path
        file_meta.filename = os.path.basename(new_path)
        if file_meta.sidecar_path:
            new_sidecar_path = new_file_path.parent / Path(file_meta.sidecar_path).name
            shutil.move(file_meta.sidecar_path, str(new_sidecar_path))
            file_meta.sidecar_path = str(new_sidecar_path)


        return {
            "id": file_meta.id,
            "path": file_meta.path,
            "filename": file_meta.filename,
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

        # Delete the file from disk
        if file_path.exists():
            os.remove(file_path)

        # Delete sidecar file if it exists
        _, sidecar = MetadataParser.resolve_sidecar(str(file_path))
        if sidecar and Path(sidecar).exists():
            os.remove(sidecar)
            logger.debug(f"Deleted sidecar file: {sidecar}")

        # Commit deletion to git first (before deleting from DB)
        from codex.core.git_manager import GitManager
        git_manager = GitManager(str(notebook_path))
        git_manager.commit(f"Delete {filename}", [])

        # Delete from database (watcher may have already deleted it due to race condition)
        from sqlalchemy.orm.exc import StaleDataError
        nb_session.delete(file_meta)
        
        try:
            nb_session.commit()
        except StaleDataError:
            # Watcher deleted the record before us - this is fine
            nb_session.rollback()

        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
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

"""File routes."""

import json
import mimetypes
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
import logging
from codex.core.metadata import MetadataParser
from codex.core.link_resolver import LinkResolver
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


def load_default_templates() -> list[dict]:
    """Load default templates from YAML files in the templates directory."""
    import yaml

    templates_dir = Path(__file__).parent.parent.parent / "templates"
    templates = []

    if templates_dir.exists():
        for template_file in sorted(templates_dir.glob("*.yaml")):
            try:
                with open(template_file) as f:
                    template_data = yaml.safe_load(f)
                    if template_data and isinstance(template_data, dict):
                        templates.append(template_data)
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")

    return templates


# Cache for default templates (loaded once)
_default_templates_cache: list[dict] | None = None


def get_default_templates() -> list[dict]:
    """Get default templates, loading from cache if available."""
    global _default_templates_cache
    if _default_templates_cache is None:
        _default_templates_cache = load_default_templates()
    return _default_templates_cache


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

    return result


@router.get("/templates")
async def list_templates(
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List available templates for a notebook.

    Returns templates from the .templates folder if it exists,
    otherwise returns the default built-in templates.
    """
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    templates_dir = notebook_path / ".templates"

    # Check if notebook has a .templates folder
    if templates_dir.exists() and templates_dir.is_dir():
        # Load templates from the .templates folder
        templates = []
        nb_session = get_notebook_session(str(notebook_path))
        try:
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

                            templates.append({
                                "id": template_id,
                                "name": properties.get("name", template_id),
                                "description": properties.get("description", ""),
                                "icon": properties.get("icon", "📄"),
                                "file_extension": ext,
                                "default_name": properties.get("default_name", f"{{title}}{ext}"),
                                "content": properties.get("template_content", body),
                                "source": "notebook",
                            })
                    except Exception as e:
                        logger.warning(f"Failed to parse template {template_file}: {e}")
                        continue
        finally:
            nb_session.close()

        # If we found custom templates, return them along with defaults
        if templates:
            # Add source to defaults
            defaults_with_source = [{**t, "source": "default"} for t in get_default_templates()]
            return {"templates": templates + defaults_with_source}

    # Return default templates
    defaults_with_source = [{**t, "source": "default"} for t in get_default_templates()]
    return {"templates": defaults_with_source}


@router.post("/from-template")
async def create_from_template(
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
        for t in get_default_templates():
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


@router.get("/by-path")
async def get_file_by_path(
    path: str,
    workspace_id: int,
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a file by its path or filename.

    Supports:
    - Exact path match: "path/to/file.md"
    - Filename only: "file.md" (searches for filename in notebook)
    """
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # First try exact path match
        file_result = nb_session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == notebook_id,
                FileMetadata.path == path
            )
        )
        file_meta = file_result.scalar_one_or_none()

        # If not found and path doesn't contain directory separator, try filename match
        if not file_meta and "/" not in path:
            file_result = nb_session.execute(
                select(FileMetadata).where(
                    FileMetadata.notebook_id == notebook_id,
                    FileMetadata.filename == path
                )
            )
            # Get first match if multiple files have same name
            file_meta = file_result.scalars().first()

        if not file_meta:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

        # Read file content if it's a text file
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
            select(FileMetadata).where(
                FileMetadata.notebook_id == notebook_id,
                FileMetadata.path == path
            )
        )
        file_meta = file_result.scalar_one_or_none()

        # If not found and path doesn't contain directory separator, try filename match
        if not file_meta and "/" not in path:
            file_result = nb_session.execute(
                select(FileMetadata).where(
                    FileMetadata.notebook_id == notebook_id,
                    FileMetadata.filename == path
                )
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
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_meta.filename
        )
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


@router.post("/resolve-link")
async def resolve_link(
    request: ResolveLinkRequest,
    workspace_id: int,
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Resolve a link to a file path.

    This endpoint helps resolve links between documents, supporting:
    - Absolute paths: "/path/to/file.md"
    - Relative paths: "./file.md", "../other/file.md"
    - Filename only: "file.md"

    Returns the resolved file metadata if found.
    """
    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Resolve the link
    try:
        resolved_path = LinkResolver.resolve_link(
            request.link,
            request.current_file_path,
            notebook_path
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Query the resolved file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        # First try exact path match
        file_result = nb_session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == notebook_id,
                FileMetadata.path == resolved_path
            )
        )
        file_meta = file_result.scalar_one_or_none()

        # If not found and path doesn't contain directory separator, try filename match
        if not file_meta and "/" not in resolved_path:
            file_result = nb_session.execute(
                select(FileMetadata).where(
                    FileMetadata.notebook_id == notebook_id,
                    FileMetadata.filename == resolved_path
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
            "file_type": file_meta.file_type,
            "size": file_meta.size,
            "hash": file_meta.hash,
            "title": file_meta.title,
            "description": file_meta.description,
            "properties": properties,
            "resolved_path": resolved_path,
            "created_at": file_meta.created_at.isoformat() if file_meta.created_at else None,
            "updated_at": file_meta.updated_at.isoformat() if file_meta.updated_at else None,
        }

        return result
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
        path_lower = path.lower()
        if path.endswith(".md"):
            file_type = "markdown"
        elif path.endswith(".cdx"):
            file_type = "view"
        elif path.endswith(".json"):
            file_type = "json"
        elif path.endswith(".xml"):
            file_type = "xml"
        elif path_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg")):
            file_type = "image"
        elif path_lower.endswith(".pdf"):
            file_type = "pdf"
        elif path_lower.endswith((".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")):
            file_type = "audio"
        elif path_lower.endswith((".mp4", ".webm", ".ogv", ".mov", ".avi")):
            file_type = "video"
        elif path_lower.endswith((".html", ".htm")):
            file_type = "html"

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

        # Determine file type
        file_type = "binary"
        path_lower = target_path.lower()
        if path_lower.endswith(".md"):
            file_type = "markdown"
        elif path_lower.endswith(".cdx"):
            file_type = "view"
        elif path_lower.endswith(".json"):
            file_type = "json"
        elif path_lower.endswith(".xml"):
            file_type = "xml"
        elif path_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg")):
            file_type = "image"
        elif path_lower.endswith(".pdf"):
            file_type = "pdf"
        elif path_lower.endswith((".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")):
            file_type = "audio"
        elif path_lower.endswith((".mp4", ".webm", ".ogv", ".mov", ".avi")):
            file_type = "video"
        elif path_lower.endswith((".html", ".htm")):
            file_type = "html"
        elif path_lower.endswith((".txt", ".csv", ".log")):
            file_type = "text"

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
            file_type=file_type,
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
                        FileMetadata.notebook_id == notebook_id,
                        FileMetadata.path == target_path
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
        from backend.core.git_manager import GitManager

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
            "file_type": file_meta.file_type,
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


@router.patch("/{file_id}/move")
async def move_file(
    file_id: int,
    workspace_id: int,
    notebook_id: int,
    request: MoveFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Move or rename a file."""
    new_path = request.new_path

    # Get notebook path from system database
    notebook_path, _ = await get_notebook_path(notebook_id, workspace_id, current_user, session)

    # Query file from notebook database
    nb_session = get_notebook_session(str(notebook_path))
    try:
        file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        file_meta = file_result.scalar_one_or_none()

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        old_file_path = notebook_path / file_meta.path
        new_file_path = notebook_path / new_path

        if not old_file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Check if target already exists
        if new_file_path.exists() and old_file_path != new_file_path:
            raise HTTPException(status_code=400, detail="Target path already exists")

        # Create parent directories if needed
        new_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Move the file
        import shutil
        shutil.move(str(old_file_path), str(new_file_path))

        # Update metadata
        from datetime import datetime, timezone

        old_path = file_meta.path
        file_meta.path = new_path
        file_meta.filename = os.path.basename(new_path)
        file_meta.updated_at = datetime.now(timezone.utc)

        # Commit changes to git
        from backend.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))
        commit_hash = git_manager.commit(
            f"Move {os.path.basename(old_path)} to {new_path}",
            [str(new_file_path)]
        )
        if commit_hash:
            file_meta.last_commit_hash = commit_hash

        nb_session.commit()
        nb_session.refresh(file_meta)

        result = {
            "id": file_meta.id,
            "notebook_id": file_meta.notebook_id,
            "path": file_meta.path,
            "filename": file_meta.filename,
            "file_type": file_meta.file_type,
            "size": file_meta.size,
            "message": "File moved successfully",
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving file in notebook {notebook_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error moving file: {str(e)}")
    finally:
        nb_session.close()


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a file."""
    # First get the file to find its notebook_id
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Find the file in all notebooks of this workspace
    notebooks_result = await session.execute(
        select(Notebook).where(Notebook.workspace_id == workspace_id)
    )
    notebooks = notebooks_result.scalars().all()

    file_meta = None
    nb_session = None
    notebook_path = None

    for notebook in notebooks:
        workspace_path = Path(workspace.path)
        nb_path = workspace_path / notebook.path
        if not nb_path.exists():
            continue

        sess = get_notebook_session(str(nb_path))
        try:
            file_result = sess.execute(select(FileMetadata).where(FileMetadata.id == file_id))
            found_file = file_result.scalar_one_or_none()
            if found_file:
                file_meta = found_file
                nb_session = sess
                notebook_path = nb_path
                break
        except Exception:
            sess.close()
            continue

    if not file_meta or not nb_session or not notebook_path:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path = notebook_path / file_meta.path

        # Delete the file from disk
        if file_path.exists():
            os.remove(file_path)

        # Delete from database
        nb_session.delete(file_meta)

        # Commit deletion to git
        from backend.core.git_manager import GitManager

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

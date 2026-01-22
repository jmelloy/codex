"""File routes."""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.api.auth import get_current_active_user
from backend.core.metadata import MetadataParser
from backend.db.database import get_notebook_session, get_system_session
from backend.db.models import FileMetadata, User, Workspace

router = APIRouter()


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
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Find the notebook directory and query its database
    workspace_path = Path(workspace.path)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace path not found")

    # Scan for notebook with matching ID
    for item in workspace_path.iterdir():
        if item.is_dir():
            codex_dir = item / ".codex"
            notebook_db_path = codex_dir / "notebook.db"
            if notebook_db_path.exists():
                try:
                    nb_session = get_notebook_session(str(item))
                    # Check if this notebook has the requested ID
                    from backend.db.models import Notebook

                    nb_result = nb_session.execute(select(Notebook).where(Notebook.id == notebook_id))
                    notebook = nb_result.scalar_one_or_none()

                    if notebook:
                        # Get all files for this notebook
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

                        nb_session.close()
                        return file_list

                    nb_session.close()
                except Exception as e:
                    print(f"Error reading notebook {item}: {e}")

    raise HTTPException(status_code=404, detail="Notebook not found")


@router.get("/{file_id}")
async def get_file(
    file_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a specific file."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Search through notebooks for the file
    workspace_path = Path(workspace.path)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace path not found")

    for item in workspace_path.iterdir():
        if item.is_dir():
            codex_dir = item / ".codex"
            notebook_db_path = codex_dir / "notebook.db"
            if notebook_db_path.exists():
                try:
                    nb_session = get_notebook_session(str(item))
                    file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
                    file_meta = file_result.scalar_one_or_none()

                    if file_meta:
                        # Read file content if it's a text file
                        file_path = item / file_meta.path
                        content = None
                        raw_content = None
                        if file_path.exists() and file_meta.file_type in ["text", "markdown", "view", "json", "xml"]:
                            try:
                                with open(file_path) as f:
                                    raw_content = f.read()
                            except Exception as e:
                                print(f"Error reading file content: {e}")

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

                        nb_session.close()
                        return result

                    nb_session.close()
                except Exception as e:
                    print(f"Error reading file from notebook {item}: {e}")

    raise HTTPException(status_code=404, detail="File not found")


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

    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Find the notebook
    workspace_path = Path(workspace.path)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace path not found")

    for item in workspace_path.iterdir():
        if item.is_dir():
            codex_dir = item / ".codex"
            notebook_db_path = codex_dir / "notebook.db"
            if notebook_db_path.exists():
                try:
                    nb_session = get_notebook_session(str(item))
                    from backend.db.models import Notebook

                    nb_result = nb_session.execute(select(Notebook).where(Notebook.id == notebook_id))
                    notebook = nb_result.scalar_one_or_none()

                    if notebook:
                        # Create the file
                        file_path = item / path

                        # Check if file already exists
                        if file_path.exists():
                            nb_session.close()
                            raise HTTPException(status_code=400, detail="File already exists")

                        # Create parent directories if needed
                        file_path.parent.mkdir(parents=True, exist_ok=True)

                        # Write content
                        with open(file_path, "w") as f:
                            f.write(content)

                        # Create metadata record
                        import hashlib

                        file_hash = hashlib.sha256(content.encode()).hexdigest()
                        file_stats = os.stat(file_path)

                        file_type = "text"
                        if path.endswith(".md"):
                            file_type = "markdown"
                        elif path.endswith(".cdx"):
                            file_type = "view"
                        elif path.endswith(".json"):
                            file_type = "json"
                        elif path.endswith(".xml"):
                            file_type = "xml"

                        from datetime import datetime

                        file_meta = FileMetadata(
                            notebook_id=notebook_id,
                            path=path,
                            filename=os.path.basename(path),
                            file_type=file_type,
                            size=file_stats.st_size,
                            hash=file_hash,
                            file_created_at=datetime.fromtimestamp(file_stats.st_ctime),
                            file_modified_at=datetime.fromtimestamp(file_stats.st_mtime),
                        )

                        # Commit file to git
                        from backend.core.git_manager import GitManager

                        git_manager = GitManager(str(item))
                        commit_hash = git_manager.commit(f"Create {os.path.basename(path)}", [str(file_path)])
                        if commit_hash:
                            file_meta.last_commit_hash = commit_hash

                        nb_session.add(file_meta)
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

                        nb_session.close()
                        return result

                    nb_session.close()
                except Exception as e:
                    print(f"Error creating file in notebook {item}: {e}")
                    raise HTTPException(status_code=500, detail=f"Error creating file: {str(e)}")

    raise HTTPException(status_code=404, detail="Notebook not found")


@router.put("/{file_id}")
async def update_file(
    file_id: int,
    workspace_id: int,
    request: UpdateFileRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update a file."""
    content = request.content

    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Search for the file
    workspace_path = Path(workspace.path)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace path not found")

    for item in workspace_path.iterdir():
        if item.is_dir():
            codex_dir = item / ".codex"
            notebook_db_path = codex_dir / "notebook.db"
            if notebook_db_path.exists():
                try:
                    nb_session = get_notebook_session(str(item))
                    file_result = nb_session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
                    file_meta = file_result.scalar_one_or_none()

                    if file_meta:
                        # Update the file
                        file_path = item / file_meta.path

                        if not file_path.exists():
                            nb_session.close()
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
                        from backend.core.git_manager import GitManager

                        git_manager = GitManager(str(item))
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

                        nb_session.close()
                        return result

                    nb_session.close()
                except Exception as e:
                    print(f"Error updating file in notebook {item}: {e}")
                    raise HTTPException(status_code=500, detail=f"Error updating file: {str(e)}")

    raise HTTPException(status_code=404, detail="File not found")

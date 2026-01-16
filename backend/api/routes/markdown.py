"""Markdown file routes for viewing and editing."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_active_user
from backend.core.metadata import MetadataParser
from backend.db.database import get_system_session
from backend.db.models import User, Workspace

router = APIRouter()


# Schemas
class MarkdownContentRequest(BaseModel):
    """Request schema for creating/updating markdown content."""

    path: str
    content: str
    frontmatter: dict[str, Any] | None = None


class MarkdownContentResponse(BaseModel):
    """Response schema for markdown content."""

    path: str
    content: str
    frontmatter: dict[str, Any] | None = None
    html: str | None = None


class MarkdownRenderRequest(BaseModel):
    """Request schema for rendering markdown."""

    content: str


class MarkdownRenderResponse(BaseModel):
    """Response schema for rendered markdown."""

    html: str
    frontmatter: dict[str, Any] | None = None


@router.post("/render", response_model=MarkdownRenderResponse)
async def render_markdown(request: MarkdownRenderRequest, current_user: User = Depends(get_current_active_user)):
    """
    Render markdown content to HTML.
    This is an extensible endpoint that can be enhanced with custom renderers.
    """
    try:
        # Parse frontmatter if present
        frontmatter_data, content = MetadataParser.parse_frontmatter(request.content)

        # For now, return the raw content (can be extended with markdown-to-html library)
        # This is intentionally minimal to allow frontend flexibility
        return MarkdownRenderResponse(html=content, frontmatter=frontmatter_data if frontmatter_data else None)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error rendering markdown: {str(e)}"
        )


@router.get("/{workspace_id}/files", response_model=list[str])
async def list_markdown_files(
    workspace_id: int,
    notebook_path: str | None = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """
    List all markdown files in a workspace or specific notebook.
    """
    from pathlib import Path as PathLib

    from sqlmodel import select

    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    workspace_path = PathLib(workspace.path)
    if not workspace_path.exists():
        return []

    markdown_files = []

    if notebook_path:
        # List files in specific notebook
        target_path = workspace_path / notebook_path
        if target_path.exists() and target_path.is_dir():
            for file_path in target_path.rglob("*.md"):
                if ".codex" not in str(file_path):
                    rel_path = str(file_path.relative_to(workspace_path))
                    markdown_files.append(rel_path)
    else:
        # List all markdown files in workspace
        for file_path in workspace_path.rglob("*.md"):
            if ".codex" not in str(file_path):
                rel_path = str(file_path.relative_to(workspace_path))
                markdown_files.append(rel_path)

    return markdown_files


@router.get("/{workspace_id}/file", response_model=MarkdownContentResponse)
async def get_markdown_file(
    workspace_id: int,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """
    Get markdown file content with parsed frontmatter.
    """
    from pathlib import Path as PathLib

    from sqlmodel import select

    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Construct full file path
    workspace_path = PathLib(workspace.path)
    full_file_path = workspace_path / file_path

    # Security check: ensure file is within workspace
    try:
        full_file_path = full_file_path.resolve()
        workspace_path = workspace_path.resolve()
        if not str(full_file_path).startswith(str(workspace_path)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: file is outside workspace"
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file path: {str(e)}")

    # Check if file exists
    if not full_file_path.exists() or not full_file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Read file content
    try:
        with open(full_file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error reading file: {str(e)}")

    # Parse frontmatter if present
    frontmatter_data, content_without_frontmatter = MetadataParser.parse_frontmatter(content)

    return MarkdownContentResponse(
        path=file_path,
        content=content_without_frontmatter,
        frontmatter=frontmatter_data if frontmatter_data else None,
        html=content_without_frontmatter,  # Basic pass-through, can be enhanced
    )


@router.post("/{workspace_id}/file", response_model=MarkdownContentResponse, status_code=status.HTTP_201_CREATED)
async def create_markdown_file(
    workspace_id: int,
    request: MarkdownContentRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """
    Create a new markdown file with optional frontmatter.
    """
    from pathlib import Path as PathLib

    import frontmatter
    from sqlmodel import select

    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Construct full file path
    workspace_path = PathLib(workspace.path)
    full_file_path = workspace_path / request.path

    # Security check: ensure file is within workspace
    try:
        full_file_path = full_file_path.resolve()
        workspace_path = workspace_path.resolve()
        if not str(full_file_path).startswith(str(workspace_path)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: file path is outside workspace"
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file path: {str(e)}")

    # Check if file already exists
    if full_file_path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File already exists")

    # Create parent directories if needed
    full_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare content with frontmatter
    try:
        if request.frontmatter:
            post = frontmatter.Post(request.content, **request.frontmatter)
            file_content = frontmatter.dumps(post)
        else:
            file_content = request.content

        # Write file
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(file_content)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating file: {str(e)}")

    return MarkdownContentResponse(
        path=request.path, content=request.content, frontmatter=request.frontmatter, html=request.content
    )


@router.put("/{workspace_id}/file", response_model=MarkdownContentResponse)
async def update_markdown_file(
    workspace_id: int,
    request: MarkdownContentRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """
    Update an existing markdown file.
    """
    from pathlib import Path as PathLib

    import frontmatter
    from sqlmodel import select

    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Construct full file path
    workspace_path = PathLib(workspace.path)
    full_file_path = workspace_path / request.path

    # Security check: ensure file is within workspace
    try:
        full_file_path = full_file_path.resolve()
        workspace_path = workspace_path.resolve()
        if not str(full_file_path).startswith(str(workspace_path)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: file path is outside workspace"
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file path: {str(e)}")

    # Check if file exists
    if not full_file_path.exists() or not full_file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Prepare content with frontmatter
    try:
        if request.frontmatter:
            post = frontmatter.Post(request.content, **request.frontmatter)
            file_content = frontmatter.dumps(post)
        else:
            file_content = request.content

        # Write file
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(file_content)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating file: {str(e)}")

    return MarkdownContentResponse(
        path=request.path, content=request.content, frontmatter=request.frontmatter, html=request.content
    )


@router.delete("/{workspace_id}/file")
async def delete_markdown_file(
    workspace_id: int,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """
    Delete a markdown file.
    """
    import os
    from pathlib import Path as PathLib

    from sqlmodel import select

    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Construct full file path
    workspace_path = PathLib(workspace.path)
    full_file_path = workspace_path / file_path

    # Security check: ensure file is within workspace
    try:
        full_file_path = full_file_path.resolve()
        workspace_path = workspace_path.resolve()
        if not str(full_file_path).startswith(str(workspace_path)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: file path is outside workspace"
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file path: {str(e)}")

    # Check if file exists
    if not full_file_path.exists() or not full_file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Delete file
    try:
        os.remove(full_file_path)
        return {"message": "File deleted successfully", "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting file: {str(e)}")

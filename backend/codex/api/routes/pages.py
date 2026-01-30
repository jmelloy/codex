"""Pages API routes for file-based page organization."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import FileMetadata, Notebook, Page, User, Workspace

router = APIRouter()
logger = logging.getLogger(__name__)


class PageCreate(BaseModel):
    """Request body for creating a page."""

    title: str
    description: str | None = None


class PageUpdate(BaseModel):
    """Request body for updating a page."""

    title: str | None = None
    description: str | None = None


class BlockCreate(BaseModel):
    """Request body for creating a block."""

    filename: str
    content: bytes | None = None


class BlockReorder(BaseModel):
    """Request body for reordering blocks."""

    file: str
    new_position: int


class PageResponse(BaseModel):
    """Response model for a page."""

    id: int
    notebook_id: int
    directory_path: str
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    blocks: list[dict] = []


class PageListResponse(BaseModel):
    """Response model for listing pages."""

    id: int
    notebook_id: int
    directory_path: str
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    block_count: int = 0


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "page"


def is_page_directory(directory: Path) -> bool:
    """Check if a directory is a page directory.
    
    A directory is considered a page if:
    1. It has a .page suffix (e.g., experiment.page/)
    2. It contains a .page or .page.json file
    """
    # Check for .page suffix
    if directory.name.endswith(".page"):
        return True
    
    # Check for .page or .page.json file inside
    if (directory / ".page").exists() or (directory / ".page.json").exists():
        return True
    
    return False


def get_page_display_name(directory_path: str) -> str:
    """Get the display name for a page, hiding the .page suffix if present."""
    if directory_path.endswith(".page"):
        return directory_path[:-5]  # Remove .page suffix
    return directory_path


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

    notebook_path = Path(workspace.path) / notebook.path
    return notebook_path, notebook


@router.post("/notebooks/{notebook_id}/pages", status_code=status.HTTP_201_CREATED)
async def create_page(
    notebook_id: int,
    workspace_id: int,
    page_data: PageCreate,
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """Create a new page directory with metadata."""
    notebook_path, notebook = await get_notebook_path(notebook_id, workspace_id, current_user, system_session)

    # Get notebook session (synchronous)
    notebook_session = get_notebook_session(str(notebook_path))

    # Create directory path from title with .page suffix
    slug = slugify(page_data.title)
    directory_path = f"{slug}.page"
    page_dir = notebook_path / directory_path

    # Check if page already exists
    result = notebook_session.execute(
        select(Page).where(Page.notebook_id == notebook_id, Page.directory_path == directory_path)
    )
    existing = result.scalar_one_or_none()
    if existing:
        notebook_session.close()
        raise HTTPException(status_code=400, detail="Page already exists")

    # Create page directory
    page_dir.mkdir(parents=True, exist_ok=True)

    # Create .page metadata file (marks this as a page directory)
    metadata = {
        "title": page_data.title,
        "description": page_data.description,
        "created_time": datetime.utcnow().isoformat() + "Z",
        "last_edited_time": datetime.utcnow().isoformat() + "Z",
        "blocks": [],
    }
    metadata_file = page_dir / ".page"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    # Create database entry
    page = Page(
        notebook_id=notebook_id,
        directory_path=directory_path,
        title=page_data.title,
        description=page_data.description,
    )
    notebook_session.add(page)
    notebook_session.commit()
    notebook_session.refresh(page)
    notebook_session.close()

    return {
        "id": page.id,
        "notebook_id": page.notebook_id,
        "directory_path": page.directory_path,
        "title": page.title,
        "description": page.description,
        "created_at": page.created_at,
        "updated_at": page.updated_at,
    }


@router.get("/notebooks/{notebook_id}/pages")
async def list_pages(
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """List all pages in a notebook.
    
    Pages are detected by:
    1. Directories with .page suffix (e.g., experiment.page/)
    2. Directories containing .page or .page.json files
    """
    notebook_path, notebook = await get_notebook_path(notebook_id, workspace_id, current_user, system_session)

    # Get notebook session (synchronous)
    notebook_session = get_notebook_session(str(notebook_path))

    # Scan filesystem for page directories
    page_dirs_found = {}
    if notebook_path.exists():
        for item in notebook_path.iterdir():
            if item.is_dir() and is_page_directory(item):
                # Get relative path from notebook
                rel_path = str(item.relative_to(notebook_path))
                page_dirs_found[rel_path] = item

    # Query existing pages from database
    result = notebook_session.execute(select(Page).where(Page.notebook_id == notebook_id))
    existing_pages = {page.directory_path: page for page in result.scalars().all()}

    # Merge filesystem pages with database pages
    pages_with_counts = []
    
    # Add all filesystem pages
    for rel_path, page_dir in page_dirs_found.items():
        # Count blocks
        block_files = [f for f in page_dir.iterdir() if f.is_file() and re.match(r"^\d{3}-", f.name)]
        block_count = len(block_files)
        
        # Get or create page metadata
        if rel_path in existing_pages:
            page = existing_pages[rel_path]
            pages_with_counts.append(
                PageListResponse(
                    id=page.id,
                    notebook_id=page.notebook_id,
                    directory_path=page.directory_path,
                    title=page.title,
                    description=page.description,
                    created_at=page.created_at,
                    updated_at=page.updated_at,
                    block_count=block_count,
                )
            )
        else:
            # Page exists on filesystem but not in database
            # Read metadata from .page or .page.json file
            metadata_file = page_dir / ".page"
            if not metadata_file.exists():
                metadata_file = page_dir / ".page.json"
            
            title = get_page_display_name(rel_path)
            description = None
            
            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                    title = metadata.get("title", title)
                    description = metadata.get("description")
                except:
                    pass
            
            # Create page in database
            page = Page(
                notebook_id=notebook_id,
                directory_path=rel_path,
                title=title,
                description=description,
            )
            notebook_session.add(page)
            notebook_session.commit()
            notebook_session.refresh(page)
            
            pages_with_counts.append(
                PageListResponse(
                    id=page.id,
                    notebook_id=page.notebook_id,
                    directory_path=page.directory_path,
                    title=page.title,
                    description=page.description,
                    created_at=page.created_at,
                    updated_at=page.updated_at,
                    block_count=block_count,
                )
            )

    notebook_session.close()
    return pages_with_counts


@router.get("/pages/{page_id}")
async def get_page(
    page_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """Get page details with blocks."""
    # First we need to find which notebook the page belongs to
    # We'll need to iterate through notebooks in the workspace to find it
    result = await system_session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get all notebooks in workspace
    result = await system_session.execute(select(Notebook).where(Notebook.workspace_id == workspace_id))
    notebooks = result.scalars().all()

    # Try to find the page in any notebook
    page = None
    notebook_path = None
    for nb in notebooks:
        nb_path = Path(workspace.path) / nb.path
        nb_session = get_notebook_session(str(nb_path))
        result = nb_session.execute(select(Page).where(Page.id == page_id))
        page = result.scalar_one_or_none()
        nb_session.close()
        if page:
            notebook_path = nb_path
            break

    if not page or not notebook_path:
        raise HTTPException(status_code=404, detail="Page not found")

    page_dir = notebook_path / page.directory_path

    # Read blocks from directory
    blocks = []
    if page_dir.exists():
        # Get all files matching block pattern (NNN-*.*)
        block_files = sorted(
            [f for f in page_dir.iterdir() if f.is_file() and re.match(r"^\d{3}-", f.name)],
            key=lambda f: f.name,
        )

        for block_file in block_files:
            # Parse position from filename
            match = re.match(r"^(\d{3})-(.+)$", block_file.name)
            if match:
                position = int(match.group(1))
                name = match.group(2)

                # Determine block type from extension
                ext = block_file.suffix.lower()
                block_type = "markdown" if ext in [".md", ".markdown"] else "file"

                blocks.append(
                    {
                        "position": position,
                        "file": block_file.name,
                        "name": name,
                        "type": block_type,
                        "path": str(page.directory_path + "/" + block_file.name),
                    }
                )

    return PageResponse(
        id=page.id,
        notebook_id=page.notebook_id,
        directory_path=page.directory_path,
        title=page.title,
        description=page.description,
        created_at=page.created_at,
        updated_at=page.updated_at,
        blocks=blocks,
    )


@router.put("/pages/{page_id}")
async def update_page(
    page_id: int,
    workspace_id: int,
    page_update: PageUpdate,
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """Update page metadata."""
    # Find the page (similar to get_page)
    result = await system_session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    result = await system_session.execute(select(Notebook).where(Notebook.workspace_id == workspace_id))
    notebooks = result.scalars().all()

    page = None
    notebook_path = None
    notebook_session = None
    for nb in notebooks:
        nb_path = Path(workspace.path) / nb.path
        nb_session = get_notebook_session(str(nb_path))
        result = nb_session.execute(select(Page).where(Page.id == page_id))
        page = result.scalar_one_or_none()
        if page:
            notebook_path = nb_path
            notebook_session = nb_session
            break
        else:
            nb_session.close()

    if not page or not notebook_path or not notebook_session:
        raise HTTPException(status_code=404, detail="Page not found")

    page_dir = notebook_path / page.directory_path

    # Update database entry
    if page_update.title is not None:
        page.title = page_update.title
    if page_update.description is not None:
        page.description = page_update.description
    page.updated_at = datetime.utcnow()

    # Update .page or .page.json file if it exists
    metadata_file = page_dir / ".page"
    if not metadata_file.exists():
        metadata_file = page_dir / ".page.json"
    
    if metadata_file.exists():
        metadata = json.loads(metadata_file.read_text())
        if page_update.title is not None:
            metadata["title"] = page_update.title
        if page_update.description is not None:
            metadata["description"] = page_update.description
        metadata["last_edited_time"] = datetime.utcnow().isoformat() + "Z"
        metadata_file.write_text(json.dumps(metadata, indent=2))

    notebook_session.commit()
    notebook_session.refresh(page)
    notebook_session.close()

    return {
        "id": page.id,
        "notebook_id": page.notebook_id,
        "directory_path": page.directory_path,
        "title": page.title,
        "description": page.description,
        "created_at": page.created_at,
        "updated_at": page.updated_at,
    }


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    page_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """Delete a page and its directory."""
    # Find the page
    result = await system_session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    result = await system_session.execute(select(Notebook).where(Notebook.workspace_id == workspace_id))
    notebooks = result.scalars().all()

    page = None
    notebook_path = None
    notebook_session = None
    for nb in notebooks:
        nb_path = Path(workspace.path) / nb.path
        nb_session = get_notebook_session(str(nb_path))
        result = nb_session.execute(select(Page).where(Page.id == page_id))
        page = result.scalar_one_or_none()
        if page:
            notebook_path = nb_path
            notebook_session = nb_session
            break
        else:
            nb_session.close()

    if not page or not notebook_path or not notebook_session:
        raise HTTPException(status_code=404, detail="Page not found")

    page_dir = notebook_path / page.directory_path

    # Delete directory and all contents
    if page_dir.exists():
        import shutil

        shutil.rmtree(page_dir)

    # Delete database entry
    notebook_session.delete(page)
    notebook_session.commit()
    notebook_session.close()

    return None


@router.post("/pages/{page_id}/blocks", status_code=status.HTTP_201_CREATED)
async def create_block(
    page_id: int,
    workspace_id: int,
    block_data: BlockCreate,
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """Create a new block (file) in the page."""
    # Find the page
    result = await system_session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    result = await system_session.execute(select(Notebook).where(Notebook.workspace_id == workspace_id))
    notebooks = result.scalars().all()

    page = None
    notebook_path = None
    notebook_session = None
    for nb in notebooks:
        nb_path = Path(workspace.path) / nb.path
        nb_session = get_notebook_session(str(nb_path))
        result = nb_session.execute(select(Page).where(Page.id == page_id))
        page = result.scalar_one_or_none()
        if page:
            notebook_path = nb_path
            notebook_session = nb_session
            break
        else:
            nb_session.close()

    if not page or not notebook_path or not notebook_session:
        raise HTTPException(status_code=404, detail="Page not found")

    page_dir = notebook_path / page.directory_path

    if not page_dir.exists():
        notebook_session.close()
        raise HTTPException(status_code=404, detail="Page directory not found")

    # Find next available position
    block_files = sorted([f for f in page_dir.iterdir() if f.is_file() and re.match(r"^\d{3}-", f.name)])
    next_position = 1
    if block_files:
        last_file = block_files[-1]
        match = re.match(r"^(\d{3})-", last_file.name)
        if match:
            next_position = int(match.group(1)) + 1

    # Create numbered filename
    numbered_filename = f"{next_position:03d}-{block_data.filename}"
    block_file = page_dir / numbered_filename

    # Create file with content if provided
    if block_data.content:
        block_file.write_bytes(block_data.content)
    else:
        block_file.touch()

    # Update page metadata and get path before closing session
    page.updated_at = datetime.utcnow()
    directory_path = page.directory_path
    notebook_session.commit()
    notebook_session.close()

    return {
        "position": next_position,
        "file": numbered_filename,
        "path": str(directory_path + "/" + numbered_filename),
    }


@router.put("/pages/{page_id}/blocks/reorder")
async def reorder_blocks(
    page_id: int,
    workspace_id: int,
    reorder_data: list[BlockReorder],
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """Reorder blocks by renaming files with new numeric prefixes."""
    # Find the page
    result = await system_session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    result = await system_session.execute(select(Notebook).where(Notebook.workspace_id == workspace_id))
    notebooks = result.scalars().all()

    page = None
    notebook_path = None
    notebook_session = None
    for nb in notebooks:
        nb_path = Path(workspace.path) / nb.path
        nb_session = get_notebook_session(str(nb_path))
        result = nb_session.execute(select(Page).where(Page.id == page_id))
        page = result.scalar_one_or_none()
        if page:
            notebook_path = nb_path
            notebook_session = nb_session
            break
        else:
            nb_session.close()

    if not page or not notebook_path or not notebook_session:
        raise HTTPException(status_code=404, detail="Page not found")

    page_dir = notebook_path / page.directory_path

    if not page_dir.exists():
        notebook_session.close()
        raise HTTPException(status_code=404, detail="Page directory not found")

    # Rename files with new positions
    # Use temp names to avoid conflicts
    temp_renames = []
    for item in reorder_data:
        old_path = page_dir / item.file
        if not old_path.exists():
            notebook_session.close()
            raise HTTPException(status_code=404, detail=f"Block file not found: {item.file}")

        # Extract original name without number prefix
        match = re.match(r"^\d{3}-(.+)$", item.file)
        if not match:
            notebook_session.close()
            raise HTTPException(status_code=400, detail=f"Invalid block filename: {item.file}")

        original_name = match.group(1)
        temp_name = f"temp_{item.new_position:03d}_{original_name}"
        temp_path = page_dir / temp_name

        old_path.rename(temp_path)
        temp_renames.append((temp_path, item.new_position, original_name))

    # Rename from temp to final names
    for temp_path, new_position, original_name in temp_renames:
        new_filename = f"{new_position:03d}-{original_name}"
        new_path = page_dir / new_filename
        temp_path.rename(new_path)

    # Update page metadata
    page.updated_at = datetime.utcnow()
    notebook_session.commit()
    notebook_session.close()

    return {"message": "Blocks reordered successfully"}


@router.delete("/pages/{page_id}/blocks/{block_filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block(
    page_id: int,
    block_filename: str,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    system_session: AsyncSession = Depends(get_system_session),
):
    """Delete a block (file) from the page."""
    # Find the page
    result = await system_session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    result = await system_session.execute(select(Notebook).where(Notebook.workspace_id == workspace_id))
    notebooks = result.scalars().all()

    page = None
    notebook_path = None
    notebook_session = None
    for nb in notebooks:
        nb_path = Path(workspace.path) / nb.path
        nb_session = get_notebook_session(str(nb_path))
        result = nb_session.execute(select(Page).where(Page.id == page_id))
        page = result.scalar_one_or_none()
        if page:
            notebook_path = nb_path
            notebook_session = nb_session
            break
        else:
            nb_session.close()

    if not page or not notebook_path or not notebook_session:
        raise HTTPException(status_code=404, detail="Page not found")

    page_dir = notebook_path / page.directory_path

    block_file = page_dir / block_filename
    if not block_file.exists():
        notebook_session.close()
        raise HTTPException(status_code=404, detail="Block file not found")

    # Delete file
    block_file.unlink()

    # Update page metadata
    page.updated_at = datetime.utcnow()
    notebook_session.commit()
    notebook_session.close()

    return None

"""Notebook routes."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.core.watcher import NotebookWatcher
from codex.db.database import get_system_session, init_notebook_db
from codex.db.models import Notebook, NotebookPluginConfig, User, Workspace


class NotebookCreate(BaseModel):
    """Request body for creating a notebook."""

    workspace_id: int
    name: str
    description: str | None = None


def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "notebook"


router = APIRouter()


@router.get("/")
async def list_notebooks(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all notebooks in a workspace."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Query notebooks from system database
    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace_id))
    notebooks = result.scalars().all()

    return [
        {
            "id": nb.id,
            "name": nb.name,
            "path": nb.path,
            "description": nb.description,
            "created_at": nb.created_at.isoformat() if nb.created_at else None,
            "updated_at": nb.updated_at.isoformat() if nb.updated_at else None,
        }
        for nb in notebooks
    ]


@router.get("/{notebook_id}")
async def get_notebook(
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a specific notebook."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Query notebook from system database
    result = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.workspace_id == workspace_id)
    )
    notebook = result.scalar_one_or_none()

    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    return {
        "id": notebook.id,
        "name": notebook.name,
        "path": notebook.path,
        "description": notebook.description,
        "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
        "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
    }


@router.get("/{notebook_id}/indexing-status")
async def get_notebook_indexing_status(
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get the indexing status for a notebook."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Verify notebook exists
    result = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id, Notebook.workspace_id == workspace_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Find the watcher for this notebook
    from codex.main import get_active_watchers

    for watcher in get_active_watchers():
        if watcher.notebook_id == notebook_id:
            return watcher.get_indexing_status()

    # If no watcher found, indexing hasn't started
    return {"notebook_id": notebook_id, "status": "not_started", "is_alive": False}


@router.post("/")
async def create_notebook(
    body: NotebookCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new notebook."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == body.workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Generate path from name
    workspace_path = Path(workspace.path)
    slug = slugify(body.name)
    notebook_path = workspace_path / slug

    # Handle name collisions by appending a number
    counter = 1
    original_slug = slug
    while notebook_path.exists():
        slug = f"{original_slug}-{counter}"
        notebook_path = workspace_path / slug
        counter += 1

    try:
        notebook_path.mkdir(parents=True, exist_ok=False)

        # Initialize notebook database (still needed for files, tags, search index)
        init_notebook_db(str(notebook_path))

        # Initialize Git repository for the notebook
        from codex.core.git_manager import GitManager

        git_manager = GitManager(str(notebook_path))

        # Create notebook record in the system database
        notebook = Notebook(workspace_id=body.workspace_id, name=body.name, slug=slug, path=slug, description=body.description)
        session.add(notebook)
        await session.commit()
        await session.refresh(notebook)

        NotebookWatcher(str(notebook_path), notebook.id).start()

        return {
            "id": notebook.id,
            "name": notebook.name,
            "path": notebook.path,
            "description": notebook.description,
            "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
            "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
        }

    except Exception as e:
        # Clean up on error
        if notebook_path.exists():
            import shutil

            shutil.rmtree(notebook_path)
        raise HTTPException(status_code=500, detail=f"Error creating notebook: {str(e)}")


@router.get("/{notebook_id}/plugins")
async def list_notebook_plugins(
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List plugin configurations for a notebook.
    
    Args:
        notebook_id: Notebook ID
        
    Returns:
        List of plugin configurations for the notebook
    """
    # Verify notebook access
    result = await session.execute(
        select(Notebook)
        .join(Workspace)
        .where(Notebook.id == notebook_id, Workspace.owner_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    # Query notebook plugin configs
    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook_id
    )
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


@router.get("/{notebook_id}/plugins/{plugin_id}")
async def get_notebook_plugin_config(
    notebook_id: int,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get plugin configuration for a notebook.
    
    Args:
        notebook_id: Notebook ID
        plugin_id: Plugin ID
        
    Returns:
        Plugin configuration for the notebook
    """
    # Verify notebook access
    result = await session.execute(
        select(Notebook)
        .join(Workspace)
        .where(Notebook.id == notebook_id, Workspace.owner_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    # Query notebook plugin config
    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook_id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        return {
            "plugin_id": plugin_id,
            "enabled": True,  # Default to enabled if no config
            "config": {},
        }
    
    return {
        "plugin_id": config.plugin_id,
        "enabled": config.enabled,
        "config": config.config,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


class NotebookPluginConfigUpdate(BaseModel):
    """Request body for updating notebook plugin configuration."""
    
    enabled: bool | None = None
    config: dict | None = None


@router.put("/{notebook_id}/plugins/{plugin_id}")
async def update_notebook_plugin_config(
    notebook_id: int,
    plugin_id: str,
    request_data: NotebookPluginConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update plugin configuration for a notebook.
    
    Args:
        notebook_id: Notebook ID
        plugin_id: Plugin ID
        request_data: Plugin configuration update
        
    Returns:
        Updated plugin configuration
    """
    # Verify notebook access
    result = await session.execute(
        select(Notebook)
        .join(Workspace)
        .where(Notebook.id == notebook_id, Workspace.owner_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    # Check if config exists
    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook_id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if config:
        # Update existing config
        if request_data.enabled is not None:
            config.enabled = request_data.enabled
        if request_data.config is not None:
            config.config = request_data.config
        session.add(config)
        await session.commit()
        await session.refresh(config)
    else:
        # Create new config
        config = NotebookPluginConfig(
            notebook_id=notebook_id,
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


@router.delete("/{notebook_id}/plugins/{plugin_id}")
async def delete_notebook_plugin_config(
    notebook_id: int,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete plugin configuration for a notebook (revert to workspace defaults).
    
    Args:
        notebook_id: Notebook ID
        plugin_id: Plugin ID
        
    Returns:
        Success message
    """
    # Verify notebook access
    result = await session.execute(
        select(Notebook)
        .join(Workspace)
        .where(Notebook.id == notebook_id, Workspace.owner_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    # Query notebook plugin config
    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook_id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if config:
        await session.delete(config)
        await session.commit()
    
    return {"message": "Plugin configuration deleted successfully"}

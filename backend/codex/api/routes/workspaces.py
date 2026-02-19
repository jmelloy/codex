"""Workspace routes."""

import os
import re
import shutil
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.core.watcher import get_watcher_for_notebook, unregister_watcher
from codex.db.database import DATA_DIRECTORY, get_system_session
from codex.db.models import (
    Agent,
    AgentActionLog,
    AgentCredential,
    AgentSession,
    IntegrationArtifact,
    Notebook,
    NotebookPluginConfig,
    PersonalAccessToken,
    PluginAPILog,
    PluginConfig,
    PluginSecret,
    Task,
    User,
    Workspace,
    WorkspacePermission,
)

# Default plugin enabled state
DEFAULT_PLUGIN_ENABLED = True


class WorkspaceCreate(BaseModel):
    """Request body for creating a workspace."""

    name: str
    path: str | None = None


class ThemeUpdate(BaseModel):
    """Request body for updating theme setting."""

    theme: str


class PluginConfigUpdate(BaseModel):
    """Request body for updating plugin configuration."""
    
    enabled: bool | None = None
    config: dict | None = None


def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    # Convert to lowercase, replace spaces and special chars with hyphens
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "workspace"


router = APIRouter()


@router.get("/")
async def list_workspaces(
    current_user: User = Depends(get_current_active_user), session: AsyncSession = Depends(get_system_session)
) -> list[Workspace]:
    """List all workspaces for the current user."""
    result = await session.execute(select(Workspace).where(Workspace.owner_id == current_user.id))
    return result.scalars().all()


@router.get("/{workspace_identifier}")
async def get_workspace(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Get a specific workspace by slug or ID."""
    return await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)


async def path_exists_in_db(session: AsyncSession, path: str) -> bool:
    """Check if a workspace path already exists in the database."""
    result = await session.execute(select(Workspace).where(Workspace.path == path))
    return result.scalar_one_or_none() is not None


async def slug_exists_in_db(session: AsyncSession, slug: str, owner_id: int) -> bool:
    """Check if a workspace slug already exists for this owner."""
    result = await session.execute(
        select(Workspace).where(Workspace.slug == slug, Workspace.owner_id == owner_id)
    )
    return result.scalar_one_or_none() is not None


async def get_workspace_by_slug_or_id(
    workspace_identifier: str, current_user: User, session: AsyncSession
) -> Workspace:
    """Get workspace by slug or ID.
    
    Args:
        workspace_identifier: Either a slug or numeric ID
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Workspace object
        
    Raises:
        HTTPException if workspace not found
    """
    # Try to parse as integer ID first
    if workspace_identifier.isdigit():
        result = await session.execute(
            select(Workspace).where(
                Workspace.id == int(workspace_identifier), Workspace.owner_id == current_user.id
            )
        )
    else:
        # Treat as slug
        result = await session.execute(
            select(Workspace).where(Workspace.slug == workspace_identifier, Workspace.owner_id == current_user.id)
        )
    
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/")
async def create_workspace(
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Create a new workspace.

    If path is not provided, automatically creates a folder in the data directory
    based on the workspace name.
    """
    name = body.name
    
    # Determine path and slug
    if body.path:
        # Explicit path provided - use it as the workspace directory
        workspace_path = Path(body.path).resolve()  # Convert to absolute path
        
        # Validate the path
        if workspace_path.exists():
            # Path already exists - check if it's in use
            if await path_exists_in_db(session, str(workspace_path)):
                raise HTTPException(status_code=400, detail="Path already in use by another workspace")
        else:
            # Path doesn't exist - verify parent directory exists and is writable
            parent = workspace_path.parent
            if not parent.exists():
                raise HTTPException(
                    status_code=400, 
                    detail=f"Parent directory does not exist: {parent}"
                )
            if not os.access(parent, os.W_OK):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Parent directory is not writable: {parent}"
                )
        
        # Generate slug from the path's basename
        base_slug = slugify(workspace_path.name)
        final_slug = base_slug
        
        # Handle slug collisions
        while await slug_exists_in_db(session, final_slug, current_user.id):
            counter = uuid4().hex[:8]
            final_slug = f"{base_slug}-{counter}"
        
        path = str(workspace_path)
    else:
        # No path provided - auto-generate from workspace name in data directory
        base_slug = slugify(name)
        base_path = Path(DATA_DIRECTORY).resolve() / "workspaces"
        workspace_path = base_path / base_slug
        final_slug = base_slug

        # Handle collisions by checking both filesystem, database path, and slug
        while (
            workspace_path.exists()
            or await path_exists_in_db(session, str(workspace_path))
            or await slug_exists_in_db(session, final_slug, current_user.id)
        ):
            counter = uuid4().hex[:8]
            final_slug = f"{base_slug}-{counter}"
            workspace_path = base_path / final_slug

        path = str(workspace_path)

    # Create the workspace directory
    workspace_dir = Path(path)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    workspace = Workspace(name=name, slug=final_slug, path=path, owner_id=current_user.id)
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace


@router.patch("/{workspace_identifier}/theme")
async def update_workspace_theme(
    workspace_identifier: str,
    body: ThemeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Update the theme setting for a workspace by slug or ID."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    
    workspace.theme_setting = body.theme
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace


@router.get("/{workspace_identifier}/plugins")
async def list_workspace_plugins(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List plugin configurations for a workspace.
    
    Args:
        workspace_identifier: Workspace slug or ID
        
    Returns:
        List of plugin configurations for the workspace
    """
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    
    # Query workspace plugin configs
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace.id
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


@router.get("/{workspace_identifier}/plugins/{plugin_id}")
async def get_workspace_plugin_config(
    workspace_identifier: str,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get plugin configuration for a workspace.
    
    Args:
        workspace_identifier: Workspace slug or ID
        plugin_id: Plugin ID
        
    Returns:
        Plugin configuration for the workspace
    """
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    
    # Query workspace plugin config
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace.id,
        PluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        return {
            "plugin_id": plugin_id,
            "enabled": DEFAULT_PLUGIN_ENABLED,
            "config": {},
        }
    
    return {
        "plugin_id": config.plugin_id,
        "enabled": config.enabled,
        "config": config.config,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


@router.put("/{workspace_identifier}/plugins/{plugin_id}")
async def update_workspace_plugin_config(
    workspace_identifier: str,
    plugin_id: str,
    request_data: PluginConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update plugin configuration for a workspace.
    
    Args:
        workspace_identifier: Workspace slug or ID
        plugin_id: Plugin ID
        request_data: Plugin configuration update
        
    Returns:
        Updated plugin configuration
    """
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    
    # Check if config exists
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace.id,
        PluginConfig.plugin_id == plugin_id,
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
        config = PluginConfig(
            workspace_id=workspace.id,
            plugin_id=plugin_id,
            enabled=request_data.enabled if request_data.enabled is not None else DEFAULT_PLUGIN_ENABLED,
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


@router.delete("/{workspace_identifier}")
async def delete_workspace(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a workspace and all its contents."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)

    # Save path before ORM object may be expired by subsequent queries
    workspace_path = workspace.path
    workspace_id = workspace.id

    # Stop watchers and delete notebook records
    notebooks_result = await session.execute(
        select(Notebook).where(Notebook.workspace_id == workspace_id)
    )
    for notebook in notebooks_result.scalars().all():
        notebook_abs_path = str(Path(workspace_path) / notebook.path)
        watcher = get_watcher_for_notebook(notebook_abs_path)
        if watcher:
            watcher.stop()
            unregister_watcher(watcher)

        # Delete notebook plugin configs
        npc_result = await session.execute(
            select(NotebookPluginConfig).where(NotebookPluginConfig.notebook_id == notebook.id)
        )
        for config in npc_result.scalars().all():
            await session.delete(config)

        await session.delete(notebook)

    # Delete workspace permissions
    wp_result = await session.execute(
        select(WorkspacePermission).where(WorkspacePermission.workspace_id == workspace_id)
    )
    for perm in wp_result.scalars().all():
        await session.delete(perm)

    # Delete tasks
    task_result = await session.execute(
        select(Task).where(Task.workspace_id == workspace_id)
    )
    for task in task_result.scalars().all():
        await session.delete(task)

    # Delete plugin configs and secrets
    pc_result = await session.execute(
        select(PluginConfig).where(PluginConfig.workspace_id == workspace_id)
    )
    for config in pc_result.scalars().all():
        await session.delete(config)

    ps_result = await session.execute(
        select(PluginSecret).where(PluginSecret.workspace_id == workspace_id)
    )
    for secret in ps_result.scalars().all():
        await session.delete(secret)

    pal_result = await session.execute(
        select(PluginAPILog).where(PluginAPILog.workspace_id == workspace_id)
    )
    for log in pal_result.scalars().all():
        await session.delete(log)

    # Delete integration artifacts
    ia_result = await session.execute(
        select(IntegrationArtifact).where(IntegrationArtifact.workspace_id == workspace_id)
    )
    for artifact in ia_result.scalars().all():
        await session.delete(artifact)

    # Delete agents and their related records
    agents_result = await session.execute(
        select(Agent).where(Agent.workspace_id == workspace_id)
    )
    for agent in agents_result.scalars().all():
        # Delete agent action logs (via sessions)
        sessions_result = await session.execute(
            select(AgentSession).where(AgentSession.agent_id == agent.id)
        )
        for agent_session in sessions_result.scalars().all():
            logs_result = await session.execute(
                select(AgentActionLog).where(AgentActionLog.session_id == agent_session.id)
            )
            for log in logs_result.scalars().all():
                await session.delete(log)
            await session.delete(agent_session)

        # Delete agent credentials
        creds_result = await session.execute(
            select(AgentCredential).where(AgentCredential.agent_id == agent.id)
        )
        for cred in creds_result.scalars().all():
            await session.delete(cred)

        await session.delete(agent)

    # Delete personal access tokens scoped to this workspace
    pat_result = await session.execute(
        select(PersonalAccessToken).where(PersonalAccessToken.workspace_id == workspace_id)
    )
    for token in pat_result.scalars().all():
        await session.delete(token)

    # Delete the workspace record
    await session.delete(workspace)
    await session.commit()

    # Delete the workspace directory from disk.
    # Retry with sleep because daemon watcher threads may briefly recreate
    # directories via get_notebook_engine's os.makedirs call.
    ws_dir = Path(workspace_path)
    for _ in range(5):
        if ws_dir.exists():
            shutil.rmtree(ws_dir, ignore_errors=True)
            time.sleep(0.05)
        else:
            break

    return {"message": "Workspace deleted successfully"}


@router.delete("/{workspace_identifier}/plugins/{plugin_id}")
async def delete_workspace_plugin_config(
    workspace_identifier: str,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete plugin configuration for a workspace (revert to defaults).
    
    Args:
        workspace_identifier: Workspace slug or ID
        plugin_id: Plugin ID
        
    Returns:
        Success message
    """
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    
    # Query workspace plugin config
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace.id,
        PluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if config:
        await session.delete(config)
        await session.commit()
    
    return {"message": "Plugin configuration deleted successfully"}

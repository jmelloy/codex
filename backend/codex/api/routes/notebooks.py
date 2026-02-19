"""Notebook routes."""

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
from codex.api.routes.workspaces import get_workspace_by_slug_or_id
from codex.core.watcher import NotebookWatcher, get_watcher_for_notebook, unregister_watcher
from codex.db.database import get_system_session, init_notebook_db
from codex.db.models import Notebook, NotebookPluginConfig, User, Workspace


class NotebookCreate(BaseModel):
    """Request body for creating a notebook."""

    name: str
    description: str | None = None


class NotebookPluginConfigUpdate(BaseModel):
    """Request body for updating notebook plugin configuration."""

    enabled: bool | None = None
    config: dict | None = None


def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "notebook"


async def get_notebook_by_slug_or_id(
    notebook_identifier: str, workspace: Workspace, session: AsyncSession
) -> Notebook:
    """Get notebook by slug or ID within a workspace."""
    if notebook_identifier.isdigit():
        result = await session.execute(
            select(Notebook).where(
                Notebook.id == int(notebook_identifier),
                Notebook.workspace_id == workspace.id
            )
        )
    else:
        result = await session.execute(
            select(Notebook).where(
                Notebook.slug == notebook_identifier,
                Notebook.workspace_id == workspace.id
            )
        )

    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


async def slug_exists_for_workspace(session: AsyncSession, slug: str, workspace_id: int) -> bool:
    """Check if a notebook slug already exists within a workspace."""
    result = await session.execute(
        select(Notebook).where(Notebook.slug == slug, Notebook.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Shared plugin config helpers (used by both main and nested routers)
# ---------------------------------------------------------------------------

def _format_plugin_config(config: NotebookPluginConfig) -> dict:
    """Format a plugin config record for API response."""
    return {
        "plugin_id": config.plugin_id,
        "enabled": config.enabled,
        "config": config.config,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


async def _verify_notebook_access(notebook_id: int, current_user: User, session: AsyncSession) -> Notebook:
    """Verify the current user has access to the notebook."""
    result = await session.execute(
        select(Notebook)
        .join(Workspace)
        .where(Notebook.id == notebook_id, Workspace.owner_id == current_user.id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


async def _list_plugin_configs(notebook_id: int, session: AsyncSession) -> list[dict]:
    """List all plugin configurations for a notebook."""
    stmt = select(NotebookPluginConfig).where(NotebookPluginConfig.notebook_id == notebook_id)
    result = await session.execute(stmt)
    return [_format_plugin_config(c) for c in result.scalars().all()]


async def _get_plugin_config(notebook_id: int, plugin_id: str, session: AsyncSession) -> dict:
    """Get a single plugin configuration for a notebook."""
    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook_id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        return {"plugin_id": plugin_id, "enabled": True, "config": {}}

    return _format_plugin_config(config)


async def _update_plugin_config(
    notebook_id: int, plugin_id: str, request_data: NotebookPluginConfigUpdate, session: AsyncSession
) -> dict:
    """Create or update a plugin configuration for a notebook."""
    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook_id,
        NotebookPluginConfig.plugin_id == plugin_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        if request_data.enabled is not None:
            config.enabled = request_data.enabled
        if request_data.config is not None:
            config.config = request_data.config
    else:
        config = NotebookPluginConfig(
            notebook_id=notebook_id,
            plugin_id=plugin_id,
            enabled=request_data.enabled if request_data.enabled is not None else True,
            config=request_data.config if request_data.config is not None else {},
        )

    session.add(config)
    await session.commit()
    await session.refresh(config)
    return _format_plugin_config(config)


async def _delete_plugin_config(notebook_id: int, plugin_id: str, session: AsyncSession) -> dict:
    """Delete a plugin configuration for a notebook."""
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


# ---------------------------------------------------------------------------
# Main router (notebook ID-based routes)
# ---------------------------------------------------------------------------

router = APIRouter()


@router.get("/{notebook_id}/plugins")
async def list_notebook_plugins(
    notebook_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List plugin configurations for a notebook."""
    await _verify_notebook_access(notebook_id, current_user, session)
    return await _list_plugin_configs(notebook_id, session)


@router.get("/{notebook_id}/plugins/{plugin_id}")
async def get_notebook_plugin_config(
    notebook_id: int,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get plugin configuration for a notebook."""
    await _verify_notebook_access(notebook_id, current_user, session)
    return await _get_plugin_config(notebook_id, plugin_id, session)


@router.put("/{notebook_id}/plugins/{plugin_id}")
async def update_notebook_plugin_config(
    notebook_id: int,
    plugin_id: str,
    request_data: NotebookPluginConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update plugin configuration for a notebook."""
    await _verify_notebook_access(notebook_id, current_user, session)
    return await _update_plugin_config(notebook_id, plugin_id, request_data, session)


@router.delete("/{notebook_id}/plugins/{plugin_id}")
async def delete_notebook_plugin_config(
    notebook_id: int,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete plugin configuration for a notebook (revert to workspace defaults)."""
    await _verify_notebook_access(notebook_id, current_user, session)
    return await _delete_plugin_config(notebook_id, plugin_id, session)


# ---------------------------------------------------------------------------
# Nested router (workspace/notebook slug-based routes)
# ---------------------------------------------------------------------------

nested_router = APIRouter()


@nested_router.get("/")
async def list_notebooks_nested(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all notebooks in a workspace."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)

    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
    notebooks = result.scalars().all()

    return [
        {
            "id": nb.id,
            "slug": nb.slug,
            "name": nb.name,
            "path": nb.path,
            "description": nb.description,
            "created_at": nb.created_at.isoformat() if nb.created_at else None,
            "updated_at": nb.updated_at.isoformat() if nb.updated_at else None,
        }
        for nb in notebooks
    ]


@nested_router.post("/")
async def create_notebook_nested(
    workspace_identifier: str,
    body: NotebookCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create a new notebook."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)

    base_slug = slugify(body.name)
    final_slug = base_slug

    workspace_path = Path(workspace.path).resolve()
    notebook_path = workspace_path / final_slug

    while notebook_path.exists() or await slug_exists_for_workspace(session, final_slug, workspace.id):
        counter = uuid4().hex[:8]
        final_slug = f"{base_slug}-{counter}"
        notebook_path = workspace_path / final_slug

    try:
        notebook_path.mkdir(parents=True, exist_ok=False)

        init_notebook_db(str(notebook_path))

        from codex.core.git_manager import GitManager
        git_manager = GitManager(str(notebook_path))

        notebook = Notebook(
            workspace_id=workspace.id,
            name=body.name,
            slug=final_slug,
            path=final_slug,
            description=body.description
        )
        session.add(notebook)
        await session.commit()
        await session.refresh(notebook)

        NotebookWatcher(str(notebook_path), notebook.id).start()

        return {
            "id": notebook.id,
            "slug": notebook.slug,
            "name": notebook.name,
            "path": notebook.path,
            "description": notebook.description,
            "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
            "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
        }

    except Exception as e:
        if notebook_path.exists():
            import shutil
            shutil.rmtree(notebook_path)
        raise HTTPException(status_code=500, detail=f"Error creating notebook: {str(e)}")


@nested_router.get("/{notebook_identifier}")
async def get_notebook_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a specific notebook by slug or ID."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    return {
        "id": notebook.id,
        "slug": notebook.slug,
        "name": notebook.name,
        "path": notebook.path,
        "description": notebook.description,
        "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
        "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
    }


@nested_router.get("/{notebook_identifier}/indexing-status")
async def get_notebook_indexing_status_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get the indexing status for a notebook."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    from codex.core.watcher import get_active_watchers

    for watcher in get_active_watchers():
        if watcher.notebook_id == notebook.id:
            return watcher.get_indexing_status()

    return {"notebook_id": notebook.id, "status": "not_started", "is_alive": False}


@nested_router.get("/{notebook_identifier}/plugins")
async def list_notebook_plugins_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List plugin configurations for a notebook."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)
    return await _list_plugin_configs(notebook.id, session)


@nested_router.get("/{notebook_identifier}/plugins/{plugin_id}")
async def get_notebook_plugin_config_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get plugin configuration for a notebook."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)
    return await _get_plugin_config(notebook.id, plugin_id, session)


@nested_router.put("/{notebook_identifier}/plugins/{plugin_id}")
async def update_notebook_plugin_config_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    plugin_id: str,
    request_data: NotebookPluginConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Update plugin configuration for a notebook."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)
    return await _update_plugin_config(notebook.id, plugin_id, request_data, session)


@nested_router.delete("/{notebook_identifier}")
async def delete_notebook_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete a notebook and all its contents from disk."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    # Save path before ORM objects are expired by commit
    notebook_dir = Path(workspace.path) / notebook.path

    # Stop the file watcher for this notebook
    watcher = get_watcher_for_notebook(str(notebook_dir))
    if watcher:
        watcher.stop()
        unregister_watcher(watcher)

    # Delete related NotebookPluginConfig records
    result = await session.execute(
        select(NotebookPluginConfig).where(NotebookPluginConfig.notebook_id == notebook.id)
    )
    for config in result.scalars().all():
        await session.delete(config)

    # Delete the notebook record
    await session.delete(notebook)
    await session.commit()

    # Delete the notebook directory from disk.
    # Retry with sleep because daemon watcher threads may briefly recreate
    # directories via get_notebook_engine's os.makedirs call.
    for _ in range(5):
        if notebook_dir.exists():
            shutil.rmtree(notebook_dir, ignore_errors=True)
            time.sleep(0.05)
        else:
            break

    return {"message": "Notebook deleted successfully"}


@nested_router.delete("/{notebook_identifier}/plugins/{plugin_id}")
async def delete_notebook_plugin_config_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete plugin configuration for a notebook (revert to workspace defaults)."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)
    return await _delete_plugin_config(notebook.id, plugin_id, session)

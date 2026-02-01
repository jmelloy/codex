"""API routes for plugin registration and management.

This module implements the frontend-led plugin architecture where:
- Frontend declares which plugins it has via registration endpoints
- Backend stores plugin manifests in the database
- Backend provides plugin state (enabled/disabled, config) at workspace/notebook level
"""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any

from codex.api.auth import get_current_user
from codex.db.database import get_system_session
from codex.db.models import Plugin, User

logger = logging.getLogger(__name__)
router = APIRouter()


class PluginRegistrationRequest(BaseModel):
    """Schema for registering a single plugin."""

    id: str = Field(..., description="Plugin ID (lowercase, numbers, hyphens only)")
    name: str = Field(..., description="Display name")
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    type: str = Field(..., description="Plugin type: view, theme, or integration")
    manifest: dict[str, Any] = Field(
        default_factory=dict, description="Full plugin manifest"
    )


class PluginRegistrationResponse(BaseModel):
    """Schema for plugin registration response."""

    id: str
    name: str
    version: str
    type: str
    registered: bool
    message: str


class BatchRegistrationRequest(BaseModel):
    """Schema for registering multiple plugins at once."""

    plugins: list[PluginRegistrationRequest]


class BatchRegistrationResponse(BaseModel):
    """Schema for batch registration response."""

    registered: int
    updated: int
    failed: int
    results: list[PluginRegistrationResponse]


class PluginResponse(BaseModel):
    """Schema for plugin information."""

    id: str
    name: str
    version: str
    type: str
    enabled: bool
    manifest: dict[str, Any]


def validate_plugin_id(plugin_id: str) -> None:
    """Validate plugin ID format.

    Args:
        plugin_id: Plugin identifier

    Raises:
        ValueError: If plugin ID is invalid
    """
    if not re.match(r"^[a-z0-9-]+$", plugin_id):
        raise ValueError(
            f"Invalid plugin ID: {plugin_id}. "
            "Must contain only lowercase letters, numbers, and hyphens."
        )


def validate_version(version: str) -> None:
    """Validate semantic version format.

    Args:
        version: Version string

    Raises:
        ValueError: If version format is invalid
    """
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise ValueError(
            f"Invalid version: {version}. Must be in semver format (e.g., 1.0.0)."
        )


def validate_plugin_type(plugin_type: str) -> None:
    """Validate plugin type.

    Args:
        plugin_type: Plugin type string

    Raises:
        ValueError: If plugin type is invalid
    """
    valid_types = {"view", "theme", "integration"}
    if plugin_type not in valid_types:
        raise ValueError(
            f"Invalid plugin type: {plugin_type}. Must be one of: {valid_types}"
        )


@router.post("/register", response_model=PluginRegistrationResponse)
async def register_plugin(
    request: PluginRegistrationRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Register a plugin from the frontend.

    This endpoint allows the frontend to declare which plugins it has.
    The backend stores the plugin manifest for later use (e.g., integration API proxying).

    Args:
        request: Plugin registration data

    Returns:
        Registration result
    """
    try:
        validate_plugin_id(request.id)
        validate_version(request.version)
        validate_plugin_type(request.type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if plugin already exists
    stmt = select(Plugin).where(Plugin.plugin_id == request.id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        # Update existing plugin
        existing.name = request.name
        existing.version = request.version
        existing.type = request.type
        existing.manifest = request.manifest
        existing.updated_at = now
        session.add(existing)
        await session.commit()

        return PluginRegistrationResponse(
            id=request.id,
            name=request.name,
            version=request.version,
            type=request.type,
            registered=True,
            message="Plugin updated",
        )
    else:
        # Create new plugin
        plugin = Plugin(
            plugin_id=request.id,
            name=request.name,
            version=request.version,
            type=request.type,
            enabled=True,
            manifest=request.manifest,
            installed_at=now,
            updated_at=now,
        )
        session.add(plugin)
        await session.commit()

        return PluginRegistrationResponse(
            id=request.id,
            name=request.name,
            version=request.version,
            type=request.type,
            registered=True,
            message="Plugin registered",
        )


@router.post("/register-batch", response_model=BatchRegistrationResponse)
async def register_plugins_batch(
    request: BatchRegistrationRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Register multiple plugins at once.

    This endpoint is used during frontend initialization to register
    all available plugins in a single request.

    Args:
        request: Batch of plugins to register

    Returns:
        Batch registration results
    """
    registered = 0
    updated = 0
    failed = 0
    results = []

    for plugin_req in request.plugins:
        try:
            validate_plugin_id(plugin_req.id)
            validate_version(plugin_req.version)
            validate_plugin_type(plugin_req.type)
        except ValueError as e:
            failed += 1
            results.append(
                PluginRegistrationResponse(
                    id=plugin_req.id,
                    name=plugin_req.name,
                    version=plugin_req.version,
                    type=plugin_req.type,
                    registered=False,
                    message=str(e),
                )
            )
            continue

        # Check if plugin already exists
        stmt = select(Plugin).where(Plugin.plugin_id == plugin_req.id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing:
            # Update existing plugin
            existing.name = plugin_req.name
            existing.version = plugin_req.version
            existing.type = plugin_req.type
            existing.manifest = plugin_req.manifest
            existing.updated_at = now
            session.add(existing)
            updated += 1
            results.append(
                PluginRegistrationResponse(
                    id=plugin_req.id,
                    name=plugin_req.name,
                    version=plugin_req.version,
                    type=plugin_req.type,
                    registered=True,
                    message="Plugin updated",
                )
            )
        else:
            # Create new plugin
            plugin = Plugin(
                plugin_id=plugin_req.id,
                name=plugin_req.name,
                version=plugin_req.version,
                type=plugin_req.type,
                enabled=True,
                manifest=plugin_req.manifest,
                installed_at=now,
                updated_at=now,
            )
            session.add(plugin)
            registered += 1
            results.append(
                PluginRegistrationResponse(
                    id=plugin_req.id,
                    name=plugin_req.name,
                    version=plugin_req.version,
                    type=plugin_req.type,
                    registered=True,
                    message="Plugin registered",
                )
            )

    await session.commit()

    return BatchRegistrationResponse(
        registered=registered,
        updated=updated,
        failed=failed,
        results=results,
    )


@router.get("", response_model=list[PluginResponse])
async def list_plugins(
    plugin_type: str | None = None,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """List all registered plugins.

    Args:
        plugin_type: Optional filter by type (view, theme, integration)

    Returns:
        List of registered plugins
    """
    if plugin_type:
        stmt = select(Plugin).where(Plugin.type == plugin_type)
    else:
        stmt = select(Plugin)

    result = await session.execute(stmt)
    plugins = result.scalars().all()

    return [
        PluginResponse(
            id=p.plugin_id,
            name=p.name,
            version=p.version,
            type=p.type,
            enabled=p.enabled,
            manifest=p.manifest,
        )
        for p in plugins
    ]


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(
    plugin_id: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get a specific plugin by ID.

    Args:
        plugin_id: Plugin identifier

    Returns:
        Plugin details
    """
    stmt = select(Plugin).where(Plugin.plugin_id == plugin_id)
    result = await session.execute(stmt)
    plugin = result.scalar_one_or_none()

    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return PluginResponse(
        id=plugin.plugin_id,
        name=plugin.name,
        version=plugin.version,
        type=plugin.type,
        enabled=plugin.enabled,
        manifest=plugin.manifest,
    )


@router.delete("/{plugin_id}")
async def unregister_plugin(
    plugin_id: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Unregister a plugin.

    Args:
        plugin_id: Plugin identifier

    Returns:
        Confirmation message
    """
    stmt = select(Plugin).where(Plugin.plugin_id == plugin_id)
    result = await session.execute(stmt)
    plugin = result.scalar_one_or_none()

    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    await session.delete(plugin)
    await session.commit()

    return {"message": f"Plugin {plugin_id} unregistered"}

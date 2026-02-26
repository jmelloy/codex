"""API routes for plugin registration and management.

This module implements the backend-driven plugin architecture where:
- Backend discovers and loads plugins from the plugins directory
- Backend serves the plugin manifest and compiled assets (JS, CSS, stylesheets)
- Frontend fetches all plugin data exclusively through the backend API
- Backend stores plugin manifests in the database for config management
- Plugins can be downloaded and verified from the Codex Plugin Service
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any

from codex.api.auth import get_current_user
from codex.db.database import get_system_session
from codex.db.models import Plugin, User
from codex.plugins.service_client import PluginServiceClient, PluginVerificationError

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


# --- Plugin Assets routes ---
# These endpoints serve plugin files (manifest, JS, CSS, stylesheets) to the frontend.
# The frontend fetches all plugin assets exclusively through these routes.
# IMPORTANT: These must be defined BEFORE /{plugin_id} to avoid the catch-all
# path parameter intercepting /manifest and /assets/* requests.

# Allowed file extensions for serving plugin assets
_ALLOWED_EXTENSIONS = {".js", ".css", ".map", ".json", ".svg", ".png", ".jpg", ".woff", ".woff2"}

# Content type mapping
_CONTENT_TYPES = {
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


def _get_plugins_dir(request: Request) -> Path:
    """Get the plugins directory from app state."""
    plugins_dir = getattr(request.app.state, "plugins_dir", None)
    if not plugins_dir:
        raise HTTPException(status_code=503, detail="Plugins directory not configured")
    return Path(plugins_dir)


@router.get("/manifest")
async def get_plugins_manifest(request: Request):
    """Serve the unified plugins manifest.

    Returns the plugins.json generated by the build script, which contains
    all plugin metadata and component file mappings. The frontend uses this
    to discover available plugins, themes, views, and blocks.
    """
    plugins_dir = _get_plugins_dir(request)
    manifest_path = plugins_dir / "plugins.json"

    if not manifest_path.exists():
        # Fall back to generating a basic manifest from discovered plugins
        loader = getattr(request.app.state, "plugin_loader", None)
        if loader:
            plugins_list = []
            for plugin in loader.plugins.values():
                plugins_list.append({
                    "id": plugin.id,
                    "name": plugin.name,
                    "version": plugin.version,
                    "type": plugin.type,
                    "manifest": plugin.manifest,
                    "components": {},
                })
            return {
                "version": "1.0.0",
                "buildTime": "",
                "plugins": plugins_list,
            }
        return {"version": "1.0.0", "buildTime": "", "plugins": []}

    try:
        with open(manifest_path) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read plugins manifest: {e}")
        raise HTTPException(status_code=500, detail="Failed to read plugin manifest")


@router.get("/assets/{file_path:path}")
async def serve_plugin_asset(file_path: str, request: Request):
    """Serve a plugin asset file (JS, CSS, stylesheets, images).

    This endpoint serves compiled plugin files from the plugins directory.
    The file_path is relative to the plugins directory, e.g.:
    - weather-api/dist/weather.js
    - cream/styles/main.css
    - chart-example/dist/plugins.css
    """
    plugins_dir = _get_plugins_dir(request)

    # Validate the file path to prevent directory traversal
    try:
        resolved = (plugins_dir / file_path).resolve()
        if not str(resolved).startswith(str(plugins_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Check file extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail=f"File type not allowed: {ext}")

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")

    content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    return FileResponse(resolved, media_type=content_type)


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


# --- Plugin Service routes ---


def _get_service_client(request: Request) -> PluginServiceClient | None:
    """Get the plugin service client from app state, if configured."""
    return getattr(request.app.state, "plugin_service_client", None)


class RemotePluginResponse(BaseModel):
    """Schema for a plugin available from the remote service."""

    id: str
    name: str
    version: str
    type: str
    description: str
    author: str
    sha256: str
    archive_size: int


class SyncResultResponse(BaseModel):
    """Schema for plugin sync results."""

    installed: list[str]
    updated: list[str]
    skipped: list[str]
    failed: list[dict[str, Any]]


class InstallPluginRequest(BaseModel):
    """Schema for installing a plugin from the service."""

    plugin_id: str = Field(..., description="Plugin ID to install")
    expected_sha256: str | None = Field(None, description="Expected SHA-256 checksum (optional, fetched from catalog if omitted)")


class InstallPluginResponse(BaseModel):
    """Schema for plugin install result."""

    plugin_id: str
    version: str
    installed: bool
    verified: bool
    message: str


@router.get("/service/catalog", response_model=list[RemotePluginResponse])
async def list_remote_plugins(
    plugin_type: str | None = None,
    request: Request = None,
    current_user: User = Depends(get_current_user),
):
    """List plugins available from the remote plugin service.

    Returns available plugins along with their SHA-256 checksums for
    integrity verification.
    """
    client = _get_service_client(request)
    if not client:
        raise HTTPException(status_code=503, detail="Plugin service not configured")

    try:
        remote_plugins = await client.fetch_catalog(plugin_type=plugin_type)
    except Exception as e:
        logger.error(f"Failed to fetch plugin catalog: {e}")
        raise HTTPException(status_code=502, detail=f"Plugin service unavailable: {e}")

    return [
        RemotePluginResponse(
            id=p.plugin_id,
            name=p.name,
            version=p.version,
            type=p.plugin_type,
            description=p.description,
            author=p.author,
            sha256=p.sha256,
            archive_size=p.archive_size,
        )
        for p in remote_plugins
    ]


@router.post("/service/install", response_model=InstallPluginResponse)
async def install_plugin_from_service(
    install_request: InstallPluginRequest,
    request: Request = None,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Download, verify, and install a plugin from the remote plugin service.

    The plugin archive is verified against its SHA-256 checksum before
    extraction. After installation, the plugin is registered in the database
    and loaded into the plugin loader.
    """
    client = _get_service_client(request)
    if not client:
        raise HTTPException(status_code=503, detail="Plugin service not configured")

    try:
        # Get plugin info first for the response
        info = await client.get_plugin_info(install_request.plugin_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Plugin not found in service: {e}")

    try:
        # Download and verify
        await client.install_plugin(
            install_request.plugin_id,
            install_request.expected_sha256 or info.sha256,
        )
    except PluginVerificationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to install plugin {install_request.plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Installation failed: {e}")

    # Register the plugin in the database
    now = datetime.now(timezone.utc)
    stmt = select(Plugin).where(Plugin.plugin_id == info.plugin_id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.name = info.name
        existing.version = info.version
        existing.type = info.plugin_type
        existing.manifest = info.manifest
        existing.updated_at = now
        session.add(existing)
    else:
        plugin = Plugin(
            plugin_id=info.plugin_id,
            name=info.name,
            version=info.version,
            type=info.plugin_type,
            enabled=True,
            manifest=info.manifest,
            installed_at=now,
            updated_at=now,
        )
        session.add(plugin)

    await session.commit()

    # Reload the plugin in the loader if available
    loader = getattr(request.app.state, "plugin_loader", None)
    if loader:
        try:
            plugin_dir = client.plugins_dir / info.plugin_id
            loader.load_plugin(plugin_dir)
        except Exception as e:
            logger.warning(f"Plugin installed but failed to load: {e}")

    return InstallPluginResponse(
        plugin_id=info.plugin_id,
        version=info.version,
        installed=True,
        verified=True,
        message=f"Plugin {info.plugin_id} v{info.version} installed and verified (SHA-256: {info.sha256[:16]}...)",
    )


@router.post("/service/sync", response_model=SyncResultResponse)
async def sync_plugins_from_service(
    request: Request = None,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Sync all plugins from the remote plugin service.

    Downloads missing or outdated plugins, verifies their checksums,
    and registers them in the database.
    """
    client = _get_service_client(request)
    if not client:
        raise HTTPException(status_code=503, detail="Plugin service not configured")

    try:
        result = await client.sync_plugins()
    except Exception as e:
        logger.error(f"Plugin sync failed: {e}")
        raise HTTPException(status_code=502, detail=f"Plugin sync failed: {e}")

    # Register all installed/updated plugins in the database
    now = datetime.now(timezone.utc)
    all_synced = result["installed"] + result["updated"]

    for plugin_id in all_synced:
        try:
            info = await client.get_plugin_info(plugin_id)
            stmt = select(Plugin).where(Plugin.plugin_id == plugin_id)
            db_result = await session.execute(stmt)
            existing = db_result.scalar_one_or_none()

            if existing:
                existing.name = info.name
                existing.version = info.version
                existing.type = info.plugin_type
                existing.manifest = info.manifest
                existing.updated_at = now
                session.add(existing)
            else:
                plugin = Plugin(
                    plugin_id=info.plugin_id,
                    name=info.name,
                    version=info.version,
                    type=info.plugin_type,
                    enabled=True,
                    manifest=info.manifest,
                    installed_at=now,
                    updated_at=now,
                )
                session.add(plugin)
        except Exception as e:
            logger.error(f"Failed to register synced plugin {plugin_id}: {e}")

    await session.commit()

    # Reload the plugin loader
    loader = getattr(request.app.state, "plugin_loader", None)
    if loader:
        loader.load_all_plugins()

    return SyncResultResponse(**result)

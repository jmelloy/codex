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

    Supports two path formats:

    1. Versioned: ``{plugin_id}/{version}/{file}``
       Used for compiled components.  The backend resolves the version
       segment to the plugin's ``dist/`` directory on disk and caches the
       result.  If the file is missing locally it attempts to download
       from S3 (when configured).

    2. Direct: ``{plugin_id}/{relative_path}``
       Used for theme stylesheets and other non-versioned assets
       (e.g. ``cream/styles/main.css``).
    """
    plugins_dir = _get_plugins_dir(request)

    # Check file extension first (cheap, avoids filesystem work)
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail=f"File type not allowed: {ext}")

    # Parse the path to detect versioned format: {plugin_id}/{version}/{file}
    parts = file_path.split("/", 2)
    resolved: Path | None = None

    if len(parts) >= 3 and re.match(r"^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$", parts[1]):
        # Versioned path – resolve to {plugin_id}/dist/{file}
        plugin_id, _version, remainder = parts
        candidate = (plugins_dir / plugin_id / "dist" / remainder).resolve()
        plugins_resolved = plugins_dir.resolve()
        if str(candidate).startswith(str(plugins_resolved)) and candidate.is_file():
            resolved = candidate
        else:
            # File not on disk – try downloading from S3
            s3_client = getattr(request.app.state, "s3_plugin_client", None)
            dynamo_registry = getattr(request.app.state, "dynamo_registry", None)
            if s3_client and dynamo_registry:
                try:
                    import asyncio

                    info = await asyncio.to_thread(dynamo_registry.get_plugin, plugin_id)
                    if info:
                        await asyncio.to_thread(s3_client.download_plugin, plugin_id, info.version)
                        candidate = (plugins_dir / plugin_id / "dist" / remainder).resolve()
                        if str(candidate).startswith(str(plugins_resolved)) and candidate.is_file():
                            resolved = candidate
                except Exception as exc:
                    logger.debug(f"S3 plugin sync failed for {plugin_id}: {exc}")

    if resolved is None:
        # Direct path – serve relative to plugins_dir
        try:
            resolved = (plugins_dir / file_path).resolve()
            if not str(resolved).startswith(str(plugins_dir.resolve())):
                raise HTTPException(status_code=403, detail="Access denied")
        except (ValueError, OSError):
            raise HTTPException(status_code=400, detail="Invalid file path")

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


# --- S3/DynamoDB Plugin Registry routes ---


class RemotePluginResponse(BaseModel):
    """Schema for a plugin available from the registry."""

    id: str
    name: str
    version: str
    type: str
    description: str
    author: str
    s3_prefix: str


class SyncResultResponse(BaseModel):
    """Schema for plugin sync results."""

    installed: list[str]
    updated: list[str]
    skipped: list[str]
    failed: list[dict[str, Any]]


class InstallPluginRequest(BaseModel):
    """Schema for installing a plugin from S3."""

    plugin_id: str = Field(..., description="Plugin ID to install")
    version: str | None = Field(None, description="Version to install (latest if omitted)")


class InstallPluginResponse(BaseModel):
    """Schema for plugin install result."""

    plugin_id: str
    version: str
    installed: bool
    message: str


@router.get("/service/catalog", response_model=list[RemotePluginResponse])
async def list_remote_plugins(
    plugin_type: str | None = None,
    request: Request = None,
    current_user: User = Depends(get_current_user),
):
    """List plugins available from the DynamoDB registry.

    Returns plugins indexed from S3 uploads.
    """
    dynamo_registry = getattr(request.app.state, "dynamo_registry", None)
    if not dynamo_registry:
        raise HTTPException(status_code=503, detail="DynamoDB plugin registry not configured")

    try:
        import asyncio

        available = await asyncio.to_thread(dynamo_registry.list_plugins)
    except Exception as e:
        logger.error(f"Failed to scan plugin registry: {e}")
        raise HTTPException(status_code=502, detail=f"Plugin registry unavailable: {e}")

    if plugin_type:
        available = [p for p in available if p.plugin_type == plugin_type]

    return [
        RemotePluginResponse(
            id=p.plugin_id,
            name=p.name,
            version=p.version,
            type=p.plugin_type,
            description=p.description,
            author=p.author,
            s3_prefix=p.s3_prefix,
        )
        for p in available
    ]


@router.post("/service/install", response_model=InstallPluginResponse)
async def install_plugin_from_s3(
    install_request: InstallPluginRequest,
    request: Request = None,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Download and install a plugin from S3.

    Downloads plugin files from the S3 bucket, registers in the database,
    and loads into the plugin loader.
    """
    dynamo_registry = getattr(request.app.state, "dynamo_registry", None)
    s3_plugin_client = getattr(request.app.state, "s3_plugin_client", None)
    if not dynamo_registry:
        raise HTTPException(status_code=503, detail="DynamoDB plugin registry not configured")
    if not s3_plugin_client:
        raise HTTPException(status_code=503, detail="S3 plugin client not configured")

    import asyncio

    try:
        if install_request.version:
            info = await asyncio.to_thread(
                dynamo_registry.get_plugin_version, install_request.plugin_id, install_request.version
            )
        else:
            info = await asyncio.to_thread(dynamo_registry.get_plugin, install_request.plugin_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Plugin not found in registry: {e}")

    if not info:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {install_request.plugin_id}")

    try:
        await asyncio.to_thread(s3_plugin_client.download_plugin, info.plugin_id, info.version)
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
            plugin_dir = s3_plugin_client.plugins_dir / info.plugin_id
            loader.load_plugin(plugin_dir)
        except Exception as e:
            logger.warning(f"Plugin installed but failed to load: {e}")

    return InstallPluginResponse(
        plugin_id=info.plugin_id,
        version=info.version,
        installed=True,
        message=f"Plugin {info.plugin_id} v{info.version} installed from S3",
    )


@router.post("/service/sync", response_model=SyncResultResponse)
async def sync_plugins_from_s3(
    request: Request = None,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Sync all plugins from S3 via the DynamoDB registry.

    Downloads missing or outdated plugins and registers them in the database.
    """
    registry = getattr(request.app.state, "dynamo_registry", None)
    s3_client = getattr(request.app.state, "s3_plugin_client", None)
    if not registry or not s3_client:
        raise HTTPException(status_code=503, detail="Plugin service not configured")

    import asyncio

    try:
        available = await asyncio.to_thread(registry.list_plugins)
    except Exception as e:
        logger.error(f"Plugin sync failed: {e}")
        raise HTTPException(status_code=502, detail=f"Plugin sync failed: {e}")

    installed = []
    updated = []
    skipped = []
    failed = []

    plugins_dir = getattr(request.app.state, "plugins_dir", None)

    for info in available:
        try:
            local_dir = plugins_dir / info.plugin_id if plugins_dir else None
            if local_dir and local_dir.exists():
                # Check if local S3 distribution version matches using a cache marker.
                current_s3_version = None
                version_marker = local_dir / ".s3_version"
                if version_marker.exists():
                    try:
                        current_s3_version = version_marker.read_text(encoding="utf-8").strip()
                    except Exception as e:
                        logger.warning(
                            "Failed to read S3 version marker for plugin %s: %s",
                            info.plugin_id,
                            e,
                        )
                if current_s3_version == str(info.version):
                    skipped.append(info.plugin_id)
                    continue

                await asyncio.to_thread(s3_client.download_plugin, info.plugin_id, info.version)
                if local_dir:
                    version_marker = local_dir / ".s3_version"
                    try:
                        version_marker.write_text(str(info.version), encoding="utf-8")
                    except Exception as e:
                        logger.warning(
                            "Failed to write S3 version marker for plugin %s: %s",
                            info.plugin_id,
                            e,
                        )
                updated.append(info.plugin_id)
            else:
                await asyncio.to_thread(s3_client.download_plugin, info.plugin_id, info.version)
                if local_dir:
                    version_marker = local_dir / ".s3_version"
                    try:
                        version_marker.write_text(str(info.version), encoding="utf-8")
                    except Exception as e:
                        logger.warning(
                            "Failed to write S3 version marker for new plugin %s: %s",
                            info.plugin_id,
                            e,
                        )
                installed.append(info.plugin_id)
        except Exception as e:
            logger.error(f"Failed to sync plugin {info.plugin_id}: {e}")
            failed.append({"id": info.plugin_id, "error": str(e)})

    # Register all installed/updated plugins in the database
    now = datetime.now(timezone.utc)
    for plugin_id in installed + updated:
        try:
            p_info = await asyncio.to_thread(registry.get_plugin, plugin_id)
            if not p_info:
                continue
            stmt = select(Plugin).where(Plugin.plugin_id == plugin_id)
            db_result = await session.execute(stmt)
            existing = db_result.scalar_one_or_none()

            if existing:
                existing.name = p_info.name
                existing.version = p_info.version
                existing.type = p_info.plugin_type
                existing.manifest = p_info.manifest
                existing.updated_at = now
                session.add(existing)
            else:
                plugin = Plugin(
                    plugin_id=p_info.plugin_id,
                    name=p_info.name,
                    version=p_info.version,
                    type=p_info.plugin_type,
                    enabled=True,
                    manifest=p_info.manifest,
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

    return SyncResultResponse(installed=installed, updated=updated, skipped=skipped, failed=failed)

"""API routes for integration plugin management.

This module provides API routes for managing integration plugins.
It now uses the database-stored plugin registry instead of filesystem-based loading.
"""

import base64
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from codex.api.auth import get_current_user
from codex.api.schemas import (
    IntegrationConfigRequest,
    IntegrationConfigResponse,
    IntegrationExecuteRequest,
    IntegrationExecuteResponse,
    IntegrationResponse,
    IntegrationTestRequest,
    IntegrationTestResponse,
    PluginEnableRequest,
    RenderRequest,
    RenderResponse,
)
from codex.db.database import get_system_session
from codex.db.models import IntegrationArtifact, PluginConfig, User, Workspace
from codex.plugins.executor import IntegrationExecutor
from codex.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)
router = APIRouter()

# Create executor instance
executor = IntegrationExecutor()

# Map content types to file extensions
CONTENT_TYPE_EXTENSIONS = {
    "application/json": "json",
    "text/html": "html",
    "text/plain": "txt",
    "text/xml": "xml",
    "application/xml": "xml",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "application/pdf": "pdf",
}


def _compute_parameters_hash(block_type: str, parameters: dict) -> str:
    """Compute a hash of block_type and parameters for cache key."""
    key_data = json.dumps({"block_type": block_type, "parameters": parameters}, sort_keys=True)
    return hashlib.sha256(key_data.encode()).hexdigest()[:32]


def _get_extension_for_content_type(content_type: str) -> str:
    """Get file extension for a content type."""
    return CONTENT_TYPE_EXTENSIONS.get(content_type, "bin")


def _get_artifact_path(workspace_path: str, plugin_id: str, params_hash: str, content_type: str) -> Path:
    """Get the filesystem path for an artifact file."""
    ext = _get_extension_for_content_type(content_type)
    return Path(workspace_path) / ".codex" / "artifacts" / plugin_id / f"{params_hash}.{ext}"


def _get_artifact_relative_path(plugin_id: str, params_hash: str, content_type: str) -> str:
    """Get the relative path for storing in the database."""
    ext = _get_extension_for_content_type(content_type)
    return f".codex/artifacts/{plugin_id}/{params_hash}.{ext}"


def _is_binary_content_type(content_type: str) -> bool:
    """Check if a content type represents binary data."""
    return content_type.startswith("image/") or content_type in (
        "application/octet-stream",
        "application/pdf",
    )


async def _read_artifact_data(artifact_path: Path, content_type: str) -> Any:
    """Read artifact data from filesystem.

    Args:
        artifact_path: Path to the artifact file
        content_type: MIME type of the artifact

    Returns:
        The artifact data (dict for JSON, str for text, base64 str for binary)
        or None if reading failed
    """
    try:
        if not artifact_path.exists():
            return None

        if content_type == "application/json":
            with open(artifact_path, encoding="utf-8") as f:
                return json.load(f)
        elif _is_binary_content_type(content_type):
            with open(artifact_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        else:
            # Text-based content (HTML, plain text, XML, etc.)
            with open(artifact_path, encoding="utf-8") as f:
                return f.read()
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to read artifact from {artifact_path}: {e}")
    return None


async def _write_artifact_data(artifact_path: Path, data: Any, content_type: str) -> bool:
    """Write artifact data to filesystem.

    Args:
        artifact_path: Path to write the artifact
        data: The data to write (dict for JSON, str for text, base64 str for binary)
        content_type: MIME type of the artifact

    Returns:
        True if successful, False otherwise
    """
    try:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        if content_type == "application/json":
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        elif _is_binary_content_type(content_type):
            # Data is base64 encoded, decode and write as binary
            with open(artifact_path, "wb") as f:
                f.write(base64.b64decode(data))
        else:
            # Text-based content
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(data)
        return True
    except OSError as e:
        logger.error(f"Failed to write artifact to {artifact_path}: {e}")
        return False


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    workspace_id: int | None = None,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """List all available integration plugins.

    Args:
        workspace_id: Optional workspace ID to check enabled status

    Returns:
        List of integration plugins with their metadata.
    """
    # Get integrations from database registry
    integrations = await PluginRegistry.get_plugins_with_integrations(session)

    responses = []
    for integration in integrations:
        enabled = True

        # Check workspace-level enabled status
        if workspace_id is not None:
            stmt = select(PluginConfig).where(
                PluginConfig.workspace_id == workspace_id,
                PluginConfig.plugin_id == integration.id,
            )
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()
            if config is not None:
                enabled = config.enabled

        responses.append(
            IntegrationResponse(
                id=integration.id,
                name=integration.name,
                description=integration.description,
                version=integration.version,
                author=integration.author,
                api_type=integration.api_type,
                base_url=integration.base_url,
                auth_method=integration.auth_method,
                enabled=enabled,
            )
        )

    return responses


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific integration plugin.

    Args:
        integration_id: Integration plugin ID

    Returns:
        Integration plugin details
    """
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    return IntegrationResponse(
        id=integration.id,
        name=integration.name,
        description=integration.description,
        version=integration.version,
        author=integration.author,
        api_type=integration.api_type,
        base_url=integration.base_url,
        auth_method=integration.auth_method,
        enabled=True,  # TODO: Check if enabled for this workspace
        properties=integration.properties,
        blocks=integration.blocks,
        endpoints=integration.endpoints,
    )


@router.put("/{integration_id}/enable", response_model=IntegrationResponse)
async def enable_disable_integration(
    integration_id: str,
    workspace_id: int,
    request_data: PluginEnableRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Enable or disable an integration plugin for a workspace.

    Args:
        integration_id: Integration plugin ID
        workspace_id: Workspace ID
        request_data: Enable/disable flag

    Returns:
        Updated integration plugin details
    """
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if config exists
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        # Update existing config
        config.enabled = request_data.enabled
        session.add(config)
        await session.commit()
        await session.refresh(config)
    else:
        # Create new config with default settings
        config = PluginConfig(
            workspace_id=workspace_id,
            plugin_id=integration_id,
            enabled=request_data.enabled,
            config={},
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)

    return IntegrationResponse(
        id=integration.id,
        name=integration.name,
        description=integration.description,
        version=integration.version,
        author=integration.author,
        api_type=integration.api_type,
        base_url=integration.base_url,
        auth_method=integration.auth_method,
        enabled=config.enabled,
        properties=integration.properties,
        blocks=integration.blocks,
        endpoints=integration.endpoints,
    )


@router.get("/{integration_id}/config", response_model=IntegrationConfigResponse)
async def get_integration_config(
    integration_id: str,
    workspace_id: int,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get integration configuration for a workspace.

    Args:
        integration_id: Integration plugin ID
        workspace_id: Workspace ID

    Returns:
        Integration configuration
    """
    # Query plugin config
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        return IntegrationConfigResponse(
            plugin_id=integration_id,
            config={},
        )

    return IntegrationConfigResponse(
        plugin_id=integration_id,
        config=config.config,
    )


@router.put("/{integration_id}/config", response_model=IntegrationConfigResponse)
async def update_integration_config(
    integration_id: str,
    workspace_id: int,
    request_data: IntegrationConfigRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Update integration configuration for a workspace.

    Args:
        integration_id: Integration plugin ID
        workspace_id: Workspace ID
        request_data: Configuration data

    Returns:
        Updated integration configuration
    """
    # Check if config exists
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        # Update existing config
        config.config = request_data.config
        session.add(config)
        await session.commit()
        await session.refresh(config)
    else:
        # Create new config
        config = PluginConfig(
            workspace_id=workspace_id,
            plugin_id=integration_id,
            config=request_data.config,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)

    return IntegrationConfigResponse(
        plugin_id=integration_id,
        config=config.config,
    )


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration_connection(
    integration_id: str,
    request_data: IntegrationTestRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Test integration connection with given configuration.

    Args:
        integration_id: Integration plugin ID
        request_data: Test configuration

    Returns:
        Test result
    """
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    logger.info(f"Testing integration {integration_id}")

    try:
        result = await executor.test_connection(integration, request_data.config)
        return IntegrationTestResponse(
            success=result["success"],
            message=result["message"],
            details={
                "integration_id": integration_id,
                "api_type": integration.api_type,
                "base_url": integration.base_url,
            },
        )
    except Exception as e:
        logger.error(f"Error testing integration {integration_id}: {e}")
        return IntegrationTestResponse(
            success=False,
            message=f"Test failed: {str(e)}",
            details={
                "integration_id": integration_id,
                "error": str(e),
            },
        )


@router.post("/{integration_id}/execute", response_model=IntegrationExecuteResponse)
async def execute_integration_endpoint(
    integration_id: str,
    workspace_id: int,
    request_data: IntegrationExecuteRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Execute an integration endpoint with artifact caching.

    This endpoint now includes the same artifact caching functionality as the
    /render endpoint. Artifacts are saved to the filesystem and tracked in the
    database for future cache hits.

    Args:
        integration_id: Integration plugin ID
        workspace_id: Workspace ID
        request_data: Execution parameters (endpoint_id and parameters)

    Returns:
        Execution result with data
    """
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    # Get workspace to determine artifact storage path
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Get workspace configuration
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=400,
            detail="Integration not configured for this workspace",
        )

    logger.info(
        f"Executing endpoint {request_data.endpoint_id} for integration {integration_id}"
    )

    try:
        execution_result = await executor.execute_endpoint(
            integration,
            request_data.endpoint_id,
            config.config,
            request_data.parameters or {},
        )

        # Compute cache key for artifact storage
        # For /execute, we use endpoint_id in place of block_type to maintain
        # consistency with /render's caching mechanism
        params_hash = _compute_parameters_hash(request_data.endpoint_id, request_data.parameters or {})

        # Get artifact path based on content type
        artifact_path = _get_artifact_path(
            workspace.path, integration_id, params_hash, execution_result.content_type
        )
        relative_path = _get_artifact_relative_path(
            integration_id, params_hash, execution_result.content_type
        )

        # Write artifact to filesystem
        if not await _write_artifact_data(artifact_path, execution_result.data, execution_result.content_type):
            logger.warning(f"Failed to cache artifact for {integration_id}/{request_data.endpoint_id}")

        # Update database record
        now = datetime.now(UTC)

        # Check if artifact already exists (update) or create new one
        stmt = select(IntegrationArtifact).where(
            IntegrationArtifact.workspace_id == workspace_id,
            IntegrationArtifact.plugin_id == integration_id,
            IntegrationArtifact.block_type == request_data.endpoint_id,
            IntegrationArtifact.parameters_hash == params_hash,
        )
        result = await session.execute(stmt)
        artifact = result.scalar_one_or_none()

        # For execute endpoint, we don't have a block config with cache_ttl
        # so we set expires_at to None (never expires unless manually cleared)
        if artifact:
            artifact.artifact_path = relative_path
            artifact.content_type = execution_result.content_type
            artifact.fetched_at = now
            artifact.expires_at = None
        else:
            artifact = IntegrationArtifact(
                workspace_id=workspace_id,
                plugin_id=integration_id,
                block_type=request_data.endpoint_id,
                parameters_hash=params_hash,
                artifact_path=relative_path,
                content_type=execution_result.content_type,
                fetched_at=now,
                expires_at=None,
            )

        session.add(artifact)
        await session.commit()

        # For execute endpoint, we return data directly
        # Non-JSON data will be returned as string (text) or base64 (binary)
        data = execution_result.data
        if not isinstance(data, dict):
            # Wrap non-dict data in a response dict
            data = {"content": data, "content_type": execution_result.content_type}
        return IntegrationExecuteResponse(
            success=True,
            data=data,
            error=None,
        )
    except ValueError as e:
        logger.error(f"Validation error executing integration: {e}")
        return IntegrationExecuteResponse(
            success=False,
            data=None,
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Error executing integration: {e}")
        return IntegrationExecuteResponse(
            success=False,
            data=None,
            error=f"Execution failed: {str(e)}",
        )


@router.get("/{integration_id}/blocks")
async def get_integration_blocks(
    integration_id: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get available block types for an integration.

    Args:
        integration_id: Integration plugin ID

    Returns:
        List of available blocks
    """
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "integration_id": integration_id,
        "blocks": integration.blocks,
    }


@router.post("/{integration_id}/render", response_model=RenderResponse)
async def render_integration_block(
    integration_id: str,
    workspace_id: int,
    request_data: RenderRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Render an integration block by fetching data from the integration API.

    This endpoint is the primary way for the frontend to request data for
    custom blocks (e.g., weather, github-issue, link-preview). The backend:

    1. Checks cache for pre-fetched data (stored in filesystem)
    2. If cache miss or stale, executes the API call through the integration
    3. Returns raw data for the frontend to render

    The frontend is responsible for rendering the data - the backend does NOT
    render markdown or HTML. This keeps rendering logic in one place (frontend).

    Artifacts are stored in the filesystem at:
      {workspace_path}/.codex/artifacts/{plugin_id}/{hash}.{ext}
    where ext is determined by content_type (json, html, txt, bin, etc.)

    Args:
        integration_id: Integration plugin ID
        workspace_id: Workspace ID for configuration lookup
        request_data: Block type, parameters, and cache preference

    Returns:
        Raw data from the integration API for frontend rendering
    """
    # Get the integration plugin
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    # Get workspace to determine artifact storage path
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Verify the block_type is supported by this integration
    block_config = None
    for block in integration.blocks or []:
        if block.get("id") == request_data.block_type:
            block_config = block
            break

    if not block_config:
        return RenderResponse(
            success=False,
            error=f"Block type '{request_data.block_type}' not supported by integration '{integration_id}'",
        )

    # Compute cache key
    params_hash = _compute_parameters_hash(request_data.block_type, request_data.parameters)

    # Check cache if requested
    if request_data.use_cache:
        stmt = select(IntegrationArtifact).where(
            IntegrationArtifact.workspace_id == workspace_id,
            IntegrationArtifact.plugin_id == integration_id,
            IntegrationArtifact.block_type == request_data.block_type,
            IntegrationArtifact.parameters_hash == params_hash,
        )
        result = await session.execute(stmt)
        cached_artifact = result.scalar_one_or_none()

        if cached_artifact:
            # Check if cache is still valid (not expired)
            now = datetime.now(UTC)
            if cached_artifact.expires_at is None or cached_artifact.expires_at > now:
                # Read data from filesystem using stored content type
                artifact_path = Path(workspace.path) / cached_artifact.artifact_path
                cached_data = await _read_artifact_data(artifact_path, cached_artifact.content_type)
                if cached_data is not None:
                    logger.debug(f"Cache hit for {integration_id}/{request_data.block_type}")
                    return RenderResponse(
                        success=True,
                        data=cached_data,
                        content_type=cached_artifact.content_type,
                        cached=True,
                        fetched_at=cached_artifact.fetched_at.isoformat(),
                    )
                else:
                    # File missing, need to re-fetch
                    logger.warning(f"Artifact file missing for {integration_id}/{request_data.block_type}")

    # Get workspace configuration for the integration
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        return RenderResponse(
            success=False,
            error="Integration not configured for this workspace",
        )

    # Find the endpoint to execute for this block type
    endpoint_id = block_config.get("endpoint")
    if not endpoint_id:
        return RenderResponse(
            success=False,
            error=f"Block type '{request_data.block_type}' has no associated endpoint",
        )

    logger.info(f"Rendering block {request_data.block_type} via endpoint {endpoint_id}")

    try:
        # Execute the integration API call
        execution_result = await executor.execute_endpoint(
            integration,
            endpoint_id,
            config.config,
            request_data.parameters,
        )

        # Get artifact path based on content type
        artifact_path = _get_artifact_path(
            workspace.path, integration_id, params_hash, execution_result.content_type
        )
        relative_path = _get_artifact_relative_path(
            integration_id, params_hash, execution_result.content_type
        )

        # Write artifact to filesystem
        if not await _write_artifact_data(artifact_path, execution_result.data, execution_result.content_type):
            logger.warning(f"Failed to cache artifact for {integration_id}/{request_data.block_type}")

        # Update database record
        now = datetime.now(UTC)

        # Check if artifact already exists (update) or create new one
        stmt = select(IntegrationArtifact).where(
            IntegrationArtifact.workspace_id == workspace_id,
            IntegrationArtifact.plugin_id == integration_id,
            IntegrationArtifact.block_type == request_data.block_type,
            IntegrationArtifact.parameters_hash == params_hash,
        )
        result = await session.execute(stmt)
        artifact = result.scalar_one_or_none()

        cache_ttl = block_config.get("cache_ttl")
        expires_at = now + timedelta(seconds=cache_ttl) if cache_ttl else None

        if artifact:
            artifact.artifact_path = relative_path
            artifact.content_type = execution_result.content_type
            artifact.fetched_at = now
            artifact.expires_at = expires_at
        else:
            artifact = IntegrationArtifact(
                workspace_id=workspace_id,
                plugin_id=integration_id,
                block_type=request_data.block_type,
                parameters_hash=params_hash,
                artifact_path=relative_path,
                content_type=execution_result.content_type,
                fetched_at=now,
                expires_at=expires_at,
            )

        session.add(artifact)
        await session.commit()

        return RenderResponse(
            success=True,
            data=execution_result.data,
            content_type=execution_result.content_type,
            cached=False,
            fetched_at=now.isoformat(),
        )

    except ValueError as e:
        logger.error(f"Validation error rendering block: {e}")
        return RenderResponse(
            success=False,
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Error rendering block: {e}")
        return RenderResponse(
            success=False,
            error=f"Render failed: {str(e)}",
        )

"""API routes for integration plugin management.

This module provides API routes for managing integration plugins.
It now uses the database-stored plugin registry instead of filesystem-based loading.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta

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
from codex.db.models import IntegrationArtifact, PluginConfig, User
from codex.plugins.executor import IntegrationExecutor
from codex.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)
router = APIRouter()

# Create executor instance
executor = IntegrationExecutor()


def _compute_parameters_hash(block_type: str, parameters: dict) -> str:
    """Compute a hash of block_type and parameters for cache key."""
    key_data = json.dumps({"block_type": block_type, "parameters": parameters}, sort_keys=True)
    return hashlib.sha256(key_data.encode()).hexdigest()[:32]


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
    """Execute an integration endpoint.

    Args:
        integration_id: Integration plugin ID
        workspace_id: Workspace ID
        request_data: Execution parameters

    Returns:
        Execution result
    """
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

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
        data = await executor.execute_endpoint(
            integration,
            request_data.endpoint_id,
            config.config,
            request_data.parameters,
        )
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

    1. Checks cache for pre-fetched data
    2. If cache miss or stale, executes the API call through the integration
    3. Returns raw data for the frontend to render

    The frontend is responsible for rendering the data - the backend does NOT
    render markdown or HTML. This keeps rendering logic in one place (frontend).

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
                logger.debug(f"Cache hit for {integration_id}/{request_data.block_type}")
                return RenderResponse(
                    success=True,
                    data=cached_artifact.data,
                    cached=True,
                    fetched_at=cached_artifact.fetched_at.isoformat(),
                )

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
        data = await executor.execute_endpoint(
            integration,
            endpoint_id,
            config.config,
            request_data.parameters,
        )

        # Cache the result
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

        if artifact:
            artifact.data = data
            artifact.fetched_at = now
            # Reset expiration based on block config (if specified)
            cache_ttl = block_config.get("cache_ttl")
            if cache_ttl:
                artifact.expires_at = now + timedelta(seconds=cache_ttl)
            else:
                artifact.expires_at = None
        else:
            cache_ttl = block_config.get("cache_ttl")
            expires_at = None
            if cache_ttl:
                expires_at = now + timedelta(seconds=cache_ttl)

            artifact = IntegrationArtifact(
                workspace_id=workspace_id,
                plugin_id=integration_id,
                block_type=request_data.block_type,
                parameters_hash=params_hash,
                data=data,
                fetched_at=now,
                expires_at=expires_at,
            )

        session.add(artifact)
        await session.commit()

        return RenderResponse(
            success=True,
            data=data,
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

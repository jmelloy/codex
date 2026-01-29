"""API routes for integration plugin management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
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
)
from codex.db.database import get_system_session
from codex.db.models import PluginConfig, User
from codex.plugins.executor import IntegrationExecutor
from codex.plugins.models import IntegrationPlugin

logger = logging.getLogger(__name__)
router = APIRouter()

# Create executor instance
executor = IntegrationExecutor()


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """List all available integration plugins.

    Returns:
        List of integration plugins with their metadata.
    """
    loader = request.app.state.plugin_loader
    integrations = loader.get_plugins_by_type("integration")

    responses = []
    for integration in integrations:
        if isinstance(integration, IntegrationPlugin):
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
                    enabled=True,  # TODO: Check if enabled for this workspace
                )
            )

    return responses


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific integration plugin.

    Args:
        integration_id: Integration plugin ID

    Returns:
        Integration plugin details
    """
    loader = request.app.state.plugin_loader
    integration = loader.get_plugin(integration_id)

    if not integration or not isinstance(integration, IntegrationPlugin):
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
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Test integration connection with given configuration.

    Args:
        integration_id: Integration plugin ID
        request_data: Test configuration

    Returns:
        Test result
    """
    loader = request.app.state.plugin_loader
    integration = loader.get_plugin(integration_id)

    if not integration or not isinstance(integration, IntegrationPlugin):
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
    request: Request,
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
    loader = request.app.state.plugin_loader
    integration = loader.get_plugin(integration_id)

    if not integration or not isinstance(integration, IntegrationPlugin):
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
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get available block types for an integration.

    Args:
        integration_id: Integration plugin ID

    Returns:
        List of available blocks
    """
    loader = request.app.state.plugin_loader
    integration = loader.get_plugin(integration_id)

    if not integration or not isinstance(integration, IntegrationPlugin):
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "integration_id": integration_id,
        "blocks": integration.blocks,
    }

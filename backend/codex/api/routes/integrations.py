"""API routes for integration plugin management.

This module provides API routes for managing integration plugins.
It now uses the database-stored plugin registry instead of filesystem-based loading.
"""

import base64
import hashlib
import json
import logging
from datetime import UTC, datetime
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
)
from codex.db.database import get_system_session
from codex.db.models import IntegrationArtifact, PluginConfig, User, Workspace
from codex.plugins.executor import IntegrationExecutor
from codex.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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
    """Read artifact data from filesystem."""
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
            with open(artifact_path, encoding="utf-8") as f:
                return f.read()
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to read artifact from {artifact_path}: {e}")
    return None


async def _write_artifact_data(artifact_path: Path, data: Any, content_type: str) -> bool:
    """Write artifact data to filesystem."""
    try:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        if content_type == "application/json":
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        elif _is_binary_content_type(content_type):
            with open(artifact_path, "wb") as f:
                f.write(base64.b64decode(data))
        else:
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(data)
        return True
    except OSError as e:
        logger.error(f"Failed to write artifact to {artifact_path}: {e}")
        return False


async def _list_integrations_for_workspace(
    workspace_id: int | None, session: AsyncSession
) -> list[IntegrationResponse]:
    """Core logic: list integrations with workspace-level enabled status."""
    integrations = await PluginRegistry.get_plugins_with_integrations(session)

    responses = []
    for integration in integrations:
        enabled = True

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


async def _enable_disable_integration(
    integration_id: str, workspace_id: int, request_data: PluginEnableRequest, session: AsyncSession
) -> IntegrationResponse:
    """Core logic: enable or disable an integration for a workspace."""
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.enabled = request_data.enabled
    else:
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


async def _get_integration_config(
    integration_id: str, workspace_id: int, session: AsyncSession
) -> IntegrationConfigResponse:
    """Core logic: get integration config for a workspace."""
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        return IntegrationConfigResponse(plugin_id=integration_id, config={})

    return IntegrationConfigResponse(plugin_id=integration_id, config=config.config)


async def _update_integration_config(
    integration_id: str, workspace_id: int, request_data: IntegrationConfigRequest, session: AsyncSession
) -> IntegrationConfigResponse:
    """Core logic: update integration config for a workspace."""
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.config = request_data.config
    else:
        config = PluginConfig(
            workspace_id=workspace_id,
            plugin_id=integration_id,
            config=request_data.config,
        )

    session.add(config)
    await session.commit()
    await session.refresh(config)

    return IntegrationConfigResponse(plugin_id=integration_id, config=config.config)


async def _execute_integration(
    integration_id: str, workspace_id: int, request_data: IntegrationExecuteRequest, session: AsyncSession
) -> IntegrationExecuteResponse:
    """Core logic: execute an integration endpoint with artifact caching."""
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    # Get workspace for artifact path
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
    configuration = result.scalar_one_or_none()

    logger.info(
        f"Executing endpoint {request_data.endpoint_id} for integration {integration_id}"
    )

    # Compute cache key
    params_hash = _compute_parameters_hash(request_data.endpoint_id, request_data.parameters or {})

    # Check for existing cached artifact
    stmt = select(IntegrationArtifact).where(
        IntegrationArtifact.workspace_id == workspace_id,
        IntegrationArtifact.plugin_id == integration_id,
        IntegrationArtifact.block_type == request_data.endpoint_id,
        IntegrationArtifact.parameters_hash == params_hash,
    )
    result = await session.execute(stmt)
    existing_artifact = result.scalar_one_or_none()

    now = datetime.now(UTC)

    # Return cached artifact if valid
    if existing_artifact:
        artifact_path = Path(workspace.path) / existing_artifact.artifact_path
        is_expired = existing_artifact.expires_at is not None and existing_artifact.expires_at < now

        if not is_expired and artifact_path.exists():
            cached_data = await _read_artifact_data(artifact_path, existing_artifact.content_type)
            if cached_data is not None:
                logger.info(
                    f"Returning cached artifact for {integration_id}/{request_data.endpoint_id}"
                )
                if not isinstance(cached_data, dict):
                    cached_data = {"content": cached_data, "content_type": existing_artifact.content_type}
                return IntegrationExecuteResponse(success=True, data=cached_data, error=None)

    try:
        execution_result = await executor.execute_endpoint(
            integration,
            request_data.endpoint_id,
            configuration.config if configuration else {},
            request_data.parameters or {},
        )

        # Cache the result
        artifact_path = _get_artifact_path(
            workspace.path, integration_id, params_hash, execution_result.content_type
        )
        relative_path = _get_artifact_relative_path(
            integration_id, params_hash, execution_result.content_type
        )

        if not await _write_artifact_data(artifact_path, execution_result.data, execution_result.content_type):
            logger.warning(f"Failed to cache artifact for {integration_id}/{request_data.endpoint_id}")

        # Update or create database record
        if existing_artifact:
            existing_artifact.artifact_path = relative_path
            existing_artifact.content_type = execution_result.content_type
            existing_artifact.fetched_at = now
            existing_artifact.expires_at = None
            artifact = existing_artifact
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

        data = execution_result.data
        if not isinstance(data, dict):
            data = {"content": data, "content_type": execution_result.content_type}
        return IntegrationExecuteResponse(success=True, data=data, error=None)
    except ValueError as e:
        logger.error(f"Validation error executing integration: {e}")
        return IntegrationExecuteResponse(success=False, data=None, error=str(e))
    except Exception as e:
        logger.error(f"Error executing integration: {e}")
        return IntegrationExecuteResponse(success=False, data=None, error=f"Execution failed: {str(e)}")


# ---------------------------------------------------------------------------
# Main router (query-param based routes under /api/v1/plugins/integrations)
# ---------------------------------------------------------------------------

router = APIRouter()


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    workspace_id: int | None = None,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """List all available integration plugins."""
    return await _list_integrations_for_workspace(workspace_id, session)


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific integration plugin."""
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
        enabled=True,
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
    """Enable or disable an integration plugin for a workspace."""
    return await _enable_disable_integration(integration_id, workspace_id, request_data, session)


@router.get("/{integration_id}/config", response_model=IntegrationConfigResponse)
async def get_integration_config(
    integration_id: str,
    workspace_id: int,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get integration configuration for a workspace."""
    return await _get_integration_config(integration_id, workspace_id, session)


@router.put("/{integration_id}/config", response_model=IntegrationConfigResponse)
async def update_integration_config(
    integration_id: str,
    workspace_id: int,
    request_data: IntegrationConfigRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Update integration configuration for a workspace."""
    return await _update_integration_config(integration_id, workspace_id, request_data, session)


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
async def test_integration_connection(
    integration_id: str,
    request_data: IntegrationTestRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Test integration connection with given configuration."""
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
    """Execute an integration endpoint with artifact caching."""
    # Validate workspace config exists
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == workspace_id,
        PluginConfig.plugin_id == integration_id,
    )
    result = await session.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Integration not configured for this workspace",
        )

    return await _execute_integration(integration_id, workspace_id, request_data, session)


@router.get("/{integration_id}/blocks")
async def get_integration_blocks(
    integration_id: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get available block types for an integration."""
    integration = await PluginRegistry.get_plugin(session, integration_id)

    if not integration or not integration.has_integration():
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "integration_id": integration_id,
        "blocks": integration.blocks,
    }


# ---------------------------------------------------------------------------
# Nested router (workspace/notebook scoped routes)
# ---------------------------------------------------------------------------

nested_router = APIRouter()


@nested_router.get("")
async def list_integrations_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """List all available integration plugins for a notebook."""
    from codex.api.routes.notebooks import get_notebook_by_slug_or_id
    from codex.api.routes.workspaces import get_workspace_by_slug_or_id

    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    return await _list_integrations_for_workspace(workspace.id, session)


@nested_router.put("/{integration_id}/enable")
async def enable_disable_integration_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    integration_id: str,
    request_data: PluginEnableRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Enable or disable an integration plugin for a workspace (via notebook route)."""
    from codex.api.routes.notebooks import get_notebook_by_slug_or_id
    from codex.api.routes.workspaces import get_workspace_by_slug_or_id

    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    return await _enable_disable_integration(integration_id, workspace.id, request_data, session)


@nested_router.get("/{integration_id}/config")
async def get_integration_config_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    integration_id: str,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Get integration configuration for a workspace (via notebook route)."""
    from codex.api.routes.notebooks import get_notebook_by_slug_or_id
    from codex.api.routes.workspaces import get_workspace_by_slug_or_id

    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    return await _get_integration_config(integration_id, workspace.id, session)


@nested_router.put("/{integration_id}/config")
async def update_integration_config_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    integration_id: str,
    request_data: IntegrationConfigRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Update integration configuration for a workspace (via notebook route)."""
    from codex.api.routes.notebooks import get_notebook_by_slug_or_id
    from codex.api.routes.workspaces import get_workspace_by_slug_or_id

    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    return await _update_integration_config(integration_id, workspace.id, request_data, session)


@nested_router.post("/{integration_id}/execute")
async def execute_integration_endpoint_nested(
    workspace_identifier: str,
    notebook_identifier: str,
    integration_id: str,
    request_data: IntegrationExecuteRequest,
    session: AsyncSession = Depends(get_system_session),
    current_user: User = Depends(get_current_user),
):
    """Execute an integration endpoint with artifact caching (via notebook route)."""
    from codex.api.routes.notebooks import get_notebook_by_slug_or_id
    from codex.api.routes.workspaces import get_workspace_by_slug_or_id

    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    await get_notebook_by_slug_or_id(notebook_identifier, workspace, session)

    return await _execute_integration(integration_id, workspace.id, request_data, session)

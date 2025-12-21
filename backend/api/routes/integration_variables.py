"""API routes for integration variables.

These endpoints allow managing default variables for integrations (plugins).
Variables can store default values like server addresses, headers, or
database connection strings.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.utils import get_workspace_path
from core.workspace import Workspace
from integrations import IntegrationRegistry

router = APIRouter()


def get_workspace(workspace_path: Optional[str] = None) -> Workspace:
    """Get a workspace instance."""
    return Workspace.load(get_workspace_path(workspace_path))


class IntegrationVariableCreate(BaseModel):
    """Request body for creating/updating an integration variable."""

    workspace_path: Optional[str] = None
    integration_type: str
    name: str
    value: Any
    description: Optional[str] = None
    is_secret: bool = False


class IntegrationVariableUpdate(BaseModel):
    """Request body for updating an integration variable."""

    workspace_path: Optional[str] = None
    value: Any
    description: Optional[str] = None
    is_secret: Optional[bool] = None


class IntegrationVariableResponse(BaseModel):
    """Response body for integration variable."""

    id: int
    integration_type: str
    name: str
    value: Any
    description: Optional[str]
    is_secret: bool
    created_at: Optional[str]
    updated_at: Optional[str]


@router.get("")
async def list_integration_variables(
    integration_type: Optional[str] = None,
    workspace_path: Optional[str] = Query(None),
) -> list[IntegrationVariableResponse]:
    """List all integration variables.

    Args:
        integration_type: Optional filter by integration type
        workspace_path: Optional workspace path
    """
    ws = get_workspace(workspace_path)
    variables = ws.db_manager.list_integration_variables(integration_type)
    return variables


@router.get("/types")
async def list_integration_types() -> list[str]:
    """List all registered integration types."""
    return IntegrationRegistry.list_integrations()


@router.post("", status_code=201)
async def create_integration_variable(
    body: IntegrationVariableCreate,
) -> IntegrationVariableResponse:
    """Create or update an integration variable.

    If a variable with the same integration_type and name already exists,
    it will be updated.

    Example:
        Set a default base URL for API calls:
        ```json
        {
            "integration_type": "api_call",
            "name": "base_url",
            "value": "https://api.example.com",
            "description": "Default API server"
        }
        ```

        Set default headers:
        ```json
        {
            "integration_type": "api_call",
            "name": "headers",
            "value": {"Authorization": "Bearer token123"},
            "is_secret": true
        }
        ```

        Set default database connection:
        ```json
        {
            "integration_type": "database_query",
            "name": "connection_string",
            "value": "postgresql://user:pass@localhost/db",
            "is_secret": true
        }
        ```
    """
    # Validate integration type exists
    if not IntegrationRegistry.has_integration(body.integration_type):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown integration type: {body.integration_type}. "
            f"Available types: {IntegrationRegistry.list_integrations()}",
        )

    ws = get_workspace(body.workspace_path)
    variable = ws.db_manager.set_integration_variable(
        integration_type=body.integration_type,
        name=body.name,
        value=body.value,
        description=body.description,
        is_secret=body.is_secret,
    )
    return variable


@router.get("/{integration_type}/{name}")
async def get_integration_variable(
    integration_type: str,
    name: str,
    workspace_path: Optional[str] = Query(None),
) -> IntegrationVariableResponse:
    """Get a specific integration variable."""
    ws = get_workspace(workspace_path)
    variable = ws.db_manager.get_integration_variable(integration_type, name)
    if not variable:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{name}' not found for integration '{integration_type}'",
        )
    return variable


@router.put("/{integration_type}/{name}")
async def update_integration_variable(
    integration_type: str,
    name: str,
    body: IntegrationVariableUpdate,
) -> IntegrationVariableResponse:
    """Update an existing integration variable."""
    ws = get_workspace(body.workspace_path)

    # Check if variable exists
    existing = ws.db_manager.get_integration_variable(integration_type, name)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{name}' not found for integration '{integration_type}'",
        )

    # Update the variable
    variable = ws.db_manager.set_integration_variable(
        integration_type=integration_type,
        name=name,
        value=body.value,
        description=(
            body.description
            if body.description is not None
            else existing.get("description")
        ),
        is_secret=(
            body.is_secret
            if body.is_secret is not None
            else existing.get("is_secret", False)
        ),
    )
    return variable


@router.delete("/{integration_type}/{name}", status_code=204)
async def delete_integration_variable(
    integration_type: str,
    name: str,
    workspace_path: Optional[str] = Query(None),
):
    """Delete an integration variable."""
    ws = get_workspace(workspace_path)
    success = ws.db_manager.delete_integration_variable(integration_type, name)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{name}' not found for integration '{integration_type}'",
        )


@router.get("/{integration_type}")
async def get_integration_variables_for_type(
    integration_type: str,
    workspace_path: Optional[str] = Query(None),
) -> dict[str, Any]:
    """Get all variables for a specific integration type as a dictionary.

    Returns a dictionary mapping variable names to their values,
    suitable for understanding what defaults are configured.
    """
    ws = get_workspace(workspace_path)
    return ws.db_manager.get_integration_variables(integration_type)

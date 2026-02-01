"""API schemas for request/response validation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool
    theme_setting: str | None = None


class ThemeUpdate(BaseModel):
    """Schema for updating user theme setting."""

    theme: str


class ThemeResponse(BaseModel):
    """Schema for theme information."""

    id: str
    name: str
    label: str
    description: str
    className: str
    category: str
    version: str
    author: str


class IntegrationResponse(BaseModel):
    """Schema for integration plugin information."""

    id: str
    name: str
    description: str
    version: str
    author: str
    api_type: str
    base_url: str | None = None
    auth_method: str | None = None
    enabled: bool = True
    properties: list[dict[str, Any]] | None = None
    blocks: list[dict[str, Any]] | None = None
    endpoints: list[dict[str, Any]] | None = None


class IntegrationConfigRequest(BaseModel):
    """Schema for updating integration configuration."""

    config: dict[str, Any]


class PluginEnableRequest(BaseModel):
    """Schema for enabling/disabling a plugin."""

    enabled: bool


class IntegrationConfigResponse(BaseModel):
    """Schema for integration configuration response."""

    plugin_id: str
    config: dict[str, Any]


class IntegrationTestRequest(BaseModel):
    """Schema for testing integration connection."""

    config: dict[str, Any] | None = None


class IntegrationTestResponse(BaseModel):
    """Schema for integration test result."""

    success: bool
    message: str
    details: dict[str, Any] | None = None


class IntegrationExecuteRequest(BaseModel):
    """Schema for executing integration endpoint."""

    endpoint_id: str
    parameters: dict[str, Any] | None = None


class IntegrationExecuteResponse(BaseModel):
    """Schema for integration execution result."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class ViewResponse(BaseModel):
    """Schema for view plugin information."""

    id: str
    name: str
    description: str
    icon: str
    plugin_id: str
    plugin_name: str
    config_schema: dict[str, Any]


class RenderRequest(BaseModel):
    """Schema for rendering an integration block.

    The frontend sends this request to fetch data for a custom block.
    The backend executes the integration API call and returns raw data
    for the frontend to render (frontend-driven rendering).
    """

    block_type: str  # e.g., "weather", "github-issue", "link-preview"
    parameters: dict[str, Any] = Field(default_factory=dict)
    use_cache: bool = True  # Whether to use cached data if available


class RenderResponse(BaseModel):
    """Schema for render response.

    Returns raw data from the integration API for the frontend to render.
    The backend does NOT render HTML/markdown - that's the frontend's job.
    """

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    cached: bool = False  # Whether data was served from cache
    fetched_at: str | None = None  # ISO timestamp when data was fetched

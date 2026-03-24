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


class ChangePasswordRequest(BaseModel):
    """Schema for changing password (authenticated)."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting a password reset."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password with a token."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


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

    Data can be:
    - dict/list for JSON responses (content_type: application/json)
    - str for HTML/text responses (content_type: text/html, text/plain)
    - base64-encoded str for binary data (content_type: image/*, application/octet-stream)
    """

    success: bool
    data: Any = None  # Can be dict, list, str, or base64-encoded binary
    content_type: str = "application/json"  # MIME type of the data
    error: str | None = None
    cached: bool = False  # Whether data was served from cache
    fetched_at: str | None = None  # ISO timestamp when data was fetched


# --- Message response (for delete endpoints etc.) ---


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# --- Token response ---


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str


# --- Notebook responses ---


class NotebookResponse(BaseModel):
    """Notebook API response."""

    id: int
    slug: str | None = None
    name: str
    path: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class NotebookIndexingStatusResponse(BaseModel):
    """Notebook indexing status response."""

    notebook_id: int
    status: str
    is_alive: bool


# --- Plugin config responses ---


class WorkspacePluginConfigResponse(BaseModel):
    """Workspace plugin configuration response."""

    plugin_id: str
    version: str | None = None
    enabled: bool
    config: dict[str, Any]
    created_at: str | None = None
    updated_at: str | None = None


class NotebookPluginConfigResponse(BaseModel):
    """Notebook plugin configuration response."""

    plugin_id: str
    enabled: bool
    config: dict[str, Any]
    created_at: str | None = None
    updated_at: str | None = None


# --- Block responses ---


class BlockResponse(BaseModel):
    """Block API response.

    Fields are optional because different endpoints return different subsets:
    - _block_dict() returns the full shape from DB models
    - Core functions (create_block, update_block_content, move_block) return minimal dicts
    """

    id: int | None = None
    block_id: str
    parent_block_id: str | None = None
    notebook_id: int | None = None
    path: str
    block_type: str | None = None
    type: str | None = None  # Alias used by core create/update functions
    content_format: str | None = None
    order_index: float | None = None
    order: float | None = None  # Alias used by core create/move functions
    file: str | None = None  # Filename, used by core create functions
    title: str | None = None
    file_id: int | None = None
    content_type: str | None = None
    size: int | None = None
    description: str | None = None
    properties: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    content: str | None = None
    children: list["BlockResponse"] | None = None
    page_metadata: dict[str, Any] | None = None
    blocks: list["BlockResponse"] | None = None


class PageResponse(BaseModel):
    """Response for page creation/conversion."""

    block_id: str
    path: str
    title: str | None = None
    description: str | None = None
    properties: dict[str, Any] | None = None
    version: int | None = None
    blocks: list[dict[str, Any]] | None = None


class RootBlocksResponse(BaseModel):
    """Response for listing root blocks."""

    blocks: list[BlockResponse]
    notebook_id: int
    workspace_id: int


class BlockChildrenResponse(BaseModel):
    """Response for listing block children."""

    parent_block_id: str
    children: list[BlockResponse]


class BlockTreeResponse(BaseModel):
    """Response for hierarchical block tree."""

    tree: list[dict[str, Any]]
    notebook_id: int
    workspace_id: int


class BlockTextContentResponse(BaseModel):
    """Response for block text content."""

    content: str
    properties: dict[str, Any] | None = None


class BlockDeleteResponse(BaseModel):
    """Response for block deletion."""

    message: str
    blocks: list[BlockResponse] | None = None


class BlockReorderResponse(BaseModel):
    """Response for block reorder."""

    parent_block_id: str
    blocks: list[BlockResponse]


class BlockResolveLinkResponse(BaseModel):
    """Response for block link resolution."""

    id: int | None = None
    block_id: str | None = None
    parent_block_id: str | None = None
    notebook_id: int | None = None
    path: str
    filename: str | None = None
    block_type: str | None = None
    content_format: str | None = None
    order_index: float | None = None
    title: str | None = None
    file_id: int | None = None
    content_type: str | None = None
    size: int | None = None
    description: str | None = None
    properties: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    resolved_path: str


class FileHistoryEntryResponse(BaseModel):
    """Git history entry."""

    hash: str
    author: str
    date: str
    message: str


class BlockHistoryResponse(BaseModel):
    """Response for block git history."""

    block_id: str
    path: str
    history: list[FileHistoryEntryResponse]


class BlockAtCommitResponse(BaseModel):
    """Response for block content at a specific commit."""

    block_id: str
    path: str
    commit_hash: str
    content: str


class ImportFolderResponse(BaseModel):
    """Response for folder import."""

    path: str
    block_id: str
    pages_created: int
    blocks_created: int


# --- Search responses ---


class SearchResultResponse(BaseModel):
    """A single search result."""

    id: int | None = None
    path: str | None = None
    filename: str | None = None
    title: str | None = None
    description: str | None = None
    content_type: str | None = None
    notebook_id: int | None = None
    snippet: str | None = None
    score: float | None = None


class WorkspaceSearchResponse(BaseModel):
    """Response for workspace-level search."""

    query: str
    workspace_id: int
    workspace_slug: str | None = None
    results: list[SearchResultResponse]
    message: str | None = None


class NotebookSearchResponse(WorkspaceSearchResponse):
    """Response for notebook-level search."""

    notebook_id: int
    notebook_slug: str | None = None


class WorkspaceTagSearchResponse(BaseModel):
    """Response for workspace-level tag search."""

    tags: list[str]
    workspace_id: int
    workspace_slug: str | None = None
    results: list[SearchResultResponse]
    message: str | None = None


class NotebookTagSearchResponse(WorkspaceTagSearchResponse):
    """Response for notebook-level tag search."""

    notebook_id: int
    notebook_slug: str | None = None

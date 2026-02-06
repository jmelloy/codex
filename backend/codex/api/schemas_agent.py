"""API schemas for AI agent endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --- Agent CRUD ---


class AgentCreate(BaseModel):
    """Create a new agent for a workspace."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    provider: str = Field(..., description="LiteLLM provider, e.g. 'openai', 'anthropic', 'ollama'")
    model: str = Field(..., description="Model identifier, e.g. 'gpt-4o', 'claude-sonnet-4-20250514', 'ollama/llama3'")

    scope: dict[str, Any] = Field(
        default_factory=lambda: {"notebooks": ["*"], "folders": ["*"], "file_types": ["*"]},
        description="Access scope configuration",
    )

    can_read: bool = True
    can_write: bool = False
    can_create: bool = False
    can_delete: bool = False
    can_execute_code: bool = False
    can_access_integrations: bool = False

    max_requests_per_hour: int = Field(default=100, ge=1)
    max_tokens_per_request: int = Field(default=4000, ge=1)

    system_prompt: str | None = None


class AgentUpdate(BaseModel):
    """Update an existing agent."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    provider: str | None = None
    model: str | None = None
    scope: dict[str, Any] | None = None

    can_read: bool | None = None
    can_write: bool | None = None
    can_create: bool | None = None
    can_delete: bool | None = None
    can_execute_code: bool | None = None
    can_access_integrations: bool | None = None

    max_requests_per_hour: int | None = None
    max_tokens_per_request: int | None = None

    is_active: bool | None = None
    system_prompt: str | None = None


class AgentResponse(BaseModel):
    """Agent response for API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None = None
    provider: str
    model: str
    scope: dict[str, Any]
    can_read: bool
    can_write: bool
    can_create: bool
    can_delete: bool
    can_execute_code: bool
    can_access_integrations: bool
    max_requests_per_hour: int
    max_tokens_per_request: int
    is_active: bool
    system_prompt: str | None = None
    created_at: datetime
    updated_at: datetime


# --- Credentials ---


class CredentialSet(BaseModel):
    """Set an agent credential (e.g., API key)."""

    key_name: str = Field(..., min_length=1, description="Credential name, e.g. 'api_key'")
    value: str = Field(..., min_length=1, description="The secret value to store (will be encrypted)")


class CredentialResponse(BaseModel):
    """Credential metadata (value is never returned)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key_name: str
    created_at: datetime


# --- Sessions ---


class SessionCreate(BaseModel):
    """Start a new agent session."""

    task_id: int | None = None
    notebook_path: str = Field(..., description="Path to the notebook for this session")


class SessionMessageRequest(BaseModel):
    """Send a message to an active agent session."""

    content: str = Field(..., min_length=1)


class SessionResponse(BaseModel):
    """Agent session response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    task_id: int | None = None
    user_id: int
    status: str
    tokens_used: int
    api_calls_made: int
    files_modified: list[str]
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


class SessionMessageResponse(BaseModel):
    """Response after sending a message to a session."""

    session_id: int
    status: str
    response: str
    messages: list[dict[str, Any]] = []
    action_logs: list[dict[str, Any]] = []


# --- Action Logs ---


class ActionLogResponse(BaseModel):
    """Agent action log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    action_type: str
    target_path: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    was_allowed: bool
    execution_time_ms: int
    created_at: datetime

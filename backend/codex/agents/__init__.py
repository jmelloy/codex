"""AI agent integration for Codex.

This module provides scoped AI agents that can operate on notebooks
within explicit permission boundaries, using LiteLLM for provider-agnostic
model access.
"""

from .engine import AgentEngine
from .provider import LiteLLMProvider
from .scope import ScopeGuard, ScopeViolation
from .tools import ToolDefinition, ToolRouter

__all__ = [
    "AgentEngine",
    "LiteLLMProvider",
    "ScopeGuard",
    "ScopeViolation",
    "ToolDefinition",
    "ToolRouter",
]

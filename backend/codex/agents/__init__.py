"""AI agent integration for Codex.

This module provides scoped AI agents that can operate on notebooks
within explicit permission boundaries, using direct httpx calls to
OpenAI-compatible APIs for provider-agnostic model access.
"""

from .engine import AgentEngine
from .provider import CompletionProvider
from .scope import ScopeGuard, ScopeViolation
from .tools import ToolDefinition, ToolRouter

__all__ = [
    "AgentEngine",
    "CompletionProvider",
    "ScopeGuard",
    "ScopeViolation",
    "ToolDefinition",
    "ToolRouter",
]

"""LiteLLM-based provider adapter for AI agent completions.

Uses LiteLLM to provide a unified interface to 100+ LLM providers
(OpenAI, Anthropic, Ollama, Azure, Bedrock, etc.) with a single API.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """A message in the agent conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    """A parsed tool call from the model response."""

    id: str
    name: str
    arguments: dict[str, Any]


class AgentResponse(BaseModel):
    """Parsed response from the LLM provider."""

    content: str | None = None
    tool_calls: list[ToolCall] = []
    finish_reason: str = "stop"  # "stop", "tool_calls", "length", "error"
    usage: dict[str, int] = {}


class LiteLLMProvider:
    """Provider adapter using LiteLLM for model-agnostic completions.

    LiteLLM handles the provider-specific formatting, auth, and API calls.
    This class wraps it with Codex-specific message/tool handling.

    Args:
        model: The model identifier in LiteLLM format.
               Examples: "gpt-4o", "claude-sonnet-4-20250514",
               "ollama/llama3", "azure/gpt-4", etc.
        api_key: API key for the provider (optional if set via env vars).
        api_base: Custom API base URL (e.g., for Ollama or self-hosted).
        extra_params: Additional params passed to litellm.acompletion().
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        **extra_params: Any,
    ):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.extra_params = extra_params

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4000,
    ) -> AgentResponse:
        """Generate a completion with optional tool use.

        Args:
            messages: Conversation history as Message objects.
            tools: Tool definitions in OpenAI function-calling format.
            max_tokens: Maximum tokens in the response.

        Returns:
            AgentResponse with content and/or tool calls.
        """
        import litellm

        # Convert messages to the dict format litellm expects
        litellm_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": litellm_messages,
            "max_tokens": max_tokens,
            **self.extra_params,
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if tools:
            kwargs["tools"] = tools

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}")
            return AgentResponse(
                content=f"Error calling model: {e}",
                finish_reason="error",
                usage={},
            )

        return self._parse_response(response)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert Message objects to litellm-compatible dicts."""
        result = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role}

            if msg.role == "tool":
                entry["content"] = msg.content or ""
                if msg.tool_call_id:
                    entry["tool_call_id"] = msg.tool_call_id
            elif msg.tool_calls:
                entry["content"] = msg.content or ""
                entry["tool_calls"] = msg.tool_calls
            else:
                entry["content"] = msg.content or ""

            result.append(entry)
        return result

    def _parse_response(self, response: Any) -> AgentResponse:
        """Parse a LiteLLM response into an AgentResponse."""
        choice = response.choices[0]
        message = choice.message

        content = message.content
        tool_calls: list[ToolCall] = []
        finish_reason = choice.finish_reason or "stop"

        if hasattr(message, "tool_calls") and message.tool_calls:
            finish_reason = "tool_calls"
            for tc in message.tool_calls:
                try:
                    args = tc.function.arguments
                    if isinstance(args, str):
                        args = json.loads(args)
                    tool_calls.append(
                        ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=args,
                        )
                    )
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to parse tool call: {e}")

        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "input_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
            }

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )

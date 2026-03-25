"""OpenAI-compatible provider adapter for AI agent completions.

Uses httpx to call any OpenAI-compatible chat completions API directly
(OpenAI, Anthropic via proxy, Ollama, Azure, vLLM, etc.) without
heavy wrapper libraries.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Well-known provider base URLs (model prefix → base URL).
_PROVIDER_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "ollama": "http://localhost:11434/v1",
}


def _default_base_url(model: str) -> str:
    """Infer a base URL from the model string or environment."""
    env_url = os.getenv("CODEX_LLM_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    # Check for provider prefix like "ollama/llama3"
    if "/" in model:
        prefix = model.split("/", 1)[0].lower()
        if prefix in _PROVIDER_URLS:
            return _PROVIDER_URLS[prefix]
    # Default to OpenAI
    return _PROVIDER_URLS["openai"]


def _strip_provider_prefix(model: str) -> str:
    """Strip provider prefix from model name (e.g. 'ollama/llama3' → 'llama3')."""
    if "/" in model:
        prefix = model.split("/", 1)[0].lower()
        if prefix in _PROVIDER_URLS:
            return model.split("/", 1)[1]
    return model


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


class CompletionProvider:
    """Provider adapter using httpx for OpenAI-compatible chat completions.

    Calls the standard ``/chat/completions`` endpoint directly, which is
    supported by OpenAI, Ollama, vLLM, LM Studio, Azure OpenAI, and many
    other providers.

    Args:
        model: The model identifier.  May include a provider prefix
               (e.g. ``"ollama/llama3"``) which is used to infer the
               base URL and then stripped before sending the request.
        api_key: API key for the provider (falls back to
                 ``CODEX_LLM_API_KEY`` or ``OPENAI_API_KEY`` env vars).
        api_base: Custom API base URL (overrides auto-detection).
        extra_params: Additional params merged into the request body.
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        **extra_params: Any,
    ):
        self.model = _strip_provider_prefix(model)
        self.api_base = (api_base or _default_base_url(model)).rstrip("/")
        self.api_key = api_key or os.getenv("CODEX_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
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
        import httpx

        body: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "max_tokens": max_tokens,
            **self.extra_params,
        }

        if tools:
            body["tools"] = tools

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Completion error: {e}")
            return AgentResponse(
                content=f"Error calling model: {e}",
                finish_reason="error",
                usage={},
            )

        return self._parse_response(data)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert Message objects to OpenAI-compatible dicts."""
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

    def _parse_response(self, data: dict[str, Any]) -> AgentResponse:
        """Parse an OpenAI-compatible JSON response into an AgentResponse."""
        choice = data["choices"][0]
        message = choice["message"]

        content = message.get("content")
        tool_calls: list[ToolCall] = []
        finish_reason = choice.get("finish_reason") or "stop"

        raw_tool_calls = message.get("tool_calls")
        if raw_tool_calls:
            finish_reason = "tool_calls"
            for tc in raw_tool_calls:
                try:
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        args = json.loads(args)
                    tool_calls.append(
                        ToolCall(
                            id=tc["id"],
                            name=tc["function"]["name"],
                            arguments=args,
                        )
                    )
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse tool call: {e}")

        usage: dict[str, int] = {}
        raw_usage = data.get("usage")
        if raw_usage:
            usage = {
                "input_tokens": raw_usage.get("prompt_tokens", 0) or 0,
                "output_tokens": raw_usage.get("completion_tokens", 0) or 0,
            }

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )


# Backwards-compatible alias
LiteLLMProvider = CompletionProvider

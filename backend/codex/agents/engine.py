"""Agent execution engine - orchestrates the agent tool-use loop."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from .provider import AgentResponse, LiteLLMProvider, Message
from .tools import ToolRouter

if TYPE_CHECKING:
    from codex.db.models import Agent, AgentSession

logger = logging.getLogger(__name__)


class AgentEngine:
    """Executes agent tasks with a tool-use loop.

    Orchestrates the conversation between the LLM and Codex tools,
    respecting scope boundaries and tracking metrics.
    """

    def __init__(
        self,
        agent: Agent,
        provider: LiteLLMProvider,
        tool_router: ToolRouter,
        session: AgentSession,
        max_iterations: int = 20,
    ):
        self.agent = agent
        self.provider = provider
        self.tool_router = tool_router
        self.session = session
        self.messages: list[Message] = []
        self.max_iterations = max_iterations

    async def run(
        self,
        user_message: str,
        system_prompt: str | None = None,
        on_action: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        """Execute agent with a user request.

        Args:
            user_message: The user's task or question.
            system_prompt: Override the default system prompt.
            on_action: Optional callback invoked on each tool call.

        Returns:
            The agent's final text response.
        """
        # Build system prompt with scope info
        base_system = system_prompt or self.agent.system_prompt or self._build_system_prompt()
        self.messages = [
            Message(role="system", content=base_system),
            Message(role="user", content=user_message),
        ]

        tools = self.tool_router.get_tool_definitions_for_litellm()
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            response: AgentResponse = await self.provider.complete(
                messages=self.messages,
                tools=tools if tools else None,
                max_tokens=self.agent.max_tokens_per_request,
            )

            # Update session metrics
            self.session.tokens_used += response.usage.get("input_tokens", 0)
            self.session.tokens_used += response.usage.get("output_tokens", 0)
            self.session.api_calls_made += 1

            # If no tool calls, we're done
            if not response.tool_calls:
                if response.content:
                    self.messages.append(Message(role="assistant", content=response.content))
                return response.content or ""

            # Add assistant message with tool calls
            assistant_tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": _serialize_args(tc.arguments),
                    },
                }
                for tc in response.tool_calls
            ]
            self.messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=assistant_tool_calls,
                )
            )

            # Process each tool call
            for tool_call in response.tool_calls:
                if on_action:
                    on_action({
                        "type": "tool_call",
                        "tool": tool_call.name,
                        "arguments": tool_call.arguments,
                    })

                result = await self.tool_router.execute_tool(
                    tool_call.name,
                    tool_call.arguments,
                    confirmed=True,  # Auto-confirm in engine loop; API layer handles confirmation
                )

                self.messages.append(
                    Message(
                        role="tool",
                        content=_serialize_args(result),
                        tool_call_id=tool_call.id,
                    )
                )

            # Check for error response that suggests stopping
            if response.finish_reason == "error":
                return response.content or "An error occurred during execution."

        return "Max iterations reached. Task may be incomplete."

    def _build_system_prompt(self) -> str:
        """Generate system prompt with scope context."""
        scope_desc = []

        if self.agent.can_read:
            scope_desc.append("- Read files and search content")
        if self.agent.can_write:
            scope_desc.append("- Write/update existing files")
        if self.agent.can_create:
            scope_desc.append("- Create new files")
        if self.agent.can_delete:
            scope_desc.append("- Delete files")

        folders = (self.agent.scope or {}).get("folders", ["*"])
        folder_desc = "all folders" if "*" in folders else f"folders: {', '.join(folders)}"

        file_types = (self.agent.scope or {}).get("file_types", ["*"])
        type_desc = "all file types" if "*" in file_types else f"file types: {', '.join(file_types)}"

        return (
            "You are an AI assistant for the Codex laboratory journal system.\n\n"
            "You have the following capabilities:\n"
            f"{chr(10).join(scope_desc)}\n\n"
            f"You can access {folder_desc}.\n"
            f"You can work with {type_desc}.\n\n"
            "When asked to modify files, explain what changes you'll make before using tools.\n"
            "If a task is outside your scope, explain what you cannot do and why.\n"
            "Be precise, helpful, and respect the user's notebook organization."
        )

    def get_messages(self) -> list[dict[str, Any]]:
        """Return conversation messages as serializable dicts."""
        return [m.model_dump() for m in self.messages]


def _serialize_args(obj: Any) -> str:
    """Serialize tool arguments/results to a string for message content."""
    import json

    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return str(obj)

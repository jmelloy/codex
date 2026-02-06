# AI Agent Integration Design Document

**Author:** Claude
**Date:** 2026-01-30
**Status:** Phase 1 & 2 Backend Complete
**Reviewers:** TBD
**Last Updated:** 2026-02-06

## Overview

This document describes the design for integrating scoped AI agents into Codex, enabling automated assistance for computational experiments, content generation, and notebook management while maintaining strict security boundaries.

## Background

Codex is a hierarchical digital laboratory journal system using a Workspace → Notebook → Files hierarchy. The existing architecture includes:

- **Task System**: A task queue with `assigned_to` field for agents (`/api/v1/tasks/`)
- **Plugin Architecture**: Extensible plugin system with IntegrationPlugin capabilities
- **Integration Executor**: API call execution with authentication and logging
- **Workspace Permissions**: Role-based access (read/write/admin) per workspace

These components provide natural extension points for AI agent integration.

## Goals

1. **Scoped Access**: Agents operate within explicit permission boundaries (workspace/notebook/folder level)
2. **Auditability**: All agent actions are logged and traceable
3. **Task-Driven**: Agents receive work through the existing task queue
4. **Provider-Agnostic**: Support multiple AI backends (OpenAI, Anthropic, local models)
5. **Safe by Default**: Agents require explicit permissions; destructive operations need confirmation

## Non-Goals

1. Building a general-purpose autonomous agent framework
2. Real-time streaming responses (initially)
3. Multi-agent orchestration (v1 scope)
4. Training or fine-tuning models on user data

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ Agent Config │  │ Task Creator │  │ Agent Activity Monitor   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ /agents/     │  │ /tasks/      │  │ /agent-sessions/         │   │
│  │ Agent CRUD   │  │ Task Queue   │  │ Active Executions        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
│                                │                                     │
│                                ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Agent Execution Engine                    │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │    │
│  │  │ Scope Guard │  │ Tool Router │  │ Provider Adapter    │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Layer                                    │
│  ┌──────────────────────┐        ┌────────────────────────────────┐ │
│  │ System DB            │        │ Notebook DBs                   │ │
│  │ - Agent configs      │        │ - File access (scoped)         │ │
│  │ - Agent credentials  │        │ - Search index                 │ │
│  │ - Execution logs     │        │ - Metadata                     │ │
│  │ - Task assignments   │        │                                │ │
│  └──────────────────────┘        └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Agent Configuration Model

Agents are defined per-workspace with explicit scope and capability declarations:

```python
# backend/codex/db/models/system.py

class Agent(Base):
    """AI agent configuration for a workspace."""
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None]
    provider: Mapped[str]  # "openai", "anthropic", "ollama", "custom"
    model: Mapped[str]  # "gpt-4", "claude-3-opus", etc.

    # Scope configuration (JSON)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    # Example: {
    #   "notebooks": ["*"] or ["notebook-id-1", "notebook-id-2"],
    #   "folders": ["/experiments/*", "/drafts"],
    #   "file_types": ["*.md", "*.py", "*.ipynb"],
    #   "operations": ["read", "write", "create", "delete"]
    # }

    # Capability flags
    can_read: Mapped[bool] = mapped_column(default=True)
    can_write: Mapped[bool] = mapped_column(default=False)
    can_create: Mapped[bool] = mapped_column(default=False)
    can_delete: Mapped[bool] = mapped_column(default=False)
    can_execute_code: Mapped[bool] = mapped_column(default=False)
    can_access_integrations: Mapped[bool] = mapped_column(default=False)

    # Rate limiting
    max_requests_per_hour: Mapped[int] = mapped_column(default=100)
    max_tokens_per_request: Mapped[int] = mapped_column(default=4000)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="agents")
    credentials: Mapped["AgentCredential"] = relationship(back_populates="agent")
    sessions: Mapped[list["AgentSession"]] = relationship(back_populates="agent")


class AgentCredential(Base):
    """Encrypted storage for agent API keys."""
    __tablename__ = "agent_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    key_name: Mapped[str]  # "api_key", "organization_id", etc.
    encrypted_value: Mapped[str]  # Fernet-encrypted
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class AgentSession(Base):
    """Active or historical agent execution session."""
    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # Who initiated

    status: Mapped[str]  # "pending", "running", "completed", "failed", "cancelled"
    context: Mapped[dict] = mapped_column(JSON, default=dict)  # Conversation state

    # Metrics
    tokens_used: Mapped[int] = mapped_column(default=0)
    api_calls_made: Mapped[int] = mapped_column(default=0)
    files_modified: Mapped[list] = mapped_column(JSON, default=list)

    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None]
    error_message: Mapped[str | None]


class AgentActionLog(Base):
    """Audit log for all agent actions."""
    __tablename__ = "agent_action_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("agent_sessions.id"))

    action_type: Mapped[str]  # "file_read", "file_write", "api_call", etc.
    target_path: Mapped[str | None]  # File/folder path if applicable
    input_summary: Mapped[str]  # Truncated input
    output_summary: Mapped[str]  # Truncated output

    was_allowed: Mapped[bool]  # Did scope guard permit this?
    execution_time_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

#### 2. Scope Guard

The Scope Guard enforces access boundaries before any agent action:

```python
# backend/codex/agents/scope.py

from dataclasses import dataclass
from pathlib import PurePath
from fnmatch import fnmatch
from typing import Literal

ActionType = Literal["read", "write", "create", "delete", "execute"]


@dataclass
class ScopeViolation(Exception):
    """Raised when an agent attempts an out-of-scope action."""
    action: ActionType
    target: str
    reason: str


class ScopeGuard:
    """Enforces agent access boundaries."""

    def __init__(self, agent: Agent, notebook_id: str | None = None):
        self.agent = agent
        self.scope = agent.scope
        self.notebook_id = notebook_id

    def check_notebook_access(self, notebook_id: str) -> bool:
        """Verify agent can access this notebook."""
        allowed = self.scope.get("notebooks", [])
        if "*" in allowed:
            return True
        return notebook_id in allowed

    def check_path_access(self, path: str, action: ActionType) -> bool:
        """Verify agent can perform action on this path."""
        # Check action permission
        action_map = {
            "read": self.agent.can_read,
            "write": self.agent.can_write,
            "create": self.agent.can_create,
            "delete": self.agent.can_delete,
            "execute": self.agent.can_execute_code,
        }
        if not action_map.get(action, False):
            return False

        # Check path against folder patterns
        folders = self.scope.get("folders", ["*"])
        path_obj = PurePath(path)

        for pattern in folders:
            if fnmatch(str(path_obj), pattern) or fnmatch(str(path_obj.parent), pattern):
                break
        else:
            if "*" not in folders:
                return False

        # Check file type restrictions
        file_types = self.scope.get("file_types", ["*"])
        if "*" not in file_types:
            if not any(fnmatch(path_obj.name, ft) for ft in file_types):
                return False

        return True

    def validate_or_raise(self, action: ActionType, target: str):
        """Validate action or raise ScopeViolation."""
        if not self.check_path_access(target, action):
            raise ScopeViolation(
                action=action,
                target=target,
                reason=f"Agent '{self.agent.name}' not permitted to {action} '{target}'"
            )
```

#### 3. Tool Router

The Tool Router maps agent intentions to Codex operations:

```python
# backend/codex/agents/tools.py

from typing import Any, Callable
from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Schema for a tool available to agents."""
    name: str
    description: str
    parameters: dict  # JSON Schema
    requires_confirmation: bool = False


class ToolRouter:
    """Routes agent tool calls to Codex operations."""

    def __init__(self, scope_guard: ScopeGuard, session: AgentSession):
        self.scope_guard = scope_guard
        self.session = session
        self._tools: dict[str, Callable] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register default Codex tools."""
        self._tools = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "list_files": self._list_files,
            "search_content": self._search_content,
            "get_file_metadata": self._get_file_metadata,
            "update_file_properties": self._update_file_properties,
            "create_file": self._create_file,
        }

    def get_tool_definitions(self) -> list[ToolDefinition]:
        """Return tools available based on agent scope."""
        tools = []

        if self.scope_guard.agent.can_read:
            tools.extend([
                ToolDefinition(
                    name="read_file",
                    description="Read the contents of a file in the notebook",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to notebook root"}
                        },
                        "required": ["path"]
                    }
                ),
                ToolDefinition(
                    name="list_files",
                    description="List files in a directory",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path", "default": "/"},
                            "pattern": {"type": "string", "description": "Glob pattern filter"}
                        }
                    }
                ),
                ToolDefinition(
                    name="search_content",
                    description="Full-text search across notebook files",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                ),
            ])

        if self.scope_guard.agent.can_write:
            tools.append(ToolDefinition(
                name="write_file",
                description="Write or update file contents",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "properties": {"type": "object", "description": "Optional frontmatter properties"}
                    },
                    "required": ["path", "content"]
                },
                requires_confirmation=True
            ))

        if self.scope_guard.agent.can_create:
            tools.append(ToolDefinition(
                name="create_file",
                description="Create a new file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "template": {"type": "string", "description": "Optional template ID"}
                    },
                    "required": ["path"]
                },
                requires_confirmation=True
            ))

        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        confirmed: bool = False
    ) -> dict[str, Any]:
        """Execute a tool call with scope validation."""
        if tool_name not in self._tools:
            return {"error": f"Unknown tool: {tool_name}"}

        # Get tool definition
        tool_def = next((t for t in self.get_tool_definitions() if t.name == tool_name), None)
        if tool_def and tool_def.requires_confirmation and not confirmed:
            return {
                "requires_confirmation": True,
                "action": tool_name,
                "arguments": arguments
            }

        try:
            result = await self._tools[tool_name](**arguments)
            await self._log_action(tool_name, arguments, result, allowed=True)
            return result
        except ScopeViolation as e:
            await self._log_action(tool_name, arguments, str(e), allowed=False)
            return {"error": str(e), "scope_violation": True}

    async def _read_file(self, path: str) -> dict:
        self.scope_guard.validate_or_raise("read", path)
        # Delegate to file service
        # ...

    async def _write_file(self, path: str, content: str, properties: dict = None) -> dict:
        self.scope_guard.validate_or_raise("write", path)
        # Delegate to file service
        # ...
```

#### 4. Provider Adapter (LiteLLM)

> **Implementation Note (2026-02-06):** The original design proposed separate
> `ProviderAdapter` subclasses per provider (Anthropic, OpenAI, Ollama). During
> implementation this was replaced with a single **LiteLLM-based adapter** that
> supports 100+ providers through one interface. This eliminated ~300 lines of
> per-provider glue code and removed the need for direct `anthropic`, `openai`,
> or `ollama` SDK dependencies.

The provider layer uses [LiteLLM](https://github.com/BerriAI/litellm) to make
provider-agnostic `acompletion()` calls with OpenAI-format tool definitions:

```python
# backend/codex/agents/provider.py  (implemented)

class LiteLLMProvider:
    """Provider adapter using LiteLLM for model-agnostic completions."""

    def __init__(
        self,
        model: str,           # e.g. "gpt-4o", "claude-sonnet-4-20250514", "ollama/llama3"
        api_key: str | None = None,
        api_base: str | None = None,
        **extra_params,
    ): ...

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,   # OpenAI function-calling format
        max_tokens: int = 4000,
    ) -> AgentResponse: ...
```

Supporting data classes (also in `provider.py`):

```python
class Message(BaseModel):
    role: str                              # "system", "user", "assistant", "tool"
    content: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict

class AgentResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = []
    finish_reason: str = "stop"            # "stop", "tool_calls", "length", "error"
    usage: dict[str, int] = {}
```

**Model string examples:**

| Provider  | Model string                   |
|-----------|-------------------------------|
| OpenAI    | `gpt-4o`                      |
| Anthropic | `claude-sonnet-4-20250514`           |
| Ollama    | `ollama/llama3`               |
| Azure     | `azure/gpt-4`                 |
| Bedrock   | `bedrock/anthropic.claude-3`  |

#### 5. Agent Execution Engine

Orchestrates the agent loop:

```python
# backend/codex/agents/engine.py

from typing import Callable


class AgentEngine:
    """Executes agent tasks with tool use loop."""

    def __init__(
        self,
        agent: Agent,
        provider: ProviderAdapter,
        tool_router: ToolRouter,
        session: AgentSession,
    ):
        self.agent = agent
        self.provider = provider
        self.tool_router = tool_router
        self.session = session
        self.messages: list[Message] = []
        self.max_iterations = 20  # Prevent infinite loops

    async def run(
        self,
        user_message: str,
        system_prompt: str | None = None,
        on_action: Callable[[dict], None] | None = None,  # Callback for UI updates
    ) -> str:
        """Execute agent with a user request."""

        # Build system prompt with scope info
        base_system = system_prompt or self._build_system_prompt()
        self.messages = [
            Message(role="system", content=base_system),
            Message(role="user", content=user_message),
        ]

        tools = self.tool_router.get_tool_definitions()
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            # Get model response
            response = await self.provider.complete(
                messages=self.messages,
                tools=tools,
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

            # Process tool calls
            self.messages.append(Message(
                role="assistant",
                content=response.content or "",
                tool_calls=[tc.model_dump() for tc in response.tool_calls],
            ))

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
                )

                self.messages.append(Message(
                    role="tool",
                    content=str(result),
                    tool_call_id=tool_call.id,
                ))

        return "Max iterations reached. Task may be incomplete."

    def _build_system_prompt(self) -> str:
        """Generate system prompt with scope context."""
        scope_desc = []

        if self.agent.can_read:
            scope_desc.append("- Read files")
        if self.agent.can_write:
            scope_desc.append("- Write/update files (requires confirmation)")
        if self.agent.can_create:
            scope_desc.append("- Create new files")
        if self.agent.can_delete:
            scope_desc.append("- Delete files (requires confirmation)")

        folders = self.agent.scope.get("folders", ["*"])
        folder_desc = "all folders" if "*" in folders else f"folders: {', '.join(folders)}"

        return f"""You are an AI assistant for the Codex laboratory journal system.

You have the following capabilities:
{chr(10).join(scope_desc)}

You can access {folder_desc}.

When asked to modify files, explain what changes you'll make before using tools.
If a task is outside your scope, explain what you cannot do and why.

Be precise, helpful, and respect the user's notebook organization."""
```

---

## API Design

### Agent Management Endpoints

```
POST   /api/v1/agents/                    Create agent for workspace
GET    /api/v1/agents/                    List agents (filtered by workspace)
GET    /api/v1/agents/{agent_id}          Get agent details
PUT    /api/v1/agents/{agent_id}          Update agent configuration
DELETE /api/v1/agents/{agent_id}          Delete agent
POST   /api/v1/agents/{agent_id}/activate   Activate/deactivate agent
```

### Agent Credential Endpoints

```
POST   /api/v1/agents/{agent_id}/credentials    Set credential
DELETE /api/v1/agents/{agent_id}/credentials/{key}  Remove credential
```

### Agent Session Endpoints

```
POST   /api/v1/agents/{agent_id}/sessions       Start new session
GET    /api/v1/agents/{agent_id}/sessions       List sessions
GET    /api/v1/sessions/{session_id}            Get session details
POST   /api/v1/sessions/{session_id}/message    Send message to agent
POST   /api/v1/sessions/{session_id}/confirm    Confirm pending action
POST   /api/v1/sessions/{session_id}/cancel     Cancel session
GET    /api/v1/sessions/{session_id}/logs       Get action logs
```

### Request/Response Examples

**Create Agent:**
```json
POST /api/v1/agents/
{
  "workspace_id": 1,
  "name": "Research Assistant",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "scope": {
    "notebooks": ["*"],
    "folders": ["/experiments/*", "/notes"],
    "file_types": ["*.md", "*.txt", "*.json"]
  },
  "can_read": true,
  "can_write": true,
  "can_create": true,
  "can_delete": false,
  "max_requests_per_hour": 50
}
```

**Send Message to Session:**
```json
POST /api/v1/sessions/{session_id}/message
{
  "content": "Summarize all the experiments from last week and create a summary.md file"
}

Response:
{
  "session_id": "abc123",
  "status": "running",
  "messages": [
    {
      "role": "assistant",
      "content": "I'll help you summarize last week's experiments. Let me first search for recent experiment files...",
      "pending_actions": [
        {
          "id": "action_1",
          "type": "create_file",
          "path": "/notes/summary.md",
          "requires_confirmation": true
        }
      ]
    }
  ]
}
```

**Confirm Action:**
```json
POST /api/v1/sessions/{session_id}/confirm
{
  "action_id": "action_1",
  "confirmed": true
}
```

---

## Frontend Integration

### Vue Components

```
frontend/src/
├── components/
│   └── agent/
│       ├── AgentConfig.vue       # Agent creation/editing form
│       ├── AgentChat.vue         # Chat interface for agent sessions
│       ├── AgentScopeEditor.vue  # Visual scope configuration
│       ├── AgentActionCard.vue   # Pending action confirmation UI
│       └── AgentActivityLog.vue  # Session history and logs
├── stores/
│   └── agent.ts                  # Pinia store for agent state
└── services/
    └── agent.ts                  # API client for agent endpoints
```

### Agent Store

```typescript
// frontend/src/stores/agent.ts

import { defineStore } from 'pinia'
import { agentService } from '@/services/agent'

interface Agent {
  id: number
  name: string
  provider: string
  model: string
  scope: AgentScope
  can_read: boolean
  can_write: boolean
  can_create: boolean
  can_delete: boolean
  is_active: boolean
}

interface AgentSession {
  id: string
  agent_id: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  messages: Message[]
  pending_actions: PendingAction[]
}

export const useAgentStore = defineStore('agent', {
  state: () => ({
    agents: [] as Agent[],
    currentSession: null as AgentSession | null,
    loading: false,
    error: null as string | null,
  }),

  actions: {
    async fetchAgents(workspaceId: number) {
      this.loading = true
      try {
        this.agents = await agentService.list(workspaceId)
      } finally {
        this.loading = false
      }
    },

    async startSession(agentId: number, message: string) {
      const session = await agentService.startSession(agentId)
      this.currentSession = session
      return this.sendMessage(message)
    },

    async sendMessage(content: string) {
      if (!this.currentSession) throw new Error('No active session')
      const response = await agentService.sendMessage(this.currentSession.id, content)
      this.currentSession = response
      return response
    },

    async confirmAction(actionId: string, confirmed: boolean) {
      if (!this.currentSession) throw new Error('No active session')
      const response = await agentService.confirmAction(
        this.currentSession.id,
        actionId,
        confirmed
      )
      this.currentSession = response
      return response
    },
  },
})
```

### UI Mockup: Agent Chat

```
┌─────────────────────────────────────────────────────────────────┐
│ Research Assistant (claude-sonnet-4-20250514)           [⚙️] [×] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐     │
│   │ Summarize all the experiments from last week and      │     │
│   │ create a summary.md file                              │ You │
│   └───────────────────────────────────────────────────────┘     │
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐     │
│   │ I found 5 experiment files from the past week:        │     │
│   │ • /experiments/2026-01-23-neural-net.md              │     │
│   │ • /experiments/2026-01-24-data-prep.md               │     │
│   │ • /experiments/2026-01-25-training-run.md            │     │
│   │ • /experiments/2026-01-27-evaluation.md              │ AI  │
│   │ • /experiments/2026-01-28-ablation.md                │     │
│   │                                                       │     │
│   │ I'll create a summary with key findings...            │     │
│   └───────────────────────────────────────────────────────┘     │
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐     │
│   │ ⚠️ PENDING ACTION                                     │     │
│   │ Create file: /notes/weekly-summary-2026-01-30.md      │     │
│   │ Preview:                                              │     │
│   │ ┌─────────────────────────────────────────────────┐   │     │
│   │ │ # Weekly Experiment Summary                     │   │     │
│   │ │ ## Week of January 23-29, 2026                 │   │     │
│   │ │ ...                                            │   │     │
│   │ └─────────────────────────────────────────────────┘   │     │
│   │                                                       │     │
│   │               [✓ Allow]  [✗ Deny]                     │     │
│   └───────────────────────────────────────────────────────┘     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ [Send] │
│ │ Type a message...                                    │        │
│ └─────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### 1. Credential Management

- API keys stored encrypted using Fernet (symmetric encryption)
- Encryption key derived from `SECRET_KEY` environment variable
- Credentials never returned in API responses (write-only)
- Keys decrypted only at execution time in memory

### 2. Scope Enforcement

- All operations pass through ScopeGuard before execution
- Scope violations logged for security auditing
- Deny-by-default: actions not explicitly permitted are blocked
- Path traversal protection in file operations

### 3. Rate Limiting

- Per-agent rate limits enforced
- Token usage tracked per session
- Rate limit violations logged and blocked

### 4. Audit Trail

- Every agent action logged with:
  - Timestamp
  - Session and user context
  - Action type and target
  - Permission decision (allowed/denied)
  - Execution time

### 5. Destructive Operation Protection

- Delete operations require explicit `can_delete` permission
- Write operations require confirmation by default
- No access to system files or parent directories
- Agents cannot modify their own configuration

### 6. Network Isolation

- Agents cannot make arbitrary HTTP requests
- Only registered integration endpoints accessible
- Provider API calls made server-side (keys never exposed to client)

---

## Implementation Phases

### Phase 1: Foundation -- COMPLETE (2026-02-06)

**Backend:**
- [x] Add database models (Agent, AgentCredential, AgentSession, AgentActionLog)
- [x] Create Alembic migration (009_add_agent_tables)
- [x] Implement ScopeGuard (`backend/codex/agents/scope.py`)
- [x] Create basic CRUD endpoints for agents (`backend/codex/api/routes/agents.py`)
- [x] Add credential encryption utilities (`backend/codex/agents/crypto.py` -- Fernet)
- [x] Add Workspace.agents relationship

**Frontend:**
- [ ] Add agent service to API client
- [ ] Create AgentConfig component
- [ ] Add agent management page

### Phase 2: Execution Engine -- BACKEND COMPLETE (2026-02-06)

**Backend:**
- [x] Implement LiteLLM provider adapter (replaces per-provider adapters)
      - `backend/codex/agents/provider.py` -- single `LiteLLMProvider` class
      - Supports OpenAI, Anthropic, Ollama, Azure, Bedrock, and 100+ others
- [x] Build ToolRouter with file operations (`backend/codex/agents/tools.py`)
      - Tools: read_file, write_file, create_file, delete_file, list_files, search_content, get_file_metadata
      - `get_tool_definitions_for_litellm()` outputs OpenAI function-calling format
- [x] Create AgentEngine orchestration (`backend/codex/agents/engine.py`)
      - Tool-use loop with iteration limit (default 20)
      - Auto-generates system prompt from agent scope
      - Token usage and API call tracking
- [x] Create session message endpoint (`POST /sessions/{id}/message`)
- [x] 40 passing tests (`backend/tests/test_agents.py`)

**Changes from original design:**
- Replaced abstract `ProviderAdapter` + 3 subclasses with single `LiteLLMProvider`
- Removed `anthropic`, `openai` SDK dependencies; added `litellm`, `cryptography`
- Added `delete_file` tool (not in original design)
- Removed `update_file_properties` tool (deferred -- requires frontmatter integration)
- Tools output OpenAI function-calling format rather than raw `ToolDefinition` objects
- Agent model gained `system_prompt` field for user-customizable system prompts
- Models use SQLModel (project convention) instead of raw SQLAlchemy Mapped columns

**Frontend:**
- [ ] Create AgentChat component
- [ ] Implement message rendering
- [ ] Add pending action confirmation UI

### Phase 3: Integration & Polish (1 week)

**Backend:**
- [ ] Add rate limiting middleware (fields exist on model, enforcement not yet wired)
- [x] Implement action logging (AgentActionLog persisted after each session)
- [x] Add session management endpoints (start, cancel, get, list, logs)
- [ ] WebSocket support for real-time updates (optional)
- [ ] `POST /sessions/{id}/confirm` endpoint (confirmation modeled but auto-confirmed in engine loop)

**Frontend:**
- [ ] AgentActivityLog component
- [ ] AgentScopeEditor with visual folder picker
- [ ] Integration with notebook file browser

### Phase 4: Extensions (Future)

- [x] Ollama support via LiteLLM (use model string `ollama/llama3`, set `api_base` credential)
- [ ] Code execution sandbox
- [ ] Integration with external plugins (`can_access_integrations` flag exists but not wired)
- [ ] Multi-agent workflows
- [ ] Streaming responses (LiteLLM supports streaming; needs API + WebSocket plumbing)
- [ ] Agent templates/presets
- [ ] `update_file_properties` tool (frontmatter/metadata editing)
- [ ] Per-agent rate limit enforcement middleware

---

## Trade-offs and Decisions

### 1. Synchronous vs Async Execution

**Decision:** Synchronous request-response for v1

**Rationale:** Simpler to implement and debug. Async/streaming can be added later.

**Trade-off:** Users may need to wait for long operations.

### 2. Confirmation Model

**Decision:** Opt-in confirmation for write/create operations

**Rationale:** Balance between safety and usability. Agents explain actions before executing.

**Trade-off:** More friction for power users who trust agents.

### 3. Tool Granularity

**Decision:** Coarse-grained tools (read_file, write_file) rather than fine-grained (read_line, insert_at_line)

**Rationale:** Matches LLM capabilities and reduces complexity.

**Trade-off:** Less precise control for complex edits.

### 4. Session State Storage

**Decision:** Store conversation context in database (JSON column)

**Rationale:** Enables session resumption, debugging, and audit.

**Trade-off:** Increased storage; may need cleanup policy.

### 5. Plugin vs Core Feature

**Decision:** Core feature with plugin-like architecture

**Rationale:** Agents need deep integration with file system and auth. Provider adapters are plugin-like.

**Trade-off:** Cannot be fully disabled without code changes.

### 6. LiteLLM vs Per-Provider SDKs (NEW -- decided during implementation)

**Decision:** Use LiteLLM as a single provider adapter instead of writing separate Anthropic, OpenAI, and Ollama adapters.

**Rationale:**
- Eliminates 300+ lines of per-provider translation code
- Removes direct `anthropic` and `openai` SDK dependencies (only `litellm` needed)
- Gives immediate access to 100+ providers (Azure, Bedrock, Vertex AI, Together, Groq, etc.)
- LiteLLM handles format translation, retries, and provider quirks
- All providers use the same OpenAI function-calling tool format

**Trade-off:** Adds `litellm` as a dependency (~80 transitive packages). Less control over provider-specific features (e.g. Anthropic's extended thinking). If LiteLLM has a bug with a specific provider, we depend on upstream fixes.

---

## Open Questions

1. **Token limits and context management:** How to handle long sessions that exceed model context windows?

2. **Cost tracking:** Should we show users estimated costs before executing?

3. **Multi-notebook agents:** Can one agent span multiple notebooks, or should scope be per-notebook?

4. **Shared agents:** Should workspace admins be able to create agents usable by all workspace members?

5. **Agent templates:** Pre-configured agents for common tasks (summarizer, reviewer, etc.)?

---

## Appendix: Alternative Approaches Considered

### A. Plugin-Only Implementation

Use the existing IntegrationPlugin system to add agents.

**Pros:** Reuses existing code, no new database models.

**Cons:** Plugin system not designed for stateful sessions; would require significant refactoring.

### B. External Agent Service

Run agents in a separate microservice.

**Pros:** Better isolation, independent scaling.

**Cons:** Operational complexity, latency, authentication challenges.

### C. Client-Side Agents

Run agent logic in the browser with user's API keys.

**Pros:** No server costs, full user control.

**Cons:** Security (keys exposed), inconsistent execution, no audit trail.

---

## Implementation Notes (2026-02-06)

### Files Created

| File | Purpose |
|------|---------|
| `backend/codex/agents/__init__.py` | Module init with public exports |
| `backend/codex/agents/scope.py` | `ScopeGuard`, `ScopeViolation` -- access boundary enforcement |
| `backend/codex/agents/tools.py` | `ToolRouter`, `ToolDefinition` -- tool dispatch with scope checks |
| `backend/codex/agents/provider.py` | `LiteLLMProvider`, `Message`, `ToolCall`, `AgentResponse` |
| `backend/codex/agents/engine.py` | `AgentEngine` -- tool-use loop orchestration |
| `backend/codex/agents/crypto.py` | Fernet encrypt/decrypt for credential storage |
| `backend/codex/api/schemas_agent.py` | Pydantic request/response schemas |
| `backend/codex/api/routes/agents.py` | REST API routes (`router` + `session_router`) |
| `backend/codex/migrations/workspace/versions/20260206_000000_009_add_agent_tables.py` | DB migration |
| `backend/tests/test_agents.py` | 40 tests (scope, tools, crypto, API integration) |

### Files Modified

| File | Change |
|------|--------|
| `backend/codex/db/models/system.py` | Added `Agent`, `AgentCredential`, `AgentSession`, `AgentActionLog` models; added `Workspace.agents` relationship |
| `backend/codex/db/models/__init__.py` | Added new model exports |
| `backend/codex/main.py` | Registered `/api/v1/agents/` and `/api/v1/sessions/` routers |
| `backend/pyproject.toml` | Added `litellm>=1.30.0` and `cryptography>=42.0.0` dependencies; relaxed Python to `>=3.11` |

### API Endpoint Summary

```
POST   /api/v1/agents/?workspace_id=N          Create agent
GET    /api/v1/agents/?workspace_id=N          List agents
GET    /api/v1/agents/{id}                     Get agent
PUT    /api/v1/agents/{id}                     Update agent
DELETE /api/v1/agents/{id}                     Delete agent
POST   /api/v1/agents/{id}/activate?active=T   Toggle active

POST   /api/v1/agents/{id}/credentials         Set credential (encrypted)
GET    /api/v1/agents/{id}/credentials         List credential keys
DELETE /api/v1/agents/{id}/credentials/{key}   Delete credential

POST   /api/v1/agents/{id}/sessions            Start session
GET    /api/v1/agents/{id}/sessions            List sessions

GET    /api/v1/sessions/{id}                   Get session
POST   /api/v1/sessions/{id}/message           Send message (runs agent)
POST   /api/v1/sessions/{id}/cancel            Cancel session
GET    /api/v1/sessions/{id}/logs              Get action audit logs
```

### Test Coverage

40 tests in `test_agents.py`:
- **ScopeGuard** (9 tests): read/write permissions, path traversal, folder/file-type restrictions, notebook access, wildcard
- **ToolRouter** (10 tests): tool availability by permission, LiteLLM format, file CRUD, search, confirmation, path escape
- **LiteLLMProvider** (1 test): message format conversion
- **Crypto** (2 tests): encrypt/decrypt roundtrip, uniqueness
- **Agent API** (8 tests): CRUD, toggle active, auth required
- **Credential API** (3 tests): set, list, delete
- **Session API** (7 tests): start, list, get, cancel, inactive agent rejection, empty logs

### Known Gaps / Future Work

1. **Rate limiting not enforced** -- `max_requests_per_hour` and `max_tokens_per_request` are stored but not checked at runtime. Needs middleware or pre-call check in `AgentEngine`.
2. **Confirmation endpoint not implemented** -- `POST /sessions/{id}/confirm` is in the design but not yet built. The engine auto-confirms tool calls. Frontend will need this for the pending-action UI.
3. **`update_file_properties` tool deferred** -- Requires integration with the frontmatter/metadata system.
4. **Frontend not started** -- Vue components, Pinia store, and agent service client are designed but not implemented.
5. **WebSocket streaming** -- LiteLLM supports async streaming; needs WebSocket plumbing to deliver incremental responses to the frontend.
6. **No per-workspace agent isolation in queries** -- `list_agents` filters by `workspace_id` query param but doesn't cross-check the current user's workspace permissions.

---

## References

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM Supported Providers](https://docs.litellm.ai/docs/providers)
- [Anthropic Claude API Documentation](https://docs.anthropic.com/claude/reference/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [Codex System Architecture](../architecture.md)

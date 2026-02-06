"""API routes for AI agent management and execution."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.agents.crypto import decrypt_value, encrypt_value
from codex.agents.engine import AgentEngine
from codex.agents.provider import LiteLLMProvider
from codex.agents.scope import ScopeGuard
from codex.agents.tools import ToolRouter
from codex.api.auth import get_current_active_user
from codex.api.schemas_agent import (
    ActionLogResponse,
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    CredentialResponse,
    CredentialSet,
    SessionCreate,
    SessionMessageRequest,
    SessionMessageResponse,
    SessionResponse,
)
from codex.db.database import get_system_session
from codex.db.models import (
    Agent,
    AgentActionLog,
    AgentCredential,
    AgentSession,
    User,
    Workspace,
)
from codex.db.models.base import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_workspace(workspace_id: int, session: AsyncSession) -> Workspace:
    result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


async def _get_agent(agent_id: int, session: AsyncSession) -> Agent:
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def _get_session(session_id: int, db: AsyncSession) -> AgentSession:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    agent_session = result.scalar_one_or_none()
    if not agent_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return agent_session


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: AgentCreate,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Agent:
    """Create a new agent for a workspace."""
    await _get_workspace(workspace_id, session)

    agent = Agent(
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        provider=body.provider,
        model=body.model,
        scope=body.scope,
        can_read=body.can_read,
        can_write=body.can_write,
        can_create=body.can_create,
        can_delete=body.can_delete,
        can_execute_code=body.can_execute_code,
        can_access_integrations=body.can_access_integrations,
        max_requests_per_hour=body.max_requests_per_hour,
        max_tokens_per_request=body.max_tokens_per_request,
        system_prompt=body.system_prompt,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[Agent]:
    """List all agents for a workspace."""
    result = await session.execute(select(Agent).where(Agent.workspace_id == workspace_id))
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Agent:
    """Get agent details."""
    return await _get_agent(agent_id, session)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    body: AgentUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Agent:
    """Update an agent's configuration."""
    agent = await _get_agent(agent_id, session)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    agent.updated_at = utc_now()

    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> None:
    """Delete an agent."""
    agent = await _get_agent(agent_id, session)
    await session.delete(agent)
    await session.commit()


@router.post("/{agent_id}/activate", response_model=AgentResponse)
async def toggle_agent_active(
    agent_id: int,
    active: bool = True,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Agent:
    """Activate or deactivate an agent."""
    agent = await _get_agent(agent_id, session)
    agent.is_active = active
    agent.updated_at = utc_now()
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


# ---------------------------------------------------------------------------
# Agent Credentials
# ---------------------------------------------------------------------------


@router.post("/{agent_id}/credentials", response_model=CredentialResponse, status_code=201)
async def set_credential(
    agent_id: int,
    body: CredentialSet,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> AgentCredential:
    """Set or update an agent credential (write-only)."""
    await _get_agent(agent_id, session)

    # Check for existing credential with same key_name
    result = await session.execute(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent_id,
            AgentCredential.key_name == body.key_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.encrypted_value = encrypt_value(body.value)
        existing.created_at = utc_now()
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    cred = AgentCredential(
        agent_id=agent_id,
        key_name=body.key_name,
        encrypted_value=encrypt_value(body.value),
    )
    session.add(cred)
    await session.commit()
    await session.refresh(cred)
    return cred


@router.get("/{agent_id}/credentials", response_model=list[CredentialResponse])
async def list_credentials(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[AgentCredential]:
    """List credential keys for an agent (values are never returned)."""
    await _get_agent(agent_id, session)
    result = await session.execute(
        select(AgentCredential).where(AgentCredential.agent_id == agent_id)
    )
    return list(result.scalars().all())


@router.delete("/{agent_id}/credentials/{key_name}", status_code=204)
async def delete_credential(
    agent_id: int,
    key_name: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> None:
    """Delete a credential by key name."""
    result = await session.execute(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent_id,
            AgentCredential.key_name == key_name,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    await session.delete(cred)
    await session.commit()


# ---------------------------------------------------------------------------
# Agent Sessions
# ---------------------------------------------------------------------------


@router.post("/{agent_id}/sessions", response_model=SessionResponse, status_code=201)
async def start_session(
    agent_id: int,
    body: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> AgentSession:
    """Start a new agent execution session."""
    agent = await _get_agent(agent_id, session)
    if not agent.is_active:
        raise HTTPException(status_code=400, detail="Agent is not active")

    agent_session = AgentSession(
        agent_id=agent_id,
        task_id=body.task_id,
        user_id=current_user.id,
        status="pending",
        context={"notebook_path": body.notebook_path},
        files_modified=[],
    )
    session.add(agent_session)
    await session.commit()
    await session.refresh(agent_session)
    return agent_session


@router.get("/{agent_id}/sessions", response_model=list[SessionResponse])
async def list_sessions(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[AgentSession]:
    """List sessions for an agent."""
    result = await session.execute(
        select(AgentSession).where(AgentSession.agent_id == agent_id).order_by(AgentSession.started_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Session operations (top-level /sessions/ routes)
# ---------------------------------------------------------------------------

session_router = APIRouter()


@session_router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_system_session),
) -> AgentSession:
    """Get session details."""
    return await _get_session(session_id, db)


@session_router.post("/{session_id}/message", response_model=SessionMessageResponse)
async def send_message(
    session_id: int,
    body: SessionMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_system_session),
) -> SessionMessageResponse:
    """Send a message to an agent session and get a response.

    This triggers the agent execution loop which may involve multiple
    tool calls before returning a final response.
    """
    agent_session = await _get_session(session_id, db)

    if agent_session.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Session is already {agent_session.status}")

    # Load the agent
    result = await db.execute(select(Agent).where(Agent.id == agent_session.agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get API key from credentials
    cred_result = await db.execute(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent.id,
            AgentCredential.key_name == "api_key",
        )
    )
    api_key_cred = cred_result.scalar_one_or_none()
    api_key = decrypt_value(api_key_cred.encrypted_value) if api_key_cred else None

    # Get optional api_base
    base_result = await db.execute(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent.id,
            AgentCredential.key_name == "api_base",
        )
    )
    api_base_cred = base_result.scalar_one_or_none()
    api_base = decrypt_value(api_base_cred.encrypted_value) if api_base_cred else None

    # Build the LiteLLM model string
    model = agent.model
    if agent.provider == "ollama" and not model.startswith("ollama/"):
        model = f"ollama/{model}"

    notebook_path = agent_session.context.get("notebook_path", "")
    if not notebook_path:
        raise HTTPException(status_code=400, detail="Session missing notebook_path in context")

    # Set up execution components
    scope_guard = ScopeGuard(agent)
    tool_router = ToolRouter(scope_guard, agent_session, notebook_path)
    provider = LiteLLMProvider(model=model, api_key=api_key, api_base=api_base)
    engine = AgentEngine(agent=agent, provider=provider, tool_router=tool_router, session=agent_session)

    # Update session status
    agent_session.status = "running"
    db.add(agent_session)
    await db.commit()

    try:
        response_text = await engine.run(body.content)

        # Persist session updates
        agent_session.status = "completed"
        agent_session.completed_at = utc_now()
        agent_session.context = {
            **agent_session.context,
            "messages": engine.get_messages(),
        }
        db.add(agent_session)

        # Persist action logs
        for log_entry in tool_router.get_action_logs():
            action_log = AgentActionLog(
                session_id=agent_session.id,
                **log_entry,
            )
            db.add(action_log)

        await db.commit()
        await db.refresh(agent_session)

        return SessionMessageResponse(
            session_id=agent_session.id,
            status=agent_session.status,
            response=response_text,
            messages=engine.get_messages(),
            action_logs=tool_router.get_action_logs(),
        )

    except Exception as e:
        logger.exception("Agent execution error")
        agent_session.status = "failed"
        agent_session.error_message = str(e)[:500]
        db.add(agent_session)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")


@session_router.post("/{session_id}/cancel", response_model=SessionResponse)
async def cancel_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_system_session),
) -> AgentSession:
    """Cancel an active session."""
    agent_session = await _get_session(session_id, db)
    if agent_session.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Session is already {agent_session.status}")

    agent_session.status = "cancelled"
    agent_session.completed_at = utc_now()
    db.add(agent_session)
    await db.commit()
    await db.refresh(agent_session)
    return agent_session


@session_router.get("/{session_id}/logs", response_model=list[ActionLogResponse])
async def get_session_logs(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_system_session),
) -> list[AgentActionLog]:
    """Get action logs for a session."""
    await _get_session(session_id, db)
    result = await db.execute(
        select(AgentActionLog).where(AgentActionLog.session_id == session_id).order_by(AgentActionLog.created_at)
    )
    return list(result.scalars().all())

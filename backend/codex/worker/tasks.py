"""ARQ task functions for background job execution."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

logger = logging.getLogger(__name__)

# Registry of job type handlers — extend this dict to add new job types.
JOB_TYPE_HANDLERS: dict[str, str] = {
    "agent": "_handle_agent_job",
}


async def run_job(ctx: dict, task_id: int, **kwargs: Any) -> dict[str, Any]:
    """Generic job dispatcher — routes to the correct handler by job_type.

    This is the primary entry point for all background jobs.  The ``job_type``
    field on the :class:`~codex.db.models.Task` record determines which handler
    is invoked.
    """
    session_maker = ctx["session_maker"]
    async with session_maker() as session:
        task = await _load_task(session, task_id)
        if task is None:
            return {"status": "error", "detail": f"Task {task_id} not found"}

        handler_name = JOB_TYPE_HANDLERS.get(task.job_type)
        if handler_name is None:
            await _fail_task(session, task, f"Unknown job_type: {task.job_type}")
            return {"status": "error", "detail": f"Unknown job_type: {task.job_type}"}

        handler = globals()[handler_name]
        return await handler(ctx, session, task, **kwargs)


async def execute_agent_task(ctx: dict, task_id: int) -> dict[str, Any]:
    """Convenience wrapper — runs a task with job_type='agent'."""
    return await run_job(ctx, task_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_task(session: AsyncSession, task_id: int):
    """Load a Task from the database."""
    from codex.db.models import Task

    result = await session.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def _set_task_status(session: AsyncSession, task, status: str) -> None:
    """Update task status and timestamps."""
    task.status = status
    task.updated_at = datetime.now(UTC)
    if status == "completed":
        task.completed_at = datetime.now(UTC)
    session.add(task)
    await session.commit()
    await session.refresh(task)


async def _fail_task(session: AsyncSession, task, error_msg: str) -> None:
    """Mark a task as failed."""
    logger.error("Task %s failed: %s", task.id, error_msg)
    task.status = "failed"
    task.updated_at = datetime.now(UTC)
    session.add(task)
    await session.commit()


async def _handle_agent_job(
    ctx: dict,
    session: AsyncSession,
    task,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute an agent task — reuses the existing AgentEngine pipeline.

    The task's ``assigned_to`` field must reference a valid Agent id.  The
    worker will:
      1. Mark the task *in_progress*.
      2. Create or reuse an AgentSession linked to the task.
      3. Run the AgentEngine tool-use loop.
      4. Persist results and mark the task *completed* (or *failed*).
    """
    from codex.agents.crypto import decrypt_value
    from codex.agents.engine import AgentEngine
    from codex.agents.provider import CompletionProvider
    from codex.agents.scope import ScopeGuard
    from codex.agents.tools import ToolRouter
    from codex.db.models import Agent, AgentActionLog, AgentCredential, AgentSession
    from codex.db.models.base import utc_now

    # --- Resolve the agent ------------------------------------------------
    if not task.assigned_to:
        await _fail_task(session, task, "No agent assigned (assigned_to is empty)")
        return {"status": "error", "detail": "No agent assigned"}

    try:
        agent_id = int(task.assigned_to)
    except (ValueError, TypeError):
        await _fail_task(session, task, f"assigned_to is not a valid agent id: {task.assigned_to}")
        return {"status": "error", "detail": "Invalid agent id"}

    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        await _fail_task(session, task, f"Agent {agent_id} not found")
        return {"status": "error", "detail": "Agent not found"}

    if not agent.is_active:
        await _fail_task(session, task, f"Agent {agent_id} is not active")
        return {"status": "error", "detail": "Agent not active"}

    # --- Mark in_progress -------------------------------------------------
    await _set_task_status(session, task, "in_progress")

    # --- Resolve credentials ----------------------------------------------
    cred_result = await session.execute(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent.id,
            AgentCredential.key_name == "api_key",
        )
    )
    api_key_cred = cred_result.scalar_one_or_none()
    api_key = decrypt_value(api_key_cred.encrypted_value) if api_key_cred else None

    base_result = await session.execute(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent.id,
            AgentCredential.key_name == "api_base",
        )
    )
    api_base_cred = base_result.scalar_one_or_none()
    api_base = decrypt_value(api_base_cred.encrypted_value) if api_base_cred else None

    model = agent.model
    if agent.provider == "ollama" and not model.startswith("ollama/"):
        model = f"ollama/{model}"

    # --- Create an AgentSession -------------------------------------------
    # Use the task description as the notebook_path context if available,
    # otherwise fall back to an empty string.
    notebook_path = kwargs.get("notebook_path", task.description or "")

    agent_session = AgentSession(
        agent_id=agent.id,
        task_id=task.id,
        user_id=None,
        status="running",
        context={"notebook_path": notebook_path, "source": "worker"},
        files_modified=[],
    )
    session.add(agent_session)
    await session.commit()
    await session.refresh(agent_session)

    # --- Build execution components ---------------------------------------
    scope_guard = ScopeGuard(agent)
    tool_router = ToolRouter(scope_guard, agent_session, notebook_path)
    provider = CompletionProvider(model=model, api_key=api_key, api_base=api_base)
    engine = AgentEngine(agent=agent, provider=provider, tool_router=tool_router, session=agent_session)

    # --- Run the agent ----------------------------------------------------
    try:
        prompt = task.title
        if task.description:
            prompt = f"{task.title}\n\n{task.description}"

        response_text = await engine.run(prompt)

        # Persist session results
        agent_session.status = "completed"
        agent_session.completed_at = utc_now()
        agent_session.context = {
            **agent_session.context,
            "messages": engine.get_messages(),
        }
        session.add(agent_session)

        # Persist action logs
        for log_entry in tool_router.get_action_logs():
            action_log = AgentActionLog(session_id=agent_session.id, **log_entry)
            session.add(action_log)

        await _set_task_status(session, task, "completed")

        logger.info("Task %s completed successfully", task.id)
        return {
            "status": "completed",
            "task_id": task.id,
            "session_id": agent_session.id,
            "response": response_text[:500],
        }

    except Exception as exc:
        logger.exception("Task %s agent execution failed", task.id)
        agent_session.status = "failed"
        agent_session.error_message = str(exc)[:500]
        session.add(agent_session)
        await session.commit()

        await _fail_task(session, task, str(exc)[:500])
        return {"status": "failed", "task_id": task.id, "error": str(exc)[:500]}

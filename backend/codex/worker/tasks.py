"""ARQ task functions for background job execution."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from arq.worker import Retry
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

logger = logging.getLogger(__name__)

# Webhook delivery tuning (issue #536) — exponential backoff between retries,
# capped so a persistently-down bot doesn't push deferrals out for hours.
WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_BACKOFF_BASE_SECONDS = 5
WEBHOOK_BACKOFF_CAP_SECONDS = 300

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


# ---------------------------------------------------------------------------
# Notification fanout (issue #530)
# ---------------------------------------------------------------------------

RecipientResolver = Callable[[AsyncSession, Any], Awaitable[set[int]]]


async def _resolve_comment_recipients(session: AsyncSession, event: Any) -> set[int]:
    """Recipients for comment.* events: mentioned principals + thread participants
    + non-muted workspace watchers, minus the actor (actors never notify themselves).

    Mute only suppresses the workspace-watcher path — a muted user who is directly
    mentioned or participating in the thread is still notified.
    """
    from codex.db.models import Comment, WorkspaceWatch

    subject = event.subject or {}
    thread_root_id = subject.get("thread_id")
    mentioned_ids = {int(uid) for uid in subject.get("mentioned_user_ids") or []}

    participant_ids: set[int] = set()
    if thread_root_id is not None:
        result = await session.execute(
            select(Comment.author_id).where(
                Comment.deleted_at.is_(None),
                (Comment.id == thread_root_id) | (Comment.thread_id == thread_root_id),
            )
        )
        participant_ids = {row[0] for row in result.all()}

    watcher_result = await session.execute(
        select(WorkspaceWatch.user_id).where(
            WorkspaceWatch.workspace_id == event.workspace_id,
            WorkspaceWatch.muted.is_(False),
        )
    )
    watcher_ids = {row[0] for row in watcher_result.all()}

    recipients = mentioned_ids | participant_ids | watcher_ids
    recipients.discard(event.actor_id)
    return recipients


async def _resolve_permission_granted_recipients(session: AsyncSession, event: Any) -> set[int]:
    """Recipients for permission.granted events: the grantee only."""
    subject = event.subject or {}
    grantee_id = subject.get("grantee_id")
    recipients = {int(grantee_id)} if grantee_id is not None else set()
    recipients.discard(event.actor_id)
    return recipients


async def _resolve_sync_conflict_recipients(session: AsyncSession, event: Any) -> set[int]:
    """Recipients for sync.conflict events: both writers whose changes collided (issue #543).

    Unlike the other resolvers, the acting writer is *not* discarded here — both sides of the
    race need to know their write turned out to conflict, including the one who caused it.
    """
    subject = event.subject or {}
    return {int(uid) for uid in subject.get("writer_ids") or []}


# Registry of recipient resolvers by event kind — extend this dict to support new kinds.
RECIPIENT_RESOLVERS: dict[str, RecipientResolver] = {
    "comment.created": _resolve_comment_recipients,
    "comment.mention": _resolve_comment_recipients,
    "comment.resolved": _resolve_comment_recipients,
    "permission.granted": _resolve_permission_granted_recipients,
    "sync.conflict": _resolve_sync_conflict_recipients,
}


# ---------------------------------------------------------------------------
# Bot mention dispatch — hosted task enqueue / external webhook delivery
# (issue #535 hosted path, issue #536 external webhook path, design doc §2.1
# and §8 phase 3)
# ---------------------------------------------------------------------------


async def _build_comment_context(session: AsyncSession, comment: Any) -> dict[str, Any]:
    """Serialize a comment plus its thread ancestry for a bot mention payload.

    Threads are flattened one level deep (see `Comment.thread_id`), so the
    "parent chain" is every earlier comment in the thread (the root, plus any
    replies before this one) — `comment` itself is excluded since it's carried
    separately as the triggering mention.
    """
    from codex.db.models import Comment, User

    root_id = comment.thread_id or comment.id
    result = await session.execute(
        select(Comment, User.username)
        .join(User, User.id == Comment.author_id)
        .where(
            Comment.deleted_at.is_(None),
            (Comment.id == root_id) | (Comment.thread_id == root_id),
            Comment.id != comment.id,
        )
        .order_by(Comment.created_at)
    )
    parent_chain = [
        {
            "comment_id": c.id,
            "author_id": c.author_id,
            "author_username": username,
            "body": c.body,
            "created_at": c.created_at.isoformat(),
        }
        for c, username in result.all()
    ]
    return {
        "comment_id": comment.id,
        "block_id": comment.block_id,
        "notebook_id": comment.notebook_id,
        "thread_id": comment.thread_id or comment.id,
        "parent_chain": parent_chain,
    }


async def _enqueue_bot_mention_tasks(ctx: dict, session: AsyncSession, event: Any) -> int:
    """Wake bot principals mentioned in a comment.

    `Agent.kind == "hosted"` bots run inside Codex: this creates a `Task` row
    and enqueues the existing ARQ agent-execution pipeline, same as a manually
    created agent task. `Agent.kind == "external"` bots (e.g. a Claude Code
    session woken from outside) instead get a signed webhook delivery — Codex
    never runs their brain, it just wakes them over HTTP.

    Idempotent on retry: a hosted bot already carrying a Task for this comment
    (matched via `task_metadata.comment_id`) is skipped, and an external bot
    that already has an `AgentWebhookDelivery` row for this event is skipped
    too, so a retried `fanout_event` doesn't double-wake a bot.

    Returns the number of hosted Tasks enqueued (external webhook deliveries
    aren't counted here — see `deliver_webhook`'s own audit trail for those).
    """
    from codex.db.models import Agent, AgentWebhookDelivery, Comment, Task, User, UserKind

    subject = event.subject or {}
    mentioned_ids = {int(uid) for uid in subject.get("mentioned_user_ids") or []}
    if not mentioned_ids:
        return 0

    comment_id = subject.get("comment_id")
    comment = await session.get(Comment, comment_id) if comment_id is not None else None
    if comment is None:
        return 0

    result = await session.execute(
        select(User, Agent)
        .join(Agent, Agent.principal_id == User.id)
        .where(
            User.id.in_(mentioned_ids),
            User.kind == UserKind.BOT.value,
            User.is_active.is_(True),
            Agent.is_active.is_(True),
        )
    )
    bot_agents = result.all()
    if not bot_agents:
        return 0

    author = await session.get(User, comment.author_id)
    comment_context = await _build_comment_context(session, comment)
    arq_pool = ctx.get("redis")
    hosted_enqueued = 0

    for bot, agent in bot_agents:
        if agent.kind == "external":
            existing_delivery = await session.execute(
                select(AgentWebhookDelivery.id).where(
                    AgentWebhookDelivery.agent_id == agent.id,
                    AgentWebhookDelivery.event_id == event.id,
                )
            )
            if existing_delivery.first() is not None:
                continue

            if arq_pool is None:
                logger.warning("Skipping webhook delivery for agent %s — task queue unavailable", agent.id)
                continue
            payload = {
                "event": event.kind,
                "event_id": event.id,
                "workspace_id": event.workspace_id,
                "comment": comment_context,
                "mention": {
                    "mentioned_principal_id": bot.id,
                    "mentioned_username": bot.username,
                    "comment_author_id": comment.author_id,
                    "comment_author_username": author.username if author else None,
                },
            }
            await arq_pool.enqueue_job("deliver_webhook", agent.id, event.id, payload)
        else:
            existing_result = await session.execute(
                select(Task).where(
                    Task.workspace_id == event.workspace_id,
                    Task.task_type == "bot_mention",
                    Task.assigned_to == str(agent.id),
                )
            )
            if any(
                json.loads(t.task_metadata or "{}").get("comment_id") == comment.id
                for t in existing_result.scalars().all()
            ):
                continue

            task = Task(
                workspace_id=event.workspace_id,
                title=f"Mentioned in a comment on block {comment.block_id}",
                description=comment.body,
                task_type="bot_mention",
                assigned_to=str(agent.id),
                job_type="agent",
                task_metadata=json.dumps({**comment_context, "mentioned_principal_id": bot.id}),
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            hosted_enqueued += 1

            if arq_pool is not None:
                job = await arq_pool.enqueue_job("run_job", task.id)
                if job is not None:
                    task.job_id = job.job_id
                    session.add(task)
                    await session.commit()
            else:
                logger.warning("Task %s created but not enqueued — task queue unavailable", task.id)

    return hosted_enqueued


def _sign_webhook_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def deliver_webhook(ctx: dict, agent_id: int, event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Deliver a signed webhook to an external bot's `Agent.webhook_url` (issue #536).

    Every attempt is recorded in `AgentWebhookDelivery` for audit. On failure,
    retries with exponential backoff (capped at `WEBHOOK_BACKOFF_CAP_SECONDS`)
    up to `Agent.webhook_max_retries` attempts by raising `arq.worker.Retry`,
    which reschedules this same job — `ctx["job_try"]` tracks the attempt
    number across those retries.
    """
    from codex.agents.crypto import decrypt_value
    from codex.db.models import Agent, AgentWebhookDelivery

    attempt = ctx.get("job_try", 1)
    session_maker = ctx["session_maker"]

    should_retry = False
    async with session_maker() as session:
        agent = await session.get(Agent, agent_id)
        if agent is None or not agent.is_active:
            logger.warning("Webhook delivery skipped — agent %s missing or inactive", agent_id)
            return {"status": "skipped", "detail": "agent missing or inactive"}

        if not agent.webhook_url or not agent.webhook_secret_encrypted:
            logger.warning("Webhook delivery skipped — agent %s has no webhook configured", agent_id)
            return {"status": "skipped", "detail": "webhook not configured"}

        body = {
            **payload,
            "delivery": {
                "attempt": attempt,
                "max_retries": agent.webhook_max_retries,
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        }
        body_bytes = json.dumps(body, sort_keys=True).encode()
        secret = decrypt_value(agent.webhook_secret_encrypted)
        signature = _sign_webhook_payload(secret, body_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Codex-Event": str(payload.get("event", "comment.mention")),
            "X-Codex-Signature-256": f"sha256={signature}",
            "X-Codex-Delivery-Attempt": str(attempt),
        }

        delivery = AgentWebhookDelivery(agent_id=agent.id, event_id=event_id, attempt=attempt, status="pending")
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
                response = await client.post(agent.webhook_url, content=body_bytes, headers=headers)
            delivery.response_status_code = response.status_code
            if 200 <= response.status_code < 300:
                delivery.status = "delivered"
                session.add(delivery)
                await session.commit()
                return {"status": "delivered", "agent_id": agent.id, "attempt": attempt}
            delivery.status = "failed"
            delivery.error = f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            delivery.status = "failed"
            delivery.error = str(exc)[:500]

        session.add(delivery)
        await session.commit()

        should_retry = attempt < agent.webhook_max_retries
        max_retries = agent.webhook_max_retries

    if should_retry:
        backoff = min(WEBHOOK_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), WEBHOOK_BACKOFF_CAP_SECONDS)
        raise Retry(defer=backoff)

    logger.error("Webhook delivery to agent %s failed permanently after %s attempts", agent_id, max_retries)
    return {"status": "failed", "agent_id": agent_id, "attempt": attempt}


async def fanout_event(ctx: dict, event_id: int) -> dict[str, Any]:
    """Fan an `Event` out into `Notification` rows for its resolved recipients.

    Idempotent on retry: recipients already notified for this event are loaded
    first and skipped, and each insert is individually committed so a unique-
    constraint violation from a concurrent retry only rolls back that one row
    rather than the whole batch.

    For `comment.mention` events, also wakes each mentioned bot principal —
    a hosted Agent (issue #535) gets a Task enqueued, an external Agent
    (issue #536) gets a signed webhook delivery — see
    `_enqueue_bot_mention_tasks`.
    """
    from codex.core.events import serialize_notification
    from codex.core.websocket import connection_manager, principal_channel
    from codex.db.models import Event, Notification

    session_maker = ctx["session_maker"]
    async with session_maker() as session:
        event = await session.get(Event, event_id)
        if event is None:
            return {"status": "error", "detail": f"Event {event_id} not found"}

        resolver = RECIPIENT_RESOLVERS.get(event.kind)
        if resolver is None:
            logger.warning("No recipient resolver registered for event kind %r", event.kind)
            return {"status": "error", "detail": f"Unknown event kind: {event.kind}"}

        recipients = await resolver(session, event)

        bot_tasks_enqueued = 0
        if event.kind == "comment.mention":
            bot_tasks_enqueued = await _enqueue_bot_mention_tasks(ctx, session, event)

        if not recipients:
            return {
                "status": "completed",
                "event_id": event.id,
                "notifications_created": 0,
                "bot_tasks_enqueued": bot_tasks_enqueued,
            }

        existing_result = await session.execute(
            select(Notification.recipient_id).where(Notification.event_id == event.id)
        )
        existing_recipient_ids = {row[0] for row in existing_result.all()}

        created = 0
        for recipient_id in sorted(recipients - existing_recipient_ids):
            notification = Notification(event_id=event.id, recipient_id=recipient_id)
            session.add(notification)
            try:
                await session.commit()
                created += 1
            except IntegrityError:
                # A concurrent retry already inserted this notification — safe to skip.
                await session.rollback()
                continue

            await session.refresh(notification)
            await connection_manager.broadcast(
                principal_channel(recipient_id),
                {"type": "notification", "notification": serialize_notification(notification, event)},
            )

        return {
            "status": "completed",
            "event_id": event.id,
            "notifications_created": created,
            "bot_tasks_enqueued": bot_tasks_enqueued,
        }

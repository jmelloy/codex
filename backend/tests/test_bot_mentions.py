"""Tests for bot mention detection -> Task enqueue for hosted agents (issue #535).

Mentioning a bot with a *hosted* Agent config should, once the comment's
`comment.mention` event is fanned out, enqueue a Task (with comment/thread
context) via the ARQ queue. Bots without a hosted Agent (no Agent at all, or
an *external*/webhook-driven one) must not get a task.
"""

import json
from unittest.mock import AsyncMock

from sqlmodel import select

from codex.db.database import async_session_maker
from codex.db.models import Event, Task
from codex.worker.tasks import fanout_event


def _create_bot(test_client, headers, workspace_slug, display_name="Review Bot"):
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/bots",
        json={"display_name": display_name},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_agent(test_client, headers, workspace_id, principal_id, kind="hosted"):
    resp = test_client.post(
        "/api/v1/agents/",
        params={"workspace_id": workspace_id},
        json={
            "name": "Review Bot Agent",
            "provider": "openai",
            "model": "gpt-4o",
            "kind": kind,
            "principal_id": principal_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_block(test_client, headers, workspace_slug, notebook_slug):
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/blocks/pages",
        json={"title": "Discussion Page"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["block_id"]


def _post_comment(test_client, headers, workspace_slug, notebook_slug, block_id, body):
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/blocks/{block_id}/comments/",
        json={"body": body},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _latest_mention_event(comment_id):
    async with async_session_maker() as session:
        result = await session.execute(select(Event).where(Event.kind == "comment.mention").order_by(Event.id.desc()))
        for event in result.scalars().all():
            if event.subject.get("comment_id") == comment_id:
                return event
    return None


async def test_hosted_bot_mention_enqueues_task(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    bot = _create_bot(test_client, headers, workspace["slug"])
    agent = _create_agent(test_client, headers, workspace["id"], principal_id=bot["id"], kind="hosted")
    block_id = _create_block(test_client, headers, workspace["slug"], notebook["slug"])

    comment = _post_comment(
        test_client, headers, workspace["slug"], notebook["slug"], block_id, f"@{bot['username']} take a look"
    )
    assert any(m["mentioned_principal_id"] == bot["id"] for m in comment["mentions"])

    event = await _latest_mention_event(comment["id"])
    assert event is not None

    mock_redis = AsyncMock()
    mock_job = AsyncMock()
    mock_job.job_id = "job-123"
    mock_redis.enqueue_job.return_value = mock_job

    ctx = {"session_maker": async_session_maker, "redis": mock_redis}
    result = await fanout_event(ctx, event.id)
    assert result["status"] == "completed"
    assert result["bot_tasks_enqueued"] == 1

    async with async_session_maker() as session:
        task_result = await session.execute(
            select(Task).where(Task.task_type == "bot_mention", Task.assigned_to == str(agent["id"]))
        )
        tasks = task_result.scalars().all()
        assert len(tasks) == 1
        task = tasks[0]
        assert task.workspace_id == workspace["id"]
        assert task.job_id == "job-123"

        metadata = json.loads(task.task_metadata)
        assert metadata["comment_id"] == comment["id"]
        assert metadata["block_id"] == block_id
        assert metadata["mentioned_principal_id"] == bot["id"]
        assert metadata["parent_chain"] == []

    mock_redis.enqueue_job.assert_called_once_with("run_job", task.id)


async def test_external_bot_mention_does_not_enqueue_task(test_client, auth_headers, workspace_and_notebook):
    """A bot backed by an *external* (webhook-driven) agent is not enqueued here."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    bot = _create_bot(test_client, headers, workspace["slug"], display_name="Webhook Bot")
    _create_agent(test_client, headers, workspace["id"], principal_id=bot["id"], kind="external")
    block_id = _create_block(test_client, headers, workspace["slug"], notebook["slug"])

    comment = _post_comment(
        test_client, headers, workspace["slug"], notebook["slug"], block_id, f"@{bot['username']} ping"
    )

    event = await _latest_mention_event(comment["id"])
    assert event is not None

    mock_redis = AsyncMock()
    ctx = {"session_maker": async_session_maker, "redis": mock_redis}
    result = await fanout_event(ctx, event.id)
    assert result["bot_tasks_enqueued"] == 0
    mock_redis.enqueue_job.assert_not_called()


async def test_bot_mention_without_agent_does_not_enqueue_task(test_client, auth_headers, workspace_and_notebook):
    """A bot principal with no Agent config at all is just a plain mention/notification."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    bot = _create_bot(test_client, headers, workspace["slug"], display_name="Configless Bot")
    block_id = _create_block(test_client, headers, workspace["slug"], notebook["slug"])

    comment = _post_comment(
        test_client, headers, workspace["slug"], notebook["slug"], block_id, f"@{bot['username']} hello"
    )

    event = await _latest_mention_event(comment["id"])
    assert event is not None

    mock_redis = AsyncMock()
    ctx = {"session_maker": async_session_maker, "redis": mock_redis}
    result = await fanout_event(ctx, event.id)
    assert result["bot_tasks_enqueued"] == 0
    mock_redis.enqueue_job.assert_not_called()


async def test_bot_mention_task_includes_parent_chain(test_client, auth_headers, workspace_and_notebook):
    """The enqueued task's context includes the thread's earlier comments."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    bot = _create_bot(test_client, headers, workspace["slug"])
    agent = _create_agent(test_client, headers, workspace["id"], principal_id=bot["id"], kind="hosted")
    block_id = _create_block(test_client, headers, workspace["slug"], notebook["slug"])

    root = _post_comment(test_client, headers, workspace["slug"], notebook["slug"], block_id, "Initial thought")
    reply = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/{block_id}/comments/",
        json={"body": f"@{bot['username']} what do you think?", "thread_id": root["id"]},
        headers=headers,
    )
    assert reply.status_code == 201, reply.text
    reply_comment = reply.json()

    event = await _latest_mention_event(reply_comment["id"])
    assert event is not None

    mock_redis = AsyncMock()
    mock_job = AsyncMock()
    mock_job.job_id = "job-456"
    mock_redis.enqueue_job.return_value = mock_job

    ctx = {"session_maker": async_session_maker, "redis": mock_redis}
    result = await fanout_event(ctx, event.id)
    assert result["bot_tasks_enqueued"] == 1

    async with async_session_maker() as session:
        task_result = await session.execute(
            select(Task).where(Task.task_type == "bot_mention", Task.assigned_to == str(agent["id"]))
        )
        task = task_result.scalars().one()
        metadata = json.loads(task.task_metadata)
        assert metadata["comment_id"] == reply_comment["id"]
        assert [entry["comment_id"] for entry in metadata["parent_chain"]] == [root["id"]]
        assert metadata["parent_chain"][0]["body"] == "Initial thought"

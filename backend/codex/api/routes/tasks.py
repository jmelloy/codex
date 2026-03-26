"""Task routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.workspaces import get_workspace_by_slug_or_id
from codex.db.database import get_system_session
from codex.db.models import Task, User, Workspace

router = APIRouter()
nested_router = APIRouter()


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    workspace_id: int
    title: str
    description: str | None = None


class TaskCreateNested(BaseModel):
    """Request body for creating a task under a workspace route."""

    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
    """Request body for updating a task."""

    status: str | None = None
    assigned_to: str | None = None


async def _verify_workspace_access(workspace_id: int, current_user: User, session: AsyncSession) -> Workspace:
    """Verify the current user owns the workspace."""
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def _list_tasks(workspace_id: int, current_user: User, session: AsyncSession) -> list[Task]:
    await _verify_workspace_access(workspace_id, current_user, session)
    result = await session.execute(select(Task).where(Task.workspace_id == workspace_id))
    return result.scalars().all()


async def _get_task(task_id: int, current_user: User, session: AsyncSession) -> Task:
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _verify_workspace_access(task.workspace_id, current_user, session)
    return task


async def _create_task(workspace_id: int, title: str, description: str | None, current_user: User, session: AsyncSession) -> Task:
    await _verify_workspace_access(workspace_id, current_user, session)
    task = Task(workspace_id=workspace_id, title=title, description=description)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def _update_task(task_id: int, body: TaskUpdate, current_user: User, session: AsyncSession) -> Task:
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _verify_workspace_access(task.workspace_id, current_user, session)

    if body.status is not None:
        task.status = body.status
    if body.assigned_to is not None:
        task.assigned_to = body.assigned_to

    task.updated_at = datetime.now(UTC)

    if body.status == "completed":
        task.completed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(task)
    return task


# --- Flat routes (legacy: /api/v1/tasks) ---


@router.get("/")
async def list_tasks(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[Task]:
    """List all tasks for a workspace."""
    return await _list_tasks(workspace_id, current_user, session)


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Get a specific task."""
    return await _get_task(task_id, current_user, session)


@router.post("/")
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Create a new task."""
    return await _create_task(body.workspace_id, body.title, body.description, current_user, session)


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Update a task."""
    return await _update_task(task_id, body, current_user, session)


# --- Nested routes (/api/v1/workspaces/{workspace_identifier}/tasks) ---


@nested_router.get("/")
async def list_tasks_nested(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[Task]:
    """List all tasks for a workspace (nested route)."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    return await _list_tasks(workspace.id, current_user, session)


@nested_router.get("/{task_id}")
async def get_task_nested(
    workspace_identifier: str,
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Get a specific task (nested route)."""
    return await _get_task(task_id, current_user, session)


@nested_router.post("/")
async def create_task_nested(
    workspace_identifier: str,
    body: TaskCreateNested,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Create a new task (nested route)."""
    workspace = await get_workspace_by_slug_or_id(workspace_identifier, current_user, session)
    return await _create_task(workspace.id, body.title, body.description, current_user, session)


@nested_router.put("/{task_id}")
async def update_task_nested(
    workspace_identifier: str,
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Update a task (nested route)."""
    return await _update_task(task_id, body, current_user, session)

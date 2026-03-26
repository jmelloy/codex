"""Task routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.db.database import get_system_session
from codex.db.models import Task, User, Workspace

router = APIRouter()


class TaskCreate(BaseModel):
    workspace_id: int
    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
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


@router.get("/")
async def list_tasks(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[Task]:
    """List all tasks for a workspace."""
    await _verify_workspace_access(workspace_id, current_user, session)
    result = await session.execute(select(Task).where(Task.workspace_id == workspace_id))
    return result.scalars().all()


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Get a specific task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify the user owns the workspace this task belongs to
    await _verify_workspace_access(task.workspace_id, current_user, session)
    return task


@router.post("/")
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Create a new task."""
    await _verify_workspace_access(body.workspace_id, current_user, session)
    task = Task(workspace_id=body.workspace_id, title=body.title, description=body.description)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Update a task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify the user owns the workspace this task belongs to
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

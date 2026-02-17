"""Task routes."""

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.db.database import get_system_session
from codex.db.models import Task, User, Workspace

router = APIRouter()


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
    workspace_id: int,
    title: str,
    description: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Create a new task."""
    await _verify_workspace_access(workspace_id, current_user, session)
    task = Task(workspace_id=workspace_id, title=title, description=description)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    status: str = None,
    assigned_to: str = None,
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

    if status:
        task.status = status
    if assigned_to:
        task.assigned_to = assigned_to

    from datetime import datetime

    task.updated_at = datetime.now(UTC)

    if status == "completed":
        task.completed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(task)
    return task

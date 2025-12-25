"""Task routes."""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.api.auth import get_current_active_user
from backend.db.database import get_system_session
from backend.db.models import Task, User

router = APIRouter()


@router.get("/")
async def list_tasks(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
) -> list[Task]:
    """List all tasks for a workspace."""
    result = await session.execute(
        select(Task).where(Task.workspace_id == workspace_id)
    )
    return result.scalars().all()


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
) -> Task:
    """Get a specific task."""
    result = await session.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/")
async def create_task(
    workspace_id: int,
    title: str,
    description: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
) -> Task:
    """Create a new task."""
    task = Task(
        workspace_id=workspace_id,
        title=title,
        description=description
    )
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
    session: AsyncSession = Depends(get_system_session)
) -> Task:
    """Update a task."""
    result = await session.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if status:
        task.status = status
    if assigned_to:
        task.assigned_to = assigned_to

    from datetime import datetime
    task.updated_at = datetime.utcnow()

    if status == "completed":
        task.completed_at = datetime.utcnow()

    await session.commit()
    await session.refresh(task)
    return task

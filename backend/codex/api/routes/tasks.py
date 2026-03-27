"""Task routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.db.database import get_system_session
from codex.db.models import Task, User, Workspace

router = APIRouter()


class TaskCreate(BaseModel):
    """Request body for creating a task."""

    title: str
    description: str | None = None
    job_type: str = "agent"


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


@router.get("/")
async def list_tasks(
    workspace_identifier: str,
    status: str | None = None,
    assigned_to: str | None = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[Task]:
    """List all tasks for a workspace, with optional filtering."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    stmt = select(Task).where(Task.workspace_id == workspace.id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if assigned_to is not None:
        stmt = stmt.where(Task.assigned_to == assigned_to)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{task_id}")
async def get_task(
    workspace_identifier: str,
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Get a specific task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _verify_workspace_access(task.workspace_id, current_user, session)
    return task


@router.post("/")
async def create_task(
    workspace_identifier: str,
    body: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Create a new task."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    task = Task(
        workspace_id=workspace.id,
        title=body.title,
        description=body.description,
        job_type=body.job_type,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.put("/{task_id}")
async def update_task(
    workspace_identifier: str,
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


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    workspace_identifier: str,
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> None:
    """Delete a task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _verify_workspace_access(task.workspace_id, current_user, session)
    await session.delete(task)
    await session.commit()


@router.post("/{task_id}/enqueue")
async def enqueue_task(
    workspace_identifier: str,
    task_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Task:
    """Enqueue a task for background execution via the ARQ worker."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _verify_workspace_access(task.workspace_id, current_user, session)

    if task.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Task cannot be enqueued — current status is '{task.status}'",
        )

    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is None:
        raise HTTPException(status_code=503, detail="Task queue is not available (Redis not connected)")

    job = await arq_pool.enqueue_job("run_job", task.id)
    task.job_id = job.job_id
    task.status = "pending"
    task.updated_at = datetime.now(UTC)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("/{task_id}/status")
async def get_task_status(
    workspace_identifier: str,
    task_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> dict:
    """Get the background job status for a task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _verify_workspace_access(task.workspace_id, current_user, session)

    response: dict = {
        "task_id": task.id,
        "status": task.status,
        "job_id": task.job_id,
    }

    # If we have a job_id and a Redis connection, query ARQ for live status
    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is not None and task.job_id:
        try:
            job = arq_pool.job(task.job_id)
            info = await job.info()
            if info:
                response["job_status"] = info.status
                response["job_result"] = info.result if info.status == "complete" else None
        except Exception:
            pass  # Redis unavailable — fall back to DB status only

    return response

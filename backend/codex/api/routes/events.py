"""Event status API routes.

This module provides API endpoints for tracking file event status,
including individual events and correlated batches.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, func, select

from codex.api.auth import get_current_active_user
from codex.db.database import get_system_session
from codex.db.models import FileEvent, FileEventStatus, User

router = APIRouter()
logger = logging.getLogger(__name__)


class EventStatusResponse(BaseModel):
    """Response model for event status."""

    id: int
    notebook_id: int
    event_type: str
    status: str
    correlation_id: str | None
    sequence: int
    created_at: str
    processed_at: str | None
    error_message: str | None
    retry_count: int


class CorrelatedEventsResponse(BaseModel):
    """Response model for correlated events."""

    correlation_id: str
    total: int
    pending: int
    processing: int
    completed: int
    failed: int
    superseded: int
    events: list[EventStatusResponse]


class QueueMetricsResponse(BaseModel):
    """Response model for queue metrics."""

    pending: int
    processing: int
    completed_24h: int
    failed_24h: int
    superseded_24h: int


@router.get("/metrics", response_model=QueueMetricsResponse)
async def get_queue_metrics(
    notebook_id: int | None = Query(None, description="Filter by notebook ID"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get event queue metrics.

    Returns counts of events by status, optionally filtered by notebook.
    """
    # Build base query conditions
    conditions = []
    if notebook_id is not None:
        conditions.append(FileEvent.notebook_id == notebook_id)

    # Count pending
    pending_query = select(func.count()).select_from(FileEvent).where(
        FileEvent.status == FileEventStatus.PENDING.value,
        *conditions,
    )
    pending = (await session.execute(pending_query)).scalar_one()

    # Count processing
    processing_query = select(func.count()).select_from(FileEvent).where(
        FileEvent.status == FileEventStatus.PROCESSING.value,
        *conditions,
    )
    processing = (await session.execute(processing_query)).scalar_one()

    # Count completed in last 24 hours
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    completed_query = select(func.count()).select_from(FileEvent).where(
        FileEvent.status == FileEventStatus.COMPLETED.value,
        FileEvent.processed_at >= cutoff,
        *conditions,
    )
    completed_24h = (await session.execute(completed_query)).scalar_one()

    # Count failed in last 24 hours
    failed_query = select(func.count()).select_from(FileEvent).where(
        FileEvent.status == FileEventStatus.FAILED.value,
        FileEvent.processed_at >= cutoff,
        *conditions,
    )
    failed_24h = (await session.execute(failed_query)).scalar_one()

    # Count superseded in last 24 hours
    superseded_query = select(func.count()).select_from(FileEvent).where(
        FileEvent.status == FileEventStatus.SUPERSEDED.value,
        FileEvent.created_at >= cutoff,
        *conditions,
    )
    superseded_24h = (await session.execute(superseded_query)).scalar_one()

    return QueueMetricsResponse(
        pending=pending,
        processing=processing,
        completed_24h=completed_24h,
        failed_24h=failed_24h,
        superseded_24h=superseded_24h,
    )


@router.get("/{event_id}", response_model=EventStatusResponse)
async def get_event_status(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get status of a single event."""
    event = await session.get(FileEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventStatusResponse(
        id=event.id,
        notebook_id=event.notebook_id,
        event_type=event.event_type,
        status=event.status,
        correlation_id=event.correlation_id,
        sequence=event.sequence,
        created_at=event.created_at.isoformat(),
        processed_at=event.processed_at.isoformat() if event.processed_at else None,
        error_message=event.error_message,
        retry_count=event.retry_count,
    )


@router.get("/correlation/{correlation_id}", response_model=CorrelatedEventsResponse)
async def get_correlated_events(
    correlation_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get status of all events in a batch operation."""
    result = await session.execute(
        select(FileEvent)
        .where(FileEvent.correlation_id == correlation_id)
        .order_by(FileEvent.sequence)
    )
    events = result.scalars().all()

    if not events:
        raise HTTPException(status_code=404, detail="Correlation ID not found")

    event_responses = [
        EventStatusResponse(
            id=e.id,
            notebook_id=e.notebook_id,
            event_type=e.event_type,
            status=e.status,
            correlation_id=e.correlation_id,
            sequence=e.sequence,
            created_at=e.created_at.isoformat(),
            processed_at=e.processed_at.isoformat() if e.processed_at else None,
            error_message=e.error_message,
            retry_count=e.retry_count,
        )
        for e in events
    ]

    # Count by status
    status_counts = {
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "superseded": 0,
    }
    for e in events:
        if e.status in status_counts:
            status_counts[e.status] += 1

    return CorrelatedEventsResponse(
        correlation_id=correlation_id,
        total=len(events),
        **status_counts,
        events=event_responses,
    )


@router.post("/{event_id}/wait", response_model=EventStatusResponse)
async def wait_for_event(
    event_id: int,
    timeout: float = Query(30.0, description="Timeout in seconds", ge=1.0, le=60.0),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Long-poll waiting for event completion.

    Waits for the event to reach a terminal state (completed, failed, or superseded).
    Returns immediately if already in terminal state.
    """
    start = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start < timeout:
        # Refresh to get latest state
        await session.expire_all()
        event = await session.get(FileEvent, event_id)

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        if event.status in (
            FileEventStatus.COMPLETED.value,
            FileEventStatus.FAILED.value,
            FileEventStatus.SUPERSEDED.value,
        ):
            return EventStatusResponse(
                id=event.id,
                notebook_id=event.notebook_id,
                event_type=event.event_type,
                status=event.status,
                correlation_id=event.correlation_id,
                sequence=event.sequence,
                created_at=event.created_at.isoformat(),
                processed_at=event.processed_at.isoformat() if event.processed_at else None,
                error_message=event.error_message,
                retry_count=event.retry_count,
            )

        await asyncio.sleep(0.5)

    raise HTTPException(status_code=408, detail="Timeout waiting for event completion")


@router.delete("/cleanup")
async def cleanup_old_events(
    days: int = Query(7, description="Delete events older than this many days", ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Clean up old completed/failed/superseded events.

    This endpoint removes events that have been processed and are older than
    the specified number of days. Pending and processing events are never deleted.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Delete old terminal events
    result = await session.execute(
        delete(FileEvent).where(
            FileEvent.status.in_([
                FileEventStatus.COMPLETED.value,
                FileEventStatus.FAILED.value,
                FileEventStatus.SUPERSEDED.value,
            ]),
            FileEvent.created_at < cutoff,
        )
    )
    await session.commit()

    deleted_count = result.rowcount

    return {
        "message": f"Deleted {deleted_count} events older than {days} days",
        "deleted_count": deleted_count,
    }

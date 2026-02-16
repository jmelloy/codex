"""Google Calendar API routes."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codex.api.auth import get_current_active_user
from codex.core.google_calendar import get_event, list_calendars, list_events
from codex.db.database import get_system_session
from codex.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


class CalendarResponse(BaseModel):
    """A Google Calendar."""

    id: str
    summary: str
    description: str = ""
    primary: bool = False
    background_color: str | None = None
    foreground_color: str | None = None
    access_role: str | None = None


class EventAttendee(BaseModel):
    """An event attendee."""

    email: str | None = None
    display_name: str | None = None
    response_status: str | None = None
    self_: bool = False

    model_config = {"populate_by_name": True}


class EventResponse(BaseModel):
    """A Google Calendar event."""

    id: str | None = None
    summary: str = "Untitled Event"
    description: str = ""
    location: str = ""
    start: str | None = None
    end: str | None = None
    all_day: bool = False
    status: str | None = None
    html_link: str | None = None
    creator: dict | None = None
    organizer: dict | None = None
    attendees: list[dict] = []
    recurring_event_id: str | None = None
    color_id: str | None = None
    created: str | None = None
    updated: str | None = None


class EventListResponse(BaseModel):
    """Response for listing events."""

    events: list[EventResponse]
    calendar_id: str


@router.get("/calendars", response_model=list[CalendarResponse])
async def get_calendars(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all Google Calendars for the current user."""
    try:
        calendars = await list_calendars(session, current_user.id)
        return [CalendarResponse(**cal) for cal in calendars]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list calendars: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch calendars from Google",
        )


@router.get("/events", response_model=EventListResponse)
async def get_events(
    calendar_id: str = Query(default="primary", description="Calendar ID"),
    time_min: datetime | None = Query(default=None, description="Start of time range (ISO format)"),
    time_max: datetime | None = Query(default=None, description="End of time range (ISO format)"),
    max_results: int = Query(default=50, ge=1, le=250, description="Maximum number of events"),
    q: str | None = Query(default=None, description="Free-text search query"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List events from a Google Calendar.

    Defaults to the primary calendar, showing events from now to 30 days out.
    """
    try:
        events = await list_events(
            session=session,
            user_id=current_user.id,
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            query=q,
        )
        return EventListResponse(
            events=[EventResponse(**event) for event in events],
            calendar_id=calendar_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list events: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch events from Google Calendar",
        )


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_single_event(
    event_id: str,
    calendar_id: str = Query(default="primary", description="Calendar ID"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get a single event by ID."""
    try:
        event = await get_event(
            session=session,
            user_id=current_user.id,
            event_id=event_id,
            calendar_id=calendar_id,
        )
        return EventResponse(**event)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch event from Google Calendar",
        )

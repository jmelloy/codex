"""Google Calendar integration service.

Provides methods to interact with the Google Calendar API using
stored OAuth credentials.
"""

import logging
from datetime import UTC, datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from codex.core.oauth import get_google_credentials

logger = logging.getLogger(__name__)


def _build_calendar_service(credentials: Credentials):
    """Build a Google Calendar API service client."""
    return build("calendar", "v3", credentials=credentials)


async def list_calendars(session: AsyncSession, user_id: int) -> list[dict]:
    """List all calendars for the user.

    Returns a list of calendar summaries with id, summary, and color.
    """
    creds = await get_google_credentials(session, user_id)
    if not creds:
        raise ValueError("No Google connection found. Please connect your Google account first.")

    service = _build_calendar_service(creds)
    calendar_list = service.calendarList().list().execute()

    return [
        {
            "id": cal["id"],
            "summary": cal.get("summary", "Untitled"),
            "description": cal.get("description", ""),
            "primary": cal.get("primary", False),
            "background_color": cal.get("backgroundColor"),
            "foreground_color": cal.get("foregroundColor"),
            "access_role": cal.get("accessRole"),
        }
        for cal in calendar_list.get("items", [])
    ]


async def list_events(
    session: AsyncSession,
    user_id: int,
    calendar_id: str = "primary",
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    max_results: int = 50,
    query: str | None = None,
) -> list[dict]:
    """List events from a Google Calendar.

    Args:
        session: Database session.
        user_id: The authenticated user's ID.
        calendar_id: Calendar ID (default "primary").
        time_min: Start of time range (default: now).
        time_max: End of time range (default: 30 days from now).
        max_results: Maximum number of events to return.
        query: Free-text search query.

    Returns:
        List of event dicts.
    """
    creds = await get_google_credentials(session, user_id)
    if not creds:
        raise ValueError("No Google connection found. Please connect your Google account first.")

    if time_min is None:
        time_min = datetime.now(UTC)
    if time_max is None:
        time_max = time_min + timedelta(days=30)

    service = _build_calendar_service(creds)

    params = {
        "calendarId": calendar_id,
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if query:
        params["q"] = query

    events_result = service.events().list(**params).execute()
    events = events_result.get("items", [])

    return [_format_event(event) for event in events]


async def get_event(
    session: AsyncSession,
    user_id: int,
    event_id: str,
    calendar_id: str = "primary",
) -> dict:
    """Get a single event by ID.

    Args:
        session: Database session.
        user_id: The authenticated user's ID.
        event_id: The event ID.
        calendar_id: Calendar ID (default "primary").

    Returns:
        Event dict.
    """
    creds = await get_google_credentials(session, user_id)
    if not creds:
        raise ValueError("No Google connection found. Please connect your Google account first.")

    service = _build_calendar_service(creds)
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    return _format_event(event)


def _format_event(event: dict) -> dict:
    """Format a Google Calendar event into a normalized dict."""
    start = event.get("start", {})
    end = event.get("end", {})

    return {
        "id": event.get("id"),
        "summary": event.get("summary", "Untitled Event"),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "all_day": "date" in start and "dateTime" not in start,
        "status": event.get("status"),
        "html_link": event.get("htmlLink"),
        "creator": event.get("creator", {}),
        "organizer": event.get("organizer", {}),
        "attendees": [
            {
                "email": a.get("email"),
                "display_name": a.get("displayName"),
                "response_status": a.get("responseStatus"),
                "self": a.get("self", False),
            }
            for a in event.get("attendees", [])
        ],
        "recurring_event_id": event.get("recurringEventId"),
        "color_id": event.get("colorId"),
        "created": event.get("created"),
        "updated": event.get("updated"),
    }

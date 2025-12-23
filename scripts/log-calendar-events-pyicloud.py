#!/usr/bin/env python3
"""
Log iCloud Calendar Events to Daily Note using PyiCloud

This script uses the PyiCloud library to fetch calendar events from iCloud
and add them to your daily note. Unlike the AppleScript version, this works
on any platform (macOS, Linux, Windows) where Python is available.

Requirements:
    pip install pyicloud

Usage:
    python scripts/log-calendar-events-pyicloud.py

    # With custom workspace
    CODEX_WORKSPACE=~/my-workspace python scripts/log-calendar-events-pyicloud.py

    # With credentials via environment variables
    ICLOUD_USERNAME=your@email.com ICLOUD_PASSWORD=your-password python scripts/log-calendar-events-pyicloud.py

First-time setup:
    The script will prompt for your Apple ID and password on first run.
    If you have 2FA enabled, it will guide you through the verification process.
    Credentials are stored securely using the system keyring.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_workspace_path() -> Path:
    """Get the workspace path from environment or use default."""
    workspace = os.environ.get('CODEX_WORKSPACE', os.path.expanduser('~/codex'))
    return Path(workspace).expanduser().resolve()


def get_daily_note_path(workspace_path: Path, date: Optional[datetime] = None) -> Path:
    """Get the path to the daily note for a given date."""
    if date is None:
        date = datetime.now()
    date_str = date.strftime('%Y-%m-%d')
    daily_notes_path = workspace_path / 'daily-notes'
    daily_notes_path.mkdir(parents=True, exist_ok=True)
    return daily_notes_path / f'{date_str}.md'


def create_daily_note(note_path: Path, date: datetime) -> None:
    """Create a new daily note with frontmatter."""
    date_str = date.strftime('%Y-%m-%d')
    content = f"""---
title: Daily Note - {date_str}
date: {date_str}
tags:
  - daily-note
  - auto-generated
---

# Daily Note - {date_str}

## Calendar Events

"""
    note_path.write_text(content)


def format_event(event: Dict[str, Any]) -> str:
    """Format a calendar event as a markdown list item."""
    title = event.get('title', 'Untitled Event')

    # Check if it's an all-day event
    is_all_day = event.get('allDay', False)

    if is_all_day:
        line = f"- **All Day**: {title}"
    else:
        # Format start and end times
        start_date = event.get('startDate')
        end_date = event.get('endDate')

        if start_date and end_date:
            # Parse the date strings - they come in various formats from pyicloud
            try:
                if isinstance(start_date, list):
                    # Format: [year, month, day, hour, minute]
                    start_time = f"{start_date[3]:02d}:{start_date[4]:02d}"
                    end_time = f"{end_date[3]:02d}:{end_date[4]:02d}"
                elif isinstance(start_date, datetime):
                    start_time = start_date.strftime('%H:%M')
                    end_time = end_date.strftime('%H:%M')
                else:
                    # Try parsing as string
                    start_dt = datetime.fromisoformat(str(start_date).replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(str(end_date).replace('Z', '+00:00'))
                    start_time = start_dt.strftime('%H:%M')
                    end_time = end_dt.strftime('%H:%M')

                line = f"- **{start_time} - {end_time}**: {title}"
            except (ValueError, IndexError, AttributeError):
                # Fallback if date parsing fails
                line = f"- {title}"
        else:
            line = f"- {title}"

    # Add location if available
    location = event.get('location', '')
    if location and location.strip():
        line += f" @ {location}"

    return line


def fetch_calendar_events() -> List[Dict[str, Any]]:
    """Fetch calendar events from iCloud for today."""
    try:
        from pyicloud import PyiCloudService
    except ImportError:
        print("Error: pyicloud module not found.")
        print("Please install it with: pip install pyicloud")
        sys.exit(1)

    # Get credentials
    apple_id = os.environ.get('ICLOUD_USERNAME')
    password = os.environ.get('ICLOUD_PASSWORD')

    if not apple_id:
        apple_id = input("Apple ID (email): ").strip()

    # Initialize PyiCloud service
    try:
        api = PyiCloudService(apple_id, password)
    except Exception as e:
        print(f"Error authenticating with iCloud: {e}")
        print("\nIf you have 2FA enabled, you'll need to complete the verification process.")
        sys.exit(1)

    # Handle 2FA if required
    if api.requires_2fa:
        print("Two-factor authentication required.")
        code = input("Enter the code you received on one of your approved devices: ").strip()
        result = api.validate_2fa_code(code)
        if not result:
            print("Failed to verify code")
            sys.exit(1)

        # Trust the session to avoid repeated prompts
        if not api.is_trusted_session:
            print("Session is not trusted. Requesting trust...")
            result = api.trust_session()
            if result:
                print("Session is now trusted.")

    # Get calendar service
    try:
        calendar = api.calendar
    except Exception as e:
        print(f"Error accessing calendar service: {e}")
        sys.exit(1)

    # Get today's date range
    from_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    to_dt = from_dt + timedelta(days=1)

    # Fetch events
    try:
        events = calendar.get_events(from_dt, to_dt)
        return events
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        sys.exit(1)


def update_daily_note_with_events(note_path: Path, events: List[Dict[str, Any]]) -> None:
    """Update the daily note with calendar events."""
    # Read current content or create new note
    date = datetime.now()
    if note_path.exists():
        content = note_path.read_text()
    else:
        create_daily_note(note_path, date)
        content = note_path.read_text()

    # Format events
    if not events:
        calendar_section = "\nNo events scheduled for today.\n"
    else:
        # Sort events by start time
        sorted_events = sorted(events, key=lambda e: e.get('startDate', [0, 0, 0, 0, 0]))

        calendar_section = "\n"
        for event in sorted_events:
            calendar_section += format_event(event) + "\n"
        calendar_section += "\n"

    # Update calendar section in the note
    if "## Calendar Events" in content:
        # Replace existing calendar section
        parts = content.split("## Calendar Events", 1)
        before_section = parts[0]
        after_section = parts[1]

        # Find the next section marker to preserve content after calendar section
        next_section_markers = ["\n## ", "\n# "]
        next_section = None

        for marker in next_section_markers:
            if marker in after_section:
                idx = after_section.index(marker)
                next_section = after_section[idx:]
                break

        if next_section:
            content = before_section + "## Calendar Events" + calendar_section + next_section
        else:
            content = before_section + "## Calendar Events" + calendar_section
    else:
        # Add calendar section after the title
        if "# Daily Note" in content:
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("# Daily Note"):
                    insert_idx = i + 1
                    break

            lines.insert(insert_idx, "")
            lines.insert(insert_idx + 1, "## Calendar Events")
            lines.insert(insert_idx + 2, calendar_section.rstrip())
            content = '\n'.join(lines)
        else:
            # Add at end
            content += "\n## Calendar Events" + calendar_section

    # Write updated content
    note_path.write_text(content)


def main():
    """Main function."""
    print("Fetching calendar events from iCloud...")

    # Get workspace path
    workspace_path = get_workspace_path()
    print(f"Using workspace: {workspace_path}")

    # Fetch events from iCloud
    events = fetch_calendar_events()
    print(f"Found {len(events)} event(s)")

    # Get daily note path
    note_path = get_daily_note_path(workspace_path)

    # Update daily note
    update_daily_note_with_events(note_path, events)

    print(f"✓ Updated daily note: {note_path}")

    # Show summary
    if events:
        print("\nEvents added:")
        for event in sorted(events, key=lambda e: e.get('startDate', [0, 0, 0, 0, 0])):
            print(f"  - {event.get('title', 'Untitled')}")


if __name__ == '__main__':
    main()

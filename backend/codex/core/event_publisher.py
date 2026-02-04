"""Event publisher for file operations.

This module provides the EventPublisher class which is used by API endpoints
to publish file operation events to the queue instead of performing operations
directly. This enables:

1. Batched git commits (every 5 seconds instead of per-operation)
2. Elimination of race conditions between API and watcher
3. Reliable ordering of file operations
4. Retry handling for transient errors
"""

import json
import logging
import uuid
from typing import Any

from sqlmodel import Session, select

from codex.db.models import FileEvent, FileEventStatus, FileEventType

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes file events to the queue for async processing."""

    def __init__(self, session: Session):
        """Initialize the event publisher.

        Args:
            session: SQLModel session for the system database
        """
        self.session = session

    def publish(
        self,
        notebook_id: int,
        event_type: FileEventType,
        operation: dict[str, Any],
        correlation_id: str | None = None,
        sequence: int = 0,
    ) -> FileEvent:
        """Publish a single event to the queue.

        Args:
            notebook_id: ID of the notebook
            event_type: Type of file event
            operation: Operation details as a dictionary
            correlation_id: Optional ID for correlating related events
            sequence: Sequence number within correlated events

        Returns:
            The created FileEvent instance
        """
        event = FileEvent(
            notebook_id=notebook_id,
            event_type=event_type.value,
            operation=json.dumps(operation),
            correlation_id=correlation_id,
            sequence=sequence,
            status=FileEventStatus.PENDING.value,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)

        logger.debug(f"Published {event_type.value} event for notebook {notebook_id}: {event.id}")
        return event

    def publish_batch(
        self,
        notebook_id: int,
        events: list[tuple[FileEventType, dict[str, Any]]],
    ) -> str:
        """Publish multiple related events with a correlation ID.

        This is useful for operations that affect multiple files, like moving
        a folder with all its contents.

        Args:
            notebook_id: ID of the notebook
            events: List of (event_type, operation) tuples

        Returns:
            The correlation ID for tracking the batch
        """
        correlation_id = str(uuid.uuid4())

        for seq, (event_type, operation) in enumerate(events):
            event = FileEvent(
                notebook_id=notebook_id,
                event_type=event_type.value,
                operation=json.dumps(operation),
                correlation_id=correlation_id,
                sequence=seq,
                status=FileEventStatus.PENDING.value,
            )
            self.session.add(event)

        self.session.commit()

        logger.info(f"Published batch of {len(events)} events with correlation_id={correlation_id}")
        return correlation_id

    def supersede_pending(
        self,
        notebook_id: int,
        path: str,
    ) -> int:
        """Mark pending events for a path as superseded.

        This handles rapid successive operations on the same file by marking
        older pending events as superseded so they won't be processed.

        Args:
            notebook_id: ID of the notebook
            path: File path to supersede events for

        Returns:
            Number of events marked as superseded
        """
        # Find pending events for this path
        # We need to check the operation JSON for the path
        result = self.session.execute(
            select(FileEvent).where(
                FileEvent.notebook_id == notebook_id,
                FileEvent.status == FileEventStatus.PENDING.value,
            )
        )
        events = result.scalars().all()

        count = 0
        for event in events:
            try:
                operation = json.loads(event.operation)
                event_path = operation.get("path") or operation.get("source_path")
                if event_path == path:
                    event.status = FileEventStatus.SUPERSEDED.value
                    count += 1
            except (json.JSONDecodeError, KeyError):
                continue

        if count > 0:
            self.session.commit()
            logger.debug(f"Superseded {count} pending events for path: {path}")

        return count

    def get_event_status(self, event_id: int) -> FileEvent | None:
        """Get the status of a specific event.

        Args:
            event_id: ID of the event to check

        Returns:
            The FileEvent if found, None otherwise
        """
        return self.session.get(FileEvent, event_id)

    def get_correlated_events(self, correlation_id: str) -> list[FileEvent]:
        """Get all events with a specific correlation ID.

        Args:
            correlation_id: The correlation ID to look up

        Returns:
            List of FileEvents ordered by sequence
        """
        result = self.session.execute(
            select(FileEvent)
            .where(FileEvent.correlation_id == correlation_id)
            .order_by(FileEvent.sequence)
        )
        return list(result.scalars().all())

    def get_pending_count(self, notebook_id: int | None = None) -> int:
        """Get the count of pending events.

        Args:
            notebook_id: Optional notebook ID to filter by

        Returns:
            Number of pending events
        """
        from sqlmodel import func

        query = select(func.count(FileEvent.id)).where(
            FileEvent.status == FileEventStatus.PENDING.value
        )
        if notebook_id is not None:
            query = query.where(FileEvent.notebook_id == notebook_id)

        result = self.session.execute(query)
        return result.scalar_one()

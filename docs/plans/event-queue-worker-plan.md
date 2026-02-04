# Event Queue Worker Plan

## Overview

This plan describes an architecture for replacing the current synchronous file operation handling with an event queue system. The goals are:

1. **Eliminate race conditions** between API endpoints and the filesystem watcher
2. **Batch git commits** to reduce overhead (every 5 seconds instead of per-operation)
3. **Provide operation isolation** for complex multi-step operations (moves, deletes)
4. **Enable reliable ordering** of file operations
5. **Support retry and failure handling** for transient errors

---

## Current Problems

### 1. Race Conditions
- API creates metadata record BEFORE writing file to disk
- Watcher may detect file and try to create duplicate metadata
- Current fix: catch UNIQUE constraint violations and re-query
- This is fragile and doesn't handle all cases (e.g., rapid delete + recreate)

### 2. Multiple Commit Points
- Single file create has 3+ database commits
- Each commit is a potential failure point
- No transactional consistency across file + metadata operations

### 3. Git Commit Overhead
- Every file change triggers an immediate git commit
- Bulk operations (moving 100 files) create 100 commits
- Blocks API responses waiting for git operations

### 4. Complex Move/Delete Logic
- Moving a folder requires updating paths of all contained files
- Delete requires removing files, then metadata, then git commit
- No rollback if operation fails partway through

---

## Proposed Architecture

### Event Queue Model

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  API Endpoints  │────▶│   Event Queue   │────▶│  Queue Worker   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
        ┌───────────────────────────────────────────────┤
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Filesystem  │      │   Database   │      │     Git      │
└──────────────┘      └──────────────┘      └──────────────┘
```

### New Database Model: `FileEvent`

```python
# backend/codex/db/models/system.py

class FileEventType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    MOVE = "move"
    DELETE = "delete"
    SYNC = "sync"  # Watcher-detected change
    BATCH_COMMIT = "batch_commit"  # Trigger git commit

class FileEventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"  # Replaced by newer event

class FileEvent(Base):
    __tablename__ = "file_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id"))

    # Event type and status
    event_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Operation details (JSON serialized)
    operation: Mapped[str] = mapped_column(Text)
    # Example operations:
    # CREATE: {"path": "/notes/foo.md", "content": "...", "metadata": {...}}
    # UPDATE: {"path": "/notes/foo.md", "content": "...", "metadata": {...}}
    # MOVE:   {"source_path": "/notes/foo.md", "dest_path": "/archive/foo.md"}
    # DELETE: {"path": "/notes/foo.md"}
    # SYNC:   {"path": "/notes/foo.md", "event": "modified"}

    # Correlation for multi-event operations
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sequence: Mapped[int] = mapped_column(default=0)  # Order within correlation

    # Tracking
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Indexes
    __table_args__ = (
        Index("ix_file_events_notebook_status", "notebook_id", "status"),
        Index("ix_file_events_correlation", "correlation_id"),
        Index("ix_file_events_path", "notebook_id", "operation"),  # JSON path extraction
    )
```

---

## Component Design

### 1. Event Publisher (API Layer)

File/folder endpoints will publish events instead of directly performing operations.

```python
# backend/codex/core/event_publisher.py

class EventPublisher:
    """Publishes file events to the queue."""

    def __init__(self, session: Session):
        self.session = session

    def publish(
        self,
        notebook_id: int,
        event_type: FileEventType,
        operation: dict,
        correlation_id: str | None = None,
        sequence: int = 0,
    ) -> FileEvent:
        """Publish a single event to the queue."""
        event = FileEvent(
            notebook_id=notebook_id,
            event_type=event_type,
            operation=json.dumps(operation),
            correlation_id=correlation_id,
            sequence=sequence,
        )
        self.session.add(event)
        self.session.commit()
        return event

    def publish_batch(
        self,
        notebook_id: int,
        events: list[tuple[FileEventType, dict]],
    ) -> str:
        """Publish multiple related events with a correlation ID."""
        correlation_id = str(uuid.uuid4())
        for seq, (event_type, operation) in enumerate(events):
            self.publish(
                notebook_id=notebook_id,
                event_type=event_type,
                operation=operation,
                correlation_id=correlation_id,
                sequence=seq,
            )
        return correlation_id

    def supersede_pending(
        self,
        notebook_id: int,
        path: str,
    ) -> int:
        """Mark pending events for a path as superseded."""
        # This handles rapid successive operations on the same file
        count = self.session.execute(
            update(FileEvent)
            .where(
                FileEvent.notebook_id == notebook_id,
                FileEvent.status == "pending",
                FileEvent.operation.contains(f'"path": "{path}"'),
            )
            .values(status="superseded")
        ).rowcount
        self.session.commit()
        return count
```

### 2. Queue Worker

```python
# backend/codex/core/event_worker.py

class EventWorker:
    """Processes file events from the queue."""

    def __init__(
        self,
        notebook_id: int,
        batch_interval: float = 5.0,  # Git commit interval
    ):
        self.notebook_id = notebook_id
        self.batch_interval = batch_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._pending_git_paths: set[str] = set()
        self._last_git_commit: float = 0

    def start(self):
        """Start the worker thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0):
        """Stop the worker thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self):
        """Main worker loop."""
        while self._running:
            try:
                # Process pending events
                events = self._fetch_pending_events(limit=50)
                for event in events:
                    self._process_event(event)

                # Check if it's time for a git commit
                if self._should_commit_git():
                    self._perform_git_commit()

                # Sleep briefly if no events
                if not events:
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1.0)  # Back off on error

    def _fetch_pending_events(self, limit: int) -> list[FileEvent]:
        """Fetch pending events ordered by creation time."""
        with get_session() as session:
            events = session.execute(
                select(FileEvent)
                .where(
                    FileEvent.notebook_id == self.notebook_id,
                    FileEvent.status == "pending",
                )
                .order_by(FileEvent.correlation_id, FileEvent.sequence)
                .limit(limit)
            ).scalars().all()

            # Mark as processing
            for event in events:
                event.status = "processing"
            session.commit()

            return events

    def _process_event(self, event: FileEvent):
        """Process a single event."""
        try:
            operation = json.loads(event.operation)

            match event.event_type:
                case FileEventType.CREATE:
                    self._handle_create(operation)
                case FileEventType.UPDATE:
                    self._handle_update(operation)
                case FileEventType.MOVE:
                    self._handle_move(operation)
                case FileEventType.DELETE:
                    self._handle_delete(operation)
                case FileEventType.SYNC:
                    self._handle_sync(operation)

            # Mark for git commit
            path = operation.get("path") or operation.get("dest_path")
            if path:
                self._pending_git_paths.add(path)

            # Mark completed
            with get_session() as session:
                event.status = "completed"
                event.processed_at = datetime.utcnow()
                session.commit()

        except Exception as e:
            self._handle_event_error(event, e)

    def _should_commit_git(self) -> bool:
        """Check if enough time has passed for a git commit."""
        if not self._pending_git_paths:
            return False
        return time.time() - self._last_git_commit >= self.batch_interval

    def _perform_git_commit(self):
        """Batch commit all pending paths to git."""
        if not self._pending_git_paths:
            return

        paths = list(self._pending_git_paths)
        self._pending_git_paths.clear()
        self._last_git_commit = time.time()

        with GitLockManager.get_lock(self.notebook_id):
            repo = git.Repo(self.notebook_path)
            repo.index.add(paths)
            repo.index.commit(f"Batch update: {len(paths)} files")
```

### 3. Event Handlers

```python
# backend/codex/core/event_handlers.py

class EventHandlers:
    """Handlers for each event type."""

    def __init__(self, notebook_id: int, notebook_path: Path):
        self.notebook_id = notebook_id
        self.notebook_path = notebook_path

    def handle_create(self, operation: dict) -> FileMetadata:
        """Handle file creation."""
        path = operation["path"]
        content = operation.get("content", "")
        metadata = operation.get("metadata", {})

        full_path = self.notebook_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content)

        # Create metadata record
        with get_notebook_session(self.notebook_id) as session:
            file_meta = FileMetadata(
                notebook_id=self.notebook_id,
                path=path,
                size=full_path.stat().st_size,
                hash=calculate_hash(full_path),
                content_type=detect_mime_type(full_path),
                **metadata,
            )
            session.add(file_meta)
            session.commit()
            return file_meta

    def handle_move(self, operation: dict) -> list[FileMetadata]:
        """Handle file/folder move."""
        source = operation["source_path"]
        dest = operation["dest_path"]

        source_full = self.notebook_path / source
        dest_full = self.notebook_path / dest

        # Perform filesystem move
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source_full, dest_full)

        # Update metadata for all affected files
        with get_notebook_session(self.notebook_id) as session:
            if source_full.is_dir():
                # Update all files with matching path prefix
                files = session.execute(
                    select(FileMetadata)
                    .where(FileMetadata.path.startswith(source + "/"))
                ).scalars().all()

                for f in files:
                    f.path = f.path.replace(source, dest, 1)
            else:
                file_meta = session.execute(
                    select(FileMetadata)
                    .where(FileMetadata.path == source)
                ).scalar_one()
                file_meta.path = dest

            session.commit()

    def handle_delete(self, operation: dict) -> None:
        """Handle file/folder deletion."""
        path = operation["path"]
        full_path = self.notebook_path / path

        # Delete from filesystem
        if full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            full_path.unlink(missing_ok=True)

        # Delete metadata
        with get_notebook_session(self.notebook_id) as session:
            if operation.get("is_directory"):
                session.execute(
                    delete(FileMetadata)
                    .where(FileMetadata.path.startswith(path + "/"))
                )
            else:
                session.execute(
                    delete(FileMetadata)
                    .where(FileMetadata.path == path)
                )
            session.commit()
```

---

## Updated API Endpoints

### File Create (Before vs After)

**Before (Current):**
```python
@router.post("/")
async def create_file(file: FileCreate, ...):
    # 1. Create metadata record (commit)
    # 2. Write file to disk
    # 3. Update metadata with stats (commit)
    # 4. Git commit
    # 5. Final update (commit)
    return file_meta
```

**After (Event-Based):**
```python
@router.post("/")
async def create_file(file: FileCreate, ...):
    publisher = EventPublisher(session)

    # Publish event and return immediately
    event = publisher.publish(
        notebook_id=notebook.id,
        event_type=FileEventType.CREATE,
        operation={
            "path": file.path,
            "content": file.content,
            "metadata": {
                "title": file.title,
                "description": file.description,
            },
        },
    )

    # Return pending status with event ID
    return FileCreateResponse(
        event_id=event.id,
        status="pending",
        path=file.path,
    )
```

### File Move (Complex Operation)

```python
@router.patch("/{file_id}/move")
async def move_file(file_id: int, move: FileMoveRequest, ...):
    publisher = EventPublisher(session)

    # For folder moves, create correlated events
    if is_directory:
        events = []
        for child_path in get_all_children(source_path):
            new_path = child_path.replace(source_path, dest_path, 1)
            events.append((
                FileEventType.MOVE,
                {"source_path": child_path, "dest_path": new_path},
            ))

        correlation_id = publisher.publish_batch(notebook.id, events)
        return FolderMoveResponse(
            correlation_id=correlation_id,
            status="pending",
            file_count=len(events),
        )
    else:
        event = publisher.publish(
            notebook_id=notebook.id,
            event_type=FileEventType.MOVE,
            operation={
                "source_path": source_path,
                "dest_path": dest_path,
            },
        )
        return FileMoveResponse(event_id=event.id, status="pending")
```

---

## Watcher Integration

The filesystem watcher becomes a secondary event source, only handling external changes.

```python
# backend/codex/core/watcher.py (updated)

class NotebookFileHandler(FileSystemEventHandler):
    def __init__(self, notebook_id: int, publisher: EventPublisher):
        self.notebook_id = notebook_id
        self.publisher = publisher
        self._recent_events: dict[str, float] = {}

    def _is_internal_change(self, path: str) -> bool:
        """Check if this change was caused by our worker."""
        # Events within 1 second of a worker operation are internal
        last_event = self._recent_events.get(path, 0)
        return time.time() - last_event < 1.0

    def on_modified(self, event):
        if self._is_internal_change(event.src_path):
            return  # Skip, worker will handle

        # External change detected, publish sync event
        self.publisher.publish(
            notebook_id=self.notebook_id,
            event_type=FileEventType.SYNC,
            operation={
                "path": self._relative_path(event.src_path),
                "event": "modified",
            },
        )
```

---

## Event Status API

New endpoints for tracking event status:

```python
# backend/codex/api/routes/events.py

@router.get("/{event_id}")
async def get_event_status(event_id: int, ...):
    """Get status of a single event."""
    event = session.get(FileEvent, event_id)
    return EventStatusResponse(
        id=event.id,
        status=event.status,
        error_message=event.error_message,
        processed_at=event.processed_at,
    )

@router.get("/correlation/{correlation_id}")
async def get_correlated_events(correlation_id: str, ...):
    """Get status of all events in a batch operation."""
    events = session.execute(
        select(FileEvent)
        .where(FileEvent.correlation_id == correlation_id)
        .order_by(FileEvent.sequence)
    ).scalars().all()

    return CorrelatedEventsResponse(
        correlation_id=correlation_id,
        total=len(events),
        completed=sum(1 for e in events if e.status == "completed"),
        failed=sum(1 for e in events if e.status == "failed"),
        events=[EventStatusResponse.from_orm(e) for e in events],
    )

@router.post("/{event_id}/wait")
async def wait_for_event(event_id: int, timeout: float = 30.0, ...):
    """Long-poll waiting for event completion."""
    start = time.time()
    while time.time() - start < timeout:
        event = session.get(FileEvent, event_id)
        if event.status in ("completed", "failed"):
            return EventStatusResponse.from_orm(event)
        await asyncio.sleep(0.5)

    raise HTTPException(408, "Timeout waiting for event")
```

---

## Git Batching Strategy

### Batch Commit Logic

```python
class GitBatcher:
    """Batches git commits across multiple file changes."""

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self._pending: dict[int, set[str]] = {}  # notebook_id -> paths
        self._last_commit: dict[int, float] = {}
        self._lock = threading.Lock()

    def add_path(self, notebook_id: int, path: str):
        """Add a path to the pending commit batch."""
        with self._lock:
            if notebook_id not in self._pending:
                self._pending[notebook_id] = set()
            self._pending[notebook_id].add(path)

    def should_commit(self, notebook_id: int) -> bool:
        """Check if it's time to commit for a notebook."""
        if notebook_id not in self._pending:
            return False
        if not self._pending[notebook_id]:
            return False

        last = self._last_commit.get(notebook_id, 0)
        return time.time() - last >= self.interval

    def commit(self, notebook_id: int, notebook_path: Path) -> int:
        """Perform batch git commit."""
        with self._lock:
            paths = self._pending.pop(notebook_id, set())
            if not paths:
                return 0

            self._last_commit[notebook_id] = time.time()

        with GitLockManager.get_lock(notebook_id):
            repo = git.Repo(notebook_path)

            # Stage all changed paths
            for path in paths:
                full_path = notebook_path / path
                if full_path.exists():
                    repo.index.add([path])
                else:
                    # File was deleted
                    try:
                        repo.index.remove([path])
                    except git.GitError:
                        pass

            # Commit with summary message
            if len(paths) == 1:
                msg = f"Update {list(paths)[0]}"
            else:
                msg = f"Batch update: {len(paths)} files"

            repo.index.commit(msg)
            return len(paths)
```

### Commit Triggers

1. **Time-based**: Every 5 seconds if there are pending changes
2. **Count-based**: If more than 100 files pending, commit immediately
3. **Shutdown**: Commit all pending on worker shutdown
4. **Explicit**: API endpoint to force immediate commit

---

## Migration Strategy

### Phase 1: Add Event Infrastructure
1. Create `FileEvent` model and migration
2. Implement `EventPublisher`
3. Implement `EventWorker` (process events, no batching yet)
4. Add `/events/` status endpoints

### Phase 2: Migrate Write Operations
1. Update `POST /files/` to publish events
2. Update `PUT /files/{id}` to publish events
3. Update `PATCH /files/{id}/move` to publish events
4. Update `DELETE /files/{id}` to publish events
5. Add synchronous fallback option (`?sync=true` query param)

### Phase 3: Add Git Batching
1. Implement `GitBatcher`
2. Integrate with `EventWorker`
3. Add `/events/commit` force-commit endpoint

### Phase 4: Update Watcher
1. Modify watcher to publish SYNC events
2. Add internal change detection
3. Remove direct database writes from watcher

### Phase 5: Cleanup
1. Remove old synchronous code paths
2. Add monitoring/metrics for queue depth
3. Document new API behavior

---

## Configuration

```python
# backend/codex/core/config.py

class EventQueueSettings:
    # Worker settings
    worker_poll_interval: float = 0.1  # seconds
    worker_batch_size: int = 50  # events per fetch

    # Git batching
    git_commit_interval: float = 5.0  # seconds
    git_commit_max_files: int = 100  # force commit threshold

    # Retry settings
    max_retries: int = 3
    retry_backoff: float = 1.0  # seconds, exponential

    # Cleanup settings
    completed_event_retention: int = 86400  # 1 day in seconds
    failed_event_retention: int = 604800  # 7 days in seconds
```

---

## Error Handling

### Retry Strategy

```python
def _handle_event_error(self, event: FileEvent, error: Exception):
    """Handle event processing error."""
    with get_session() as session:
        event = session.get(FileEvent, event.id)
        event.retry_count += 1
        event.error_message = str(error)

        if event.retry_count >= self.max_retries:
            event.status = "failed"
            logger.error(f"Event {event.id} failed permanently: {error}")
        else:
            event.status = "pending"  # Will be retried
            logger.warning(f"Event {event.id} failed, retry {event.retry_count}")

        session.commit()
```

### Conflict Resolution

```python
def resolve_conflicts(self, notebook_id: int, path: str):
    """Resolve conflicting events for the same path."""
    with get_session() as session:
        pending = session.execute(
            select(FileEvent)
            .where(
                FileEvent.notebook_id == notebook_id,
                FileEvent.status == "pending",
                FileEvent.operation.contains(f'"path": "{path}"'),
            )
            .order_by(FileEvent.created_at.desc())
        ).scalars().all()

        if len(pending) <= 1:
            return

        # Keep only the most recent, supersede others
        for event in pending[1:]:
            event.status = "superseded"

        session.commit()
```

---

## Monitoring

### Queue Metrics

```python
@router.get("/metrics")
async def get_queue_metrics():
    """Get event queue metrics."""
    with get_session() as session:
        pending = session.execute(
            select(func.count())
            .where(FileEvent.status == "pending")
        ).scalar()

        processing = session.execute(
            select(func.count())
            .where(FileEvent.status == "processing")
        ).scalar()

        failed_24h = session.execute(
            select(func.count())
            .where(
                FileEvent.status == "failed",
                FileEvent.processed_at >= datetime.utcnow() - timedelta(hours=24),
            )
        ).scalar()

        return {
            "pending": pending,
            "processing": processing,
            "failed_24h": failed_24h,
        }
```

---

## Benefits Summary

| Issue | Current | With Event Queue |
|-------|---------|------------------|
| Race conditions | Catch UNIQUE violations | Single writer per path |
| Git commits | 1 per operation | Batched every 5s |
| Complex moves | Multi-step, partial failure risk | Atomic with correlation |
| Operation ordering | Undefined | FIFO with sequence |
| Retry on failure | None | Configurable retries |
| Status tracking | None | Full event lifecycle |
| Watcher conflicts | Exception handling | Deduplication |

---

## Open Questions

1. **Sync vs Async API responses**: Should endpoints wait for event completion or always return pending status?
   - Recommendation: Default to async, offer `?sync=true` for backwards compatibility

2. **Event retention**: How long to keep completed/failed events?
   - Recommendation: 24h for completed, 7d for failed

3. **Worker scaling**: One worker per notebook or shared pool?
   - Recommendation: One per notebook for isolation, shared thread pool

4. **Watcher necessity**: With queue handling all operations, is watcher still needed?
   - Recommendation: Keep for external changes (user edits files directly)

# Event Queue Worker Architecture

## Overview

The event queue system is designed to handle file system operations (move, delete) in a batched, asynchronous manner to reduce race conditions and timing issues that can occur with concurrent operations.

## Architecture

### Components

1. **FileSystemEvent Model** (`codex/db/models/notebook.py`)
   - SQLModel table stored in per-notebook databases
   - Fields:
     - `notebook_id`: Reference to notebook
     - `event_type`: Type of operation ('create', 'modify', 'delete', 'move')
     - `file_path`: Source path for the operation
     - `new_path`: Target path for move operations (optional)
     - `event_metadata`: JSON-encoded additional data (optional)
     - `status`: Current status ('pending', 'processing', 'completed', 'failed')
     - `error_message`: Error details if status is 'failed'
     - `created_at`: When the event was created
     - `processed_at`: When the event was processed

2. **EventQueueWorker** (`codex/core/queue_worker.py`)
   - Background thread that processes events in batches
   - Runs every 5 seconds by default (configurable)
   - Uses threading.Lock for isolation during processing
   - Handles all file system operations: move, delete, create, modify

3. **API Endpoints** (modified)
   - `PATCH /files/{file_id}/move`: Queues move operation
   - `DELETE /files/{file_id}`: Queues delete operation
   - `DELETE /folders/{folder_path}`: Queues folder deletion
   - All return `{"queued": true}` to indicate asynchronous processing

### Workflow

1. **Client Request**: User initiates a file operation via API
2. **Event Creation**: API endpoint creates a FileSystemEvent record with status='pending'
3. **Immediate Response**: API returns success with queued=true
4. **Batch Processing**: EventQueueWorker picks up pending events every 5 seconds
5. **Operation Execution**: Worker performs the actual file system operation
6. **Status Update**: Event status updated to 'completed' or 'failed'

## Batching Strategy

### Why Creates Are Synchronous

Create operations (POST /files/) remain synchronous for several reasons:

1. **File ID Required**: The API must return the new file's ID immediately so clients can work with it
2. **No Race Condition**: Creating a file doesn't conflict with the file watcher - the watcher will simply index the new file
3. **User Expectation**: Users expect newly created files to be immediately available

### Why Moves/Deletes Are Queued

Move and delete operations are queued because:

1. **Watcher Race Conditions**: The file watcher may try to update metadata for a file that's being moved/deleted
2. **Concurrent Operations**: Multiple API calls might try to operate on the same file
3. **Ordering Matters**: Moving then deleting a file must happen in order

### Git Commit Batching

Git commits are batched per processing cycle:

1. All filesystem/database changes in a batch are processed first
2. At the end of the batch, a single git commit is created with a summary message
3. This reduces git overhead and creates cleaner commit history

Example commit messages:
- Single operation: `Move renamed.md`
- Multiple operations: `Batch: move 2 files, delete 3 files`

## Benefits

### Prevents Race Conditions

Before the queue system, move and delete operations could conflict with:
- File watcher updates
- Concurrent API operations
- Git commit operations

The queue system serializes these operations with proper locking.

### Improves Response Times

API endpoints return immediately after queuing, rather than waiting for:
- File system operations
- Database updates
- Git commits

### Better Error Handling

Failed operations are recorded with error messages for debugging.
Events can be retried or inspected for troubleshooting.

## Configuration

The batch interval can be configured when starting the worker:

```python
worker = EventQueueWorker(
    notebook_path="/path/to/notebook",
    notebook_id=1,
    batch_interval=5.0  # seconds
)
```

## Testing

Tests are located in `backend/tests/test_queue_worker.py`:

- `test_queue_event_model`: Tests the FileSystemEvent model
- `test_queue_worker_processing`: Tests worker batch processing
- `test_move_file_queued`: Tests queued move operations
- `test_delete_file_queued`: Tests queued delete operations
- `test_delete_folder_queued`: Tests queued folder deletion

To run the tests:

```bash
cd backend
pytest tests/test_queue_worker.py -v
```

## Migration

The queue system was added in migration `20250204_000000_005_add_filesystem_events_table.py`.

When upgrading:
1. Alembic migration runs automatically on notebook initialization
2. Existing operations continue to work
3. New operations are automatically queued

## Future Enhancements

Potential improvements:

1. **Priority Queue**: Add priority field for urgent operations
2. **Retry Logic**: Automatically retry failed operations
3. **Monitoring**: Add metrics for queue depth and processing time
4. **Batch Optimization**: Group related operations (e.g., folder moves)
5. **External Changes**: Consider routing watcher events through queue
6. **Status API**: Add endpoint to query event status

## Troubleshooting

### Events Not Processing

Check if queue worker is running:
```python
from codex.main import get_active_queue_workers
workers = get_active_queue_workers()
print(f"Active workers: {len(workers)}")
```

### Slow Processing

Events process in batches every 5 seconds. Reduce batch_interval for faster processing:
```python
worker = EventQueueWorker(notebook_path, notebook_id, batch_interval=2.0)
```

### Failed Operations

Query failed events:
```python
from codex.db.models import FileSystemEvent
from codex.db.database import get_notebook_session

session = get_notebook_session(notebook_path)
failed_events = session.query(FileSystemEvent).filter_by(status='failed').all()
for event in failed_events:
    print(f"Event {event.id}: {event.error_message}")
```

## Implementation Notes

### Why Not Use Celery?

We chose a simple threading-based approach because:
- No external dependencies (Redis, RabbitMQ)
- Simpler deployment
- Events stored in SQLite for durability
- Sufficient for single-server deployments

For multi-server deployments, consider migrating to Celery or similar.

### Watcher Integration

The file watcher (`NotebookWatcher`) continues to handle external file changes.
Only API-initiated operations go through the queue.

This allows:
- Real-time indexing of external changes
- Serialized API operations
- Clear separation of concerns

### Database Considerations

Events are stored in per-notebook databases, not the system database.
This provides:
- Isolation between notebooks
- Simpler cleanup (delete notebook = delete events)
- Better scaling for large deployments

## References

- FileSystemEvent model: `backend/codex/db/models/notebook.py`
- EventQueueWorker: `backend/codex/core/queue_worker.py`
- API integration: `backend/codex/api/routes/files.py`, `backend/codex/api/routes/folders.py`
- Lifecycle management: `backend/codex/main.py`
- Tests: `backend/tests/test_queue_worker.py`

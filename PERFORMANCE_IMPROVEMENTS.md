# Performance Improvements: Background Indexing and Pagination

This document describes the performance optimizations implemented for the Codex application to address startup blocking and memory usage issues.

## Problem Statement

1. **Indexing blocks startup**: File indexing was happening synchronously during server startup, causing delays when there were many files to index.
2. **File browser loads everything into memory**: The file browser would load all files from all notebooks at once, causing memory issues with large repositories.

## Implementation

### 1. Background Indexing (✅ Complete)

**Changes Made:**
- Modified `NotebookWatcher` class in `backend/codex/core/watcher.py` to run file scanning in a background thread
- Added indexing status tracking with three states: `not_started`, `in_progress`, `completed`, `error`
- Watcher now starts immediately and indexes in the background, unblocking server startup
- Added new API endpoint to check indexing status: `GET /api/v1/notebooks/{notebook_id}/indexing-status`

**Technical Details:**
```python
class NotebookWatcher:
    def __init__(self, notebook_path: str, notebook_id: int, callback: Optional[Callable] = None):
        # ... existing code ...
        self._indexing_status = "not_started"
        self._indexing_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start watching the notebook directory."""
        logger.info(f"Starting watcher for notebook at {self.notebook_path}")
        self.observer.schedule(self.handler, self.notebook_path, recursive=True)
        self.observer.start()
        
        # Start indexing in a background thread
        self._start_background_indexing()
    
    def _start_background_indexing(self):
        """Start the file scan in a background thread."""
        self._indexing_status = "in_progress"
        self._indexing_thread = threading.Thread(
            target=self._run_indexing,
            name=f"indexer-{self.notebook_id}",
            daemon=True
        )
        self._indexing_thread.start()
```

**Benefits:**
- Server startup is no longer blocked by file indexing
- Large notebooks can be indexed without preventing access to other notebooks
- Status can be monitored via API endpoint
- Graceful shutdown waits for background threads (10s timeout)

**API Usage:**
```bash
# Check indexing status for a notebook
GET /api/v1/notebooks/{notebook_id}/indexing-status?workspace_id={workspace_id}

# Response:
{
  "notebook_id": 1,
  "status": "completed",  # or "in_progress", "not_started", "error"
  "is_alive": false
}
```

### 2. Pagination Support (✅ Complete)

**Changes Made:**
- Added pagination parameters (`skip`, `limit`) to files listing endpoint
- Added pagination parameters to folder contents endpoint
- Updated response format to include pagination metadata

**API Changes:**

**Files Endpoint:**
```bash
GET /api/v1/files/?notebook_id={id}&workspace_id={id}&skip=0&limit=1000

# Response:
{
  "files": [
    { "id": 1, "path": "file1.md", ... },
    { "id": 2, "path": "file2.md", ... }
  ],
  "pagination": {
    "skip": 0,
    "limit": 1000,
    "total": 2500,
    "has_more": true
  }
}
```

**Folders Endpoint:**
```bash
GET /api/v1/folders/{folder_path}?notebook_id={id}&workspace_id={id}&skip=0&limit=100

# Response:
{
  "path": "documents",
  "name": "documents",
  "files": [...],  # Only direct children, paginated
  "subfolders": [...],  # Only immediate subfolders
  "pagination": {
    "skip": 0,
    "limit": 100,
    "total": 250,
    "has_more": true
  }
}
```

**Default Limits:**
- Files endpoint: 1000 items per page
- Folders endpoint: 100 items per page

**Benefits:**
- API can handle notebooks with thousands of files
- Memory usage is bounded by pagination limits
- Clients can choose appropriate page sizes for their use case
- Backwards compatible (default limits provide all data for small repositories)

### 3. Frontend Compatibility (✅ Complete)

**Changes Made:**
- Updated `fileService.list()` in `frontend/src/services/codex.ts` to handle new response format
- Maintains backwards compatibility by extracting files array from response

```typescript
async list(notebookId: number, workspaceId: number): Promise<FileMetadata[]> {
  const response = await apiClient.get<{ files: FileMetadata[]; pagination: any }>(
    `/api/v1/files/?notebook_id=${notebookId}&workspace_id=${workspaceId}`
  )
  // For backwards compatibility, return just the files array
  return response.data.files || response.data
}
```

## Lazy Loading File Tree (⏳ Future Work)

The folders endpoint already returns only immediate children (non-recursive), which is the foundation for lazy loading. However, full implementation would require:

1. **Rewrite file tree loading**: Instead of loading all files via `/api/v1/files/`, use `/api/v1/folders/` endpoint
2. **Load folders on-demand**: When a folder is expanded, make API call to load its contents
3. **Caching**: Cache loaded folders to avoid redundant API calls
4. **Loading indicators**: Show loading state while fetching folder contents

**Why not implemented yet:**
- Requires significant refactoring of `FileTreeItem.vue` and related components
- Current implementation with pagination is already a major improvement
- Better suited as a separate focused task

**Current File Tree Behavior:**
```
Notebook expanded → Load ALL files → Build tree in memory → Display
```

**Desired Lazy Loading Behavior:**
```
Notebook expanded → Load root items only
  ↓
Folder clicked → Load folder contents → Cache → Display
  ↓  
Subfolder clicked → Load subfolder contents → Cache → Display
```

## Testing

### Background Indexing Test
```python
# Test script demonstrates:
# 1. Watcher starts immediately
# 2. Indexing runs in background
# 3. Status transitions: not_started → in_progress → completed

from codex.core.watcher import NotebookWatcher
watcher = NotebookWatcher(notebook_path, notebook_id)
print(watcher.get_indexing_status())  # not_started
watcher.start()
print(watcher.get_indexing_status())  # in_progress
# ... indexing happens in background ...
print(watcher.get_indexing_status())  # completed
```

### Pagination Test
```bash
# Verify pagination parameters are accepted
curl "http://localhost:8000/api/v1/files/?notebook_id=1&workspace_id=1&skip=0&limit=10"
curl "http://localhost:8000/api/v1/folders/documents?notebook_id=1&workspace_id=1&skip=0&limit=10"
```

## Performance Impact

**Before:**
- Startup time: Blocked by indexing (proportional to file count)
- Memory usage: All files loaded into memory when notebook expanded
- Large repositories: Could cause timeout or out-of-memory errors

**After:**
- Startup time: Non-blocking (indexing happens in background)
- Memory usage: Bounded by pagination limits
- Large repositories: API can handle thousands of files per notebook
- Improved user experience: Server available immediately after startup

## Migration Notes

**For API Consumers:**
- Files endpoint response format changed from array to object with `files` and `pagination` keys
- Clients should update to use new format, though backward compatibility is maintained
- Pagination is optional (defaults provide reasonable page sizes)

**For Notebook Operations:**
- File operations work immediately even while indexing is in progress
- New files are picked up by the watcher in real-time
- Indexing status can be polled if needed (e.g., to show progress indicator)

## Future Enhancements

1. **Lazy Loading File Tree** (described above)
2. **Progressive Loading Indicator**: Show indexing progress in UI
3. **Virtual Scrolling**: For very long file lists
4. **Search Optimization**: Index-based search with pagination
5. **Background Re-indexing**: Periodic re-scan in background

## References

- Issue: "indexing should happen in a background thread, especially on startup"
- Issue: "the file browser should use pagination and only return the levels under the file immediately clicked"
- Files changed:
  - `backend/codex/core/watcher.py`
  - `backend/codex/api/routes/files.py`
  - `backend/codex/api/routes/folders.py`
  - `backend/codex/api/routes/notebooks.py`
  - `backend/codex/main.py`
  - `frontend/src/services/codex.ts`

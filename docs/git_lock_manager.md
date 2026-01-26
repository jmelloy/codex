# Git Operations Lock Manager

## Overview

The Git Lock Manager provides thread-safe access to git operations to prevent conflicts when multiple operations are performed concurrently. This is essential in environments where:

- Multiple API requests may trigger git commits simultaneously
- File watchers auto-commit changes while API operations are in progress
- Concurrent file operations occur in the same notebook

## Architecture

### GitLockManager Class

The `GitLockManager` is a singleton class that maintains per-notebook-path locks. It provides both synchronous and asynchronous locking mechanisms.

**Key Features:**
- Singleton pattern ensures a single lock manager instance across the application
- Per-notebook-path locking using dictionaries of locks
- `threading.RLock` (reentrant lock) for synchronous operations - allows nested locking
- `asyncio.Lock` for asynchronous operations
- Context managers for easy lock acquisition and release

### Integration with GitManager

All git operations in the `GitManager` class are now wrapped with the lock manager:

- Repository initialization (`_init_or_get_repo`)
- File addition (`add_file`)
- Committing changes (`commit`)
- Reading file history (`get_file_history`)
- Getting file content at commit (`get_file_at_commit`)
- Getting diffs (`get_diff`)
- Auto-committing changes (`auto_commit_on_change`)

## Usage

### Basic Example

```python
from codex.core.git_manager import GitManager

# GitManager automatically uses the lock manager internally
git_manager = GitManager("/path/to/notebook")
git_manager.commit("My commit message", ["/path/to/file"])
```

The lock manager is transparent to users of `GitManager` - all operations are automatically protected.

### Advanced Usage

If you need to perform multiple git operations atomically, you can directly use the lock manager:

```python
from codex.core.git_lock_manager import git_lock_manager
from codex.core.git_manager import GitManager

notebook_path = "/path/to/notebook"
git_manager = GitManager(notebook_path)

# Synchronous operations
with git_lock_manager.lock(notebook_path):
    # Multiple operations will be atomic
    git_manager.add_file("file1.md")
    git_manager.add_file("file2.md")
    git_manager.commit("Add multiple files")

# Asynchronous operations
async with git_lock_manager.async_lock(notebook_path):
    # Multiple operations will be atomic
    git_manager.add_file("file3.md")
    git_manager.commit("Add file asynchronously")
```

## Concurrency Behavior

### Per-Notebook Isolation

Locks are maintained per notebook path. This means:
- Operations on different notebooks can run in parallel without blocking each other
- Operations on the same notebook are serialized to prevent conflicts
- The lock manager automatically resolves symlinks to ensure consistent path handling

### Nested Lock Acquisition

The lock manager uses `threading.RLock` (reentrant lock), which allows the same thread to acquire the lock multiple times. This is important for methods like `auto_commit_on_change` which internally calls both `add_file` and `commit`, each of which tries to acquire the lock.

### Read vs Write Operations

Currently, all git operations use the same lock (no distinction between read and write operations). This ensures maximum safety but may serialize read operations that could theoretically run in parallel. This is an acceptable trade-off for:
- Simplicity of implementation
- Safety - git operations can be complex and may have side effects
- Performance - git operations are typically fast

## Testing

Comprehensive tests are provided in `tests/test_git_lock.py`:

- `test_git_lock_manager_singleton` - Verifies singleton pattern
- `test_concurrent_commits_same_notebook` - Tests concurrent commits are serialized
- `test_concurrent_add_and_commit` - Tests add/commit race conditions
- `test_concurrent_reads_and_writes` - Tests mixed read/write operations
- `test_auto_commit_concurrent` - Tests file watcher auto-commits
- `test_lock_per_notebook_isolation` - Tests multi-notebook independence
- `test_nested_lock_acquisition` - Tests reentrant lock behavior
- `test_concurrent_init_same_path` - Tests concurrent repo initialization

Run tests with:
```bash
pytest tests/test_git_lock.py -v
```

## Performance Considerations

The lock manager has minimal overhead:
- Lock acquisition/release is very fast (microseconds)
- Locks are only held during actual git operations
- Different notebooks can be accessed in parallel
- The singleton pattern ensures no memory bloat from creating multiple lock managers

## Troubleshooting

### Deadlocks

Deadlocks should not occur because:
- We use `RLock` which allows nested acquisition
- Each notebook has its own lock (no inter-notebook locking)
- Lock acquisition follows a consistent order

If you suspect a deadlock, check for:
- External git operations not using the lock manager
- Custom code that acquires locks in different orders

### Performance Issues

If git operations seem slow:
- Check if multiple threads are competing for the same notebook
- Consider splitting notebooks to allow more parallelism
- Review git repository size - large repos have slower operations

### Lock Manager Not Working

If you're still seeing git conflicts:
- Ensure all git operations go through `GitManager`
- Check for external processes modifying the git repository
- Verify that the lock manager is being used (check logs for "Acquiring/Acquired/Released" messages)

## Future Enhancements

Potential improvements:
- Separate read/write locks for better read concurrency
- Lock timeout with automatic deadlock detection
- Metrics and monitoring for lock contention
- Configuration for lock behavior (timeout, retries, etc.)

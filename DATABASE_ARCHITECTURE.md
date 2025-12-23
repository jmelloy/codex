# Database Architecture - Split Database System

## Overview

Codex now uses a three-tier database architecture instead of a single monolithic database. This split improves performance, enables parallel queries, and allows for better scalability.

## Architecture Diagram

```
Root Directory
├── .lab/
│   └── db/
│       └── core.db                    # Core database (authentication)
│
└── workspaces/
    └── {username}/
        ├── .lab/
        │   └── db/
        │       └── workspace.db        # Workspace database (notebook registry)
        └── notebooks/
            ├── {notebook_id_1}/
            │   └── .lab/
            │       └── notebook.db     # Notebook 1 database
            └── {notebook_id_2}/
                └── .lab/
                    └── notebook.db     # Notebook 2 database
```

## Database Types

### 1. Core Database (`core.db`)

**Location**: `{CODEX_WORKSPACE_PATH}/.lab/db/core.db`

**Purpose**: Centralized authentication and user management

**Tables**:
- `users`: User accounts (username, email, hashed_password, workspace_path, is_active)
- `refresh_tokens`: JWT refresh tokens (token, user_id, expires_at, revoked)

**Manager**: `CoreDatabaseManager` (`db/core_operations.py`)

**Models**: `db/core_models.py` (User, RefreshToken)

### 2. Workspace Database (`workspace.db`)

**Location**: `{workspace}/.lab/db/workspace.db`

**Purpose**: Registry of notebooks within a workspace

**Tables**:
- `notebooks`: Notebook metadata (id, title, description, db_path, created_at, updated_at, settings, metadata)

**Manager**: `WorkspaceDatabaseManager` (`db/workspace_operations.py`)

**Models**: `db/workspace_models.py` (Notebook)

**Note**: The `db_path` column stores the path to each notebook's individual database file.

### 3. Notebook Databases (`notebook.db`)

**Location**: `{workspace}/notebooks/{notebook_id}/.lab/notebook.db`

**Purpose**: Per-notebook data storage for fast notebook-scoped operations

**Tables**:
- `pages`: Pages in the notebook (id, notebook_id, title, date, narrative, metadata)
- `tags`: Tags used in the notebook (id, name, color)
- `page_tags`: Many-to-many relationship between pages and tags
- `markdown_files`: Indexed markdown files in the notebook directory

**Manager**: `NotebookDatabaseManager` (`db/notebook_operations.py`)

**Models**: `db/notebook_models.py` (Page, Tag, PageTag, MarkdownFile)

## Benefits

### 1. Fast Notebook-Scoped Search
Each notebook has its own database, making searches within a notebook much faster:
- No need to filter by notebook_id on every query
- Smaller databases = faster queries
- Better query optimization for notebook-specific operations

### 2. Parallel Queries
Can query multiple notebook databases simultaneously:
- Workspace-wide search can query all notebook databases in parallel
- Reduces overall search time for cross-notebook queries
- Better utilization of multi-core systems

### 3. Isolated Authentication
Authentication data is completely separate from workspace data:
- Core database can be backed up independently
- Authentication system can be scaled separately
- Easier to implement multi-tenant systems

### 4. Scalability
- Notebook databases can be distributed across different storage systems
- Individual notebook databases can be backed up/restored independently
- Easier to implement notebook archival strategies
- Reduces database lock contention

## Usage Examples

### Creating a Workspace

```python
from core.workspace import Workspace

# Initialize workspace (creates workspace.db)
ws = Workspace.initialize("/path/to/workspace", "My Workspace")
```

### Creating a Notebook

```python
# Creates notebook entry in workspace.db
# Also creates and initializes notebook-specific database
notebook = ws.create_notebook("AI Experiments", "Machine learning notes")

# Notebook database is at:
# /path/to/workspace/notebooks/{notebook_id}/.lab/notebook.db
```

### Accessing Databases

```python
# Workspace database manager
ws.workspace_db_manager.get_notebook(notebook_id)

# Notebook database manager (per notebook)
notebook_db = ws.get_notebook_db_manager(notebook_id)
notebook_db.create_page(page_data)
```

### Authentication

```python
from api.utils import get_core_db_path
from db.core_operations import CoreDatabaseManager

# Core database manager
core_db = CoreDatabaseManager(get_core_db_path())
user = core_db.get_user_by_username("john")
```

## Code Organization

### Database Models

Each database type has its own base class with CRUD operations:

- `CoreBase` (from `db/core_models.py`)
- `WorkspaceBase` (from `db/workspace_models.py`)
- `NotebookBase` (from `db/notebook_models.py`)

All base classes inherit from `CRUDMixin` (`db/crud_mixin.py`) which provides:
- `create()`, `get_by_id()`, `get_all()`, `find_by()`, `find_one_by()`
- `update()`, `delete()`, `delete_by_id()`
- Foreign key validation

### Database Managers

Each database type has a manager class:

- `CoreDatabaseManager`: User and auth operations
- `WorkspaceDatabaseManager`: Notebook registry operations
- `NotebookDatabaseManager`: Page, tag, and markdown file operations

### Workspace Integration

The `Workspace` class manages all database types:

```python
class Workspace:
    @property
    def workspace_db_manager(self) -> WorkspaceDatabaseManager:
        """Get the workspace database manager (notebook registry)."""
        
    def get_notebook_db_manager(self, notebook_id: str) -> NotebookDatabaseManager:
        """Get the database manager for a specific notebook."""
```

## Migration from Old System

The old system used a single `index.db` file at `{workspace}/.lab/db/index.db` containing:
- Users (now in core.db)
- Notebooks (now in workspace.db)
- Pages (now in per-notebook databases)
- Tags (now in per-notebook databases)
- MarkdownFiles (now in per-notebook databases)

**Migration Strategy** (if needed):
1. Read all data from old `index.db`
2. Create new `core.db` with users and refresh tokens
3. Create new `workspace.db` with notebook registry
4. For each notebook, create a `notebook.db` with its pages, tags, and files
5. Update workspace path references

## Performance Considerations

### Query Patterns

**Fast Operations**:
- Authenticate user (single core.db query)
- List notebooks (single workspace.db query)
- Search within notebook (single notebook.db query)
- Get page details (single notebook.db query)

**Slower Operations** (but parallelizable):
- Search across all notebooks (queries N notebook databases)
- Get all pages in workspace (queries N notebook databases)

### Best Practices

1. **Cache notebook database managers**: The workspace class caches notebook database managers for reuse
2. **Use notebook-scoped queries when possible**: Always specify notebook_id to query only one database
3. **Parallel workspace-wide searches**: Use concurrent queries when searching across notebooks
4. **Index properly**: Each database has appropriate indexes for common queries

## Testing

Tests have been updated to work with the new architecture:

- `test_initialize_workspace`: Checks for workspace.db creation
- `test_create_notebook`: Verifies notebook.db is created
- `test_list_notebooks`: Uses WorkspaceDatabaseManager
- `test_update_notebook`: Uses WorkspaceDatabaseManager
- `test_delete_notebook`: Uses WorkspaceDatabaseManager

## Future Enhancements

1. **Database Sharding**: Distribute notebook databases across multiple storage systems
2. **Caching Layer**: Add Redis caching for frequently accessed data
3. **Replication**: Replicate core.db for high availability
4. **Archival**: Move inactive notebook databases to cold storage
5. **Full-Text Search**: Implement FTS5 in each notebook database for advanced search

## Related Files

- `backend/db/core_models.py`: Core database models
- `backend/db/workspace_models.py`: Workspace database models
- `backend/db/notebook_models.py`: Notebook database models
- `backend/db/crud_mixin.py`: Shared CRUD operations
- `backend/db/core_operations.py`: Core database manager
- `backend/db/workspace_operations.py`: Workspace database manager
- `backend/db/notebook_operations.py`: Notebook database manager
- `backend/core/workspace.py`: Workspace class with database integration
- `backend/core/notebook.py`: Notebook class with database operations
- `backend/api/auth.py`: Authentication using core database
- `backend/api/utils.py`: Helper functions (get_core_db_path)

## Summary

The split database architecture provides:
- ✅ Better performance through database isolation
- ✅ Parallel query capabilities
- ✅ Independent authentication system
- ✅ Scalable notebook storage
- ✅ Easier backup and recovery
- ✅ Foundation for future enhancements

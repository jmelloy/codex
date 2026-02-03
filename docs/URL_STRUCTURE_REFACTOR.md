# Backend URL Structure Refactoring

## Overview

This document outlines the refactoring of the Codex backend API URL structure to use path-based routing with slugs instead of query parameters.

## Status: IN PROGRESS

**Completed:**
- ✅ Database models updated with slug fields
- ✅ Migration created and tested
- ✅ Workspace routes support slug-based access
- ✅ Notebook routes support nested slug-based access
- ✅ Comprehensive test suite for new routes
- ✅ Both slug and ID access supported for backward compatibility

**In Progress:**
- 🔄 File routes refactoring
- 🔄 Search routes refactoring
- 🔄 Folder routes refactoring

**Remaining:**
- ⏳ Update frontend API client
- ⏳ Update all existing tests
- ⏳ Plugin routes refactoring (if needed)
- ⏳ Documentation updates

## Goals

1. **RESTful Design**: Use hierarchical URL paths that reflect resource relationships
2. **Slug-based Routing**: Use human-readable slugs instead of numeric IDs
3. **Cleaner API**: Eliminate query parameters for resource identification
4. **Backward Compatibility**: Maintain existing functionality during transition

## Current URL Structure

### Workspaces
```
GET    /api/v1/workspaces/                     # List all workspaces
GET    /api/v1/workspaces/{workspace_id}       # Get specific workspace
POST   /api/v1/workspaces/                     # Create workspace
PATCH  /api/v1/workspaces/{workspace_id}/theme # Update theme
```

### Notebooks
```
GET    /api/v1/notebooks/?workspace_id={id}                    # List notebooks
GET    /api/v1/notebooks/{notebook_id}?workspace_id={id}       # Get notebook
POST   /api/v1/notebooks/                                      # Create notebook
GET    /api/v1/notebooks/{id}/indexing-status?workspace_id={id} # Get indexing status
GET    /api/v1/notebooks/{id}/plugins                          # List plugins
GET    /api/v1/notebooks/{id}/plugins/{plugin_id}              # Get plugin config
PUT    /api/v1/notebooks/{id}/plugins/{plugin_id}              # Update plugin config
DELETE /api/v1/notebooks/{id}/plugins/{plugin_id}              # Delete plugin config
```

### Files
```
GET    /api/v1/files/?notebook_id={id}&workspace_id={id}       # List files
GET    /api/v1/files/{file_id}?notebook_id={id}&workspace_id={id} # Get file
POST   /api/v1/files/                                          # Create file
PUT    /api/v1/files/{file_id}?notebook_id={id}&workspace_id={id} # Update file
DELETE /api/v1/files/{file_id}?workspace_id={id}              # Delete file
GET    /api/v1/files/by-path?path={path}&notebook_id={id}&workspace_id={id} # Get by path
POST   /api/v1/files/upload                                    # Upload file
POST   /api/v1/files/{id}/move?notebook_id={id}&workspace_id={id} # Move file
GET    /api/v1/files/{id}/history?notebook_id={id}&workspace_id={id} # Get history
```

### Search
```
GET /api/v1/search/?workspace_id={id}&notebook_id={id}&query={q}
```

### Folders
```
GET  /api/v1/folders/?notebook_id={id}&workspace_id={id}&path={path}
POST /api/v1/folders/                                          # Create folder
```

## Proposed URL Structure

### Workspaces
```
GET    /api/v1/workspaces/                     # List all workspaces
GET    /api/v1/workspaces/{workspace_slug}     # Get specific workspace
POST   /api/v1/workspaces/                     # Create workspace
PATCH  /api/v1/workspaces/{workspace_slug}/theme # Update theme
```

### Notebooks
```
GET    /api/v1/workspaces/{workspace_slug}/notebooks                    # List notebooks
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}    # Get notebook
POST   /api/v1/workspaces/{workspace_slug}/notebooks                    # Create notebook
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/indexing-status
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins/{plugin_id}
PUT    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins/{plugin_id}
DELETE /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins/{plugin_id}
```

### Files
```
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/{file_path:path}
POST   /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files
PUT    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/{file_path:path}
DELETE /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/{file_path:path}
POST   /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/upload
POST   /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/{file_path:path}/move
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/{file_path:path}/history
```

### Search
```
GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/search?query={q}
GET /api/v1/workspaces/{workspace_slug}/search?query={q}  # Search all notebooks in workspace
```

### Folders
```
GET  /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/folders/{folder_path:path}
POST /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/folders
```

## Implementation Strategy

### Phase 1: Add Slug Fields to Models

1. Add `slug` field to `Workspace` model (unique per user)
2. Add `slug` field to `Notebook` model (unique per workspace)
3. Create database migration to add slug columns
4. Populate slugs for existing records from `name` or `path` fields
5. Ensure slug generation on new record creation

### Phase 2: Update Route Handlers

1. Create helper functions to lookup by slug instead of ID
2. Update workspace routes to accept slug parameter
3. Update notebook routes to accept workspace_slug and notebook_slug
4. Update file routes to accept workspace_slug, notebook_slug, and file path
5. Update search and folder routes similarly
6. Keep internal logic using IDs for database queries

### Phase 3: Update Tests

1. Update all test files to use new URL patterns
2. Ensure tests create slugs appropriately
3. Add tests for slug uniqueness and collision handling

### Phase 4: Update Frontend

1. Update API service layer to use new URLs
2. Update routing in frontend to use slugs
3. Update all component calls to API

## Slug Generation Rules

1. **Convert to lowercase**: All slugs are lowercase
2. **Replace spaces**: Spaces become hyphens
3. **Remove special characters**: Only alphanumeric and hyphens allowed
4. **Uniqueness**: Must be unique within scope (workspace slugs unique per user, notebook slugs unique per workspace)
5. **Collision handling**: Append counter or UUID segment if slug exists
6. **Immutability**: Once created, slugs should not change (or implement redirect logic)

Example:
- "My Research Project" → "my-research-project"
- "Experiment #42" → "experiment-42"
- "Data (2024)" → "data-2024"

## Benefits

1. **Improved Readability**: URLs are more human-readable and self-documenting
2. **Better RESTful Design**: Resource hierarchy is clear from URL structure
3. **Easier Bookmarking**: Slug-based URLs are easier to remember and share
4. **SEO-friendly**: More descriptive URLs (if frontend exposed publicly)
5. **Cleaner Code**: No need to pass workspace_id and notebook_id as query params everywhere

## Considerations

1. **Slug Changes**: If workspace/notebook names change, should slugs change?
   - **Recommendation**: Keep slugs immutable or implement redirects
2. **URL Length**: Very long names could create long URLs
   - **Recommendation**: Limit slug length (e.g., 50 characters)
3. **Performance**: Slug lookups vs ID lookups
   - **Recommendation**: Add database indexes on slug fields
4. **Backward Compatibility**: Old URLs with IDs
   - **Recommendation**: Maintain both routes initially, deprecate ID-based routes later

## Migration Path

1. **Phase 1**: Add slug fields, keep existing ID-based routes working
2. **Phase 2**: Implement new slug-based routes alongside old ones
3. **Phase 3**: Update tests and frontend to use new routes
4. **Phase 4**: Mark old routes as deprecated in documentation
5. **Phase 5**: (Future) Remove old routes in major version bump

## Database Schema Changes

### Workspace Table
```sql
ALTER TABLE workspaces ADD COLUMN slug VARCHAR(100) UNIQUE;
CREATE INDEX idx_workspaces_slug ON workspaces(slug);
```

### Notebook Table
```sql
ALTER TABLE notebooks ADD COLUMN slug VARCHAR(100);
CREATE UNIQUE INDEX idx_notebooks_slug_workspace ON notebooks(workspace_id, slug);
```

## Implementation Details

### What Has Been Implemented

#### 1. Database Models (✅ Complete)
- Added `slug` field to `Workspace` model (unique, indexed)
- Added `slug` field to `Notebook` model (unique per workspace, indexed)
- Created Alembic migration `20260203_000000_007_add_slug_fields.py`
- Migration handles SQLite constraints properly using batch operations
- Automatically populates slugs for existing records from path/name

#### 2. Workspace Routes (✅ Complete)
**New/Updated Endpoints:**
- `GET /api/v1/workspaces/` - List workspaces (now includes slug in response)
- `GET /api/v1/workspaces/{workspace_slug}` - Get workspace by slug OR ID
- `POST /api/v1/workspaces/` - Create workspace (auto-generates slug)
- `PATCH /api/v1/workspaces/{workspace_slug}/theme` - Update theme by slug OR ID

**Implementation Details:**
- Added `slugify()` function to convert names to URL-safe slugs
- Added `slug_exists_in_db()` to check for slug collisions
- Added `get_workspace_by_slug_or_id()` helper for flexible lookup
- Slug collision handling with UUID suffix
- Backward compatible: accepts both slug and numeric ID

#### 3. Notebook Routes (✅ Complete)
**New Nested Endpoints:**
- `GET /api/v1/workspaces/{workspace_slug}/notebooks` - List notebooks in workspace
- `POST /api/v1/workspaces/{workspace_slug}/notebooks` - Create notebook in workspace
- `GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}` - Get notebook
- `GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/indexing-status` - Get indexing status

**Implementation Details:**
- Created separate `nested_router` for workspace-nested routes
- Added `get_notebook_by_slug_or_id()` helper for flexible lookup
- Added `slug_exists_for_workspace()` to check notebook slug collisions
- Slug collision handling with UUID suffix
- Backward compatible: old flat routes still work (marked as deprecated)
- Both slug and numeric ID accepted in nested routes

#### 4. Tests (✅ Complete)
Created comprehensive test suite in `backend/tests/test_slug_routes.py`:
- ✅ Workspace slug generation on creation
- ✅ Get workspace by slug and by ID
- ✅ Nested notebook creation with slug generation
- ✅ Get notebook by slug and by ID
- ✅ List notebooks using nested route

All 5 tests passing.

### What Needs to Be Done

#### 1. File Routes (⏳ TODO)
Files currently use query parameters. Need to create nested router:

**Current:**
```
GET /api/v1/files/?notebook_id={id}&workspace_id={id}
GET /api/v1/files/{file_id}?notebook_id={id}&workspace_id={id}
```

**Proposed:**
```
GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files
GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/{file_path:path}
```

**Considerations:**
- Files have paths within notebooks (can be nested in folders)
- Need to handle path parameter properly (use FastAPI's `path` type)
- Many file operations: list, get, create, update, delete, upload, move, history
- File access by ID vs by path - may need both approaches

#### 2. Search Routes (⏳ TODO)
**Current:**
```
GET /api/v1/search/?workspace_id={id}&notebook_id={id}&query={q}
```

**Proposed:**
```
GET /api/v1/workspaces/{workspace_slug}/search?query={q}
GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/search?query={q}
```

#### 3. Folder Routes (⏳ TODO)
**Current:**
```
GET /api/v1/folders/?notebook_id={id}&workspace_id={id}&path={path}
POST /api/v1/folders/
```

**Proposed:**
```
GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/folders/{folder_path:path}
POST /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/folders
```

#### 4. Frontend Updates (⏳ TODO)
Update `frontend/src/services/codex.ts` to use new URL patterns:
- Update all workspace API calls to use slugs
- Update all notebook API calls to use nested routes
- Update file, search, and folder calls once backend is updated
- Keep backward compatibility during transition

#### 5. Existing Test Updates (⏳ TODO)
Many existing tests use the old URL patterns with query parameters. Need to update:
- `tests/test_files_api.py` - File operation tests
- `tests/test_file_creation.py` - File creation tests  
- `tests/test_search_api.py` - Search tests
- Any other tests that create workspaces/notebooks/files

## Note on Terminology

The problem statement mentions "workbooks" but the codebase consistently uses "workspaces". This document maintains the current "workspace" terminology to avoid confusion and minimize changes.

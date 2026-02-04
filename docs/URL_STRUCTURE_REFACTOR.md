# Backend URL Structure Refactoring

## Overview

This document outlines the refactoring of the Codex backend API URL structure to use path-based routing with slugs instead of query parameters.

## Status: MOSTLY COMPLETE (2026-02-04)

**Completed:**
- ✅ Database models updated with slug fields
- ✅ Migration created and tested
- ✅ Workspace routes support slug-based access
- ✅ Notebook routes support nested slug-based access
- ✅ File routes refactored (14/17 routes nested)
- ✅ Folder routes refactored (all routes nested)
- ✅ Search routes refactored (all routes nested)
- ✅ Integration routes refactored (all routes nested)
- ✅ Comprehensive test suite for new routes (325/328 passing)
- ✅ Both slug and ID access supported for backward compatibility
- ✅ Frontend updated for most routes

**Remaining:**
- 🔄 File routes: 3 missing nested routes (upload, from-template, history/{commit})
- 🔄 Frontend: Update fileService.upload() and templateService.createFromTemplate()
- ⏳ Query routes: Not yet nested (frontend uses old route)
- ⏳ Task routes: Not yet nested (no frontend usage)
- ⏳ Deprecate/remove old flat routes
- ⏳ Documentation updates

**Test Status:**
- 325 passing, 3 failing (template API tests using old route)
- All new nested routes have comprehensive test coverage

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
- `GET /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins` - List plugins
- `GET/PUT/DELETE /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins/{plugin_id}` - Plugin config

**Implementation Details:**
- Created separate `nested_router` for workspace-nested routes
- Added `get_notebook_by_slug_or_id()` helper for flexible lookup
- Added `slug_exists_for_workspace()` to check notebook slug collisions
- Slug collision handling with UUID suffix
- Backward compatible: old flat routes still work (but deprecated)
- Both slug and numeric ID accepted in nested routes

#### 4. File Routes (✅ Mostly Complete - 14/17 routes)
**Implemented Nested Endpoints:**
- `GET/POST /api/v1/workspaces/{ws}/notebooks/{nb}/files/` - List/create files
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/templates` - List templates
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` - Get file metadata
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/text` - Get text content
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/content` - Get binary content
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/path/{filepath:path}` - Get by path
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/path/{filepath:path}/text` - Get text by path
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/path/{filepath:path}/content` - Get binary by path
- `PUT /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` - Update file
- `PATCH /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/move` - Move file
- `DELETE /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` - Delete file
- `POST /api/v1/workspaces/{ws}/notebooks/{nb}/files/resolve-link` - Resolve wiki link
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history` - Get file history

**Missing Nested Routes (Frontend Uses Old):**
- ⏳ `POST /api/v1/workspaces/{ws}/notebooks/{nb}/files/upload` - File upload
- ⏳ `POST /api/v1/workspaces/{ws}/notebooks/{nb}/files/from-template` - Create from template
- ⏳ `GET /api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history/{commit}` - Get file at commit

#### 5. Folder Routes (✅ Complete)
**Implemented Nested Endpoints:**
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` - Get folder
- `PUT /api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` - Update folder properties
- `DELETE /api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` - Delete folder

Frontend fully migrated to use nested routes.

#### 6. Search Routes (✅ Complete)
**Implemented Nested Endpoints:**
- `GET /api/v1/workspaces/{ws}/search/?q=` - Workspace-wide search
- `GET /api/v1/workspaces/{ws}/search/tags?tags=` - Search by tags in workspace
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/search/?q=` - Notebook-specific search
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/search/tags?tags=` - Search by tags in notebook

Frontend fully migrated to use nested routes.

#### 7. Integration Routes (✅ Complete)
**Implemented Nested Endpoints:**
- `GET /api/v1/workspaces/{ws}/notebooks/{nb}/integrations` - List integrations
- `PUT /api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/enable` - Enable integration
- `GET/PUT /api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/config` - Get/update config
- `POST /api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/execute` - Execute integration

All integration tests updated to use nested routes.

#### 8. Tests (✅ Mostly Complete)
Created comprehensive test suite:
- ✅ `test_slug_routes.py` - Slug generation and lookup (5 tests)
- ✅ `test_files_api.py` - File operations with nested routes (50+ tests)
- ✅ `test_folders_api.py` - Folder operations (10+ tests)
- ✅ `test_search_api.py` - Search functionality (15+ tests)
- ✅ `test_plugin_api.py` - Plugin config (11 tests, using nested)
- ✅ `test_integrations_api.py` - Integration operations (9 tests, using nested)
- ✅ `test_notebooks_api.py` - Notebook operations (20 tests)
- ❌ `test_template_api.py` - 1 failure (uses old from-template route)

**Overall: 325 passing, 3 failing (template tests using old routes)**

### What Needs to Be Done

#### 1. File Routes - Missing 3 Nested Routes (⏳ High Priority)

**Current Problem:**
Frontend still uses old flat routes for these operations:
- `/api/v1/files/upload` → `fileService.upload()`
- `/api/v1/files/from-template` → `templateService.createFromTemplate()`
- `/api/v1/files/{id}/history/{commit}` → `fileService.getAtCommit()`

**Required Implementation:**
```
POST /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/upload
POST /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/from-template
GET  /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/files/{id}/history/{commit}
```

**Action Items:**
- [ ] Implement nested upload route (similar to existing upload but with nested params)
- [ ] Implement nested from-template route (similar to existing but with nested params)
- [ ] Implement nested history/{commit} route (similar to existing but with nested params)
- [ ] Update frontend `fileService.upload()` to use new route
- [ ] Update frontend `templateService.createFromTemplate()` to use new route
- [ ] Update frontend `fileService.getAtCommit()` to use new route
- [ ] Fix test failure in `test_template_api.py`

#### 2. Query Routes (⏳ Medium Priority)

**Current:**
```
POST /api/v1/query/?workspace_id={id}
```

**Proposed:**
```
POST /api/v1/workspaces/{workspace_slug}/query/
```

Frontend actively uses the query service for dynamic views. This is medium priority.

**Action Items:**
- [ ] Create nested query router
- [ ] Implement workspace-nested query endpoint
- [ ] Update frontend `queryService.execute()` to use new route
- [ ] Update tests to use new route

#### 3. Task Routes (⏳ Low Priority)

**Current:**
```
GET  /api/v1/tasks/?workspace_id={id}
POST /api/v1/tasks/?workspace_id={id}&title={title}
```

**Proposed:**
```
GET  /api/v1/workspaces/{workspace_slug}/tasks/
POST /api/v1/workspaces/{workspace_slug}/tasks/
```

Tasks are not used by frontend. This is low priority.

**Action Items:**
- [ ] Create nested task routes under workspace
- [ ] Update tests to use new routes

#### 4. Frontend Updates (⏳ After Backend Routes Added)

Files that need updates:
- `frontend/src/services/codex.ts`:
  - `fileService.upload()` - Line 594
  - `templateService.createFromTemplate()` - Line 668
  - `fileService.getAtCommit()` - Referenced but not shown
- `frontend/src/services/queryService.ts`:
  - `queryService.execute()` - Line 22-26

#### 5. Cleanup (⏳ Future)

After all routes are implemented and frontend migrated:

**Deprecate Old Routes:**
- Old notebook plugin routes (4 routes) - have nested equivalents
- Old file routes (14+ routes) - have nested equivalents
- Old integration routes (5 routes) - have nested equivalents

**Delete Unused Files:**
- `backend/codex/api/routes/markdown.py` - empty router, not used

**Update Documentation:**
- Mark URL_STRUCTURE_REFACTOR.md as COMPLETE
- Update any API documentation

## Note on Terminology

The problem statement mentions "workbooks" but the codebase consistently uses "workspaces". This document maintains the current "workspace" terminology to avoid confusion and minimize changes.

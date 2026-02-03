# Backend URL Structure Refactoring

## Overview

This document outlines the refactoring of the Codex backend API URL structure to use path-based routing with slugs instead of query parameters.

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

## Note on Terminology

The problem statement mentions "workbooks" but the codebase consistently uses "workspaces". This document maintains the current "workspace" terminology to avoid confusion and minimize changes.

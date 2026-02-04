# Plugin and Integration Endpoint Migration

## Overview

This document describes the migration of plugin and integration endpoints from the old flat/workspace-scoped structure to the new notebook-nested structure, as specified in ROUTE_AUDIT.md and URL_STRUCTURE_REFACTOR.md.

## Changes Made

### 1. Notebook Plugin Routes

**Old Structure (Deprecated):**
```
GET    /api/v1/notebooks/{notebook_id}/plugins
GET    /api/v1/notebooks/{notebook_id}/plugins/{plugin_id}
PUT    /api/v1/notebooks/{notebook_id}/plugins/{plugin_id}
DELETE /api/v1/notebooks/{notebook_id}/plugins/{plugin_id}
```

**New Structure:**
```
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins
GET    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins/{plugin_id}
PUT    /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins/{plugin_id}
DELETE /api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/plugins/{plugin_id}
```

**Implementation:**
- Added nested router in `backend/codex/api/routes/notebooks.py`
- New endpoints use `workspace_identifier` and `notebook_identifier` parameters (supporting both slug and ID)
- Uses helper functions `get_workspace_by_slug_or_id()` and `get_notebook_by_slug_or_id()`
- Registered in `main.py` under workspace/notebook hierarchy

### 2. Integration Routes

**Old Structure (Query Parameter Based):**
```
GET  /api/v1/plugins/integrations?workspace_id={id}
PUT  /api/v1/plugins/integrations/{id}/enable?workspace_id={id}
GET  /api/v1/plugins/integrations/{id}/config?workspace_id={id}
PUT  /api/v1/plugins/integrations/{id}/config?workspace_id={id}
POST /api/v1/plugins/integrations/{id}/execute?workspace_id={id}
```

**New Structure:**
```
GET  /api/v1/workspaces/{ws}/notebooks/{nb}/integrations
PUT  /api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/enable
GET  /api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/config
PUT  /api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/config
POST /api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/execute
```

**Implementation:**
- Created `nested_router` in `backend/codex/api/routes/integrations.py`
- New endpoints follow the same pattern as file/folder nested routes
- Integration execution and configuration now scoped to notebook context
- Registered in `main.py` under workspace/notebook hierarchy

### 3. Global Plugin Routes (Unchanged)

These routes remain as-is for system-level plugin management:
```
GET    /api/v1/plugins
POST   /api/v1/plugins/register
POST   /api/v1/plugins/register-batch
GET    /api/v1/plugins/{plugin_id}
DELETE /api/v1/plugins/{plugin_id}
GET    /api/v1/plugins/integrations/{id}          # Global integration info
POST   /api/v1/plugins/integrations/{id}/test     # Test connection (no workspace context)
GET    /api/v1/plugins/integrations/{id}/blocks   # Get integration blocks
```

## Files Modified

### Backend Routes
- `backend/codex/api/routes/notebooks.py` - Added nested plugin routes
- `backend/codex/api/routes/integrations.py` - Added nested integration routes, imported Notebook model
- `backend/codex/main.py` - Registered new nested routers

### Tests
- `backend/tests/test_plugin_api.py` - Updated to use new nested routes
- `backend/tests/test_integrations_api.py` - Updated to use new nested routes, added workspace_and_notebook fixture
- `backend/tests/test_notebooks_api.py` - Updated plugin tests to use new nested routes

## Test Results

All tests passing:
- `test_plugin_api.py`: 11/11 tests ✅
- `test_integrations_api.py`: 9/9 tests ✅
- `test_notebooks_api.py`: 20/20 tests ✅
- Full plugin/integration/notebook test suite: 82/82 tests ✅

## Backward Compatibility

The old flat routes (`/api/v1/notebooks/{id}/plugins`) are still functional but should be considered deprecated. They can be removed in a future version after:
1. Updating all frontend code to use new routes
2. Providing a deprecation notice period
3. Ensuring all consumers have migrated

## Migration Guide for Frontend

To migrate frontend code:

1. **Notebook Plugins:**
   ```javascript
   // Old
   GET /api/v1/notebooks/${notebookId}/plugins
   
   // New
   GET /api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/plugins
   ```

2. **Integration Configuration:**
   ```javascript
   // Old
   GET /api/v1/plugins/integrations/weather-api/config?workspace_id=${workspaceId}
   
   // New
   GET /api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/integrations/weather-api/config
   ```

3. **Integration Execution:**
   ```javascript
   // Old
   POST /api/v1/plugins/integrations/weather-api/execute?workspace_id=${workspaceId}
   
   // New
   POST /api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/integrations/weather-api/execute
   ```

## Benefits

1. **Consistent URL Structure**: All notebook-scoped operations now follow the same hierarchy pattern
2. **Better RESTful Design**: Resource relationships are clear from URL structure
3. **Improved Security**: Workspace and notebook access control is implicit in the URL
4. **Better Documentation**: API structure is self-documenting
5. **Slug Support**: New routes support both slugs and IDs for workspace/notebook identifiers

## Notes

- Integration configuration is still stored at the workspace level (PluginConfig model) but accessed via notebook routes
- This matches the existing pattern where integrations are workspace-scoped but files/folders/etc are accessed via notebook routes
- Artifact caching for integration execution continues to work as before

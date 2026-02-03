# Backend Routes Audit

## Summary

Based on the URL_STRUCTURE_REFACTOR.md document, the target URL pattern is:
- `/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/...`
- Nested resources under workspace/notebook hierarchy
- Slug-based routing with ID fallback for backward compatibility

---

## 1. USER ROUTES (`/api/v1/users/...`)
**File:** `backend/codex/api/routes/users.py`

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/users/token` | POST | ✅ test_users.py | Not in codex.ts (uses api.ts directly) | N/A (auth) | **KEEP** - Auth endpoint, no refactor needed |
| `/api/v1/users/me` | GET | ✅ test_users.py | Not in codex.ts | N/A (auth) | **KEEP** - User profile endpoint |
| `/api/v1/users/register` | POST | ✅ test_registration.py | Not in codex.ts | N/A (auth) | **KEEP** - Registration endpoint |
| `/api/v1/users/me/theme` | PATCH | ❌ | ❌ | N/A (auth) | **KEEP** - User-level theme setting |

---

## 2. WORKSPACE ROUTES (`/api/v1/workspaces/...`)
**File:** `backend/codex/api/routes/workspaces.py`

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/workspaces/` | GET | ✅ test_workspaces.py | ✅ workspaceService.list() | ✅ | **KEEP** |
| `/api/v1/workspaces/` | POST | ✅ test_workspaces.py | ✅ workspaceService.create() | ✅ | **KEEP** |
| `/api/v1/workspaces/{identifier}` | GET | ✅ test_slug_routes.py | ✅ workspaceService.get() | ✅ | **KEEP** - Supports slug + ID |
| `/api/v1/workspaces/{identifier}/theme` | PATCH | ✅ test_workspaces.py | ✅ workspaceService.updateTheme() | ✅ | **KEEP** |

---

## 3. NOTEBOOK ROUTES (`/api/v1/notebooks/...`)
**File:** `backend/codex/api/routes/notebooks.py`

### Legacy Flat Routes (Deprecated)

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/notebooks/` | POST | ❌ | ❌ | ❌ | **DELETE** - Returns 410, dead code |
| `/api/v1/notebooks/` | GET | ❌ | ❌ | ❌ | **DELETE** - Returns 410, dead code |
| `/api/v1/notebooks/{id}` | GET | ❌ | ❌ | ❌ | **DELETE** - Returns 410, dead code |
| `/api/v1/notebooks/{id}/indexing-status` | GET | ❌ | ❌ | ❌ | **DELETE** - Returns 410, dead code |
| `/api/v1/notebooks/{id}/plugins` | GET | ✅ test_plugin_api.py | ❌ | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/notebooks/{id}/plugins/{plugin_id}` | GET | ✅ test_plugin_api.py | ❌ | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/notebooks/{id}/plugins/{plugin_id}` | PUT | ✅ test_plugin_api.py | ❌ | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/notebooks/{id}/plugins/{plugin_id}` | DELETE | ✅ test_plugin_api.py | ❌ | ❌ | **UPDATE** - Move to nested route |

### New Nested Routes (Target Pattern) ✅

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/` | GET | ✅ test_slug_routes.py, test_notebooks_api.py | ✅ notebookService.list() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/` | POST | ✅ test_notebooks_api.py | ✅ notebookService.create() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}` | GET | ✅ test_slug_routes.py | ✅ notebookService.get() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/indexing-status` | GET | ✅ test_notebooks_api.py | ❌ | ✅ | **KEEP** |

### Missing Nested Routes (Not Yet Implemented)

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/plugins` | GET | Not implemented | **ADD** - Per URL_STRUCTURE_REFACTOR.md |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/plugins/{plugin_id}` | GET/PUT/DELETE | Not implemented | **ADD** - Per URL_STRUCTURE_REFACTOR.md |

---

## 4. FILE ROUTES (`/api/v1/files/...`)
**File:** `backend/codex/api/routes/files.py`

### Legacy Flat Routes (Query Param Based)

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/files/` | GET | ❌ | ❌ | ❌ | **DELETE** - Returns 410, dead code |
| `/api/v1/files/` | POST | ❌ | ❌ | ❌ | **DELETE** - Returns 410, dead code |
| `/api/v1/files/templates` | GET | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/from-template` | POST | ❌ | ✅ templateService.createFromTemplate() | ❌ | **UPDATE** - Add nested route, update FE |
| `/api/v1/files/by-path` | GET | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/by-path/text` | GET | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/by-path/content` | GET | ❌ | ❌ | ❌ | **UPDATE** - Add nested equivalent |
| `/api/v1/files/{id}` | GET | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/{id}/text` | GET | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/{id}/history` | GET | ❌ | ❌ | ❌ | **UPDATE** - Add nested equivalent |
| `/api/v1/files/{id}/history/{commit}` | GET | ❌ | ✅ fileService.getAtCommit() | ❌ | **UPDATE** - Add nested route, update FE |
| `/api/v1/files/{id}/content` | GET | ❌ | ❌ | ❌ | **UPDATE** - Add nested equivalent |
| `/api/v1/files/resolve-link` | POST | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/{id}` | PUT | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/upload` | POST | ❌ | ✅ fileService.upload() | ❌ | **UPDATE** - Add nested route, update FE |
| `/api/v1/files/{id}/move` | PATCH | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |
| `/api/v1/files/{id}` | DELETE | ❌ | ❌ | ❌ | **DELETE** - Has nested equivalent |

### New Nested Routes (Target Pattern) ✅

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/` | GET | ✅ test_files_api.py | ✅ fileService.list() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/` | POST | ✅ test_files_api.py, test_file_creation.py | ✅ fileService.create() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/templates` | GET | ❌ | ✅ templateService.list() | ✅ | **KEEP** - Add tests |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` | GET | ✅ test_files_api.py | ✅ fileService.get() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/text` | GET | ✅ test_files_api.py | ✅ fileService.getContent() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/by-path` | GET | ✅ test_files_api.py | ✅ fileService.getByPath() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/by-path/text` | GET | ✅ test_files_api.py | ✅ fileService.getContentByPath() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` | PUT | ✅ test_files_api.py | ✅ fileService.update() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/move` | PATCH | ✅ test_files_api.py | ✅ fileService.move() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` | DELETE | ✅ test_files_api.py | ✅ fileService.delete() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/resolve-link` | POST | ✅ test_files_api.py | ✅ fileService.resolveLink() | ✅ | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history` | GET | ✅ test_files_api.py | ✅ fileService.getHistory() | ✅ | **KEEP** |

### Missing Nested Routes (Not Yet Implemented)

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/upload` | POST | Not implemented | **ADD** - Update FE fileService.upload() |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/from-template` | POST | Not implemented | **ADD** - Update FE templateService.createFromTemplate() |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history/{commit}` | GET | Not implemented | **ADD** - Update FE fileService.getAtCommit() |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/content` | GET | Not implemented | **ADD** - Binary file serving |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/by-path/content` | GET | Not implemented | **ADD** - Binary file serving by path |

---

## 5. FOLDER ROUTES (`/api/v1/folders/...`)
**File:** `backend/codex/api/routes/folders.py`

### Legacy Routes (Query Param Based)

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/folders/{path}?notebook_id=&workspace_id=` | GET | ✅ test_folders_api.py | ✅ folderService.get() | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/folders/{path}?notebook_id=&workspace_id=` | PUT | ✅ test_folders_api.py | ✅ folderService.updateProperties() | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/folders/{path}?notebook_id=&workspace_id=` | DELETE | ✅ test_folders_api.py | ✅ folderService.delete() | ❌ | **UPDATE** - Move to nested route |

### Target Pattern (Not Implemented)

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` | GET | Not implemented | **ADD** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` | PUT | Not implemented | **ADD** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` | DELETE | Not implemented | **ADD** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/folders` | POST | Not implemented | **ADD** - Create folder |

---

## 6. SEARCH ROUTES (`/api/v1/search/...`)
**File:** `backend/codex/api/routes/search.py`

### Legacy Routes (Query Param Based)

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/search/?q=&workspace_id=` | GET | ✅ test_search_api.py | ✅ searchService.search() | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/search/tags?tags=&workspace_id=` | GET | ✅ test_search_api.py | ✅ searchService.searchByTags() | ❌ | **UPDATE** - Move to nested route |

### Target Pattern (Not Implemented)

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/search?query=` | GET | Not implemented | **ADD** - Workspace-wide search |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/search?query=` | GET | Not implemented | **ADD** - Notebook-specific search |

---

## 7. TASK ROUTES (`/api/v1/tasks/...`)
**File:** `backend/codex/api/routes/tasks.py`

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/tasks/?workspace_id=` | GET | ✅ test_tasks.py | ❌ | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/tasks/{id}` | GET | ✅ test_tasks.py | ❌ | N/A | **KEEP** - Task by ID is reasonable |
| `/api/v1/tasks/?workspace_id=&title=` | POST | ✅ test_tasks.py | ❌ | ❌ | **UPDATE** - Move to nested route |
| `/api/v1/tasks/{id}` | PUT | ✅ test_tasks.py | ❌ | N/A | **KEEP** - Task update by ID |

### Target Pattern

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/tasks/` | GET/POST | Not implemented | **ADD** - List/create tasks in workspace |

---

## 8. QUERY ROUTES (`/api/v1/query/...`)
**File:** `backend/codex/api/routes/query.py`

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/query/?workspace_id=` | POST | ✅ test_query_api.py | ❌ | ❌ | **UPDATE** - Move to nested route |

### Target Pattern

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/query/` | POST | Not implemented | **ADD** |

---

## 9. PLUGIN ROUTES (`/api/v1/plugins/...`)
**File:** `backend/codex/api/routes/plugins.py`

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/plugins/register` | POST | ❌ | ❌ | N/A (system) | **KEEP** - Global plugin registration |
| `/api/v1/plugins/register-batch` | POST | ❌ | ❌ | N/A (system) | **KEEP** - Batch registration |
| `/api/v1/plugins` | GET | ❌ | ❌ | N/A (system) | **KEEP** - List all plugins |
| `/api/v1/plugins/{plugin_id}` | GET | ❌ | ❌ | N/A (system) | **KEEP** - Get plugin details |
| `/api/v1/plugins/{plugin_id}` | DELETE | ❌ | ❌ | N/A (system) | **KEEP** - Unregister plugin |

---

## 10. INTEGRATION ROUTES (`/api/v1/plugins/integrations/...`)
**File:** `backend/codex/api/routes/integrations.py`

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| `/api/v1/plugins/integrations?workspace_id=` | GET | ✅ test_integrations_api.py | ❌ | ❌ | **UPDATE** - Move to workspace nested |
| `/api/v1/plugins/integrations/{id}` | GET | ✅ test_weather_integration.py | ❌ | N/A | **KEEP** - Global integration info |
| `/api/v1/plugins/integrations/{id}/enable?workspace_id=` | PUT | ✅ test_plugin_api.py | ❌ | ❌ | **UPDATE** - Move to workspace nested |
| `/api/v1/plugins/integrations/{id}/config?workspace_id=` | GET | ✅ test_integrations_api.py | ❌ | ❌ | **UPDATE** - Move to workspace nested |
| `/api/v1/plugins/integrations/{id}/config?workspace_id=` | PUT | ✅ test_integrations_api.py | ❌ | ❌ | **UPDATE** - Move to workspace nested |
| `/api/v1/plugins/integrations/{id}/test` | POST | ✅ test_integrations_api.py | ❌ | N/A | **KEEP** |
| `/api/v1/plugins/integrations/{id}/execute?workspace_id=` | POST | ✅ test_integrations_api.py | ❌ | ❌ | **UPDATE** - Move to workspace nested |
| `/api/v1/plugins/integrations/{id}/blocks` | GET | ✅ test_weather_integration.py | ❌ | N/A | **KEEP** |

---

## 11. MARKDOWN ROUTES
**File:** `backend/codex/api/routes/markdown.py`

| Route | Method | Tested | Frontend | Fits Pattern | Recommendation |
|-------|--------|--------|----------|--------------|----------------|
| (empty router) | - | N/A | N/A | N/A | **DELETE** - File is empty/unused |

---

## Summary Statistics

| Category | Keep | Delete | Update/Add |
|----------|------|--------|------------|
| User Routes | 4 | 0 | 0 |
| Workspace Routes | 4 | 0 | 0 |
| Notebook Routes (nested) | 4 | 0 | 4 (add plugin routes) |
| Notebook Routes (legacy) | 0 | 4 | 4 (move plugins) |
| File Routes (nested) | 12 | 0 | 5 (add missing) |
| File Routes (legacy) | 0 | 11 | 4 (add then delete) |
| Folder Routes | 0 | 0 | 4 (add nested) |
| Search Routes | 0 | 0 | 4 (add nested) |
| Task Routes | 2 | 0 | 2 (add nested) |
| Query Routes | 0 | 0 | 1 (add nested) |
| Plugin Routes | 5 | 0 | 0 |
| Integration Routes | 3 | 0 | 5 (add nested) |
| Markdown Routes | 0 | 1 | 0 |
| **TOTAL** | **34** | **16** | **33** |

---

## Priority Recommendations

### High Priority (Frontend Currently Uses Old Routes)
1. **File Upload** - Add `/api/v1/workspaces/{ws}/notebooks/{nb}/files/upload`
2. **File at Commit** - Add `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history/{commit}`
3. **Create from Template** - Add `/api/v1/workspaces/{ws}/notebooks/{nb}/files/from-template`
4. **Folder Routes** - Add all nested folder routes (frontend uses old pattern)

### Medium Priority (Tests Use Old Routes, No Frontend)
1. **Notebook Plugin Routes** - Move to nested pattern under workspace/notebook
2. **Integration Config Routes** - Move workspace_id from query param to path
3. **Search Routes** - Add nested routes under workspace/notebook

### Low Priority (No Frontend or Tests)
1. **Delete deprecated notebook routes** (410 responses)
2. **Delete deprecated file routes** (have nested equivalents)
3. **Delete empty markdown.py**

---

## Implementation Order

### Phase 1: High Priority Frontend-Impacting Routes
1. Add nested file upload route
2. Add nested from-template route
3. Add nested file content routes (binary serving)
4. Add nested file history at commit route
5. Update frontend to use new routes

### Phase 2: Folder Routes Migration
1. Add nested folder routes (GET, PUT, DELETE, POST)
2. Update frontend folderService
3. Mark old folder routes as deprecated

### Phase 3: Search & Query Routes Migration
1. Add nested search routes under workspace/notebook
2. Add nested query route under workspace
3. Update frontend services

### Phase 4: Plugin/Integration Routes Migration
1. Add nested notebook plugin routes
2. Add nested workspace integration config routes
3. Update tests to use new routes

### Phase 5: Cleanup
1. Delete deprecated routes returning 410
2. Delete unused file routes
3. Delete empty markdown.py
4. Update URL_STRUCTURE_REFACTOR.md status

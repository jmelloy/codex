# Backend Routes Audit

## Summary

**Status: MOSTLY COMPLETE** (as of 2026-02-04)

Based on the URL_STRUCTURE_REFACTOR.md document, the target URL pattern is:
- `/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/...`
- Nested resources under workspace/notebook hierarchy
- Slug-based routing with ID fallback for backward compatibility

**Major Completion Status:**
- ✅ Workspace routes - COMPLETE (slug + ID support)
- ✅ Notebook routes - COMPLETE (nested under workspace, slug + ID support)
- ✅ File routes - MOSTLY COMPLETE (missing: upload, from-template, history/{commit} nested routes)
- ✅ Folder routes - COMPLETE (nested)
- ✅ Search routes - COMPLETE (workspace and notebook level nested)
- ✅ Integration routes - COMPLETE (nested)
- ⏳ Query routes - NOT NESTED (still uses query param)
- ⏳ Task routes - NOT NESTED (still uses query param)

**Frontend Migration Status:**
- ✅ Files: Using nested routes EXCEPT upload, from-template
- ✅ Folders: Using nested routes
- ✅ Search: Using nested routes
- ⏳ Query: Still using old `/api/v1/query/?workspace_id=`
- ⏳ Upload/Template: Still using old `/api/v1/files/upload`, `/api/v1/files/from-template`

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

### Legacy Flat Routes (Still Exist But Have Nested Equivalents)

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/notebooks/{id}/plugins` | GET | ✅ test_plugin_api.py (uses nested) | ❌ | ⚠️ OLD ROUTE EXISTS | **DEPRECATE** - Nested route exists and is used |
| `/api/v1/notebooks/{id}/plugins/{plugin_id}` | GET | ✅ test_plugin_api.py (uses nested) | ❌ | ⚠️ OLD ROUTE EXISTS | **DEPRECATE** - Nested route exists and is used |
| `/api/v1/notebooks/{id}/plugins/{plugin_id}` | PUT | ✅ test_plugin_api.py (uses nested) | ❌ | ⚠️ OLD ROUTE EXISTS | **DEPRECATE** - Nested route exists and is used |
| `/api/v1/notebooks/{id}/plugins/{plugin_id}` | DELETE | ✅ test_plugin_api.py (uses nested) | ❌ | ⚠️ OLD ROUTE EXISTS | **DEPRECATE** - Nested route exists and is used |

### New Nested Routes (Target Pattern) ✅ IMPLEMENTED

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/` | GET | ✅ test_slug_routes.py, test_notebooks_api.py | ✅ notebookService.list() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/` | POST | ✅ test_notebooks_api.py | ✅ notebookService.create() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}` | GET | ✅ test_slug_routes.py | ✅ notebookService.get() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/indexing-status` | GET | ✅ test_notebooks_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/plugins` | GET | ✅ test_plugin_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/plugins/{plugin_id}` | GET | ✅ test_plugin_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/plugins/{plugin_id}` | PUT | ✅ test_plugin_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/plugins/{plugin_id}` | DELETE | ✅ test_plugin_api.py | ❌ | ✅ DONE | **KEEP** |

---

## 4. FILE ROUTES (`/api/v1/files/...`)
**File:** `backend/codex/api/routes/files.py`

### Legacy Flat Routes (Still Exist, Used by Frontend)

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/files/from-template` | POST | ✅ test_template_api.py | ✅ templateService.createFromTemplate() | ⚠️ FRONTEND USES | **MIGRATE** - Add nested route, update FE |
| `/api/v1/files/{id}/history/{commit}` | GET | ❌ | ✅ fileService.getAtCommit() | ⚠️ FRONTEND USES | **MIGRATE** - Add nested route, update FE |
| `/api/v1/files/upload` | POST | ❌ | ✅ fileService.upload() | ⚠️ FRONTEND USES | **MIGRATE** - Add nested route, update FE |

### Legacy Flat Routes (No Longer Used)

These routes may still exist in the code but are not used by frontend or tests:

| Route | Method | Status | Recommendation |
|-------|--------|--------|----------------|
| `/api/v1/files/` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/` | POST | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/templates` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/by-path` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/by-path/text` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/by-path/content` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/{id}` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/{id}/text` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/{id}/history` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/{id}/content` | GET | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/resolve-link` | POST | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/{id}` | PUT | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/{id}/move` | PATCH | ❌ | **CAN DELETE** - Has nested equivalent |
| `/api/v1/files/{id}` | DELETE | ❌ | **CAN DELETE** - Has nested equivalent |

### New Nested Routes (Target Pattern) ✅ IMPLEMENTED

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/` | GET | ✅ test_files_api.py | ✅ fileService.list() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/` | POST | ✅ test_files_api.py, test_file_creation.py | ✅ fileService.create() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/templates` | GET | ❌ | ✅ templateService.list() | ✅ DONE | **KEEP** - Add tests |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` | GET | ✅ test_files_api.py | ✅ fileService.get() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/text` | GET | ✅ test_files_api.py | ✅ fileService.getContent() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/content` | GET | ✅ test_files_api.py | ✅ fileService.getContentUrl() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/path/{path}/text` | GET | ✅ test_files_api.py | ✅ fileService.getContentByPath() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/path/{path}/content` | GET | ✅ test_files_api.py | ✅ fileService.getContentUrlByPath() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/path/{path}` | GET | ✅ test_files_api.py | ✅ fileService.getByPath() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` | PUT | ✅ test_files_api.py | ✅ fileService.update() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/move` | PATCH | ✅ test_files_api.py | ✅ fileService.move() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}` | DELETE | ✅ test_files_api.py | ✅ fileService.delete() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/resolve-link` | POST | ✅ test_files_api.py | ✅ fileService.resolveLink() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history` | GET | ✅ test_files_api.py | ✅ fileService.getHistory() | ✅ DONE | **KEEP** |

### Missing Nested Routes (Need Implementation)

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/upload` | POST | Frontend uses old route | **HIGH PRIORITY** - Update FE fileService.upload() |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/from-template` | POST | Frontend uses old route | **HIGH PRIORITY** - Update FE templateService.createFromTemplate() |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history/{commit}` | GET | Frontend uses old route | **HIGH PRIORITY** - Update FE fileService.getAtCommit() |

---

## 5. FOLDER ROUTES (`/api/v1/folders/...`)
**File:** `backend/codex/api/routes/folders.py`

### New Nested Routes (Target Pattern) ✅ IMPLEMENTED

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` | GET | ✅ test_folders_api.py | ✅ folderService.get() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` | PUT | ✅ test_folders_api.py | ✅ folderService.updateProperties() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/folders/{path}` | DELETE | ✅ test_folders_api.py | ✅ folderService.delete() | ✅ DONE | **KEEP** |

---

## 6. SEARCH ROUTES (`/api/v1/search/...`)
**File:** `backend/codex/api/routes/search.py`

### New Nested Routes (Target Pattern) ✅ IMPLEMENTED

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/workspaces/{ws}/search/?q=` | GET | ✅ test_search_api.py | ✅ searchService.search() | ✅ DONE | **KEEP** - Workspace-wide search |
| `/api/v1/workspaces/{ws}/search/tags?tags=` | GET | ✅ test_search_api.py | ✅ searchService.searchByTags() | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/search/?q=` | GET | ✅ test_search_api.py | ✅ searchService.searchInNotebook() | ✅ DONE | **KEEP** - Notebook-specific search |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/search/tags?tags=` | GET | ✅ test_search_api.py | ✅ searchService.searchByTagsInNotebook() | ✅ DONE | **KEEP** |

---

## 7. TASK ROUTES (`/api/v1/tasks/...`)
**File:** `backend/codex/api/routes/tasks.py`

### Current Routes (Still Using Query Params)

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/tasks/?workspace_id=` | GET | ✅ test_tasks.py | ❌ | ⚠️ NOT NESTED | **LOW PRIORITY** - Move to nested route |
| `/api/v1/tasks/{id}` | GET | ✅ test_tasks.py | ❌ | ✅ OK | **KEEP** - Task by ID is reasonable |
| `/api/v1/tasks/?workspace_id=&title=` | POST | ✅ test_tasks.py | ❌ | ⚠️ NOT NESTED | **LOW PRIORITY** - Move to nested route |
| `/api/v1/tasks/{id}` | PUT | ✅ test_tasks.py | ❌ | ✅ OK | **KEEP** - Task update by ID |

### Target Pattern (Not Implemented)

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/tasks/` | GET/POST | Not implemented | **LOW PRIORITY** - No frontend usage, tasks not heavily used |

---

## 8. QUERY ROUTES (`/api/v1/query/...`)
**File:** `backend/codex/api/routes/query.py`

### Current Routes (Still Using Query Params)

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/query/?workspace_id=` | POST | ✅ test_query_api.py | ✅ queryService.execute() | ⚠️ FRONTEND USES | **MEDIUM PRIORITY** - Move to nested route, update FE |

### Target Pattern (Not Implemented)

| Route | Method | Notes | Recommendation |
|-------|--------|-------|----------------|
| `/api/v1/workspaces/{ws}/query/` | POST | Not implemented | **MEDIUM PRIORITY** - Frontend actively uses query service |

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

### Global Integration Routes ✅ (No Changes Needed)

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/plugins/integrations/{id}` | GET | ✅ test_weather_integration.py | ❌ | ✅ OK | **KEEP** - Global integration info |
| `/api/v1/plugins/integrations/{id}/test` | POST | ✅ test_integrations_api.py | ❌ | ✅ OK | **KEEP** - Test connection (no workspace context) |
| `/api/v1/plugins/integrations/{id}/blocks` | GET | ✅ test_weather_integration.py | ❌ | ✅ OK | **KEEP** - Get integration blocks |

### New Nested Routes (Target Pattern) ✅ IMPLEMENTED

| Route | Method | Tested | Frontend | Status | Recommendation |
|-------|--------|--------|----------|--------|----------------|
| `/api/v1/workspaces/{ws}/notebooks/{nb}/integrations` | GET | ✅ test_integrations_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/enable` | PUT | ✅ test_plugin_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/config` | GET | ✅ test_integrations_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/config` | PUT | ✅ test_integrations_api.py | ❌ | ✅ DONE | **KEEP** |
| `/api/v1/workspaces/{ws}/notebooks/{nb}/integrations/{id}/execute` | POST | ✅ test_integrations_api.py | ❌ | ✅ DONE | **KEEP** |

### Legacy Routes (Still Exist, Not Used by Frontend)

These routes still exist but tests now use nested routes:

| Route | Method | Status | Recommendation |
|-------|--------|--------|----------------|
| `/api/v1/plugins/integrations?workspace_id=` | GET | ⚠️ OLD | **CAN DEPRECATE** - Has nested equivalent |
| `/api/v1/plugins/integrations/{id}/enable?workspace_id=` | PUT | ⚠️ OLD | **CAN DEPRECATE** - Has nested equivalent |
| `/api/v1/plugins/integrations/{id}/config?workspace_id=` | GET | ⚠️ OLD | **CAN DEPRECATE** - Has nested equivalent |
| `/api/v1/plugins/integrations/{id}/config?workspace_id=` | PUT | ⚠️ OLD | **CAN DEPRECATE** - Has nested equivalent |
| `/api/v1/plugins/integrations/{id}/execute?workspace_id=` | POST | ⚠️ OLD | **CAN DEPRECATE** - Has nested equivalent |

---

## 11. MARKDOWN ROUTES
**File:** `backend/codex/api/routes/markdown.py`

**Status:** File exists but is empty/unused - no routes defined.

| Status | Recommendation |
|--------|----------------|
| Empty router | **CAN DELETE** - No routes, not used |

---

## Summary Statistics

**Current Implementation Status (2026-02-04):**

| Category | Implemented | Still Old Pattern | Missing Nested | Can Delete |
|----------|-------------|-------------------|----------------|------------|
| User Routes | 4 ✅ | 0 | 0 | 0 |
| Workspace Routes | 4 ✅ | 0 | 0 | 0 |
| Notebook Routes | 8 ✅ | 4 old exist | 0 | 0 |
| File Routes | 14 ✅ | 3 old (FE uses) | 3 | 11 |
| Folder Routes | 3 ✅ | 0 | 0 | 0 |
| Search Routes | 4 ✅ | 0 | 0 | 0 |
| Task Routes | 2 ✅ (by ID) | 2 | 1 | 0 |
| Query Routes | 0 | 1 (FE uses) | 1 | 0 |
| Plugin Routes | 5 ✅ | 0 | 0 | 0 |
| Integration Routes | 8 ✅ | 5 old exist | 0 | 0 |
| **TOTAL** | **52 ✅** | **15 old** | **5 missing** | **11 deletable** |

**Progress:**
- ✅ **Major Routes Complete:** Workspaces, Notebooks, Files (mostly), Folders, Search, Integrations
- ⚠️ **Minor Gaps:** 3 file routes (upload, from-template, history/{commit})
- ⚠️ **Low Priority:** Query and Tasks routes (low frontend usage)

---

## Priority Recommendations

### High Priority (Frontend Uses Old Routes) 🔴

1. **File Upload** - Add `/api/v1/workspaces/{ws}/notebooks/{nb}/files/upload`
   - Frontend: `fileService.upload()` uses `/api/v1/files/upload`
   - Old route exists and works, needs nested equivalent

2. **File from Template** - Add `/api/v1/workspaces/{ws}/notebooks/{nb}/files/from-template`
   - Frontend: `templateService.createFromTemplate()` uses `/api/v1/files/from-template`
   - Old route exists and works, needs nested equivalent
   - **Note:** 1 test failure in `test_template_api.py::test_create_from_template_with_custom_filename`

3. **File at Commit** - Add `/api/v1/workspaces/{ws}/notebooks/{nb}/files/{id}/history/{commit}`
   - Frontend: `fileService.getAtCommit()` uses `/api/v1/files/{id}/history/{commit}`
   - Old route exists and works, needs nested equivalent

### Medium Priority (No Frontend, Incomplete Pattern) 🟡

4. **Query Routes** - Add `/api/v1/workspaces/{ws}/query/`
   - Frontend: `queryService.execute()` uses `/api/v1/query/?workspace_id=`
   - Used by dynamic views feature

### Low Priority (No Frontend Usage, Nice to Have) 🟢

5. **Task Routes** - Add `/api/v1/workspaces/{ws}/tasks/`
   - Currently uses `/api/v1/tasks/?workspace_id=`
   - No frontend usage, internal API

### Cleanup Tasks (When Safe) 🧹

6. **Delete Unused Old Routes** - After all nested routes are implemented and frontend migrated:
   - Old flat file routes (11 routes)
   - Old notebook plugin routes (4 routes)
   - Old integration routes (5 routes)
   - Empty markdown.py router

---

## Implementation Order

### ✅ Phase 1: Core URL Structure - COMPLETE
- [x] Add slug fields to database models
- [x] Create migrations for slug support
- [x] Implement workspace slug routes
- [x] Implement nested notebook routes under workspace
- [x] Test slug generation and collision handling

### ✅ Phase 2: Primary Resource Routes - COMPLETE
- [x] Implement nested file routes (list, get, create, update, delete)
- [x] Implement nested folder routes (get, update, delete)
- [x] Implement nested search routes (workspace and notebook level)
- [x] Update file tests to use nested routes
- [x] Update folder tests to use nested routes
- [x] Update search tests to use nested routes

### ✅ Phase 3: Plugin/Integration Routes - COMPLETE
- [x] Add nested notebook plugin routes
- [x] Add nested workspace/notebook integration routes
- [x] Update plugin tests to use new routes
- [x] Update integration tests to use new routes

### 🔄 Phase 4: Remaining File Routes - IN PROGRESS
- [ ] Add nested file upload route
- [ ] Add nested from-template route
- [ ] Add nested file history at commit route
- [ ] Update frontend fileService to use new upload route
- [ ] Update frontend templateService to use new from-template route
- [ ] Fix test failure in test_template_api.py

### ⏳ Phase 5: Query & Task Routes - NOT STARTED
- [ ] Add nested query route under workspace
- [ ] Add nested task routes under workspace
- [ ] Update frontend queryService (if needed)
- [ ] Update tests to use new routes

### ⏳ Phase 6: Cleanup - NOT STARTED
- [ ] Mark old routes as deprecated with @deprecated decorator
- [ ] Add deprecation warnings to old route responses
- [ ] Remove unused flat routes after frontend migration
- [ ] Delete empty markdown.py
- [ ] Update URL_STRUCTURE_REFACTOR.md status to COMPLETE

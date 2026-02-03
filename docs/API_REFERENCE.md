# Codex API Reference

## Overview

This document provides a comprehensive reference of all backend API endpoints in the Codex system, including test coverage and frontend usage information.

**Base URL**: `http://localhost:8000` (configurable via `VITE_API_BASE_URL`)

**Authentication**: Most endpoints require JWT Bearer token authentication (obtained via `/api/token`)

---

## Table of Contents

1. [Users & Authentication](#users--authentication)
2. [Workspaces](#workspaces)
3. [Notebooks](#notebooks)
4. [Files](#files)
5. [Folders](#folders)
6. [Search](#search)
7. [Tasks](#tasks)
8. [Markdown](#markdown)
9. [Query](#query)
10. [Integrations](#integrations)
11. [Plugins](#plugins)
12. [Test Coverage Summary](#test-coverage-summary)

---

## Users & Authentication

### POST `/api/token`
**Description**: Login endpoint to obtain access token  
**Authentication**: None (public)  
**Request Body**: Form-urlencoded `username`, `password`  
**Response**: `{ access_token, refresh_token, token_type }`

**Tested**: ✅ `test_users.py`  
**Frontend Usage**: ✅ `auth.ts::login()`

---

### GET `/api/users/me`
**Description**: Get current authenticated user information  
**Authentication**: Required  
**Response**: User object with id, username, email, theme, etc.

**Tested**: ✅ `test_users.py`  
**Frontend Usage**: ✅ `auth.ts::getCurrentUser()`

---

### POST `/api/register`
**Description**: Register a new user account  
**Authentication**: None (public)  
**Request Body**: `{ username, email, password }`  
**Response**: User object

**Tested**: ✅ `test_users.py`  
**Frontend Usage**: ✅ `auth.ts::register()`

---

### PATCH `/api/users/me/theme`
**Description**: Update theme setting for current user  
**Authentication**: Required  
**Request Body**: `{ theme: string }`  
**Response**: Updated user object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `auth.ts::updateTheme()`

---

## Workspaces

### GET `/api/v1/workspaces/`
**Description**: List all workspaces for current user  
**Authentication**: Required  
**Response**: Array of workspace objects

**Tested**: ✅ `test_workspaces.py`  
**Frontend Usage**: ✅ `codex.ts::workspaceService.list()`

---

### GET `/api/v1/workspaces/{workspace_id}`
**Description**: Get a specific workspace by ID  
**Authentication**: Required  
**Path Parameters**: `workspace_id` (string)  
**Response**: Workspace object

**Tested**: ✅ `test_workspaces.py`  
**Frontend Usage**: ✅ `codex.ts::workspaceService.get()`

---

### POST `/api/v1/workspaces/`
**Description**: Create a new workspace  
**Authentication**: Required  
**Request Body**: `{ name, path, description? }`  
**Response**: Created workspace object

**Tested**: ✅ `test_workspaces.py`, `test_plugin_api.py`, `test_integrations_api.py`  
**Frontend Usage**: ✅ `codex.ts::workspaceService.create()`

---

### PATCH `/api/v1/workspaces/{workspace_id}/theme`
**Description**: Update workspace theme  
**Authentication**: Required  
**Path Parameters**: `workspace_id` (string)  
**Request Body**: `{ theme: string }`  
**Response**: Updated workspace object

**Tested**: ✅ `test_workspaces.py`  
**Frontend Usage**: ✅ `codex.ts::workspaceService.updateTheme()`

---

## Notebooks

### GET `/api/v1/notebooks/`
**Description**: List notebooks in a workspace  
**Authentication**: Required  
**Query Parameters**: `workspace_id` (required)  
**Response**: Array of notebook objects

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::notebookService.list()`

---

### GET `/api/v1/notebooks/{notebook_id}`
**Description**: Get a specific notebook  
**Authentication**: Required  
**Path Parameters**: `notebook_id` (string)  
**Query Parameters**: `workspace_id` (required)  
**Response**: Notebook object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::notebookService.get()`

---

### GET `/api/v1/notebooks/{notebook_id}/indexing-status`
**Description**: Get indexing status for notebook  
**Authentication**: Required  
**Path Parameters**: `notebook_id` (string)  
**Response**: `{ is_indexing: boolean, indexed_files: number, total_files: number }`

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### POST `/api/v1/notebooks/`
**Description**: Create a new notebook  
**Authentication**: Required  
**Request Body**: `{ workspace_id, name, path, description? }`  
**Response**: Created notebook object

**Tested**: ✅ `test_plugin_api.py`  
**Frontend Usage**: ✅ `codex.ts::notebookService.create()`

---

### GET `/api/v1/notebooks/{notebook_id}/plugins`
**Description**: List plugin configurations for notebook  
**Authentication**: Required  
**Path Parameters**: `notebook_id` (string)  
**Query Parameters**: `workspace_id` (required)  
**Response**: Array of plugin config objects

**Tested**: ✅ `test_plugin_api.py`  
**Frontend Usage**: ❌ Not currently used

---

### GET `/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}`
**Description**: Get specific plugin configuration for notebook  
**Authentication**: Required  
**Path Parameters**: `notebook_id`, `plugin_id` (strings)  
**Query Parameters**: `workspace_id` (required)  
**Response**: Plugin config object

**Tested**: ✅ `test_plugin_api.py`  
**Frontend Usage**: ❌ Not currently used

---

### PUT `/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}`
**Description**: Update plugin configuration for notebook  
**Authentication**: Required  
**Path Parameters**: `notebook_id`, `plugin_id` (strings)  
**Request Body**: `{ config: object }`  
**Response**: Updated plugin config object

**Tested**: ✅ `test_plugin_api.py`  
**Frontend Usage**: ❌ Not currently used

---

### DELETE `/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}`
**Description**: Delete plugin configuration for notebook  
**Authentication**: Required  
**Path Parameters**: `notebook_id`, `plugin_id` (strings)  
**Query Parameters**: `workspace_id` (required)  
**Response**: 204 No Content

**Tested**: ✅ `test_plugin_api.py`  
**Frontend Usage**: ❌ Not currently used

---

## Files

### GET `/api/v1/files/templates`
**Description**: Get available file templates  
**Authentication**: Required  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: Array of template objects

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::templateService.list()`

---

### POST `/api/v1/files/from-template`
**Description**: Create file from template  
**Authentication**: Required  
**Request Body**: `{ notebook_id, workspace_id, template_id, path, ... }`  
**Response**: Created file metadata object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::templateService.createFromTemplate()`

---

### GET `/api/v1/files/`
**Description**: List files in notebook  
**Authentication**: Required  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: Array of file metadata objects

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.list()`

---

### GET `/api/v1/files/{file_id}`
**Description**: Get file metadata by ID  
**Authentication**: Required  
**Path Parameters**: `file_id` (string)  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: File metadata object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.get()`

---

### GET `/api/v1/files/{file_id}/text`
**Description**: Get file text content  
**Authentication**: Required  
**Path Parameters**: `file_id` (string)  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: `{ content: string }`

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.getContent()`

---

### GET `/api/v1/files/{file_id}/history`
**Description**: Get file commit history  
**Authentication**: Required  
**Path Parameters**: `file_id` (string)  
**Query Parameters**: `notebook_id`, `workspace_id`, `max_count?` (optional)  
**Response**: Array of commit objects

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.getHistory()`

---

### GET `/api/v1/files/{file_id}/history/{commit_hash}`
**Description**: Get file at specific commit  
**Authentication**: Required  
**Path Parameters**: `file_id`, `commit_hash` (strings)  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: File content at specified commit

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.getAtCommit()`

---

### GET `/api/v1/files/by-path`
**Description**: Get file metadata by path  
**Authentication**: Required  
**Query Parameters**: `path`, `notebook_id`, `workspace_id` (required)  
**Response**: File metadata object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.getByPath()`

---

### GET `/api/v1/files/by-path/text`
**Description**: Get file text content by path  
**Authentication**: Required  
**Query Parameters**: `path`, `notebook_id`, `workspace_id` (required)  
**Response**: `{ content: string }`

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.getContentByPath()`

---

### GET `/api/v1/files/by-path/content`
**Description**: Get raw file content by path (for images, etc.)  
**Authentication**: Required  
**Query Parameters**: `path`, `notebook_id`, `workspace_id` (required)  
**Response**: Raw file bytes

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.getContentUrlByPath()` (URL builder)

---

### GET `/api/v1/files/{file_id}/content`
**Description**: Get raw file content by ID  
**Authentication**: Required  
**Path Parameters**: `file_id` (string)  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: Raw file bytes

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.getContentUrl()` (URL builder)

---

### POST `/api/v1/files/resolve-link`
**Description**: Resolve wiki-style file links  
**Authentication**: Required  
**Request Body**: `{ notebook_id, workspace_id, link, current_file_path }`  
**Response**: `{ path: string, exists: boolean }`

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.resolveLink()`

---

### POST `/api/v1/files/`
**Description**: Create new file  
**Authentication**: Required  
**Request Body**: `{ notebook_id, workspace_id, path, content, metadata? }`  
**Response**: Created file metadata object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.create()`

---

### PUT `/api/v1/files/{file_id}`
**Description**: Update file content and metadata  
**Authentication**: Required  
**Path Parameters**: `file_id` (string)  
**Request Body**: `{ notebook_id, workspace_id, content?, metadata? }`  
**Response**: Updated file metadata object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.update()`

---

### POST `/api/v1/files/upload`
**Description**: Upload file (multipart form data)  
**Authentication**: Required  
**Request Body**: Multipart form with `file`, `notebook_id`, `workspace_id`, `path`  
**Response**: Created file metadata object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.upload()`

---

### PATCH `/api/v1/files/{file_id}/move`
**Description**: Move or rename file  
**Authentication**: Required  
**Path Parameters**: `file_id` (string)  
**Request Body**: `{ notebook_id, workspace_id, new_path }`  
**Response**: Updated file metadata object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.move()`

---

### DELETE `/api/v1/files/{file_id}`
**Description**: Delete file  
**Authentication**: Required  
**Path Parameters**: `file_id` (string)  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: 204 No Content

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::fileService.delete()`

---

## Folders

### GET `/api/v1/folders/{folder_path:path}`
**Description**: Get folder metadata and list files with pagination  
**Authentication**: Required  
**Path Parameters**: `folder_path` (path string)  
**Query Parameters**: `notebook_id`, `workspace_id`, `skip?`, `limit?` (optional)  
**Response**: `{ properties, files: [...] }`

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::folderService.get()`

---

### PUT `/api/v1/folders/{folder_path:path}`
**Description**: Update folder properties  
**Authentication**: Required  
**Path Parameters**: `folder_path` (path string)  
**Request Body**: `{ notebook_id, workspace_id, properties }`  
**Response**: Updated folder properties

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::folderService.updateProperties()`

---

### DELETE `/api/v1/folders/{folder_path:path}`
**Description**: Delete folder and all contents  
**Authentication**: Required  
**Path Parameters**: `folder_path` (path string)  
**Query Parameters**: `notebook_id`, `workspace_id` (required)  
**Response**: 204 No Content

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::folderService.delete()`

---

## Search

### GET `/api/v1/search/`
**Description**: Full-text search across files and content  
**Authentication**: Required  
**Query Parameters**: `q` (query string), `workspace_id` (required)  
**Response**: Array of matching file objects with highlights

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::searchService.search()`

---

### GET `/api/v1/search/tags`
**Description**: Search files by tags  
**Authentication**: Required  
**Query Parameters**: `tags` (comma-separated), `workspace_id` (required)  
**Response**: Array of matching file objects

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `codex.ts::searchService.searchByTags()`

---

## Tasks

### GET `/api/v1/tasks/`
**Description**: List tasks for workspace  
**Authentication**: Required  
**Query Parameters**: `workspace_id` (required)  
**Response**: Array of task objects

**Tested**: ✅ `test_tasks.py`  
**Frontend Usage**: ❌ Not currently used

---

### GET `/api/v1/tasks/{task_id}`
**Description**: Get specific task by ID  
**Authentication**: Required  
**Path Parameters**: `task_id` (string)  
**Response**: Task object

**Tested**: ✅ `test_tasks.py`  
**Frontend Usage**: ❌ Not currently used

---

### POST `/api/v1/tasks/`
**Description**: Create new task  
**Authentication**: Required  
**Request Body**: `{ workspace_id, title, description?, status?, assigned_to? }`  
**Response**: Created task object

**Tested**: ✅ `test_tasks.py`  
**Frontend Usage**: ❌ Not currently used

---

### PUT `/api/v1/tasks/{task_id}`
**Description**: Update task  
**Authentication**: Required  
**Path Parameters**: `task_id` (string)  
**Request Body**: `{ status?, assigned_to?, ... }`  
**Response**: Updated task object

**Tested**: ✅ `test_tasks.py`  
**Frontend Usage**: ❌ Not currently used

---

## Markdown

### POST `/api/v1/markdown/render`
**Description**: Render markdown to HTML and detect custom blocks  
**Authentication**: Required  
**Request Body**: `{ content, workspace_id?, notebook_id? }`  
**Response**: `{ html, custom_blocks: [...] }`

**Tested**: ✅ `test_markdown_api.py`  
**Frontend Usage**: ❌ Not currently used

---

### GET `/api/v1/markdown/{workspace_id}/files`
**Description**: List markdown files in workspace  
**Authentication**: Required  
**Path Parameters**: `workspace_id` (string)  
**Response**: Array of markdown file paths

**Tested**: ✅ `test_markdown_api.py`  
**Frontend Usage**: ❌ Not currently used

---

### GET `/api/v1/markdown/{workspace_id}/file`
**Description**: Get markdown file content with frontmatter  
**Authentication**: Required  
**Path Parameters**: `workspace_id` (string)  
**Query Parameters**: `file_path` (required)  
**Response**: `{ content, frontmatter: {...} }`

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### POST `/api/v1/markdown/{workspace_id}/file`
**Description**: Create markdown file  
**Authentication**: Required  
**Path Parameters**: `workspace_id` (string)  
**Request Body**: `{ file_path, content, frontmatter? }`  
**Response**: Created file object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### PUT `/api/v1/markdown/{workspace_id}/file`
**Description**: Update markdown file  
**Authentication**: Required  
**Path Parameters**: `workspace_id` (string)  
**Request Body**: `{ file_path, content?, frontmatter? }`  
**Response**: Updated file object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### DELETE `/api/v1/markdown/{workspace_id}/file`
**Description**: Delete markdown file  
**Authentication**: Required  
**Path Parameters**: `workspace_id` (string)  
**Query Parameters**: `file_path` (required)  
**Response**: 204 No Content

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

## Query

### POST `/api/v1/query/`
**Description**: Advanced query API for dynamic views with filtering, sorting, and grouping  
**Authentication**: Required  
**Query Parameters**: `workspace_id` (required)  
**Request Body**: `{ filters?, sort?, group?, limit?, offset? }`  
**Response**: Array of file objects matching query

**Tested**: ✅ `test_query_api.py` (partial coverage)  
**Frontend Usage**: ✅ `queryService.ts::execute()`, `queryService.ts::queryFiles()`, `queryService.ts::queryWithGroups()`

---

## Integrations

### GET `/api/v1/integrations`
**Description**: List all integration plugins  
**Authentication**: Required  
**Query Parameters**: `workspace_id?` (optional)  
**Response**: Array of integration plugin objects

**Tested**: ✅ `test_integrations_api.py`, `test_plugin_api.py`  
**Frontend Usage**: ✅ `integration.ts::listIntegrations()`

---

### GET `/api/v1/integrations/{integration_id}`
**Description**: Get integration details  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Response**: Integration plugin object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ✅ `integration.ts::getIntegration()`

---

### PUT `/api/v1/integrations/{integration_id}/enable`
**Description**: Enable or disable integration for workspace  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Request Body**: `{ workspace_id, enabled: boolean }`  
**Response**: Updated integration status

**Tested**: ✅ `test_plugin_api.py`  
**Frontend Usage**: ❌ Not currently used

---

### GET `/api/v1/integrations/{integration_id}/config`
**Description**: Get integration configuration for workspace  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Query Parameters**: `workspace_id` (required)  
**Response**: Integration config object

**Tested**: ✅ `test_integrations_api.py`  
**Frontend Usage**: ✅ `integration.ts::getIntegrationConfig()`

---

### PUT `/api/v1/integrations/{integration_id}/config`
**Description**: Update integration configuration for workspace  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Request Body**: `{ workspace_id, config: {...} }`  
**Response**: Updated integration config

**Tested**: ✅ `test_integrations_api.py`  
**Frontend Usage**: ✅ `integration.ts::updateIntegrationConfig()`

---

### POST `/api/v1/integrations/{integration_id}/test`
**Description**: Test integration connection  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Request Body**: `{ config: {...} }`  
**Response**: `{ success: boolean, message: string }`

**Tested**: ✅ `test_integrations_api.py`  
**Frontend Usage**: ✅ `integration.ts::testIntegrationConnection()`

---

### POST `/api/v1/integrations/{integration_id}/execute`
**Description**: Execute integration-specific endpoint  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Query Parameters**: `workspace_id` (required)  
**Request Body**: Integration-specific parameters  
**Response**: Integration-specific response

**Tested**: ✅ `test_integrations_api.py`  
**Frontend Usage**: ✅ `integration.ts::executeIntegrationEndpoint()`

---

### GET `/api/v1/integrations/{integration_id}/blocks`
**Description**: Get available block types for integration  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Response**: Array of block type definitions

**Tested**: ✅ `test_integrations_api.py`  
**Frontend Usage**: ✅ `integration.ts::getIntegrationBlocks()`

---

### POST `/api/v1/integrations/{integration_id}/render`
**Description**: Render integration block with caching  
**Authentication**: Required  
**Path Parameters**: `integration_id` (string)  
**Query Parameters**: `workspace_id` (required)  
**Request Body**: `{ block_type, parameters: {...} }`  
**Response**: `{ html: string, cache_key?: string }`

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

## Plugins

### POST `/api/v1/plugins/register`
**Description**: Register a plugin from frontend  
**Authentication**: Required  
**Request Body**: `{ plugin_id, name, version, type, manifest: {...} }`  
**Response**: Registered plugin object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### POST `/api/v1/plugins/register-batch`
**Description**: Register multiple plugins at once  
**Authentication**: Required  
**Request Body**: `{ plugins: [...] }`  
**Response**: Array of registered plugin objects

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### GET `/api/v1/plugins`
**Description**: List all registered plugins  
**Authentication**: Required  
**Query Parameters**: `plugin_type?` (optional filter)  
**Response**: Array of plugin objects

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### GET `/api/v1/plugins/{plugin_id}`
**Description**: Get specific plugin details  
**Authentication**: Required  
**Path Parameters**: `plugin_id` (string)  
**Response**: Plugin object

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

### DELETE `/api/v1/plugins/{plugin_id}`
**Description**: Unregister a plugin  
**Authentication**: Required  
**Path Parameters**: `plugin_id` (string)  
**Response**: 204 No Content

**Tested**: ❌ Not specifically tested  
**Frontend Usage**: ❌ Not currently used

---

## Test Coverage Summary

### Overall Statistics
- **Total API Endpoints**: 65+
- **Endpoints with Tests**: ~20 (31%)
- **Endpoints without Tests**: ~45 (69%)

### Coverage by Category

| Category | Total Endpoints | Tested | Coverage % |
|----------|----------------|--------|-----------|
| Users & Auth | 4 | 3 | 75% |
| Workspaces | 4 | 4 | 100% |
| Notebooks | 8 | 4 | 50% |
| Files | 17 | 0 | 0% |
| Folders | 3 | 0 | 0% |
| Search | 2 | 0 | 0% |
| Tasks | 4 | 4 | 100% |
| Markdown | 6 | 2 | 33% |
| Query | 1 | 1 | 100% |
| Integrations | 9 | 6 | 67% |
| Plugins | 5 | 0 | 0% |

### High Priority Endpoints for Testing
Based on frontend usage, these endpoints should have tests added:

1. **Files endpoints** (17 endpoints, 0 tests) - Heavily used by frontend
2. **Folders endpoints** (3 endpoints, 0 tests) - Used by frontend
3. **Search endpoints** (2 endpoints, 0 tests) - Used by frontend
4. **Notebook list/get** (2 endpoints, 0 tests) - Core functionality
5. **Plugin registration** (5 endpoints, 0 tests) - New feature

### Frontend Usage Statistics

- **Actively Used in Frontend**: ~35 endpoints (54%)
- **Backend Only/Not Used**: ~30 endpoints (46%)

### Notable Gaps

1. **File operations**: No test coverage despite extensive frontend usage
2. **Search functionality**: Critical feature but no tests
3. **Plugin system**: New feature area needs comprehensive testing
4. **Markdown CRUD**: Some endpoints not used by frontend or tested

---

## Additional Resources

- **OpenAPI Documentation**: Available at `/docs` when server is running
- **OpenAPI JSON**: Available at `/openapi.json`
- **Health Check**: `GET /health` - Returns `{ status: "healthy", version: "0.1.0" }`
- **Root Endpoint**: `GET /` - Returns API information and docs link

---

*Last Updated*: 2026-02-03  
*Generated from*: Backend route definitions, test files, and frontend service layer analysis

# Information Hierarchy Analysis

**Date:** 2026-03-07
**Scope:** Workspace → Notebook → Files hierarchy across backend models, API routes, database migrations, and frontend

## Expected Hierarchy

```
User
 └── Workspace (owned by user)
      ├── Notebook (belongs to workspace)
      │    ├── Files (stored in per-notebook SQLite DB)
      │    ├── Folders (derived from file paths)
      │    └── Tags / Search Index
      ├── Tasks (workspace-scoped)
      ├── Agents (workspace-scoped)
      └── Plugins / Integrations
```

---

## Discrepancies Found

### 1. **HIGH — Missing Database-Level Cascade Deletes**

**Location:** `backend/codex/db/models/system.py`, `backend/codex/migrations/workspace/versions/20250123_000000_001_initial_system_schema.py`

None of the foreign keys in the system database declare `ondelete="CASCADE"`. Instead, cascade deletion is implemented manually in the API layer:

- **Workspace deletion** (`backend/codex/api/routes/workspaces.py:380-474`): Manually deletes notebooks, permissions, tasks, plugin configs, secrets, API logs, agents/credentials, and PATs in sequence.
- **Notebook deletion** (`backend/codex/api/routes/notebooks.py:414-421`): Manually deletes `NotebookPluginConfig` before deleting the notebook.

**Risk:** Records deleted directly via database CLI, migrations, or external tools bypass these manual cascades, leaving orphaned records (permissions, tasks, agents, tokens, plugin configs) referencing deleted workspaces or notebooks.

**Recommendation:** Add `ondelete="CASCADE"` to all foreign keys in a migration, and keep the manual deletion for filesystem cleanup.

---

### 2. **HIGH — Dual Router Pattern Allows Hierarchy Bypass**

**Location:** `backend/codex/main.py:264` vs `267-269`

Notebooks are registered with **two** routers:

```python
# Direct access — bypasses workspace context
app.include_router(notebooks.router, prefix="/api/v1/notebooks", tags=["notebooks"])

# Nested access — proper hierarchy
app.include_router(notebooks.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/notebooks", ...)
```

The direct `notebooks.router` (at `/api/v1/notebooks/{id}`) allows accessing notebook plugin configs without any workspace ownership check. The frontend `NotebookSettingsPanel.vue` actively uses this bypass pattern:

```typescript
// NotebookSettingsPanel.vue:98 — bypasses workspace context
api.get(`/api/v1/notebooks/${props.notebookId}/plugins`)

// Should be:
api.get(`/api/v1/workspaces/${props.workspaceId}/notebooks/${props.notebookId}/plugins`)
```

**Risk:** Cross-workspace access to notebook settings if a user guesses another notebook's ID. The `SettingsDialog.vue` already passes `workspaceId` to `NotebookSettingsPanel`, but the panel ignores it.

**Recommendation:** Either remove the direct notebook router or add workspace ownership verification to it. Update `NotebookSettingsPanel` to use the nested route.

---

### 3. **HIGH — Tasks Route Not Nested Under Workspace**

**Location:** `backend/codex/main.py:295`, `backend/codex/api/routes/tasks.py`

Tasks are registered at `/api/v1/tasks/` as a flat route, not nested under workspaces, despite `Task.workspace_id` being a required field:

```python
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
```

The `list_tasks` endpoint takes `workspace_id` as a query parameter instead of a path parameter:

```python
@router.get("/")
async def list_tasks(workspace_id: int, ...):
```

**Inconsistency:** Files, folders, search, and integrations are all nested under `/api/v1/workspaces/{id}/notebooks/{id}/...`, but tasks are flat. The `get_task` and `update_task` endpoints accept a bare `task_id` with no workspace in the URL at all.

**Recommendation:** Create a `nested_router` for tasks at `/api/v1/workspaces/{workspace_identifier}/tasks/` for consistency, or document the intentional deviation.

---

### 4. **HIGH — Agents Route Not Nested Under Workspace**

**Location:** `backend/codex/main.py:300`, `backend/codex/api/routes/agents.py`

Similar to tasks, agents are registered flat despite having `workspace_id`:

```python
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(agents.session_router, prefix="/api/v1/sessions", tags=["agent-sessions"])
```

The `_get_workspace` helper validates workspace existence but the URL doesn't reflect the hierarchy.

**Recommendation:** Nest under `/api/v1/workspaces/{workspace_identifier}/agents/` for consistency.

---

### 5. **MEDIUM — Cross-Database Reference Without Enforcement**

**Location:** `backend/codex/db/models/notebook.py:42,82`

The notebook database models store `notebook_id` as a plain integer — not a foreign key — since SQLite can't enforce cross-database constraints:

```python
notebook_id: int  # Reference to notebook in system database (not a foreign key)
```

**Risk:** If a Notebook record is deleted from the system database but the `.codex/notebook.db` file remains on disk, the FileMetadata, Tag, and SearchIndex records become permanently orphaned. The notebook deletion endpoint does attempt filesystem cleanup, but failures (permissions, disk errors) silently leave orphans.

**Recommendation:** Add a startup reconciliation check that verifies all notebook database directories correspond to registered notebooks in the system database.

---

### 6. **MEDIUM — Task.assigned_to Is a Loose String Reference**

**Location:** `backend/codex/db/models/system.py:91`

```python
assigned_to: str | None = None  # Agent identifier
```

This is a string field, not a foreign key to the `Agent` model. If an agent is deleted, tasks retain a dangling string reference. There's no way to query "all tasks assigned to agent X" via relationship, only by string matching.

**Recommendation:** Either make this a proper foreign key to `agents.id` (nullable), or document that agent identifiers are intentionally decoupled from the Agent model.

---

### 7. **MEDIUM — PersonalAccessToken Has Ambiguous Dual Scope**

**Location:** `backend/codex/db/models/system.py:314-315`

```python
workspace_id: int | None = Field(default=None, foreign_key="workspaces.id")
notebook_id: int | None = Field(default=None, foreign_key="notebooks.id")
```

Both fields are optional and independent. There is no constraint ensuring:
- If `notebook_id` is set, it belongs to the referenced `workspace_id`
- Both aren't set simultaneously with conflicting scope
- Neither has a back-relationship from Workspace or Notebook

**Recommendation:** Add a check constraint or application-level validation ensuring referential consistency.

---

### 8. **MEDIUM — Snippets Route Exists Outside the Hierarchy**

**Location:** `backend/codex/main.py:303`, `backend/codex/api/routes/snippets.py`

Snippets are registered at `/api/v1/snippets/` flat, but the implementation queries notebooks within a workspace. The route internally resolves workspace context but the URL doesn't reflect the hierarchy.

**Recommendation:** Consider nesting under workspace or documenting as an intentional cross-cutting concern.

---

### 9. **LOW — Frontend API Parameter Order Inconsistency**

**Location:** `frontend/src/services/codex.ts`

API service methods have inconsistent parameter ordering:

```typescript
// Notebook service — workspace first (correct)
notebookService.list(workspaceIdentifier)

// File service — notebook first, workspace second (reversed)
fileService.list(notebookId, workspaceId)

// Folder service — path first, then notebook, then workspace
folderService.get(path, notebookId, workspaceId)
```

The URL construction is correct, but the function signatures don't follow a consistent `workspace → notebook → resource` ordering.

**Recommendation:** Standardize all service methods to accept `(workspaceId, notebookId, ...rest)`.

---

### 10. **LOW — No Breadcrumb Navigation in Frontend**

**Location:** `frontend/src/views/HomeView.vue`

The frontend has no visual breadcrumb trail showing the current position in the hierarchy (Workspace > Notebook > Folder > File). Users must rely on the sidebar to understand their context. The document title is set programmatically but there's no in-page breadcrumb component.

---

### 11. **LOW — WorkspacePermission Has No Back-Reference from User**

**Location:** `backend/codex/db/models/system.py:40-41, 66-79`

`WorkspacePermission` references both `Workspace` and `User` via foreign keys, but only `Workspace` has a back-relationship (`permissions`). The `User` model has no `permissions` relationship, making it inefficient to query "which workspaces does user X have access to?"

---

### 12. **MEDIUM — Missing Composite Index on workspace_permissions**

**Location:** `backend/codex/migrations/workspace/versions/20250123_000000_001_initial_system_schema.py:82-94`

The `workspace_permissions` table has foreign keys on both `workspace_id` and `user_id`, but lacks a composite index on `(workspace_id, user_id)`. This means:
- O(n) lookups when checking user permissions
- No UNIQUE constraint preventing duplicate permission entries for the same user-workspace pair

**Recommendation:** Add a migration creating a composite unique index on `(workspace_id, user_id)`.

---

### 13. **LOW — Schema Drift: Notebook Slug Unique Constraint Not Reflected in Model**

**Location:** Migration `20260203_000000_007_add_slug_fields.py:103-107` creates `uq_notebooks_workspace_slug`, but `backend/codex/db/models/system.py:105` only documents this in a comment — missing from `__table_args__`.

**Risk:** SQLAlchemy ORM may not enforce the uniqueness constraint, leading to potential duplicate slug issues caught only at the DB level.

---

### 14. **LOW — Missing Foreign Key Indexes on agent_sessions**

**Location:** `backend/codex/migrations/workspace/versions/20260206_000000_009_add_agent_tables.py:94-96`

The `task_id` and `user_id` columns on `agent_sessions` are foreign keys without indexes, causing slow queries when filtering by task or user.

---

### 15. **INFO — Folders Are Virtual Entities (Not a Discrepancy)**

Folders have no database table — they are derived from file paths via string manipulation in `backend/codex/api/routes/folders.py`. Folder metadata is stored in `.metadata` sidecar files with YAML frontmatter. This is a deliberate design choice aligned with the filesystem-based storage model, but has trade-offs:
- No referential integrity for folder structure
- Folder deletion cascades via path string filtering (potential race conditions)
- Performance concerns with large directories (MAX_COUNT_THRESHOLD = 10,000)

---

## Summary Table

| # | Severity | Issue | Area |
|---|----------|-------|------|
| 1 | HIGH | No database-level cascade deletes | Backend Models/Migrations |
| 2 | HIGH | Dual router allows hierarchy bypass for notebooks | Backend API + Frontend |
| 3 | HIGH | Tasks route not nested under workspace | Backend API |
| 4 | HIGH | Agents route not nested under workspace | Backend API |
| 5 | MEDIUM | Cross-database notebook_id without enforcement | Backend Models |
| 6 | MEDIUM | Task.assigned_to is loose string, not FK | Backend Models |
| 7 | MEDIUM | PersonalAccessToken ambiguous dual scope | Backend Models |
| 8 | MEDIUM | Snippets route outside hierarchy | Backend API |
| 9 | LOW | Frontend API parameter order inconsistency | Frontend Services |
| 10 | LOW | No breadcrumb navigation | Frontend UI |
| 11 | LOW | WorkspacePermission no User back-reference | Backend Models |
| 12 | MEDIUM | Missing composite index on workspace_permissions | Migrations |
| 13 | LOW | Schema drift: notebook slug constraint not in model | Models/Migrations |
| 14 | LOW | Missing FK indexes on agent_sessions | Migrations |

## Entities and Their Hierarchy Position

| Entity | Expected Parent | Actual Enforcement | Route Pattern | Consistent? |
|--------|----------------|-------------------|---------------|-------------|
| Workspace | User | FK `owner_id` → users.id | `/api/v1/workspaces/` | Yes |
| Notebook | Workspace | FK `workspace_id` → workspaces.id | Both `/api/v1/notebooks/` AND nested | **No** — dual route |
| Files | Notebook | Per-notebook DB (no FK) | Nested only | Yes |
| Folders | Notebook | Derived from file paths | Nested only | Yes |
| Tasks | Workspace | FK `workspace_id` → workspaces.id | `/api/v1/tasks/` (flat) | **No** |
| Agents | Workspace | FK `workspace_id` → workspaces.id | `/api/v1/agents/` (flat) | **No** |
| Sessions | Agent | FK `agent_id` → agents.id | `/api/v1/sessions/` (flat) | **No** |
| Snippets | Workspace* | Resolved internally | `/api/v1/snippets/` (flat) | **No** |
| Tokens | User | FK `user_id` → users.id | `/api/v1/tokens/` | Yes (user-level) |
| Search | Notebook | Per-notebook DB | Nested only | Yes |
| Plugins | Global/Notebook | Mixed | Both flat and nested | Partial |

# Information Hierarchy Analysis

## Expected Hierarchy

```
User → Workspace → Notebook → Files/Folders
```

The system uses a two-database pattern:
- **System DB** (`codex_system.db`): Users, Workspaces, Notebooks, Tasks, Agents, Plugins
- **Notebook DBs** (per-notebook `notebook.db`): FileMetadata, Tags, SearchIndex

---

## Discrepancies Found

### 1. Missing `UniqueConstraint` on Notebook Slug (Medium Severity)

**Location:** `backend/codex/db/models/system.py:105`

The `Notebook.slug` field is indexed but lacks a database-level `UniqueConstraint("workspace_id", "slug")`. Compare with `Workspace`, which correctly has `UniqueConstraint("owner_id", "slug")` at line 48.

- **Workspace** (correct): `UniqueConstraint("owner_id", "slug", name="uq_workspaces_owner_slug")`
- **Notebook** (missing): No equivalent constraint

The application code prevents duplicates via `slug_exists_for_workspace()` in `notebooks.py:59-64`, but this is a race-condition-vulnerable code-level check. A concurrent request could create duplicate slugs.

**Fix:** Add `__table_args__ = (UniqueConstraint("workspace_id", "slug", name="uq_notebooks_workspace_slug"),)` to the Notebook model.

---

### 2. Frontend `Notebook` Interface Missing `workspace_id` (Medium Severity)

**Location:** `frontend/src/services/codex.ts:14-22`

The frontend `Notebook` TypeScript interface does not include `workspace_id`:

```typescript
export interface Notebook {
  id: number
  slug?: string
  name: string
  path: string
  description?: string
  created_at: string
  updated_at: string
}
```

The backend `Notebook` model has `workspace_id` as a required field. The frontend never receives or tracks which workspace a notebook belongs to. This means:

- The workspace store must always implicitly associate notebooks with `currentWorkspace`
- There is no way to verify notebook→workspace parentage on the frontend
- If a notebook list response were ever mixed between workspaces, the frontend couldn't detect it

**Fix:** Add `workspace_id: number` to the `Notebook` interface.

---

### 3. `fileService.list()` Has Swapped Parameter Order (Low Severity)

**Location:** `frontend/src/services/codex.ts:168`

```typescript
async list(notebookId: number | string, workspaceId: number | string)
```

The parameter order is `(notebookId, workspaceId)`, but the URL template puts workspace first:
```
/api/v1/workspaces/${workspaceId}/notebooks/${notebookId}/files/
```

While functionally correct (parameters are named), this is inconsistent with the hierarchical order (workspace before notebook) and inconsistent with other methods like `get()` at line 181 which uses `(id, workspaceId, notebookId)`. The `create()` method at line 262 also uses `(notebookId, workspaceId, ...)`.

**Impact:** Confusing developer experience. Some callers pass `(notebookId, workspaceId)`, others `(id, workspaceId, notebookId)`. There's no consistent convention.

---

### 4. Tasks API Bypasses Hierarchical URL Structure (Medium Severity)

**Location:** `backend/codex/api/routes/tasks.py`, registered at `main.py:295`

Tasks are registered at `/api/v1/tasks/` (flat, non-nested), even though `Task.workspace_id` is a required field. The `workspace_id` is passed as a query parameter instead of being part of the URL path.

Compare with the consistent nested patterns:
- Files: `/api/v1/workspaces/{ws}/notebooks/{nb}/files/`
- Folders: `/api/v1/workspaces/{ws}/notebooks/{nb}/folders/`
- Search: `/api/v1/workspaces/{ws}/search/`
- Tasks: `/api/v1/tasks/?workspace_id=X` (inconsistent)

The tasks route does verify workspace access via `_verify_workspace_access()`, so this is a URL design inconsistency rather than a security issue.

---

### 5. Query API Bypasses Hierarchical URL Structure (Medium Severity)

**Location:** `backend/codex/api/routes/query.py`, registered at `main.py:296`

The query endpoint is at `/api/v1/query/` (flat), but it accepts `notebook_ids` in the request body. It should be nested under a workspace to enforce the ownership check at the URL level.

The query route does verify workspace ownership by joining through `Notebook → Workspace`, but the URL pattern doesn't reflect the hierarchy.

---

### 6. Flat `notebooks.router` Exists Alongside Nested `notebooks.nested_router` (Low Severity)

**Location:** `main.py:264` vs `main.py:265-269`

Two routers for notebooks are registered:
- `/api/v1/notebooks/{notebook_id}/...` (flat `router` - for plugin config by ID)
- `/api/v1/workspaces/{workspace_identifier}/notebooks/...` (nested `nested_router`)

The flat router (lines 170-218 in notebooks.py) handles plugin configs by notebook ID. It uses `_verify_notebook_access()` which joins through Workspace to verify ownership, so it's secure. However, the flat URL `/api/v1/notebooks/5/plugins` doesn't communicate the hierarchy in the URL structure.

---

### 7. No Cross-Database Referential Integrity (By Design, But Risky)

**Location:** `backend/codex/db/models/notebook.py:42,82`

`FileMetadata.notebook_id` and `Tag.notebook_id` are plain integers with no foreign key constraint (they can't have one - different database). This means:

- Deleting a Notebook in the system DB does not cascade to the notebook DB
- The workspace deletion code (`workspaces.py`) handles this by deleting the notebook directory (which includes the `.codex/notebook.db`), but if the filesystem delete fails, orphaned notebook DBs could remain
- There's no periodic consistency check to find orphaned notebook databases

---

### 8. Frontend `slug` Fields Are Optional But Backend Requires Them (Low Severity)

**Location:** `frontend/src/services/codex.ts:5,16`

```typescript
// Frontend
interface Workspace { slug?: string; ... }
interface Notebook { slug?: string; ... }
```

```python
# Backend
class Workspace: slug: str = Field(index=True)
class Notebook: slug: str = Field(index=True)
```

The backend always generates a slug on creation. The frontend marks `slug` as optional (`slug?`), which means TypeScript code must always null-check before using it, even though it will always be present in API responses.

---

### 9. `PersonalAccessToken` Can Scope to Notebook Without Workspace (Low Severity)

**Location:** `backend/codex/db/models/system.py:314-315`

```python
workspace_id: int | None = Field(default=None, foreign_key="workspaces.id")
notebook_id: int | None = Field(default=None, foreign_key="notebooks.id")
```

A token could theoretically be scoped to a `notebook_id` without a `workspace_id`, which breaks the hierarchy. There's no database constraint or application validation ensuring that if `notebook_id` is set, `workspace_id` must also be set (and must be the parent workspace).

---

### 10. `Notebook` Interface Missing from Frontend Router (Minor)

**Location:** `frontend/src/router/index.ts`

There is no dedicated route for viewing a notebook itself (e.g., `/w/:workspaceSlug/:notebookSlug`). The only path-based route is for files:

```
/w/:workspaceSlug/:notebookSlug/:filePath*
```

This means navigating to a notebook without selecting a file has no URL representation. The notebook is selected through the sidebar UI, but the URL doesn't reflect the notebook-level navigation state until a file is selected.

---

## Summary Table

| # | Discrepancy | Severity | Type | Location |
|---|-------------|----------|------|----------|
| 1 | Missing `UniqueConstraint` on Notebook slug | Medium | Data integrity | `system.py:97-112` |
| 2 | Frontend `Notebook` missing `workspace_id` | Medium | Interface mismatch | `codex.ts:14-22` |
| 3 | `fileService.list()` swapped param order | Low | API consistency | `codex.ts:168` |
| 4 | Tasks API flat URL, not nested under workspace | Medium | URL design | `tasks.py`, `main.py:295` |
| 5 | Query API flat URL, not nested under workspace | Medium | URL design | `query.py`, `main.py:296` |
| 6 | Flat notebook plugin router alongside nested | Low | URL design | `main.py:264` |
| 7 | No cross-DB referential integrity safeguards | Low* | Data integrity | `notebook.py:42,82` |
| 8 | Frontend `slug` optional, backend required | Low | Interface mismatch | `codex.ts:5,16` |
| 9 | PAT can scope to notebook without workspace | Low | Data integrity | `system.py:314-315` |
| 10 | No notebook-level URL in frontend router | Minor | Navigation | `router/index.ts` |

*\*Item 7 is by design (two-database pattern), but could benefit from a consistency check.*

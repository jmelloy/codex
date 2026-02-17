# .page System: Audit, Bugs, and Improvement Plan

## Overview

The `.page` system provides a convention-based approach to creating multi-block pages within Codex notebooks. A "page" is a directory ending in `.page` that contains numbered block files (`001-intro.md`, `002-chart.png`, etc.) rendered sequentially as a unified view. Page metadata is stored in `.page` or `.page.json` JSON files within the directory.

This document catalogs current bugs, architectural weaknesses, and concrete improvements.

---

## Architecture Summary

```
notebook-root/
  experiment-log.page/          # Page directory (identified by .page suffix)
    .page                       # JSON metadata: {title, description, created_time, last_edited_time}
    .metadata                   # Optional YAML folder properties
    001-intro.md                # Block 1 (markdown)
    002-diagram.png             # Block 2 (image)
    003-results.json            # Block 3 (data file)
```

**Key design decisions:**
- No dedicated `Page` database table -- pages are a frontend convention layered on folders
- Backend is entirely unaware of `.page` semantics -- it treats them as regular directories
- All page logic lives in `frontend/src/services/codex.ts` (`pageService`) and two view components
- Block ordering is determined by 3-digit filename prefixes (`001-`, `002-`, ...)

**Relevant files:**

| Component | Path |
|-----------|------|
| Page service (CRUD, listing) | `frontend/src/services/codex.ts:180-456` |
| Unified page renderer | `frontend/src/components/PageUnifiedView.vue` |
| Standalone page viewer | `frontend/src/views/PageDetailView.vue` |
| HomeView integration | `frontend/src/views/HomeView.vue:699-712, 1063-1067, 1666-1695` |
| Router | `frontend/src/router/index.ts` (page-detail route) |
| Backend folder API | `backend/codex/api/routes/folders.py` |
| Backend file API | `backend/codex/api/routes/files.py` |

---

## Critical Bugs

### 1. Five core page operations throw "not implemented" errors

**Location:** `frontend/src/services/codex.ts:402-454`

The following methods exist with complete signatures but immediately throw:

| Method | Line | Error |
|--------|------|-------|
| `pageService.update()` | 402 | `"Updating pages requires backend file update support"` |
| `pageService.delete()` | 410 | `"Deleting pages requires backend directory deletion support"` |
| `pageService.createBlock()` | 427 | `"Creating blocks requires backend file creation support"` |
| `pageService.reorderBlocks()` | 440 | `"Reordering blocks requires backend file rename support"` |
| `pageService.deleteBlock()` | 453 | `"Deleting blocks requires backend file deletion support"` |

**Impact:** After creating a page, users cannot edit its title/description, add new blocks, reorder blocks, delete individual blocks, or delete the page itself. The page system is essentially read-only + create-only.

**Root cause:** These operations need backend endpoints that don't exist yet:
- Update file content by path (for `.page` metadata)
- Delete a directory recursively
- Create a file at a specific path within a page directory
- Rename files (for reordering)
- Delete a file by path

**Fix:** The backend folder route (`folders.py`) already supports `DELETE` for directories. The file route (`files.py`) already supports `POST` for creating files. The missing pieces are: file update by path, file rename, and file delete by path. Once those backend endpoints exist, the frontend stubs can be completed.

### 2. No backend awareness of pages

**Location:** `backend/codex/api/routes/folders.py`, `backend/codex/api/routes/files.py`

The backend has zero knowledge of the `.page` convention. There are no:
- Page-specific API endpoints
- Validation that `.page` directories maintain structural integrity
- Search/query support that understands pages as a first-class entity

Grep for `.page` across the entire backend returns zero results. All page semantics are client-side only.

**Impact:** The backend cannot enforce invariants, provide efficient page queries, or support page-level operations. Any backend consumer (CLI tools, other frontends, agents) must re-implement the page convention from scratch.

---

## High-Severity Issues

### 3. Page listing fetches ALL files in the notebook

**Location:** `frontend/src/services/codex.ts:215`

```typescript
async list(notebookId, workspaceId): Promise<PageListItem[]> {
  const files = await fileService.list(notebookId, workspaceId)  // ALL files
  // ... then filters client-side
}
```

`pageService.list()` calls `fileService.list()` which retrieves every file in the notebook, then iterates over all of them to find `.page` directories and count blocks. For notebooks with thousands of files, this is an O(n) client-side scan on every page list request.

**Fix:** Add a backend endpoint that queries the database directly for files whose paths match `%.page/%` or filenames matching `.page`/`.page.json`. Return aggregated page metadata server-side.

### 4. `pageService.get()` also fetches ALL files

**Location:** `frontend/src/services/codex.ts:317`

```typescript
async get(directoryPath, notebookId, workspaceId): Promise<PageWithBlocks> {
  // ...
  const files = await fileService.list(notebookId, workspaceId)  // ALL files again
  const blockFiles = files.filter(f => f.path.startsWith(directoryPath + "/") && ...)
}
```

Even to view a single page, the entire notebook's file list is fetched. This should be a targeted query for files under the specific directory path.

### 5. Duplicate page entries when metadata parsing fails

**Location:** `frontend/src/services/codex.ts:237-293`

The listing algorithm processes pages in two passes:
1. Scan for `.page`/`.page.json` files and parse their metadata
2. Scan for directories ending in `.page`

If pass 1 fails (corrupted JSON at line 259-260), the error is caught and the page is NOT added to the `pages` array. But pass 2 finds the same directory and adds it with fallback metadata. This is correct behavior.

However, if pass 1 succeeds but produces a different `dirPath` than expected (e.g., due to path normalization differences), the deduplication check at line 267 may not match, causing the same page to appear twice with potentially different metadata.

### 6. Zero test coverage

There are no dedicated tests for the page system in either:
- `backend/tests/` -- no `test_pages*.py` files
- `frontend/src/__tests__/` -- no page-related test files

This means all the logic in `pageService` (slug generation, block detection, metadata parsing, deduplication) has no regression protection.

---

## Medium-Severity Issues

### 7. Block numbering limited to 000-999

**Location:** `frontend/src/components/PageUnifiedView.vue:170-178`

```typescript
function parsePosition(filename: string): number {
  const match = filename.match(/^(\d{3})-/)
  return match && match[1] ? parseInt(match[1], 10) : 999
}

function isBlockFile(file: FileMetadata): boolean {
  return /^\d{3}-/.test(file.filename)
}
```

The pattern `^\d{3}-` requires exactly 3 digits. This means:
- Files like `1-intro.md` or `01-intro.md` are NOT recognized as blocks
- Maximum of 999 blocks per page (positions 001-999)
- A file named `1000-extra.md` is silently ignored
- Non-matching files default to position 999, colliding with legitimate block 999

**Fix:** Accept variable-width numeric prefixes (`/^(\d+)-/`) and use a higher default position for non-matching files.

### 8. No validation on page creation

**Location:** `frontend/src/services/codex.ts:351-376`

`pageService.create()` does not validate:
- Empty or whitespace-only titles (the slugify function falls back to `"page"`)
- Excessively long titles that produce filesystem-unfriendly paths
- Titles containing only special characters (slugify strips them all, leaving `"page"`)
- Whether a page with the same slug already exists (would silently overwrite `.page` metadata)
- Reserved filesystem names (`.`, `..`, `CON`, `NUL` on Windows)

**Example:** Creating three pages with titles `"!!!"`, `"@@@"`, and `"###"` would all produce `page.page` as the directory name, with each creation overwriting the previous metadata.

### 9. Root-level pages are silently skipped

**Location:** `frontend/src/services/codex.ts:239-240`

```typescript
const dirPath = pageFile.path.substring(0, pageFile.path.lastIndexOf("/"))
if (dirPath) {  // Empty string is falsy -- root pages skipped
```

A `.page` file at the notebook root (path = `.page`) yields `dirPath = ""`, which fails the truthiness check. The page is silently excluded from listings.

### 10. Content loading has no size limits or timeouts

**Location:** `frontend/src/components/PageUnifiedView.vue:225-242`

All text block content is loaded in parallel with no constraints:
- No file size limit -- a 100MB text file would be fetched entirely
- No timeout -- if one request hangs, `Promise.all()` waits forever
- No concurrency limit -- a page with 50 text blocks fires 50 simultaneous requests
- No streaming or pagination for large content

### 11. PageDetailView and PageUnifiedView are redundant

Two separate components render pages:
- `PageDetailView.vue` -- standalone route at `/page/:notebookId/:pagePath+`, shows blocks as cards with emoji icons
- `PageUnifiedView.vue` -- embedded in HomeView, renders blocks inline with actual content

These have diverged significantly:
- PageDetailView doesn't render inline content (just links to markdown)
- PageUnifiedView renders markdown, images, code, video, audio, and PDFs inline
- PageDetailView uses emoji icons; PageUnifiedView uses content-type detection
- They use different data loading strategies (pageService.get vs folder.files)

### 12. Inconsistent metadata field naming

The `.page` JSON files use Notion-style field names:
```json
{"created_time": "...", "last_edited_time": "..."}
```

The TypeScript `Page` interface uses Rails-style names:
```typescript
interface Page { created_at?: string; updated_at?: string; }
```

The mapping happens silently in `pageService.list()` and `pageService.get()`:
```typescript
created_at: metadata.created_time,
updated_at: metadata.last_edited_time,
```

This creates confusion when debugging or when other tools read `.page` files directly.

### 13. Sort stability for blocks with duplicate positions

**Location:** `frontend/src/components/PageUnifiedView.vue:191-193`

```typescript
const sortedBlocks = computed(() => {
  return [...blocks.value].sort((a, b) => a.position - b.position)
})
```

If two blocks have the same position number (e.g., both `001-intro.md` and `001-summary.md` exist), the sort is unstable across JavaScript engines. The display order could differ between Chrome and Firefox.

**Fix:** Use a secondary sort key (filename) to guarantee deterministic ordering.

### 14. No error recovery or retry in page views

**Location:** `frontend/src/views/PageDetailView.vue:168-185`

If `loadPage()` fails, the error is displayed and the user must manually navigate away and back. There is no:
- Retry button
- Auto-retry with backoff
- Partial loading (show what succeeded)
- Fallback to cached data

---

## Low-Severity Issues

### 15. No `.page` file format versioning

The JSON stored in `.page` files has no schema version field. If the format needs to evolve (new fields, renamed fields, structural changes), there's no way to distinguish v1 pages from v2 pages. Migration tooling would have to guess based on field presence.

### 16. Slugify edge cases

**Location:** `frontend/src/services/codex.ts:201-208`

```typescript
_slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[-\s]+/g, "-")
    .trim()
    .replace(/^-+|-+$/g, "") || "page"
}
```

- Unicode titles (CJK characters, emoji, accented letters) are stripped entirely by `[^\w\s-]` since `\w` only matches `[a-zA-Z0-9_]` without the unicode flag
- A title like "Analyse des donnees" becomes "analyse-des-donnes" (accent stripped, meaning changed)
- Leading/trailing whitespace in titles produces different slugs depending on trim order

### 17. PageDetailView route parameter parsing

**Location:** `frontend/src/views/PageDetailView.vue:133-140`

```typescript
const notebookId = ref<number>(parseInt(route.params.notebookId as string))
const workspaceId = ref<number>(parseInt(route.query.workspace_id as string))
```

- `workspaceId` comes from a query parameter, not a route param -- easy to miss when constructing URLs
- `parseInt` on `undefined` returns `NaN`, no error handling for missing params
- Values are captured once in `ref()` -- navigating between pages without a full remount would show stale data

### 18. Path traversal in frontend page discovery

**Location:** `frontend/src/services/codex.ts:224-231`

The path splitting logic doesn't normalize paths before processing:
```typescript
for (const file of files) {
  const parts = file.path.split("/")
  for (let i = 0; i < parts.length; i++) {
    if (part && part.endsWith(".page")) {
      pageDirs.add(parts.slice(0, i + 1).join("/"))
    }
  }
}
```

A file with path `foo/../bar.page/file.md` would register `foo/../bar.page` as a page directory. While the backend has path traversal guards, the frontend doesn't normalize these paths, which could cause inconsistent behavior.

---

## Improvement Recommendations

### Phase 1: Fix Critical Gaps

1. **Implement missing backend endpoints:**
   - `PUT /api/v1/.../files/path/{path}/content` -- update file content by path
   - `DELETE /api/v1/.../files/path/{path}` -- delete file by path
   - `POST /api/v1/.../files/path/{path}/rename` -- rename/move a file
   - These unblock all five stubbed `pageService` methods

2. **Complete the frontend stubs** in `pageService.update()`, `.delete()`, `.createBlock()`, `.reorderBlocks()`, `.deleteBlock()` once backend endpoints exist.

3. **Add basic test coverage:**
   - Unit tests for `pageService._slugify()`, `parsePosition()`, `isBlockFile()`
   - Integration test for page creation flow
   - Backend test for folder operations on `.page` directories

### Phase 2: Performance and Reliability

4. **Add a backend page listing endpoint** that queries for `.page` directories directly in the database rather than fetching all files. SQL: `SELECT DISTINCT substr(path, 1, instr(path, '.page/') + 4) FROM file_metadata WHERE path LIKE '%.page/%'`.

5. **Add content size limits and timeouts** to block loading in `PageUnifiedView.vue`. Cap text content at ~1MB, add a 10-second timeout per block, and limit concurrent requests to ~5 at a time.

6. **Accept variable-width block prefixes** (`/^(\d+)-/` instead of `/^(\d{3})-/`) and add a secondary filename sort for stability.

7. **Validate page creation inputs:** check for slug collisions, enforce title length limits, handle unicode titles (use the `u` flag in regex or a proper slugify library).

### Phase 3: Consolidation and Backend Awareness

8. **Unify PageDetailView and PageUnifiedView** into a single component. PageDetailView currently shows blocks as non-interactive cards with emoji -- it should reuse PageUnifiedView's inline rendering. Alternatively, remove PageDetailView and its route entirely if the HomeView integration is sufficient.

9. **Add optional backend page awareness:**
   - A `page_type` or `is_page` flag on folders in the database
   - Page-level metadata indexed in the system for search
   - API responses that include block count and page metadata without requiring full file scans

10. **Standardize metadata field names.** Pick one convention (`created_at`/`updated_at` or `created_time`/`last_edited_time`) and use it consistently in both the `.page` JSON format and the TypeScript interfaces.

11. **Add a format version** to `.page` files: `{"version": 1, "title": "...", ...}` to enable future migrations.

### Phase 4: UX Enhancements

12. **Block management UI:** Add buttons to insert new blocks between existing ones, drag-and-drop reorder, and delete individual blocks -- all gated behind the backend endpoints from Phase 1.

13. **Page templates:** Allow creating pages from templates (e.g., "Experiment Log" with pre-defined block structure) similar to the existing file template system.

14. **Page-level search:** Support searching within a page's blocks as a unit rather than individual files.

15. **Block type indicators in sidebar:** Show the block structure of a page in the file tree (expand to see numbered blocks with type icons).

---

## Summary Table

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | Critical | 5 page operations throw errors | `codex.ts:402-454` |
| 2 | Critical | Backend has zero page awareness | `backend/` (absent) |
| 3 | High | Page listing fetches ALL notebook files | `codex.ts:215` |
| 4 | High | Page get fetches ALL notebook files | `codex.ts:317` |
| 5 | High | Duplicate entries on metadata parse failure | `codex.ts:237-293` |
| 6 | High | No test coverage | `tests/` (absent) |
| 7 | Medium | Block numbering limited to 000-999 | `PageUnifiedView.vue:170-178` |
| 8 | Medium | No validation on page creation | `codex.ts:351-376` |
| 9 | Medium | Root-level pages silently skipped | `codex.ts:239-240` |
| 10 | Medium | No content size limits or timeouts | `PageUnifiedView.vue:225-242` |
| 11 | Medium | Two redundant page view components | `PageDetailView.vue`, `PageUnifiedView.vue` |
| 12 | Medium | Inconsistent metadata field names | `codex.ts:255-256` |
| 13 | Medium | Unstable block sort order | `PageUnifiedView.vue:191-193` |
| 14 | Medium | No error recovery/retry | `PageDetailView.vue:168-185` |
| 15 | Low | No `.page` format versioning | `.page` JSON files |
| 16 | Low | Slugify drops unicode characters | `codex.ts:201-208` |
| 17 | Low | PageDetailView param parsing fragile | `PageDetailView.vue:133-140` |
| 18 | Low | Path normalization missing | `codex.ts:224-231` |

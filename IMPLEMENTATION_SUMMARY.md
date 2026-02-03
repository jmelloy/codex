# Backend URL Structure Reorganization - Summary

## Overview

This PR implements a major refactoring of the Codex backend API to use RESTful, slug-based URLs instead of query parameter-based routing. This makes the API more intuitive, bookmarkable, and follows REST best practices.

## What Was Accomplished

### 1. Database Changes ✅

**Models Updated:**
- Added `slug` field to `Workspace` model (unique, indexed)
- Added `slug` field to `Notebook` model (unique per workspace, indexed)

**Migration:**
- Created Alembic migration `20260203_000000_007_add_slug_fields.py`
- Handles SQLite constraints properly using batch operations
- Automatically populates slugs for existing records
- Tested and working

### 2. Workspace API ✅

**New URL Patterns:**
```
GET    /api/v1/workspaces/                    # List all workspaces
GET    /api/v1/workspaces/{workspace_slug}    # Get by slug OR ID
POST   /api/v1/workspaces/                    # Create (auto-generates slug)
PATCH  /api/v1/workspaces/{workspace_slug}/theme  # Update theme
```

**Implementation:**
- Automatic slug generation from workspace name
- Collision detection with UUID suffix fallback
- Accepts both slug and numeric ID for backward compatibility
- Helper function `get_workspace_by_slug_or_id()` for flexible lookups

### 3. Notebook API ✅

**New Nested URL Patterns:**
```
GET    /api/v1/workspaces/{ws_slug}/notebooks                  # List notebooks
POST   /api/v1/workspaces/{ws_slug}/notebooks                  # Create notebook
GET    /api/v1/workspaces/{ws_slug}/notebooks/{nb_slug}        # Get notebook
GET    /api/v1/workspaces/{ws_slug}/notebooks/{nb_slug}/indexing-status
```

**Implementation:**
- Created separate `nested_router` for workspace-nested routes
- Automatic slug generation from notebook name
- Collision detection with UUID suffix fallback
- Accepts both slug and numeric ID in nested routes
- Helper function `get_notebook_by_slug_or_id()` for flexible lookups
- Old flat routes `/api/v1/notebooks/` still work but deprecated

### 4. Testing ✅

**New Test Suite:** `backend/tests/test_slug_routes.py`

5 comprehensive tests:
- ✅ Workspace slug generation on creation
- ✅ Get workspace by slug and by ID
- ✅ Nested notebook creation with slug generation
- ✅ Get notebook by slug and by ID  
- ✅ List notebooks using nested route

**Test Results:**
- All 5 new tests passing
- All 4 existing API tests still passing
- No regressions introduced

### 5. Documentation ✅

**Created/Updated:**
- `docs/URL_STRUCTURE_REFACTOR.md` - Comprehensive design document
- Documents current vs proposed structure
- Implementation details and status
- Clear roadmap for remaining work

## URL Pattern Changes

### Before (Query Parameters)
```
GET /api/v1/workspaces/{id}
GET /api/v1/notebooks/?workspace_id={id}
GET /api/v1/notebooks/{id}?workspace_id={id}
GET /api/v1/files/?notebook_id={id}&workspace_id={id}
```

### After (Path-Based with Slugs) ✅ Partially Complete
```
# Implemented:
GET /api/v1/workspaces/{slug}
GET /api/v1/workspaces/{ws_slug}/notebooks
GET /api/v1/workspaces/{ws_slug}/notebooks/{nb_slug}

# To Be Implemented:
GET /api/v1/workspaces/{ws_slug}/notebooks/{nb_slug}/files
GET /api/v1/workspaces/{ws_slug}/notebooks/{nb_slug}/files/{path:path}
GET /api/v1/workspaces/{ws_slug}/search?query={q}
```

## Technical Details

### Slug Generation
```python
def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "default"
```

**Examples:**
- "My Research Project" → "my-research-project"
- "Experiment #42!" → "experiment-42"
- "Data (2024)" → "data-2024"

### Collision Handling
When a slug already exists, a UUID suffix is added:
- First: "my-notebook"
- Second: "my-notebook-a3b4c5d6"

### Backward Compatibility
All endpoints accept both slug and numeric ID:
```python
# Both work:
GET /api/v1/workspaces/my-workspace
GET /api/v1/workspaces/123
```

## What Remains To Be Done

### High Priority

1. **File Routes** (⏳ TODO)
   - Create nested router under notebooks
   - Handle file paths properly (may contain slashes)
   - Many endpoints: list, get, create, update, delete, upload, move, history

2. **Search Routes** (⏳ TODO)
   - Nest under workspace and/or notebook
   - Maintain query parameter for search terms

3. **Folder Routes** (⏳ TODO)
   - Nest under notebooks
   - Handle folder paths properly

### Medium Priority

4. **Frontend Updates** (⏳ TODO)
   - Update `frontend/src/services/codex.ts`
   - Use new URL patterns throughout
   - Test thoroughly

5. **Existing Test Updates** (⏳ TODO)
   - Update tests in `test_files_api.py`
   - Update tests in `test_file_creation.py`
   - Update tests in `test_search_api.py`
   - Any other tests using old URL patterns

### Low Priority

6. **Plugin/Integration Routes** (⏳ Review)
   - May need similar nesting
   - Review and plan

7. **OpenAPI Documentation** (⏳ TODO)
   - Update endpoint descriptions
   - Add examples using slugs

## Benefits Achieved

1. **✅ More RESTful**: Clear resource hierarchy in URLs
2. **✅ Human-Readable**: URLs are intuitive and self-documenting
3. **✅ Bookmarkable**: Slug-based URLs are easier to remember
4. **✅ Backward Compatible**: Old URLs still work during transition
5. **✅ Type-Safe**: FastAPI validates slug format automatically
6. **✅ Tested**: Comprehensive test coverage for new functionality

## Migration Strategy

1. **✅ Phase 1**: Add slug fields (COMPLETE)
2. **✅ Phase 2**: Implement workspace/notebook slug routes (COMPLETE)
3. **🔄 Phase 3**: Implement file/search/folder routes (IN PROGRESS)
4. **⏳ Phase 4**: Update frontend and tests (TODO)
5. **⏳ Phase 5**: Deprecate old routes in docs (TODO)
6. **⏳ Phase 6**: Remove old routes in next major version (FUTURE)

## Code Quality

- ✅ No code duplication (shared helper functions)
- ✅ Consistent naming conventions
- ✅ Comprehensive error handling
- ✅ Type hints throughout
- ✅ Async/await properly used
- ✅ Database transactions handled correctly

## Performance Considerations

- Slug fields are indexed for fast lookups
- Unique constraints prevent duplicates
- Workspace slug lookup: O(log n) with index
- Notebook slug lookup: O(log n) with composite index
- No significant performance impact expected

## Security Considerations

- Slug generation removes special characters
- No SQL injection risk (parameterized queries)
- Authorization checks unchanged
- User can only access their own workspaces
- Workspace owner controls notebook access

## Example Usage

### Creating and Accessing Resources

```bash
# Create workspace
POST /api/v1/workspaces/
{"name": "Research Project"}
# Returns: {"id": 1, "slug": "research-project", ...}

# Access by slug (recommended)
GET /api/v1/workspaces/research-project

# Access by ID (still works)
GET /api/v1/workspaces/1

# Create notebook
POST /api/v1/workspaces/research-project/notebooks
{"name": "Data Analysis"}
# Returns: {"id": 5, "slug": "data-analysis", ...}

# Access notebook
GET /api/v1/workspaces/research-project/notebooks/data-analysis
```

## Conclusion

This PR successfully implements the foundation for slug-based, hierarchical URL routing in the Codex backend. The workspace and notebook APIs are complete, tested, and backward compatible. The remaining work involves applying the same pattern to file, search, and folder routes, then updating the frontend and existing tests.

The implementation follows REST best practices, maintains backward compatibility, and provides a clear migration path for clients. All changes are well-tested and documented.

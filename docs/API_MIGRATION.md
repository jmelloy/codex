# API Restructuring - Migration Guide

## Overview

This document describes the API changes made to restructure endpoints for better organization and slug-based routing.

## Changes Summary

### 1. User Endpoints Moved to v1

**Old Endpoints (Deprecated but still functional):**
- `POST /api/token` - Login
- `POST /api/register` - Register new user
- `GET /api/users/me` - Get current user
- `PATCH /api/users/me/theme` - Update user theme

**New v1 Endpoints:**
- `POST /api/v1/users/token` - Login
- `POST /api/v1/users/register` - Register new user
- `GET /api/v1/users/me` - Get current user
- `PATCH /api/v1/users/me/theme` - Update user theme

**Migration:** Both old and new endpoints work. Update client code to use `/api/v1/users` prefix. Legacy endpoints at `/api` will be maintained for backward compatibility.

### 2. Slug Fields Added

**Database Changes:**
- `workspaces` table now has a `slug` field (unique, indexed)
- `notebooks` table now has a `slug` field (indexed)

**Migration Applied:** Database migration `20260203_000000_007_add_slug_fields.py` automatically populates slugs for existing records.

### 3. Slug-Based Endpoints

New slug-based endpoints allow accessing resources by human-readable slugs instead of numeric IDs:

**Workspace Endpoints:**
- `GET /api/v1/workspaces/by-slug/{workspace_slug}` - Get workspace by slug

**Notebook Endpoints:**
- `GET /api/v1/notebooks/by-slug/{workspace_slug}/{notebook_slug}` - Get notebook by slug

**File Endpoints (New Pattern):**
- `GET /api/v1/{workspace_slug}/{notebook_slug}/files/` - List files
- `GET /api/v1/{workspace_slug}/{notebook_slug}/files/{file_id}` - Get file by ID
- `GET /api/v1/{workspace_slug}/{notebook_slug}/files/by-path?path={file_path}` - Get file by path

## Examples

### Using Slug-Based File Endpoints

**Old way (still works):**
```bash
GET /api/v1/files/?workspace_id=1&notebook_id=2
```

**New way with slugs:**
```bash
GET /api/v1/my-workspace/my-notebook/files/
```

### Getting a Workspace by Slug

```bash
GET /api/v1/workspaces/by-slug/my-workspace
```

Response includes:
```json
{
  "id": 1,
  "name": "My Workspace",
  "slug": "my-workspace",
  "path": "/data/workspaces/my-workspace",
  ...
}
```

### Getting a Notebook by Slug

```bash
GET /api/v1/notebooks/by-slug/my-workspace/my-notebook
```

Response includes:
```json
{
  "id": 2,
  "name": "My Notebook",
  "slug": "my-notebook",
  "workspace_slug": "my-workspace",
  ...
}
```

## Backward Compatibility

- All existing endpoints using numeric IDs continue to work
- Legacy user endpoints at `/api` continue to work
- No breaking changes for existing clients
- Clients can migrate to new endpoints at their own pace

## Benefits

1. **Better URLs:** Slug-based URLs are more human-readable and SEO-friendly
2. **Organized API:** Clear v1 namespace for all endpoints
3. **Flexibility:** Both ID-based and slug-based access supported
4. **Future-proof:** Version namespace allows for future API evolution

## Testing

All changes are covered by comprehensive tests:
- `tests/test_users_v1.py` - V1 user endpoint tests
- `tests/test_slug_endpoints.py` - Slug-based endpoint tests
- Existing tests continue to pass, ensuring backward compatibility

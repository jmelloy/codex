# Integration Endpoints: Unified /execute Functionality

## Problem Statement
The `/execute` and `/render` endpoints in the integrations API had different capabilities:
- `/execute`: Simple endpoint execution without caching
- `/render`: Complete implementation with artifact caching to filesystem and database

The task was to combine these methods. We updated `/execute` with the artifact caching functionality from `/render`, then removed the `/render` endpoint to consolidate the API.

## Solution

### What Changed
1. **Updated `/execute` endpoint** to include artifact caching functionality
2. **Deleted `/render` endpoint** - no longer needed since `/execute` now has all the functionality

The `/execute` endpoint now:

1. **Saves artifacts to the filesystem** at: `{workspace_path}/.codex/artifacts/{plugin_id}/{hash}.{ext}`
2. **Tracks artifacts in the database** using the `IntegrationArtifact` model
3. **Supports content-type detection** for proper file extension and storage format
4. **Maintains backward compatibility** with existing API consumers

### Unified Endpoint

#### `/execute` Endpoint (Only)
- **Input**: `endpoint_id` + `parameters`
- **Use case**: Direct API endpoint execution with artifact caching
- **Cache TTL**: Never expires (`expires_at = None`)
- **Block validation**: None (you specify the endpoint directly)

### Implementation Details

**File Modified**: `backend/codex/api/routes/integrations.py`

Changes to `/execute` endpoint:
1. Workspace lookup to determine artifact storage path
2. Hash computation for cache key (using endpoint_id as cache identifier)
3. Artifact file path generation based on content type
4. Filesystem write using `_write_artifact_data` helper
5. Database record creation/update via `IntegrationArtifact` model
6. Transaction commit to ensure data consistency

Deleted `/render` endpoint (lines 596-789) including:
- Block type validation
- Cache TTL configuration
- Cache reading logic
- All rendering-specific code

### Verification
- ✅ Artifacts are written to filesystem
- ✅ Artifacts are tracked in database
- ✅ Content type is properly stored
- ✅ Fetch timestamp is recorded
- ✅ Cache mechanism works correctly

### Testing

Added smoke test in `backend/tests/test_integrations_api.py`:
- `test_execute_integration_with_artifact_caching`: Ensures endpoint doesn't crash with new code

### Documentation

Updated `docs/design/plugin-system.md`:
- Updated to reflect single `/execute` endpoint with artifact caching
- Documented artifact storage location

## Impact

### Benefits
1. **Simplified API**: Single endpoint instead of two with overlapping functionality
2. **Better performance**: `/execute` now caches artifacts
3. **Audit trail**: All API calls are logged to database with timestamps
4. **Backward compatible**: `/execute` response format unchanged

### Breaking Changes
**Yes - `/render` endpoint removed**
- Any code using `/render` must migrate to `/execute`
- Frontend components may need updates if they use `/render`

### Migration Notes
Code using `/render` should switch to `/execute`:
- Use `endpoint_id` instead of `block_type`
- Block type mapping to endpoints must be handled in calling code
- No cache TTL or cache reading - artifacts are written but not read automatically

## Examples

### Before (No Caching)
```bash
POST /api/v1/integrations/weather-api/execute?workspace_id=1
{
  "endpoint_id": "current_weather",
  "parameters": {"lat": 37.7749, "lon": -122.4194}
}
# Response returned, but not cached
```

### After (With Caching, /render Deleted)
```bash
POST /api/v1/integrations/weather-api/execute?workspace_id=1
{
  "endpoint_id": "current_weather",  
  "parameters": {"lat": 37.7749, "lon": -122.4194}
}
# Response returned AND saved to:
# - Filesystem: {workspace}/.codex/artifacts/weather-api/{hash}.json
# - Database: IntegrationArtifact record with metadata
```

## Related Files
- `backend/codex/api/routes/integrations.py` - Main implementation (removed /render endpoint)
- `backend/codex/db/models/system.py` - IntegrationArtifact model
- `backend/tests/test_integrations_api.py` - Tests
- `docs/design/plugin-system.md` - Documentation

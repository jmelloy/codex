# Integration Endpoints: Combined /execute and /render Functionality

## Problem Statement
The `/execute` and `/render` endpoints in the integrations API had different capabilities:
- `/execute`: Simple endpoint execution without caching
- `/render`: Complete implementation with artifact caching to filesystem and database

The task was to combine these methods, using `/render` as the base since it was more complete, and verify that artifacts are being saved to the log.

## Solution

### What Changed
We updated the `/execute` endpoint to include the same artifact caching functionality as `/render`. Both endpoints now:

1. **Save artifacts to the filesystem** at: `{workspace_path}/.codex/artifacts/{plugin_id}/{hash}.{ext}`
2. **Track artifacts in the database** using the `IntegrationArtifact` model
3. **Support content-type detection** for proper file extension and storage format
4. **Maintain backward compatibility** with existing API consumers

### Key Differences Between Endpoints

While both endpoints now cache artifacts, they serve different purposes:

#### `/execute` Endpoint
- **Input**: `endpoint_id` + `parameters`
- **Use case**: Direct API endpoint execution
- **Cache TTL**: Never expires (`expires_at = None`)
- **Block validation**: None (you specify the endpoint directly)

#### `/render` Endpoint  
- **Input**: `block_type` + `parameters`
- **Use case**: Semantic block rendering (e.g., "weather", "github-issue")
- **Cache TTL**: Configured per block type in plugin manifest
- **Block validation**: Validates block_type against plugin's blocks configuration

### Implementation Details

**File Modified**: `backend/codex/api/routes/integrations.py`

Added to `/execute` endpoint (lines 458-541):
1. Workspace lookup to determine artifact storage path
2. Hash computation for cache key (using endpoint_id as block_type)
3. Artifact file path generation based on content type
4. Filesystem write using `_write_artifact_data` helper
5. Database record creation/update via `IntegrationArtifact` model
6. Transaction commit to ensure data consistency

### Verification

The `/render` endpoint already had this functionality, so we verified:
- ✅ Artifacts are written to filesystem (line 666)
- ✅ Artifacts are tracked in database (lines 673-703)
- ✅ Content type is properly stored
- ✅ Fetch timestamp is recorded
- ✅ Cache expiration is managed

### Testing

Added smoke test in `backend/tests/test_integrations_api.py`:
- `test_execute_integration_with_artifact_caching`: Ensures endpoint doesn't crash with new code

### Documentation

Updated `docs/design/plugin-system.md`:
- Added note about artifact caching for both endpoints
- Documented artifact storage location

## Impact

### Benefits
1. **Consistent behavior**: Both endpoints now cache artifacts
2. **Better performance**: Subsequent calls can use cached data
3. **Audit trail**: All API calls are logged to database with timestamps
4. **Backward compatible**: No breaking changes to API response format

### Breaking Changes
None. The response format remains unchanged.

### Migration Notes
No migration needed. Existing code will continue to work as before, with the added benefit of artifact caching.

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

### After (With Caching)
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
- `backend/codex/api/routes/integrations.py` - Main implementation
- `backend/codex/db/models/system.py` - IntegrationArtifact model
- `backend/tests/test_integrations_api.py` - Tests
- `docs/design/plugin-system.md` - Documentation

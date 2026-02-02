# Plugin Test Endpoint Configuration

## Overview

Integration plugins can now specify a dedicated test endpoint for connection testing instead of using a randomly selected endpoint. This makes plugin testing more predictable and reliable.

## Problem Statement

Previously, when testing an integration connection (via the `/api/v1/integrations/{integration_id}/test` endpoint), the system would use the first endpoint in the `endpoints` array. This had several issues:

1. **Unpredictable**: The first endpoint might not be the simplest or most appropriate for testing
2. **Brittle**: Reordering endpoints in the manifest would change which endpoint was used for testing
3. **Inefficient**: Complex endpoints requiring many parameters weren't ideal for quick connection tests

## Solution

Plugins can now specify a `test_endpoint` field in their integration configuration that identifies which endpoint should be used for connection testing.

## Configuration

### Manifest Structure

Add a `test_endpoint` field to your plugin's `integration` section in `manifest.yml`:

```yaml
integration:
  api_type: rest
  base_url: "https://api.example.com"
  auth_method: token
  test_endpoint: simple_endpoint_id  # Specify which endpoint to use for testing
```

### Choosing a Test Endpoint

When selecting a test endpoint, choose one that:

1. **Requires minimal parameters**: Fewer required parameters mean easier automated testing
2. **Has well-known test values**: Use endpoints that work with predictable test data
3. **Is lightweight**: Avoid endpoints that return large responses or do heavy processing
4. **Validates authentication**: Ensures the API credentials are working correctly

## Examples

### GitHub Integration

```yaml
integration:
  api_type: rest
  base_url: "https://api.github.com"
  auth_method: token
  test_endpoint: get_repo  # Uses well-known test repo (octocat/hello-world)
```

**Why `get_repo`?**
- Simple parameters (just owner and repo)
- Well-known test values exist (octocat/hello-world)
- Fast response
- Validates token authentication

### Weather API Integration

```yaml
integration:
  api_type: rest
  base_url: "https://api.openweathermap.org"
  auth_method: api_key
  test_endpoint: geocode  # Doesn't require coordinates, just city name
```

**Why `geocode`?**
- Simpler than `current_weather` (doesn't need lat/lon coordinates)
- Works with simple city names like "London"
- Validates API key
- Quick response

### Single-Endpoint Plugins

For plugins with only one endpoint, you can still specify it explicitly:

```yaml
integration:
  api_type: rest
  auth_method: none
  test_endpoint: fetch_metadata
```

## Behavior

### When test_endpoint is specified

1. The executor looks for an endpoint with the matching ID
2. If found, that endpoint is used for testing
3. If not found, an error is returned with message: "Specified test endpoint '{id}' not found"

### When test_endpoint is NOT specified

Falls back to the legacy behavior:
- Uses the first endpoint in the `endpoints` array

### Endpoint Not Found

If you specify an invalid `test_endpoint` ID, the test will fail with an error message indicating the endpoint wasn't found. This helps catch configuration errors early.

## Implementation Details

### Plugin Models

The `test_endpoint` property is available on:
- `Plugin` class (filesystem-based plugins)
- `RegisteredPlugin` class (database-stored plugins)

Both implement:
```python
@property
def test_endpoint(self) -> str | None:
    """Get the endpoint ID to use for testing connection."""
    return self.integration_config.get("test_endpoint")
```

### Integration Executor

The `test_connection()` method in `IntegrationExecutor` has been updated to:

1. Check if `test_endpoint` is specified
2. Look up the endpoint by ID if specified
3. Fall back to first endpoint if not specified
4. Return an error if the specified endpoint doesn't exist

### Protocol

The `IntegrationPluginProtocol` has been updated to include the `test_endpoint` property, ensuring both filesystem-based and database-stored plugins can use this feature.

## Testing

The feature includes comprehensive tests in `backend/tests/test_executor.py`:

1. `test_plugin_test_endpoint`: Verifies plugins load with correct test_endpoint values
2. `test_test_connection_uses_specified_endpoint`: Tests endpoint selection logic
3. `test_test_connection_invalid_test_endpoint`: Tests error handling for invalid endpoints

## Migration Guide

### Updating Existing Plugins

1. Identify the simplest endpoint in your plugin suitable for testing
2. Add `test_endpoint: <endpoint_id>` to the `integration` section
3. Test the plugin to ensure connection testing works

### Example Migration

**Before:**
```yaml
integration:
  api_type: rest
  base_url: "https://api.example.com"
  auth_method: token

endpoints:
  - id: complex_operation  # First endpoint (was used for testing)
    parameters: [...]
  - id: simple_ping        # Better for testing
    parameters: []
```

**After:**
```yaml
integration:
  api_type: rest
  base_url: "https://api.example.com"
  auth_method: token
  test_endpoint: simple_ping  # Explicitly specify test endpoint

endpoints:
  - id: complex_operation
    parameters: [...]
  - id: simple_ping
    parameters: []
```

## Best Practices

1. **Always specify a test_endpoint** for clarity and predictability
2. **Document your choice** in plugin README or comments
3. **Test the test endpoint** to ensure it works with generated test values
4. **Keep it simple** - the test endpoint should be the easiest endpoint to call
5. **Validate authentication** - ensure the test endpoint checks credentials

## Future Enhancements

Possible improvements:
- Allow specifying test parameters in the manifest
- Support multiple test endpoints for different scenarios
- Add retry logic for flaky test endpoints
- Cache test results for faster subsequent tests

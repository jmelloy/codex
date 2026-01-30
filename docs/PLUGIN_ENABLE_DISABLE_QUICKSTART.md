# Plugin Enable/Disable - Quick Start Guide

## Overview

Codex now supports hierarchical plugin configuration at three levels:
- **Global**: Plugin registry (all installations)
- **Workspace**: Per-workspace overrides
- **Notebook**: Per-notebook overrides (highest priority)

## Quick Examples

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000"
headers = {"Authorization": f"Bearer {token}"}

# 1. Disable plugin for entire workspace
response = requests.put(
    f"{BASE_URL}/api/v1/integrations/github/enable?workspace_id=1",
    json={"enabled": False},
    headers=headers,
)

# 2. Override for specific notebook (enable despite workspace disabled)
response = requests.put(
    f"{BASE_URL}/api/v1/notebooks/5/plugins/github",
    json={
        "enabled": True,
        "config": {
            "api_key": "your-key",
            "repository": "owner/repo"
        }
    },
    headers=headers,
)

# 3. Check current config for a notebook
response = requests.get(
    f"{BASE_URL}/api/v1/notebooks/5/plugins/github",
    headers=headers,
)
config = response.json()
print(f"Enabled: {config['enabled']}")
print(f"Config: {config['config']}")

# 4. Revert to workspace defaults
response = requests.delete(
    f"{BASE_URL}/api/v1/notebooks/5/plugins/github",
    headers=headers,
)
```

### cURL Examples

```bash
# Get auth token
TOKEN=$(curl -X POST "http://localhost:8000/api/token" \
  -d "username=user&password=pass" | jq -r '.access_token')

# Disable plugin at workspace level
curl -X PUT "http://localhost:8000/api/v1/integrations/github/enable?workspace_id=1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Configure plugin for specific notebook
curl -X PUT "http://localhost:8000/api/v1/notebooks/5/plugins/github" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "config": {
      "api_key": "your-key",
      "repository": "owner/repo"
    }
  }'

# List all plugin configs for a notebook
curl "http://localhost:8000/api/v1/notebooks/5/plugins" \
  -H "Authorization: Bearer $TOKEN"

# Delete notebook config (revert to defaults)
curl -X DELETE "http://localhost:8000/api/v1/notebooks/5/plugins/github" \
  -H "Authorization: Bearer $TOKEN"
```

## Common Use Cases

### Use Case 1: Disable Plugin Workspace-Wide, Enable for One Notebook

```python
# Scenario: You want GitHub integration disabled for most notebooks,
# but enabled for a specific development notebook

# Step 1: Disable for workspace
requests.put(
    f"{BASE_URL}/api/v1/integrations/github/enable?workspace_id=1",
    json={"enabled": False},
    headers=headers,
)

# Step 2: Enable for development notebook
requests.put(
    f"{BASE_URL}/api/v1/notebooks/dev_notebook_id/plugins/github",
    json={"enabled": True, "config": {"repository": "myorg/myrepo"}},
    headers=headers,
)

# Result:
# - All notebooks in workspace: GitHub disabled
# - dev_notebook_id: GitHub enabled with custom config
```

### Use Case 2: Different API Keys per Notebook

```python
# Scenario: Multiple notebooks using same plugin but different API keys

notebooks = [
    {"id": 1, "name": "Production", "key": "prod-key-123"},
    {"id": 2, "name": "Staging", "key": "staging-key-456"},
    {"id": 3, "name": "Development", "key": "dev-key-789"},
]

for notebook in notebooks:
    requests.put(
        f"{BASE_URL}/api/v1/notebooks/{notebook['id']}/plugins/openai",
        json={
            "enabled": True,
            "config": {"api_key": notebook["key"]}
        },
        headers=headers,
    )
```

### Use Case 3: Temporarily Disable Plugin for Testing

```python
# Disable plugin for a notebook
response = requests.put(
    f"{BASE_URL}/api/v1/notebooks/5/plugins/analytics",
    json={"enabled": False},
    headers=headers,
)

# ... do testing ...

# Re-enable plugin
response = requests.put(
    f"{BASE_URL}/api/v1/notebooks/5/plugins/analytics",
    json={"enabled": True},
    headers=headers,
)
```

### Use Case 4: Clean Reset to Defaults

```python
# Get list of all configured plugins
response = requests.get(
    f"{BASE_URL}/api/v1/notebooks/5/plugins",
    headers=headers,
)
plugins = response.json()

# Delete all notebook-specific configs (revert to workspace defaults)
for plugin_config in plugins:
    plugin_id = plugin_config["plugin_id"]
    requests.delete(
        f"{BASE_URL}/api/v1/notebooks/5/plugins/{plugin_id}",
        headers=headers,
    )
```

## Configuration Priority

Remember the hierarchy:
```
Notebook Config (highest priority)
    ↓
Workspace Config
    ↓
Global Plugin Setting (lowest priority)
```

**Example:**
- Global: `enabled=True`
- Workspace: `enabled=False`
- Notebook: `enabled=True`

**Result:** Plugin is **enabled** for that notebook because notebook config has highest priority.

## Testing Your Configuration

```python
def check_plugin_status(notebook_id, plugin_id, headers):
    """Check if plugin is enabled for a notebook."""
    response = requests.get(
        f"{BASE_URL}/api/v1/notebooks/{notebook_id}/plugins/{plugin_id}",
        headers=headers,
    )
    config = response.json()
    return config["enabled"]

# Check status
is_enabled = check_plugin_status(5, "github", headers)
print(f"GitHub plugin is {'enabled' if is_enabled else 'disabled'}")
```

## Migration Notes

If you have existing plugin configurations:
- They will continue to work
- New `enabled` field defaults to `True`
- No action required unless you want to disable specific plugins

## Best Practices

1. **Use workspace-level for general policies**
   - Disable plugins you don't want most notebooks to use
   - Set default configurations

2. **Use notebook-level for exceptions**
   - Override workspace settings for specific use cases
   - Store sensitive credentials per-notebook

3. **Document your configuration**
   - Keep track of which notebooks have custom configs
   - Use descriptive config values

4. **Test before deploying**
   - Verify plugin behavior with different enabled states
   - Check that disabling doesn't break existing workflows

## Troubleshooting

### Plugin Not Working Despite Being Enabled

1. Check all three levels:
   ```python
   # Check global (not exposed in API yet, check database)
   # Check workspace
   response = requests.get(
       f"{BASE_URL}/api/v1/integrations?workspace_id=1",
       headers=headers,
   )
   
   # Check notebook
   response = requests.get(
       f"{BASE_URL}/api/v1/notebooks/5/plugins/{plugin_id}",
       headers=headers,
   )
   ```

2. Verify configuration is valid:
   ```python
   config = requests.get(...).json()
   print(f"Enabled: {config['enabled']}")
   print(f"Config: {config['config']}")
   ```

### Can't Access Plugin Endpoints

- Verify you're authenticated: include `Authorization: Bearer {token}` header
- Check you have permission to the workspace/notebook
- Verify the notebook/plugin exists

## Support

For issues or questions:
- Check the full API documentation: `docs/PLUGIN_ENABLE_DISABLE_API.md`
- Run tests: `pytest tests/test_plugin_*.py`
- Check logs for error details

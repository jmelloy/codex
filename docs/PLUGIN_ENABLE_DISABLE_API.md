# Plugin Enable/Disable API Documentation

## Overview

The Codex plugin system supports hierarchical configuration at three levels:
1. **Global**: `Plugin.enabled` field (managed in plugin registry)
2. **Workspace-level**: `PluginConfig.enabled` field (overrides global)
3. **Notebook-level**: `NotebookPluginConfig.enabled` field (overrides workspace)

This allows fine-grained control over which plugins are active in different contexts.

## Database Schema

### PluginConfig (Workspace-level)
```sql
CREATE TABLE plugin_configs (
    id INTEGER PRIMARY KEY,
    workspace_id INTEGER NOT NULL,
    plugin_id VARCHAR NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,  -- NEW: workspace-level enable/disable
    config JSON NOT NULL DEFAULT '{}',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
);
```

### NotebookPluginConfig (Notebook-level)
```sql
CREATE TABLE notebook_plugin_configs (
    id INTEGER PRIMARY KEY,
    notebook_id INTEGER NOT NULL,
    plugin_id VARCHAR NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,  -- Notebook-level enable/disable
    config JSON NOT NULL DEFAULT '{}',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id),
    FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
);
```

## Workspace-Level Plugin Management

### List Integrations with Workspace Status
Get all available integrations with their enabled status for a specific workspace.

```http
GET /api/v1/integrations?workspace_id={workspace_id}
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": "github",
    "name": "GitHub Integration",
    "description": "Integration with GitHub API",
    "version": "1.0.0",
    "author": "Codex Team",
    "api_type": "rest",
    "base_url": "https://api.github.com",
    "auth_method": "token",
    "enabled": true
  }
]
```

### Enable/Disable Plugin at Workspace Level
Enable or disable a plugin for a specific workspace.

```http
PUT /api/v1/integrations/{plugin_id}/enable?workspace_id={workspace_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "enabled": false
}
```

**Response:**
```json
{
  "id": "github",
  "name": "GitHub Integration",
  "description": "Integration with GitHub API",
  "version": "1.0.0",
  "author": "Codex Team",
  "api_type": "rest",
  "base_url": "https://api.github.com",
  "auth_method": "token",
  "enabled": false
}
```

## Notebook-Level Plugin Management

### List All Notebook Plugin Configurations
Get all plugin configurations for a specific notebook.

```http
GET /api/v1/notebooks/{notebook_id}/plugins
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "plugin_id": "github",
    "enabled": false,
    "config": {
      "api_key": "...",
      "repository": "owner/repo"
    },
    "created_at": "2026-01-30T19:00:00.000000",
    "updated_at": "2026-01-30T19:00:00.000000"
  }
]
```

### Get Specific Plugin Configuration
Get configuration for a specific plugin in a notebook. Returns defaults if no configuration exists.

```http
GET /api/v1/notebooks/{notebook_id}/plugins/{plugin_id}
Authorization: Bearer {token}
```

**Response (with custom config):**
```json
{
  "plugin_id": "github",
  "enabled": false,
  "config": {
    "api_key": "...",
    "repository": "owner/repo"
  },
  "created_at": "2026-01-30T19:00:00.000000",
  "updated_at": "2026-01-30T19:00:00.000000"
}
```

**Response (no config - defaults):**
```json
{
  "plugin_id": "github",
  "enabled": true,
  "config": {}
}
```

### Create/Update Plugin Configuration
Create or update plugin configuration for a notebook. Supports partial updates.

```http
PUT /api/v1/notebooks/{notebook_id}/plugins/{plugin_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "enabled": false,
  "config": {
    "api_key": "sk-...",
    "repository": "owner/repo"
  }
}
```

**Partial Update (only enabled):**
```json
{
  "enabled": false
}
```

**Partial Update (only config):**
```json
{
  "config": {
    "api_key": "sk-..."
  }
}
```

**Response:**
```json
{
  "plugin_id": "github",
  "enabled": false,
  "config": {
    "api_key": "sk-...",
    "repository": "owner/repo"
  },
  "created_at": "2026-01-30T19:00:00.000000",
  "updated_at": "2026-01-30T19:30:00.000000"
}
```

### Delete Plugin Configuration
Delete notebook-specific configuration, reverting to workspace defaults.

```http
DELETE /api/v1/notebooks/{notebook_id}/plugins/{plugin_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "message": "Plugin configuration deleted successfully"
}
```

## Configuration Hierarchy

When determining if a plugin is enabled and what configuration to use:

1. **Check notebook-level config** (`NotebookPluginConfig`)
   - If exists and has `enabled=False`, plugin is disabled
   - If exists and has `enabled=True`, plugin is enabled with notebook config
   
2. **Check workspace-level config** (`PluginConfig`)
   - If no notebook config, use workspace-level enabled status
   - Workspace config also applies when notebook has no override
   
3. **Check global plugin status** (`Plugin.enabled`)
   - If no workspace config, use global enabled status
   - Default is `True` if not configured

### Example Scenarios

**Scenario 1: Plugin disabled at workspace, enabled for specific notebook**
```
Global: enabled=True
Workspace: enabled=False
Notebook: enabled=True
Result: Plugin is ENABLED for this notebook
```

**Scenario 2: Plugin enabled at workspace, disabled for specific notebook**
```
Global: enabled=True
Workspace: enabled=True
Notebook: enabled=False
Result: Plugin is DISABLED for this notebook
```

**Scenario 3: No notebook-specific config**
```
Global: enabled=True
Workspace: enabled=False
Notebook: (no config)
Result: Plugin is DISABLED (inherits workspace setting)
```

## Use Cases

### 1. Disable Plugin for Entire Workspace
```bash
curl -X PUT "http://localhost:8000/api/v1/integrations/github/enable?workspace_id=1" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### 2. Enable Plugin for Specific Notebook (Override Workspace)
```bash
curl -X PUT "http://localhost:8000/api/v1/notebooks/5/plugins/github" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "config": {"repository": "my/repo"}}'
```

### 3. Revert Notebook to Workspace Defaults
```bash
curl -X DELETE "http://localhost:8000/api/v1/notebooks/5/plugins/github" \
  -H "Authorization: Bearer {token}"
```

## Testing

Run the test suite:
```bash
cd backend
pytest tests/test_plugin_enable_disable.py -v  # Model tests
pytest tests/test_plugin_api.py -v              # API tests
```

Manual testing script:
```bash
cd backend
python /tmp/test_plugin_manual.py
```

## Migration

The database migration `20260130_000000_004_add_plugin_enable_disable.py` adds:
- `enabled` column to `plugin_configs` table (default: `True`)
- New `notebook_plugin_configs` table with full schema

Migration runs automatically on application startup.

## Error Handling

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "detail": "Notebook not found"
}
```
or
```json
{
  "detail": "Integration not found"
}
```

## Security Considerations

1. **Authentication Required**: All endpoints require valid JWT token
2. **Authorization**: Users can only access notebooks in their owned workspaces
3. **Input Validation**: All inputs are validated via Pydantic models
4. **SQL Injection Prevention**: Using SQLModel ORM with parameterized queries

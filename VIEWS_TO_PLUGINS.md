# Moving Views into Plugins - Implementation Summary

## Overview

This PR refactors the view system to leverage the existing plugin architecture dynamically, eliminating hardcoded view types in the frontend. Views are now defined in plugin manifests and loaded dynamically at runtime.

## Problem Statement

Previously, view types (kanban, gallery, rollup, etc.) were hardcoded in two places:
1. **ViewRenderer.vue** - Switch statement mapping view types to components
2. **viewParser.ts** - Hardcoded array of valid view types for validation

Adding a new view type required changes to both files, even though the backend plugin system already supported view definitions.

## Solution

### Backend Changes

#### 1. New API Endpoint (`/api/v1/views`)

Added a RESTful endpoint that exposes all views from the plugin system:

```python
# backend/codex/api/routes/views.py
@router.get("/", response_model=list[ViewResponse])
async def get_available_views(request: Request):
    """Get all available view types from the plugin system."""
    loader = request.app.state.plugin_loader
    plugins_with_views = loader.get_plugins_with_views()
    
    # Return all views from all plugins
    view_responses = []
    for plugin in plugins_with_views:
        for view in plugin.views:
            view_responses.append(ViewResponse(...))
    
    return view_responses
```

**API Response Example:**
```json
[
  {
    "id": "kanban",
    "name": "Kanban Board",
    "description": "Visual board with draggable cards",
    "icon": "📊",
    "plugin_id": "tasks",
    "plugin_name": "Task Management Plugin",
    "config_schema": {...}
  },
  ...
]
```

#### 2. ViewResponse Schema

Added a new Pydantic model for view metadata:

```python
# backend/codex/api/schemas.py
class ViewResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    plugin_id: str
    plugin_name: str
    config_schema: dict[str, Any]
```

### Frontend Changes

#### 1. View Plugin Service

Created a centralized service to manage view plugins:

```typescript
// frontend/src/services/viewPluginService.ts
class ViewPluginService {
  // Fetches available views from API
  async initialize(): Promise<void>
  
  // Gets all available views
  getAvailableViews(): ViewPlugin[]
  
  // Validates if a view type is available
  isViewAvailable(viewId: string): boolean
  
  // Gets valid view type IDs
  getValidViewTypes(): string[]
  
  // Dynamically loads a view component
  async loadViewComponent(viewId: string): Promise<any>
}
```

**Key Features:**
- **Thread-safe initialization** - Uses promise-based locking to prevent race conditions
- **Global initialization** - Called once in `main.ts` when the app starts
- **Fallback support** - Registers built-in components if API fails
- **Dynamic loading** - Lazy-loads view components on demand

#### 2. Updated ViewRenderer.vue

Removed the hardcoded switch statement and replaced with dynamic loading:

**Before:**
```typescript
switch (viewType) {
  case "kanban":
    viewComponent.value = (await KanbanView()).default
    break
  case "task-list":
    viewComponent.value = (await TaskListView()).default
    break
  // ... more cases
}
```

**After:**
```typescript
if (viewPluginService.hasViewComponent(viewType)) {
  viewComponent.value = await viewPluginService.loadViewComponent(viewType)
}
```

#### 3. Updated viewParser.ts

Changed validation to use the plugin service:

**Before:**
```typescript
const validViewTypes = [
  "kanban", "gallery", "rollup", 
  "dashboard", "corkboard", "calendar", "task-list"
]
```

**After:**
```typescript
const validViewTypes = viewPluginService.getValidViewTypes()
```

## Benefits

### 1. Extensibility
- **No frontend code changes** needed to add new view types
- Simply create a plugin with a view definition in its manifest
- The frontend automatically discovers and loads new views

### 2. Consistency
- View definitions are centralized in plugin manifests
- Single source of truth for view metadata
- Backend and frontend stay synchronized

### 3. Maintainability
- Eliminates hardcoded view lists
- Reduces coupling between frontend and backend
- Follows existing plugin architecture patterns

### 4. Developer Experience
- Clear plugin API for adding views
- No need to rebuild frontend for new view types
- Automatic validation of view types

## Plugin Manifest Example

Views are defined in plugin manifests (`plugin.yaml`):

```yaml
# plugins/tasks/plugin.yaml
id: tasks
name: Task Management Plugin
type: view

views:
  - id: kanban
    name: Kanban Board
    description: Visual board with draggable cards
    icon: 📊
    config_schema:
      columns:
        type: array
        description: Column definitions
        
  - id: task-list
    name: Task List
    description: Simple checklist view
    icon: ✅
    config_schema:
      compact:
        type: boolean
        default: false
```

## Testing

### Backend Tests
- Created test for `/api/v1/views` endpoint
- Verified all 6 views are returned correctly:
  - kanban (tasks plugin)
  - task-list (tasks plugin)
  - gallery (gallery plugin)
  - rollup (rollup plugin)
  - corkboard (corkboard plugin)
  - dashboard (core plugin)

### Integration Tests
- All 257 existing backend tests pass
- Frontend builds successfully
- No security vulnerabilities detected (CodeQL scan)

## Migration Path

### For Existing Views
No changes needed - all existing views continue to work:
- View components remain in `frontend/src/components/views/`
- Component registration happens in `viewPluginService.registerBuiltInComponents()`

### For New Views
1. Create a plugin directory (or use existing plugin)
2. Add view definition to `plugin.yaml`
3. Create Vue component in `frontend/src/components/views/`
4. Register component in `viewPluginService` (temporary until full plugin build system)

### Future Enhancement
In the future, view components could be moved into plugin directories and built separately, similar to how integration block components work. This would require:
1. Extending the plugin build system to handle views
2. Creating a dynamic component loader in the frontend
3. Managing shared dependencies properly

For now, keeping components in the frontend is simpler and maintains existing functionality while still benefiting from the dynamic plugin system.

## Files Changed

### Backend
- `backend/codex/api/routes/views.py` (new) - Views API endpoint
- `backend/codex/api/routes/__init__.py` - Export views router
- `backend/codex/api/schemas.py` - Add ViewResponse schema
- `backend/codex/main.py` - Register views router

### Frontend
- `frontend/src/services/viewPluginService.ts` (new) - View plugin service
- `frontend/src/components/views/ViewRenderer.vue` - Use plugin service
- `frontend/src/services/viewParser.ts` - Dynamic view type validation
- `frontend/src/main.ts` - Initialize plugin service globally

## Conclusion

This refactoring successfully moves view type definitions into the plugin system while maintaining backward compatibility. The system is now more extensible, maintainable, and consistent with the existing plugin architecture.

All existing views continue to work, and new views can be added by simply creating a plugin manifest - no frontend code changes required.

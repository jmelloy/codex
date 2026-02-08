# Dynamic Views Design Document

**Version:** 1.1 | **Date:** 2026-01-24 | **Status:** Implemented (v1)

## Overview

Dynamic Views enable documents that execute queries, aggregate content, and render interactive visualizations at render-time. Unlike static markdown, they display live data from the workspace through plugin-provided view components.

## Goals

1. **Query & Aggregate**: Query files across notebooks by metadata, tags, dates, content
2. **Dynamic Rendering**: Support specialized views through plugins (kanban, gallery, dashboards, etc.)
3. **Composability**: Embed mini-views within dashboards
4. **Interactivity**: Enable editing through views (e.g., task status updates)
5. **Extensibility**: Plugin-based framework for custom view types

## Architecture

### Component Stack
```
┌─────────────────────────────────┐
│   Plugin View Components        │
│   (Loaded from plugins/)        │
│   - KanbanView                  │
│   - GalleryView                 │
│   - TaskListView                │
│   - RollupView                  │
│   - CorkboardView               │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   ViewRenderer.vue              │
│   - Parse .cdx files            │
│   - Load plugin components      │
│   - Execute queries             │
│   - Handle interactions         │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   Query Service API             │
│   (/api/v1/query/)             │
│   - Advanced file filtering     │
│   - Tag-based queries           │
│   - Property matching           │
└─────────────────────────────────┘
```

## View Definition Format

Views are stored as `.cdx` files with YAML frontmatter:

```yaml
---
type: view
view_type: kanban
title: Project Tasks
query:
  tags: [task, todo]
  properties:
    status: [todo, in-progress, done]
config:
  columns:
    - id: todo
      title: To Do
      filter: { status: todo }
  editable: true
---
# Optional markdown content
```

## Implemented View Types

### 1. Kanban Board (tasks plugin)
- **Purpose**: Task management, project tracking
- **Features**: Drag-and-drop cards, status updates, filtering
- **Component**: `plugins/tasks/components/KanbanView.vue`
- **Config**: Column definitions, card fields, drag-drop settings

### 2. Task List (tasks plugin)
- **Purpose**: Simple checklist view
- **Features**: Task completion, compact mode, sorting
- **Component**: `plugins/tasks/components/TaskListView.vue`
- **Config**: Display mode, editable checkboxes, sort options

### 3. Gallery View (gallery plugin)
- **Purpose**: Image collections, screenshots, diagrams
- **Features**: Grid/masonry layout, lightbox viewer, metadata display
- **Component**: `plugins/gallery/components/GalleryView.vue`
- **Config**: Layout style, column count, thumbnail size

### 4. Rollup/Dashboard (rollup plugin)
- **Purpose**: Aggregate summaries, reports, multiple data sources
- **Features**: Multiple mini-views, statistics, sections
- **Component**: `plugins/rollup/components/` (various dashboard components)
- **Config**: Section definitions, mini-view configurations

### 5. Corkboard (corkboard plugin)
- **Purpose**: Visual pinboard for notes and ideas
- **Features**: Free-form layout, positioning, visual organization
- **Component**: `plugins/corkboard/components/`
- **Config**: Layout settings, card appearance

## Implementation

### Frontend Components

**Main Component**: `frontend/src/components/views/ViewRenderer.vue`

The ViewRenderer is the core component that:
- Loads and parses .cdx file content
- Extracts view definition from YAML frontmatter
- Dynamically loads view components from plugins via `viewPluginService`
- Executes queries through the query service
- Handles view updates and interactions

**Additional Components**:
- `DashboardView.vue` - Dashboard container for multiple mini-views
- `MiniViewContainer.vue` - Wrapper for embedded mini-views

### Plugin System Integration

View components are provided by plugins in the `/plugins` directory:

```
plugins/
├── tasks/
│   ├── components/
│   │   ├── KanbanView.vue
│   │   └── TaskListView.vue
│   └── manifest.yml
├── gallery/
│   ├── components/
│   │   └── GalleryView.vue
│   └── manifest.yml
├── rollup/
│   └── components/ (dashboard components)
└── corkboard/
    └── components/ (corkboard components)
```

Plugins are registered with the backend via `/api/v1/plugins/register` and loaded dynamically at runtime.

### Backend API

**Endpoints**:
- `POST /api/v1/query/execute` - Execute view queries with filters
- `GET /api/v1/files/{id}` - Get file content (including .cdx files)
- `PUT /api/v1/files/{id}` - Update file metadata (for interactive views)
- `GET /api/v1/plugins/` - List registered plugins and their view types

**Query Language**:
The query service supports:
```python
{
  "tags": ["task"],           # Filter by tags
  "properties": {             # Filter by metadata properties
    "status": "todo"
  },
  "date_range": {             # Date-based filtering
    "after": "2026-01-01"
  },
  "content_search": "text",   # Full-text search
  "sort": "created_at desc",  # Sorting
  "limit": 50                 # Result limiting
}
```

### View Plugin Service

**Location**: `frontend/src/services/viewPluginService.ts`

The view plugin service:
- Initializes and registers plugin-provided view components
- Dynamically imports components using Vite's `import.meta.glob`
- Maps view_type strings to Vue components
- Validates view types against registered plugins

## Security

- Views execute with user permissions only
- Query results filtered by workspace/notebook access
- No arbitrary code execution in view definitions
- View definitions validated against schema
- Plugin components sandboxed in Vue component context

## Future Enhancements

- Calendar view plugin (date-based visualization)
- Table view plugin (sortable data grids)
- Real-time updates via WebSocket for collaborative editing
- View composition with nested sub-views
- Export views to static HTML/PDF
- Custom query aggregation functions
- View sharing and permissions

## Migration Path

Existing markdown files remain unchanged. Users opt-in to dynamic views by creating `.cdx` files with view definitions. The `.cdx` extension is registered with the system to trigger view rendering instead of markdown rendering.

---

For implementation details, see:
- `frontend/src/components/views/ViewRenderer.vue` - Main view renderer
- `frontend/src/services/viewPluginService.ts` - Plugin loading
- `frontend/src/services/queryService.ts` - Query execution
- `backend/codex/api/routes/query.py` - Query API
- `plugins/*/components/*.vue` - View component implementations

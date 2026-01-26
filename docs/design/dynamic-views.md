# Dynamic Views Design Document

**Version:** 1.1 | **Date:** 2026-01-24 | **Status:** Implemented (v1)

## Overview

Dynamic Views enable documents that execute queries, aggregate content, and render interactive visualizations at render-time. Unlike static markdown, they display live data from the workspace.

## Goals

1. **Query & Aggregate**: Query files across notebooks by metadata, tags, dates, content
2. **Dynamic Rendering**: Support specialized views (kanban, gallery, calendar)
3. **Composability**: Embed mini-views within dashboards
4. **Interactivity**: Enable editing through views (e.g., task status)
5. **Extensibility**: Framework for custom view types

## Architecture

### Component Stack
```
┌─────────────────────────────────┐
│   Frontend View Components      │
│   (Kanban, Gallery, Rollup)    │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   View Runtime Engine           │
│   - Parse .cdx files            │
│   - Execute queries             │
│   - Render components           │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   Query & Aggregation API       │
│   - Advanced file filtering     │
│   - Tag-based queries           │
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

## Supported View Types

### 1. Kanban Board
- **Purpose**: Task management, project tracking
- **Features**: Drag-and-drop, status updates, filtering
- **Query**: Files with `status` property

### 2. Gallery View
- **Purpose**: Image collections, screenshots, diagrams
- **Features**: Grid layout, lightbox, filtering by tags
- **Query**: Files matching image extensions

### 3. Rollup/Dashboard
- **Purpose**: Aggregate summaries, reports
- **Features**: Multiple mini-views, statistics
- **Query**: Multiple queries with aggregation

### 4. Calendar View
- **Purpose**: Time-based entries, experiments
- **Features**: Month/week/day views, date filtering
- **Query**: Files with date metadata

### 5. Table View
- **Purpose**: Structured data display
- **Features**: Sortable columns, filtering
- **Query**: Files with structured properties

## Implementation

### Frontend Components

**Location**: `frontend/src/components/views/`

- `ViewRenderer.vue` - Main component, routes to specific view types
- `KanbanView.vue` - Kanban board implementation
- `GalleryView.vue` - Gallery grid and lightbox
- `RollupView.vue` - Dashboard with multiple sections
- `CalendarView.vue` - Calendar grid with date selection
- `TableView.vue` - Sortable data table

### Backend API

**Endpoints**:
- `GET /api/v1/views/` - List all views in workspace
- `GET /api/v1/views/{id}` - Get view definition
- `POST /api/v1/views/{id}/query` - Execute view query
- `PUT /api/v1/views/{id}/update` - Update item through view

**Query Language**:
```python
{
  "tags": ["task"],
  "properties": {"status": "todo"},
  "date_range": {"after": "2026-01-01"},
  "content_search": "experiment",
  "sort": "created_at desc",
  "limit": 50
}
```

### Database Schema

**New Tables**:
- `views` - View definitions and metadata
- `view_queries` - Cached query results

## Query System

### Filter Operations
- Tag matching (AND/OR)
- Property filters (exact, range, exists)
- Date range filtering
- Full-text content search
- Notebook scoping

### Aggregation Functions
- Count, sum, average, min, max
- Group by property/tag
- Date-based grouping

## Security

- Views execute with user permissions
- Query results filtered by notebook access
- No arbitrary code execution
- Validated view definitions

## Future Enhancements

- Custom view templates
- View sharing between users
- Real-time updates via WebSocket
- Export views to static HTML
- View composition (nested views)
- Custom aggregation functions

## Migration Path

Existing markdown files remain unchanged. Users opt-in by creating `.cdx` files.

---

For implementation details, see source code in `frontend/src/components/views/` and `backend/api/routes/views.py`.

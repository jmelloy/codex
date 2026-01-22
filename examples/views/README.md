# Dynamic View Examples

This directory contains example `.cdx` (Codex Dynamic View) files demonstrating various view types and use cases.

## Available Examples

### 1. Kanban Board (`kanban-board.cdx`)
A project task board with drag-and-drop functionality.
- **View Type**: kanban
- **Features**: Multi-column layout, drag-and-drop status updates
- **Use Case**: Project management, sprint planning

### 2. Task List (`task-list-today.cdx`)
Compact task list showing today's tasks.
- **View Type**: task-list
- **Features**: Checkbox completion, priority sorting
- **Use Case**: Daily task management, mini-views

### 3. Weekly Rollup (`weekly-rollup.cdx`)
Activity report grouped by day.
- **View Type**: rollup
- **Features**: Date grouping, statistics, categorized sections
- **Use Case**: Weekly reviews, activity tracking

### 4. Photo Gallery (`photo-gallery.cdx`)
Image gallery with lightbox.
- **View Type**: gallery
- **Features**: Grid layout, lightbox viewer, metadata display
- **Use Case**: Photo libraries, image collections

### 5. Novel Outline (`novel-outline.cdx`)
Visual corkboard for novel scenes and chapters.
- **View Type**: corkboard
- **Features**: Swimlane layout, notecard styling
- **Use Case**: Creative writing, story planning

### 6. Home Dashboard (`home-dashboard.cdx`)
Composite dashboard with embedded mini-views.
- **View Type**: dashboard
- **Features**: Grid layout, embedded views
- **Use Case**: Personal dashboard, command center

## View Types

| Type | Description | Key Features |
|------|-------------|--------------|
| `kanban` | Kanban board with columns | Drag-drop, status filters |
| `task-list` | Simple task list | Compact mode, checkboxes |
| `rollup` | Date-grouped report | Statistics, sections |
| `gallery` | Image gallery | Lightbox, grid layout |
| `corkboard` | Visual canvas | Free-form, swimlanes |
| `dashboard` | Composite layout | Embedded mini-views |

## Query Syntax

Views use a declarative query syntax to filter files:

```yaml
query:
  # Scope
  notebook_ids: [1, 2]
  paths: ["folder/**/*.md"]

  # Filtering
  tags: [task, urgent]
  file_types: [markdown]

  # Properties
  properties:
    status: todo
    priority: [high, critical]

  # Dates
  created_after: "{{ startOfWeek }}"
  date_property: due_date
  date_before: "{{ today }}"

  # Sorting
  sort: created_at desc
  limit: 50
```

## Template Variables

Use template variables for dynamic date queries:

- `{{ today }}` - Current date/time
- `{{ todayStart }}` - Start of today (00:00)
- `{{ todayEnd }}` - End of today (23:59)
- `{{ startOfWeek }}` - Start of current week (Sunday)
- `{{ endOfWeek }}` - End of current week (Saturday)
- `{{ startOfMonth }}` - Start of current month
- `{{ endOfMonth }}` - End of current month

## Creating Custom Views

1. Create a new `.cdx` file
2. Add YAML frontmatter with view definition
3. Configure query and view-specific settings
4. Add optional markdown content below frontmatter

Example:

```yaml
---
type: view
view_type: kanban
title: My Custom Board
query:
  tags: [task]
config:
  columns:
    - id: todo
      title: To Do
      filter: { status: todo }
---

# My Custom Board

Description and instructions go here.
```

## Best Practices

1. **Use descriptive titles** - Makes views easy to find
2. **Add descriptions** - Explain what the view shows
3. **Keep queries focused** - Filter for specific content
4. **Use template variables** - For dynamic date ranges
5. **Document custom properties** - List expected frontmatter fields

## Learn More

See the full design document at `/docs/design/dynamic-views.md` for detailed information about:
- Query API reference
- View type specifications
- Property validation
- Advanced features

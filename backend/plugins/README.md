# Codex Plugins

This directory contains plugins for Codex. Plugins extend functionality through three types:

1. **Views** (`plugins/views/`) - Custom view components with templates and examples
2. **Themes** (`plugins/themes/`) - Visual styling with CSS
3. **Integrations** (`plugins/integrations/`) - External API connections

## Built-in View Plugins

Codex includes several built-in view plugins:

### Task Management (`plugins/views/tasks/`)

Task management with Kanban boards and task lists.

- **Views**: Kanban Board, Task List
- **Templates**: Task Board, Task List, Todo Item
- **Examples**: Project task board, today's tasks
- **Custom Properties**: status, priority, due_date, assignee, estimated_hours

### Photo Gallery (`plugins/views/gallery/`)

Image galleries with grid layouts and lightbox viewing.

- **Views**: Gallery
- **Templates**: Photo Gallery
- **Examples**: Workspace photo gallery
- **Layouts**: Grid, masonry

### Core Views (`plugins/views/core/`)

Essential note templates and dashboard views.

- **Views**: Dashboard
- **Templates**: Blank Note, Daily Journal, Meeting Notes, Project Document, Data File
- **Examples**: Home dashboard
- **Features**: Date patterns, structured sections

### Rollup Views (`plugins/views/rollup/`)

Time-based activity rollups and reports.

- **Views**: Rollup
- **Templates**: Weekly Rollup
- **Examples**: Weekly activity report
- **Features**: Date grouping, statistics, categorized sections

### Corkboard (`plugins/views/corkboard/`)

Visual canvas for creative writing and planning.

- **Views**: Corkboard
- **Templates**: None (use examples as starting point)
- **Examples**: Novel outline
- **Features**: Swimlanes, drag-and-drop, notecard styling

## Built-in Themes

Codex includes four built-in themes:

### Light Themes

- **Cream** (`themes/cream/`) - Classic notebook with cream pages (default)
- **Manila** (`themes/manila/`) - Vintage manila folder aesthetic
- **White** (`themes/white/`) - Clean white pages

### Dark Themes

- **Blueprint** (`themes/blueprint/`) - Dark mode with blueprint styling

## Plugin Structure

Each plugin type has a specific structure:

### View Plugin Structure

```
views/
  <plugin-id>/
    plugin.yaml         # Plugin manifest
    views/              # Vue components (optional)
      ViewComponent.vue
    templates/          # Template definitions
      template1.yaml
      template2.yaml
    examples/           # Example files
      example1.cdx
      example2.cdx
    README.md           # Plugin documentation
```

### View Plugin Manifest (`plugin.yaml`)

```yaml
# Plugin Metadata
id: plugin-id
name: Plugin Name
version: 1.0.0
author: Author Name
description: Plugin description
license: MIT

# Plugin Type
type: view

# Codex Compatibility
codex_version: ">=1.0.0"
api_version: 1

# View Types
views:
  - id: view-id
    name: View Name
    description: View description
    icon: 📊
    config_schema:
      # JSON schema for view configuration

# Templates
templates:
  - id: template-id
    name: Template Name
    file: templates/template.yaml
    description: Template description
    icon: 📋
    default_name: filename.cdx

# Example Files
examples:
  - name: Example Name
    file: examples/example.cdx
    description: Example description
```

### Theme Plugin Structure

```
themes/
  <theme-id>/
    theme.yaml          # Theme manifest
    styles/
      main.css         # Main stylesheet
    README.md          # Optional documentation
```

### Theme Manifest (`theme.yaml`)

```yaml
# Theme Metadata
id: theme-id
name: Theme Name
version: 1.0.0
author: Author Name
description: Theme description
license: MIT

# Theme Type
type: theme

# Codex Compatibility
codex_version: ">=1.0.0"

# Theme Configuration
theme:
  display_name: Display Name
  category: light  # or 'dark'
  className: theme-class-name
  stylesheet: styles/main.css

# Color Palette
colors:
  bg-primary: "#ffffff"
  text-primary: "#000000"
  accent-primary: "#667eea"
```

## Using the Plugin Loader

```python
from pathlib import Path
from codex.plugins.loader import PluginLoader

# Initialize loader
plugins_dir = Path("plugins")
loader = PluginLoader(plugins_dir)

# Discover all plugins
discovered = loader.discover_plugins()

# Load all plugins
plugins = loader.load_all_plugins()

# Get a specific plugin
theme = loader.get_plugin("cream")
print(f"Theme: {theme.display_name}")
print(f"CSS Class: {theme.class_name}")

# Get all themes
themes = loader.get_plugins_by_type("theme")
```

## Creating Custom Themes

1. Create a new directory in `plugins/themes/<your-theme-id>/`
2. Create `theme.yaml` with required fields
3. Create `styles/main.css` with your styles
4. Use CSS class `.theme-<your-theme-id>` for theme-specific styling
5. Test with the plugin loader

Example CSS structure:

```css
/* Your theme CSS */
.theme-your-theme-id {
  --notebook-bg: #f0f0f0;
  --notebook-text: #333333;
  --color-primary: #4a90e2;
  
  background-color: var(--notebook-bg);
  color: var(--notebook-text);
}

/* Component overrides */
.theme-your-theme-id .notebook-sidebar {
  background: rgba(0, 0, 0, 0.05);
}
```

## Plugin Validation

The plugin loader validates:

- ✅ Plugin ID format: lowercase letters, numbers, hyphens only
- ✅ Version format: semantic versioning (e.g., 1.0.0)
- ✅ Required manifest fields: id, name, version, type
- ✅ Plugin type matches directory structure

## Theme API Integration

Themes are dynamically loaded from the backend and available in the frontend through a REST API:

### Backend API

**Endpoint:** `GET /api/v1/themes`

Returns all available theme plugins with their metadata:

```json
[
  {
    "id": "cream",
    "name": "cream",
    "label": "Cream",
    "description": "Classic notebook with cream pages",
    "className": "theme-cream",
    "category": "light",
    "version": "1.0.0",
    "author": "Codex Team"
  }
]
```

### Frontend Integration

The frontend theme store (`frontend/src/stores/theme.ts`) automatically loads themes from the API on initialization. This ensures that:

- New themes are automatically available when added to `plugins/themes/`
- Theme metadata stays synchronized between backend and frontend
- No frontend code changes needed to add new themes
- Fallback to default themes if API is unavailable

### Adding New Themes

1. Create theme directory in `plugins/themes/<theme-id>/`
2. Add `theme.yaml` manifest with required fields
3. Create `styles/main.css` with theme styles
4. Theme automatically appears in User Settings

No frontend rebuild or code changes required!

## See Also

- [Plugin System Design Document](../docs/design/plugin-system.md) - Complete specification
- [Dynamic Views Design](../docs/design/dynamic-views.md) - View plugin architecture
- [Theme Store](../frontend/src/stores/theme.ts) - Frontend theme management
- [Theme API Route](../backend/codex/api/routes/themes.py) - Backend theme endpoint

## Migration Notes

### Template Migration

Templates have been migrated from `backend/codex/templates/` to view plugins in `plugins/views/`. The system now supports both:

1. **Legacy templates**: Still loaded from `backend/codex/templates/` for backward compatibility
2. **Plugin templates**: Loaded from view plugin `templates/` directories

When the API returns templates, each template includes a `source` field:
- `"default"`: Legacy template from `backend/codex/templates/`
- `"plugin"`: Template from a view plugin (includes `plugin_id` field)
- `"notebook"`: Custom template from notebook's `.templates/` folder

### Migration Details

The following templates have been migrated to plugins:

**Tasks Plugin** (`plugins/views/tasks/`):
- `task-board.yaml` - Kanban board template
- `task-list.yaml` - Task list template
- `todo-item.yaml` - Individual todo item template

**Gallery Plugin** (`plugins/views/gallery/`):
- `photo-gallery.yaml` - Photo gallery template

**Core Plugin** (`plugins/views/core/`):
- `blank-note.yaml` - Blank note template
- `daily-journal.yaml` - Daily journal template
- `meeting-notes.yaml` - Meeting notes template
- `project-doc.yaml` - Project documentation template
- `data-file.yaml` - JSON data file template

**Rollup Plugin** (`plugins/views/rollup/`):
- `weekly-rollup.yaml` - Weekly activity rollup template

Example CDX files have also been migrated from `examples/views/` to their respective plugin `examples/` directories.

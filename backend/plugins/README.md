# Codex Plugins

This directory contains plugins for Codex. Plugins are flexible components that can provide any combination of:

1. **Views** - Custom view components with query configurations
2. **Templates** - File templates for creating new content
3. **Themes** - Visual styling with CSS
4. **Integrations** - External API connections

## Flexible Plugin Architecture

**The plugin system uses a capability-based architecture** where any plugin type can expose themes, templates, views, or integrations. The plugin system is no longer hierarchical.

### Examples of Mixed Capabilities:

- A **theme plugin** can also provide templates (e.g., Manila theme includes a "Manila Note" template)
- An **integration plugin** can provide templates (e.g., GitHub integration includes an "Issue Tracker" template)
- A **view plugin** could theoretically include a matching theme
- Any plugin can mix and match capabilities as needed

### Plugin Types (by manifest)

While plugins are declared with a `type` field in their manifest (`view`, `theme`, or `integration`), this is primarily for organizational purposes. The actual capabilities are determined by what sections are present in the manifest:

- `theme` section → Plugin provides a theme
- `templates` section → Plugin provides templates
- `views` section → Plugin provides custom views
- `integration` section → Plugin provides API integration

## Directory Structure

Plugins are organized by their primary type for convenience:

1. **Views** (`plugins/views/`) - Primarily focused on custom views
2. **Themes** (`plugins/themes/`) - Primarily focused on visual styling
3. **Integrations** (`plugins/integrations/`) - Primarily focused on API connections

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

### Creating Plugins with Mixed Capabilities

Any plugin can now include multiple capability sections in its manifest. Here are some examples:

#### Example 1: Theme Plugin with Templates

A theme plugin can provide matching templates:

```yaml
# theme.yaml
id: manila
name: Manila
type: theme
version: 1.0.0

# Theme configuration
theme:
  display_name: Manila
  category: light
  className: theme-manila
  stylesheet: styles/main.css

# Templates - themes can also include templates
templates:
  - id: manila-note
    name: Manila Note
    file: templates/manila-note.yaml
    description: A note template matching the Manila theme
    icon: 📄
    default_name: manila-note.cdx
```

#### Example 2: Integration Plugin with Templates and Theme

An integration plugin can provide both templates and even a theme:

```yaml
# integration.yaml
id: github
name: GitHub Integration
type: integration
version: 1.0.0

# Integration configuration
integration:
  api_type: rest
  base_url: "https://api.github.com"
  auth_method: token

# Templates - integrations can also provide templates
templates:
  - id: github-issue-tracker
    name: GitHub Issue Tracker
    file: templates/issue-tracker.yaml
    description: Track GitHub issues
    icon: 🐛

# Optional: Theme configuration
theme:
  display_name: GitHub Dark
  category: dark
  className: theme-github
  stylesheet: styles/github.css
```

#### Example 3: View Plugin with Theme

A view plugin could include a matching theme:

```yaml
# plugin.yaml
id: kanban
name: Kanban View
type: view
version: 1.0.0

# Views
views:
  - id: kanban-board
    name: Kanban Board
    description: Task board view

# Templates
templates:
  - id: task-board
    name: Task Board

# Optional: Theme for the view
theme:
  display_name: Kanban Theme
  category: light
  className: theme-kanban
```

### Standard Plugin Structures

Each plugin type still has a recommended primary structure:

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

## Using the Capability-Based Plugin API

The plugin loader provides capability-based methods in addition to type-based filtering:

### Python API

```python
from codex.plugins.loader import PluginLoader

loader = PluginLoader(plugins_dir)
loader.load_all_plugins()

# Get all plugins with specific capabilities (regardless of type)
themes = loader.get_plugins_with_themes()  # All plugins providing themes
templates = loader.get_plugins_with_templates()  # All plugins providing templates
views = loader.get_plugins_with_views()  # All plugins providing views
integrations = loader.get_plugins_with_integrations()  # All plugins providing integrations

# Traditional type-based filtering still works
theme_plugins = loader.get_plugins_by_type("theme")  # Only "theme" type plugins
```

### Checking Plugin Capabilities

Every plugin instance has capability checking methods:

```python
plugin = loader.get_plugin("manila")

if plugin.has_theme():
    print(f"Theme: {plugin.display_name}")
    
if plugin.has_templates():
    print(f"Templates: {[t['id'] for t in plugin.templates]}")
    
if plugin.has_views():
    print(f"Views: {[v['id'] for v in plugin.views]}")
    
if plugin.has_integration():
    print(f"Integration: {plugin.api_type}")
```

## Migration Guide

### For Plugin Developers

If you have existing plugins, they will continue to work without changes. To add new capabilities:

1. **Add templates to a theme**:
   - Create a `templates/` directory in your theme plugin
   - Add template YAML files
   - Add a `templates` section to your `theme.yaml`

2. **Add a theme to a view or integration**:
   - Create a `styles/` directory
   - Add CSS files
   - Add a `theme` section to your manifest

3. **Add templates to an integration**:
   - Create a `templates/` directory
   - Add template YAML files
   - Add a `templates` section to your `integration.yaml`

### For API Consumers

If you're using the plugin API:

- **Recommended**: Use capability-based methods (`get_plugins_with_themes()`, etc.)
- **Still supported**: Type-based methods (`get_plugins_by_type()`)
- The capability-based methods are more flexible and future-proof

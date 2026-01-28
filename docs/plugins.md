# Codex Plugins

Codex provides an extensible plugin system for customizing views, themes, and integrations. This document provides an overview of the plugin system and available plugins.

## Overview

The plugin system supports three types of plugins:

1. **View Plugins** - Custom visualization components, templates, and examples
2. **Theme Plugins** - Visual styling with CSS customization
3. **Integration Plugins** - External API connections (planned)

## Implemented Plugins

### View Plugins

Codex includes five built-in view plugins located in `backend/plugins/views/`:

| Plugin | Description | Views | Templates | Examples |
|--------|-------------|-------|-----------|----------|
| **Tasks** | Task management with Kanban boards | Kanban Board, Task List | Task Board, Task List, Todo Item | Project task board, daily tasks |
| **Gallery** | Photo galleries with grid layouts | Gallery | Photo Gallery | Workspace photo gallery |
| **Core** | Essential note templates and dashboard | Dashboard | Blank Note, Daily Journal, Meeting Notes, Project Document, Data File | Home dashboard |
| **Rollup** | Time-based activity rollups | Rollup | Weekly Rollup | Weekly activity report |
| **Corkboard** | Visual canvas for creative writing | Corkboard | None | Novel outline |

Each view plugin includes:
- Custom properties (e.g., status, priority, due_date for tasks)
- Reusable templates with frontmatter schemas
- Example CDX files demonstrating usage
- Plugin manifest (`plugin.yaml`) with metadata

### Theme Plugins

Codex includes four built-in themes located in `backend/plugins/themes/`:

| Theme | Category | Description |
|-------|----------|-------------|
| **Cream** | Light | Classic notebook with cream pages (default) |
| **Manila** | Light | Vintage manila folder aesthetic |
| **White** | Light | Clean white pages |
| **Blueprint** | Dark | Dark mode with blueprint styling |

Themes are dynamically loaded via the `/api/v1/themes` REST API endpoint and automatically available in the frontend without code changes.

## Plugin Structure

### View Plugin Structure

```
plugins/views/<plugin-id>/
├── plugin.yaml         # Plugin manifest with metadata
├── views/              # Vue components (optional)
├── templates/          # Template YAML definitions
├── examples/           # Example CDX files
└── README.md          # Plugin documentation
```

### Theme Plugin Structure

```
plugins/themes/<theme-id>/
├── theme.yaml         # Theme manifest
├── styles/
│   └── main.css      # Main stylesheet
└── README.md         # Documentation
```

### Integration Plugin Structure (Planned)

```
plugins/integrations/<plugin-id>/
├── integration.yaml   # Integration manifest
├── settings.vue       # Settings UI component
├── blocks/           # Block renderers
└── transforms/       # Data transformers
```

## Using Plugins

### Plugin Loader

The plugin loader (`backend/codex/plugins/loader.py`) discovers and loads plugins:

```python
from pathlib import Path
from codex.plugins.loader import PluginLoader

# Initialize loader
plugins_dir = Path("backend/plugins")
loader = PluginLoader(plugins_dir)

# Discover and load all plugins
plugins = loader.load_all_plugins()

# Get specific plugin
theme = loader.get_plugin("cream")

# Get all themes
themes = loader.get_plugins_by_type("theme")
```

### Template Migration

Templates have been migrated from `backend/codex/templates/` to view plugins. The system supports both:

1. **Legacy templates**: Loaded from `backend/codex/templates/` (backward compatibility)
2. **Plugin templates**: Loaded from view plugin `templates/` directories
3. **Notebook templates**: Custom templates from notebook `.templates/` folders

Each template includes a `source` field indicating its origin: `"default"`, `"plugin"`, or `"notebook"`.

## Future Plans: Integration Plugins

Integration plugins will connect Codex to external APIs and services, enabling:

- Data import/export from external services
- Real-time synchronization with third-party APIs
- Custom block renderers for embedded content
- Secure API key storage with encryption
- Rate limiting and error handling

### Planned Integration Features

- **API Type Support**: REST, GraphQL, WebSocket
- **Authentication Methods**: API keys, OAuth, JWT
- **Custom Block Renderers**: Embed external content in markdown
- **Settings UI**: Vue components for configuration
- **Data Transformers**: Transform API responses for display
- **Triggers**: On-demand, interval-based, or event-driven updates
- **Permissions System**: Explicit grants for network and storage access

### Example Integration Use Cases

- Weather displays with forecast data
- GitHub issue/PR tracking
- Open Graph link unfurling
- Calendar event synchronization
- Social media embeds

### Implementation Status

Integration plugins are defined in the plugin system architecture but not yet implemented. The foundation includes:

- ✅ Plugin models (`IntegrationPlugin` class)
- ✅ Plugin loader with integration support
- ✅ Database schema design
- ⏳ API endpoint execution framework (planned)
- ⏳ Settings UI framework (planned)
- ⏳ Block renderer system (planned)
- ⏳ Example integrations (planned)

## Creating Custom Plugins

### Creating a View Plugin

1. Create directory in `plugins/views/<your-plugin-id>/`
2. Add `plugin.yaml` with required fields (id, name, version, type)
3. Define custom properties, views, and templates
4. Add example CDX files
5. Test with the plugin loader

### Creating a Theme

1. Create directory in `plugins/themes/<your-theme-id>/`
2. Add `theme.yaml` with theme configuration
3. Create `styles/main.css` with CSS
4. Use CSS class `.theme-<your-theme-id>` for theme-specific styling
5. Theme automatically appears in User Settings (no frontend rebuild needed)

## Documentation

For detailed plugin system architecture and specifications, see:

- **[Plugin System Design Document](design/plugin-system.md)** - Complete specification with examples
- **[Dynamic Views Design](design/dynamic-views.md)** - View plugin architecture
- **[Backend Plugin README](../backend/plugins/README.md)** - Implementation details
- **[Theme Store](../frontend/src/stores/theme.ts)** - Frontend theme management
- **[Theme API Route](../backend/codex/api/routes/themes.py)** - Backend theme endpoint

## Plugin Validation

The plugin loader validates:

- ✅ Plugin ID format: lowercase letters, numbers, hyphens only
- ✅ Version format: semantic versioning (e.g., 1.0.0)
- ✅ Required manifest fields: id, name, version, type
- ✅ Plugin type matches directory structure
- ✅ Codex version compatibility

## Implementation Roadmap

### Completed (v1.0-1.2)
- ✅ Plugin database schema and loader
- ✅ View plugin system with 5 built-in plugins
- ✅ Theme plugin system with 4 built-in themes
- ✅ Template migration to plugins
- ✅ Dynamic theme loading via API

### Planned (v1.3+)
- ⏳ Integration plugin framework
- ⏳ API client and execution system
- ⏳ Settings UI framework
- ⏳ Block renderer system
- ⏳ Example integrations (Weather, GitHub, Open Graph)
- ⏳ Plugin marketplace UI
- ⏳ Plugin dependencies and hooks
- ⏳ Auto-update system

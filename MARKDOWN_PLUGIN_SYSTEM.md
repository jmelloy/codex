# Markdown Frontmatter Viewing Plugin System

## Overview

The Codex system provides an extensible framework for rendering markdown frontmatter (colophon) data. This allows different types of metadata to be displayed in a structured, user-friendly format with support for custom renderers.

## Architecture

The system consists of two main parts:

1. **Backend Plugin System** (`codex.core.markdown_renderers`) - Defines how frontmatter fields are rendered to structured data
2. **Frontend Display Component** (`FrontmatterViewer.vue`) - Displays the rendered frontmatter with appropriate styling

## Backend: Creating Custom Renderers

### Basic Renderer Structure

All renderers inherit from the `FrontmatterRenderer` base class:

```python
from codex.core.markdown_renderers import FrontmatterRenderer
from typing import Any, Dict

class CustomRenderer(FrontmatterRenderer):
    """Renderer for custom field type."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render a frontmatter field value.

        Args:
            value: The value to render
            key: The frontmatter key

        Returns:
            Dictionary with rendering information:
            - type: The render type (identifier for frontend)
            - value: The formatted value
            - display: Display-friendly value
        """
        return {
            "type": "custom",
            "value": process_value(value),
            "display": format_for_display(value),
        }
```

### Built-in Renderers

The system includes several built-in renderers:

- **TextRenderer** - Simple text values (default)
- **DateRenderer** - Date/datetime values
- **NumberRenderer** - Numeric values (int/float)
- **BooleanRenderer** - Boolean values (Yes/No display)
- **ListRenderer** - Arrays/lists (displayed as tags)
- **LinkRenderer** - URLs
- **MarkdownRenderer** - Markdown content

### Registering Custom Renderers

There are three ways to register custom renderers:

#### 1. By Key Name

Register a renderer for specific frontmatter keys:

```python
from codex.core.markdown_renderers import (
    FrontmatterRenderer,
    register_renderer_for_key,
)

class StatusRenderer(FrontmatterRenderer):
    """Renderer for status field."""
    
    def render(self, value: Any, key: str) -> Dict[str, Any]:
        status_colors = {
            "draft": "#6b7280",
            "published": "#10b981",
            "archived": "#ef4444",
        }
        return {
            "type": "status",
            "value": str(value),
            "display": str(value).title(),
            "color": status_colors.get(str(value).lower(), "#6b7280"),
        }

# Register for the "status" key
register_renderer_for_key("status", StatusRenderer())
```

#### 2. By Value Type

Register a renderer for all values of a specific Python type:

```python
from datetime import datetime
from codex.core.markdown_renderers import register_renderer_for_type

class DateTimeRenderer(FrontmatterRenderer):
    """Renderer for datetime objects."""
    
    def render(self, value: Any, key: str) -> Dict[str, Any]:
        if isinstance(value, datetime):
            return {
                "type": "datetime",
                "value": value.isoformat(),
                "display": value.strftime("%Y-%m-%d %H:%M"),
            }
        return {"type": "text", "value": str(value), "display": str(value)}

# Register for datetime type
register_renderer_for_type(datetime, DateTimeRenderer())
```

#### 3. Using the Registry Directly

For more control, use the global registry:

```python
from codex.core.markdown_renderers import get_registry

registry = get_registry()

# Register by key
registry.register_for_key("priority", PriorityRenderer())

# Register by type
registry.register_for_type(dict, DictRenderer())

# Register named renderer
registry.register_renderer("custom_name", CustomRenderer())
```

### Renderer Priority

When rendering a field, the system checks in this order:

1. **Key-specific renderer** - Registered for that exact key name
2. **Type-specific renderer** - Registered for the value's Python type
3. **Default text renderer** - Fallback for all other cases

Example:

```python
# This frontmatter:
# date: 2024-12-20
# count: 42
# unknown: some value

# Will use:
# - DateRenderer for "date" (key-specific)
# - NumberRenderer for "count" (type-specific for int)
# - TextRenderer for "unknown" (default fallback)
```

## Frontend: Custom Field Display

### Using FrontmatterViewer Component

The `FrontmatterViewer` component automatically renders fields based on their `type`:

```vue
<template>
  <FrontmatterViewer :rendered="renderedFrontmatter" />
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import FrontmatterViewer from "@/components/markdown/FrontmatterViewer.vue";

const renderedFrontmatter = ref({});

onMounted(async () => {
  const response = await fetch(
    `/api/markdown/frontmatter/rendered?path=myfile.md&workspace_path=/path/to/workspace`
  );
  const data = await response.json();
  renderedFrontmatter.value = data.rendered;
});
</script>
```

### Adding Custom Field Types

To display custom field types, edit the `FrontmatterViewer.vue` component:

```vue
<!-- In FrontmatterViewer.vue template -->

<!-- Custom status display -->
<div
  v-else-if="rendered[key]?.type === 'status'"
  class="value-status"
  :style="{ color: rendered[key].color }"
>
  <span class="status-badge">{{ rendered[key].display }}</span>
</div>

<!-- Custom rating display -->
<div v-else-if="rendered[key]?.type === 'rating'" class="value-rating">
  <span v-for="i in 5" :key="i" class="star" :class="{ filled: i <= rendered[key].value }">
    ★
  </span>
</div>
```

Add corresponding styles:

```vue
<style scoped>
.value-status {
  font-weight: 600;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-md);
  background: currentColor;
  color: white;
  opacity: 0.9;
}

.value-rating {
  display: flex;
  gap: 0.25rem;
}

.star {
  color: #d1d5db;
  font-size: 1.25rem;
}

.star.filled {
  color: #fbbf24;
}
</style>
```

## Complete Example: Priority Field

Here's a complete example of adding a priority field renderer:

### Backend Renderer

```python
# In your plugin or initialization code
from codex.core.markdown_renderers import FrontmatterRenderer, register_renderer_for_key
from typing import Any, Dict

class PriorityRenderer(FrontmatterRenderer):
    """Renderer for priority fields (high, medium, low)."""
    
    PRIORITIES = {
        "high": {"level": 3, "color": "#ef4444", "icon": "!!!"},
        "medium": {"level": 2, "color": "#f59e0b", "icon": "!!"},
        "low": {"level": 1, "color": "#10b981", "icon": "!"},
    }
    
    def render(self, value: Any, key: str) -> Dict[str, Any]:
        priority = str(value).lower()
        info = self.PRIORITIES.get(priority, self.PRIORITIES["low"])
        
        return {
            "type": "priority",
            "value": priority,
            "display": f"{info['icon']} {priority.title()}",
            "level": info["level"],
            "color": info["color"],
        }

# Register for the "priority" key
register_renderer_for_key("priority", PriorityRenderer())
```

### Frontend Display

```vue
<!-- In FrontmatterViewer.vue, add to the template -->
<div
  v-else-if="rendered[key]?.type === 'priority'"
  class="value-priority"
>
  <span
    class="priority-badge"
    :class="`priority-${rendered[key].value}`"
    :style="{ color: rendered[key].color }"
  >
    {{ rendered[key].display }}
  </span>
</div>
```

```vue
<!-- Add to styles -->
<style scoped>
.value-priority {
  display: flex;
  align-items: center;
}

.priority-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border: 2px solid currentColor;
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: 0.875rem;
  background: transparent;
}

.priority-badge.priority-high {
  background: rgba(239, 68, 68, 0.1);
}
</style>
```

### Usage

```markdown
---
title: Important Task
priority: high
date: 2024-12-20
---

Task content here...
```

## API Endpoints

### Parse Markdown

```
GET /api/markdown/parse?path={file_path}&workspace_path={workspace}
```

Returns the full parsed markdown document:

```json
{
  "frontmatter": {
    "title": "Example",
    "date": "2024-12-20",
    "tags": ["example", "demo"]
  },
  "blocks": [
    {
      "type": "note",
      "content": "Block content here"
    }
  ],
  "content": "Main markdown content"
}
```

### Get Rendered Frontmatter

```
GET /api/markdown/frontmatter/rendered?path={file_path}&workspace_path={workspace}
```

Returns rendered frontmatter with type information:

```json
{
  "rendered": {
    "title": {
      "key": "title",
      "type": "text",
      "value": "Example",
      "display": "Example"
    },
    "date": {
      "key": "date",
      "type": "date",
      "value": "2024-12-20",
      "display": "2024-12-20"
    },
    "tags": {
      "key": "tags",
      "type": "list",
      "value": ["example", "demo"],
      "display": "example, demo"
    }
  }
}
```

## Testing Custom Renderers

```python
# tests/test_custom_renderer.py
import pytest
from codex.core.markdown_renderers import FrontmatterRendererRegistry
from my_plugin import PriorityRenderer

def test_priority_renderer():
    """Test priority field rendering."""
    renderer = PriorityRenderer()
    
    # Test high priority
    result = renderer.render("high", "priority")
    assert result["type"] == "priority"
    assert result["value"] == "high"
    assert result["level"] == 3
    assert "#ef4444" in result["color"]

def test_registry_integration():
    """Test renderer in registry."""
    registry = FrontmatterRendererRegistry()
    registry.register_for_key("priority", PriorityRenderer())
    
    frontmatter = {"priority": "high", "title": "Task"}
    rendered = registry.render_frontmatter(frontmatter)
    
    assert rendered["priority"]["type"] == "priority"
    assert rendered["title"]["type"] == "text"
```

## Best Practices

1. **Keep renderers simple** - Each renderer should handle one type of data
2. **Always provide display value** - Make fields human-readable
3. **Include type identifier** - Frontend needs this to choose display logic
4. **Handle edge cases** - Validate and provide fallbacks for invalid data
5. **Test thoroughly** - Write unit tests for custom renderers
6. **Document custom types** - Explain what data format your renderer expects

## Plugin Distribution

To share your custom renderers:

1. **Create a Python package**:
```python
# my_codex_plugin/__init__.py
from codex.core.markdown_renderers import register_renderer_for_key
from .renderers import CustomRenderer

def register_plugin():
    """Register all custom renderers."""
    register_renderer_for_key("custom_field", CustomRenderer())
```

2. **Install and activate**:
```python
# In your application setup or config
from my_codex_plugin import register_plugin
register_plugin()
```

3. **Share via PyPI** or internal package repository

## Future Enhancements

Potential future improvements to the plugin system:

- Dynamic renderer loading from configuration
- Renderer marketplace/registry
- Visual renderer builder/editor
- Renderer composition (combining multiple renderers)
- Validation and schema support
- i18n/localization support for display values

## Support

For questions or issues:
- Check the examples in `/examples`
- Review test cases in `/tests/test_markdown_renderers.py`
- Open an issue on GitHub

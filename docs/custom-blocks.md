# Custom Markdown Blocks

Custom markdown blocks allow you to embed rich, interactive components within your markdown documents using a special code fence syntax.

## Overview

Custom blocks use the standard markdown code fence syntax (triple backticks) with a custom block type identifier:

```
```blocktype
key: value
another_key: another_value
```
```

The Codex system recognizes these blocks and renders them as interactive Vue.js components instead of plain code blocks.

## Available Block Types

### Weather Block

Display weather information for a location.

**Syntax:**
```
```weather
location: San Francisco, CA
units: imperial
```
```

**Configuration:**
- `location` (string): The location to display weather for
- `units` (string): Temperature units - `imperial`, `metric`, or `kelvin`

**Example:**
```markdown
# Trip Planning

Check the weather before your trip:

```weather
location: Tokyo, Japan
units: metric
```
```

### Link Preview Block

Display a rich preview of a URL with Open Graph metadata.

**Syntax:**
```
```link-preview
url: https://github.com/jmelloy/codex
```
```

**Configuration:**
- `url` (string, required): The URL to preview

**Example:**
```markdown
# Resources

Check out our repository:

```link-preview
url: https://github.com/jmelloy/codex
```
```

## How It Works

### Backend (Python)

1. **CustomBlockParser** (`codex/core/custom_blocks.py`)
   - Parses markdown and extracts custom block definitions
   - Distinguishes custom blocks from standard code blocks (python, javascript, etc.)
   - Parses YAML configuration inside blocks
   - Returns structured block metadata

2. **API Endpoint** (`/api/v1/markdown/render`)
   - Accepts markdown content
   - Returns rendered HTML plus custom block metadata
   - Custom blocks are detected and their configurations are extracted

### Frontend (Vue.js)

1. **Block Components** (`frontend/src/components/blocks/`)
   - `WeatherBlock.vue` - Renders weather information
   - `LinkPreviewBlock.vue` - Renders link previews
   - Each component receives block configuration as props

2. **MarkdownViewer Component** (`frontend/src/components/MarkdownViewer.vue`)
   - Detects custom blocks in rendered markdown
   - Looks up registered block components
   - Dynamically mounts Vue components for each custom block
   - Preserves standard code block syntax highlighting

3. **Component Registry**
   - Custom blocks are registered in a component map
   - New block types can be added by registering their components

## Creating Custom Blocks

### 1. Define Block in Integration Plugin

Create or edit an integration plugin manifest (`integration.yaml`):

```yaml
# backend/plugins/integrations/my-integration/integration.yaml
id: my-integration
name: My Integration
type: integration

blocks:
  - id: my-custom-block
    name: My Custom Block
    description: A custom block that does something cool
    icon: 🎨
    syntax: "```my-custom-block\nkey: value\n```"
    config_schema:
      key:
        type: string
        description: A configuration key
        required: true
```

### 2. Create Vue Component

Create a Vue component for rendering the block:

```vue
<!-- frontend/src/components/blocks/MyCustomBlock.vue -->
<template>
  <div class="custom-block my-custom-block">
    <div class="block-header">
      <span class="block-icon">🎨</span>
      <span class="block-title">My Custom Block</span>
    </div>
    <div class="block-content">
      <p>{{ config.key }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
interface MyCustomBlockConfig {
  key?: string
  [key: string]: any
}

interface Props {
  config: MyCustomBlockConfig
}

defineProps<Props>()
</script>

<style scoped>
.my-custom-block {
  border: 2px solid #10b981;
  background: linear-gradient(135deg, #d1fae5 0%, #ecfdf5 100%);
}
/* Add more styles... */
</style>
```

### 3. Register Component

Add your component to the registry in `MarkdownViewer.vue`:

```typescript
import MyCustomBlock from "./blocks/MyCustomBlock.vue"

const customBlockComponents: Record<string, any> = {
  weather: WeatherBlock,
  "link-preview": LinkPreviewBlock,
  "my-custom-block": MyCustomBlock,  // Add your block here
}
```

## Standard vs Custom Blocks

Custom blocks are distinguished from standard code blocks by their block type:

**Standard code blocks** (syntax highlighted as code):
- `python`, `javascript`, `typescript`, `java`, `c`, `cpp`, etc.
- Any language recognized by highlight.js

**Custom blocks** (rendered as components):
- Defined in integration plugin manifests
- Not standard programming languages
- Examples: `weather`, `link-preview`, `github-issue`

## Testing

### Backend Tests

Run backend tests:
```bash
cd backend
pytest tests/test_custom_blocks.py -v
pytest tests/test_markdown_api.py -v
```

### Frontend Tests

Build the frontend to check for TypeScript errors:
```bash
cd frontend
npm run build
```

## Troubleshooting

### Custom Block Not Rendering

1. **Check block type name** - Must match exactly (case-sensitive)
2. **Verify YAML syntax** - Configuration must be valid YAML
3. **Check component registration** - Component must be in `customBlockComponents` registry
4. **Check browser console** - Look for JavaScript errors

### Standard Code Block Rendered as Custom Block

1. **Check if block type is in standard languages list** - Add it to `STANDARD_LANGUAGES` in `CustomBlockParser`
2. **Verify frontend registry** - Make sure it's not in `customBlockComponents`

## Future Enhancements

Planned features for custom blocks:

- **Live data integration** - Connect blocks to real APIs (Weather API, Open Graph, etc.)
- **Interactive controls** - Add buttons, forms, and other interactive elements
- **Block templates** - Pre-configured block templates for common use cases
- **Plugin marketplace** - Share and discover custom block types
- **Real-time updates** - Automatic refresh of dynamic content
- **Nested blocks** - Support for blocks inside blocks

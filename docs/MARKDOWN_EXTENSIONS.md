# Markdown Viewer and Editor Extension System

## Overview

The Codex markdown viewer and editor provide an extensible architecture that allows developers to add custom markdown syntax, rendering logic, and UI enhancements without modifying the core components.

## Extension Interface

Extensions follow a simple interface:

```typescript
export interface MarkdownExtension {
  name: string
  renderer?: any  // Custom renderer functions
}
```

## Creating Custom Extensions

### Example: Custom Callout Boxes

```typescript
const calloutExtension: MarkdownExtension = {
  name: 'callout-boxes',
  renderer: {
    paragraph(text: string) {
      const match = text.match(/^!!! (\w+) (.+)$/);
      if (match) {
        const [, type, content] = match;
        return `<div class="callout callout-${type}">${content}</div>`;
      }
      return false; // Use default rendering
    }
  }
}
```

## Component Props

### MarkdownEditor

- `modelValue` (string): The markdown content
- `frontmatter` (object): Frontmatter metadata
- `autosave` (boolean): Enable auto-save
- `extensions` (MarkdownExtension[]): Custom extensions

### MarkdownViewer

- `content` (string): Markdown content to display
- `frontmatter` (object): Frontmatter metadata  
- `showFrontmatter` (boolean): Display metadata
- `extensions` (MarkdownExtension[]): Custom extensions

## Toolbar Customization

Both components support custom toolbar actions via slots:

```vue
<MarkdownEditor v-model="content">
  <template #toolbar-actions>
    <button @click="customAction">Custom Button</button>
  </template>
</MarkdownEditor>
```

## Backend API

The markdown API supports:

- `POST /api/v1/markdown/render` - Render markdown with frontmatter parsing
- `GET /api/v1/markdown/{workspace_id}/files` - List markdown files
- `GET/POST/PUT/DELETE /api/v1/markdown/{workspace_id}/file` - CRUD operations

All endpoints require authentication.

## Testing

Comprehensive tests are available in `tests/test_markdown_api.py`.

Run tests with: `pytest tests/test_markdown_api.py -v`

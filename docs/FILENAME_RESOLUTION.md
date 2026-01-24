# Filename-Based Image and Link Resolution in Markdown Viewer

## Overview

The Codex markdown viewer now supports resolving images and links by filename, making it easier to reference files within a notebook without needing to specify full paths.

## Features

### 1. Image Resolution by Filename

When you reference an image by filename in markdown, the viewer automatically resolves it to the correct file in the current notebook.

**Example:**
```markdown
![My Screenshot](screenshot.png)
```

This will be automatically resolved to:
```html
<img src="/api/v1/files/by-path/content?path=screenshot.png&workspace_id=1&notebook_id=2" alt="My Screenshot">
```

### 2. Link Resolution by Filename

Links to other markdown files or documents can be referenced by filename.

**Example:**
```markdown
[Read the documentation](README.md)
```

This will be automatically resolved to:
```html
<a href="/api/v1/files/by-path/content?path=README.md&workspace_id=1&notebook_id=2">Read the documentation</a>
```

### 3. Support for Relative Paths

The system also supports relative path references:

```markdown
![Diagram](./images/architecture.png)
[Related](../other-notebook/file.md)
```

### 4. External URLs Preserved

External URLs are not modified and work as expected:

```markdown
![Logo](https://example.com/logo.png)
[Website](https://example.com)
```

## How It Works

### Backend

The backend already has support for filename-based file lookup through the `/api/v1/files/by-path/content` endpoint:

1. **Exact Path Match**: First tries to find a file with the exact path
2. **Filename Search**: If the path doesn't contain a directory separator, searches for any file with that filename in the notebook
3. **Returns First Match**: If multiple files have the same name, returns the first match

**Implementation**: See `backend/codex/api/routes/files.py` - `get_file_content_by_path()` function

### Frontend

The MarkdownViewer component intercepts markdown rendering to resolve file references:

1. **Custom Renderer**: Uses a custom `marked` renderer that intercepts image and link tokens
2. **URL Resolution**: Converts filename references to proper API URLs with workspace and notebook context
3. **Conditional Resolution**: Only resolves local file references (not external URLs or API paths)

**Implementation**: See `frontend/src/components/MarkdownViewer.vue`

## Usage

### In Vue Components

Pass the workspace and notebook context to the MarkdownViewer:

```vue
<MarkdownViewer 
  :content="markdownContent"
  :workspace-id="workspaceId"
  :notebook-id="notebookId"
  :current-file-path="currentFilePath"
/>
```

### In Markdown Files

Simply reference files by name or relative path:

```markdown
# My Document

Here's a diagram:

![System Architecture](architecture.png)

For more details, see:
- [Setup Guide](setup.md)
- [API Documentation](./docs/api.md)
- [External Resource](https://example.com/guide)
```

## Examples

### Example 1: Simple Image Reference

**Markdown:**
```markdown
![Profile Picture](avatar.jpg)
```

**Rendered as:**
- Searches for `avatar.jpg` in the current notebook
- Displays the image if found
- Shows broken image icon if not found

### Example 2: Link to Another Document

**Markdown:**
```markdown
See [Installation Instructions](INSTALL.md) for details.
```

**Rendered as:**
- Searches for `INSTALL.md` in the current notebook
- Creates a link that opens/downloads the file
- Link is clickable and functional

### Example 3: Relative Paths

**Markdown:**
```markdown
![Chart](./charts/revenue-2024.png)
[Previous Quarter](../2024-Q3/report.md)
```

**Rendered as:**
- Resolves paths relative to the current file's location
- Maintains directory structure
- Works across subdirectories

## Technical Details

### File Search Priority

1. **Exact path match**: `path/to/file.md`
2. **Filename-only search**: `file.md` (searches anywhere in notebook)
3. **First match wins**: If multiple files have the same name

### URL Encoding

Filenames are properly URL-encoded to handle:
- Spaces: `my file.png` → `my%20file.png`
- Special characters: `chart (1).png` → `chart%20(1).png`

### Security

- Path validation prevents directory traversal attacks
- All file paths are resolved within the notebook boundary
- No access to files outside the current notebook

## Browser Compatibility

The feature works in all modern browsers that support:
- ES6 JavaScript
- Vue 3
- Fetch API

## Testing

The feature includes comprehensive unit tests:

```bash
cd frontend
npm test -- src/__tests__/components/MarkdownViewer.test.ts
```

Test coverage includes:
- Image resolution by filename ✓
- Link resolution by filename ✓
- External URL preservation ✓
- Relative path handling ✓
- Multiple images/links in same document ✓
- No context fallback behavior ✓

## Limitations

1. **Same-Name Files**: If multiple files have the same name, only the first match is returned
2. **Notebook Scope**: Files can only be referenced within the same notebook (cross-notebook references not supported yet)
3. **Performance**: Large notebooks with many files may experience slower filename lookups

## Future Enhancements

Potential improvements for future versions:

1. **Cross-Notebook References**: Support linking to files in other notebooks
2. **Fuzzy Matching**: Better handling of similar filenames
3. **File Browser Integration**: Click to browse and insert file references
4. **Preview on Hover**: Show image previews when hovering over image links
5. **Disambiguation UI**: When multiple files match, show selection dialog

## API Reference

### MarkdownViewer Props

```typescript
interface Props {
  content: string              // Markdown content to render
  workspaceId?: number        // Current workspace ID (for file resolution)
  notebookId?: number         // Current notebook ID (for file resolution)
  currentFilePath?: string    // Path of current file (for relative references)
  frontmatter?: Record<string, any>
  editable?: boolean
  showToolbar?: boolean
  showFrontmatter?: boolean
  extensions?: MarkdownExtension[]
}
```

### Backend Endpoint

```
GET /api/v1/files/by-path/content
Query Parameters:
  - path: string (filename or path)
  - workspace_id: number
  - notebook_id: number
```

## Troubleshooting

### Images Not Displaying

1. **Check file exists**: Verify the image file is in the notebook
2. **Check filename**: Ensure exact filename match (case-sensitive)
3. **Check context**: Verify workspace_id and notebook_id are passed to MarkdownViewer
4. **Check console**: Look for 404 errors in browser developer console

### Links Not Working

1. **Check file type**: Link resolution works for `.md`, `.txt` and non-URL paths
2. **Check external URLs**: External URLs should start with `http://` or `https://`
3. **Check permissions**: Ensure user has access to the notebook

### Performance Issues

1. **Large notebooks**: Consider organizing files into subdirectories
2. **Many same-named files**: Use more specific paths or rename files
3. **Image optimization**: Compress large images to improve load times

## Contributing

When contributing to this feature:

1. **Add tests**: All changes should include corresponding tests
2. **Update documentation**: Keep this document up-to-date
3. **Consider edge cases**: Handle errors gracefully
4. **Maintain backward compatibility**: Don't break existing functionality

## Related Documentation

- [Markdown Storage](MARKDOWN_STORAGE.md)
- [File Management API](../backend/codex/api/routes/files.py)
- [LinkResolver](../backend/codex/core/link_resolver.py)

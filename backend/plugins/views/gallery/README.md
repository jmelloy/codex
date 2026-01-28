# Photo Gallery Plugin

A visual gallery plugin for displaying images in grid layouts with lightbox viewing.

## Features

- **Grid Layout**: Display images in a responsive grid
- **Masonry Layout**: Alternative Pinterest-style layout
- **Lightbox Viewer**: Full-size image viewing with keyboard navigation
- **Metadata Display**: Show EXIF data and image properties

## View Type

### Gallery

Display images in a grid layout with lightbox.

**View Type**: `gallery`

**Configuration Options**:
- `layout`: Layout style (grid, masonry)
- `columns`: Number of columns (1-8, default: 4)
- `thumbnail_size`: Thumbnail size in pixels (default: 300)
- `show_metadata`: Show image metadata (default: true)
- `lightbox`: Enable lightbox viewer (default: true)

**Example**:
```yaml
---
type: view
view_type: gallery
title: Photo Gallery
query:
  paths: ["photos/**/*", "images/**/*"]
  content_types:
    - image/png
    - image/jpeg
    - image/gif
    - image/webp
config:
  layout: grid
  columns: 4
  thumbnail_size: 300
  show_metadata: true
  lightbox: true
---
```

## Templates

### Photo Gallery

Create a new image gallery view.

**Template ID**: `photo-gallery`  
**Default Name**: `gallery.cdx`  
**Icon**: 🖼️

## Examples

The plugin includes an example photo gallery that displays all images in the workspace with lightbox viewing.

## Usage

### Creating a Gallery

1. Use the "Photo Gallery" template to create a new gallery view
2. Configure the query to filter specific images (by path, tags, or content type)
3. Adjust layout options (columns, thumbnail size)
4. Click any image to view in lightbox mode

### Keyboard Navigation

In lightbox mode:
- **Arrow Keys**: Navigate between images
- **Escape**: Close lightbox
- **+/-**: Zoom in/out

## Permissions

This plugin requires the following permissions:
- `read_files`: Read image files

## License

MIT License - See LICENSE file for details

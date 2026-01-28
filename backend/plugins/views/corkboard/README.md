# Corkboard Plugin

Visual corkboard views for creative writing, story planning, and visual organization.

## Features

- **Visual Canvas**: Notecard-style layout for visual thinking
- **Swimlanes**: Organize cards into horizontal lanes
- **Drag and Drop**: Move cards freely or between lanes
- **Card Styles**: Multiple display styles (notecard, minimal, detailed)
- **Flexible Layouts**: Freeform, swimlanes, or grid

## View Type

### Corkboard

Visual canvas with notecard-style layout, perfect for creative writing and story planning.

**View Type**: `corkboard`

**Configuration Options**:
- `group_by`: Property to group by (creates swimlanes)
- `card_style`: Display style (notecard, minimal, detailed)
- `layout`: Layout type (freeform, swimlanes, grid)
- `draggable`: Allow drag and drop (default: true)
- `editable`: Allow inline editing (default: true)
- `card_fields`: Fields to display on cards

**Example**:
```yaml
---
type: view
view_type: corkboard
title: Novel Outline
query:
  paths: ["novel/chapters/**/*.md"]
  sort: properties.chapter asc
config:
  group_by: properties.chapter
  card_style: notecard
  layout: swimlanes
  draggable: true
  editable: true
  card_fields:
    - scene
    - characters
    - summary
    - word_count
---
```

## Examples

### Novel Outline

The plugin includes a novel outline example that demonstrates how to use swimlanes to organize chapters and scenes visually.

**Features**:
- Each swimlane represents a chapter
- Each card is a scene within the chapter
- Drag and drop to reorder scenes
- Click to edit scene details

## Usage

### Creating a Corkboard

1. Create a new `.cdx` file with `view_type: corkboard`
2. Configure the query to select relevant files
3. Set `group_by` to create swimlanes (e.g., by chapter, category, or status)
4. Choose card style and fields to display
5. Drag cards to reorganize your content

### Use Cases

- **Novel Writing**: Organize chapters and scenes
- **Story Planning**: Map character arcs and plot points
- **Research**: Organize notes and sources visually
- **Project Planning**: Visual task organization
- **Brainstorming**: Freeform idea capture and organization

### Custom Properties

Define custom frontmatter properties for your cards:

```yaml
---
title: Scene 1 - Opening
chapter: 1
scene: 1
characters: [Alice, Bob]
summary: Alice discovers the mysterious box
word_count: 500
---
```

## Permissions

This plugin requires the following permissions:
- `read_files`: Read card files
- `write_files`: Create and update cards
- `modify_metadata`: Update card properties when dragging

## License

MIT License - See LICENSE file for details

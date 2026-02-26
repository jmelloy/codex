# Core Views Plugin

Essential note templates and dashboard views for everyday use in Codex.

## Features

- **Note Templates**: Blank notes, journals, meeting notes, project documentation
- **Dashboard Views**: Composite dashboards with embedded mini-views
- **Data Files**: JSON data file templates

## View Types

### Dashboard

Composite dashboard with embedded mini-views organized in rows and columns.

**View Type**: `dashboard`

**Configuration Options**:
- `layout`: Array of row definitions
  - `type`: Row type (currently only "row")
  - `components`: Array of mini-view components
    - `type`: Component type (currently only "mini-view")
    - `span`: Column span (1-12, using 12-column grid)
    - `view`: Path to view file

**Example**:
```yaml
---
type: view
view_type: dashboard
title: Home Dashboard
layout:
  - type: row
    components:
      - type: mini-view
        span: 8
        view: views/task-list-today.cdx
      - type: mini-view
        span: 4
        view: views/task-stats.cdx
---
```

## Templates

### Blank Note

A simple blank markdown note.

**Template ID**: `blank-note`  
**Default Name**: `{title}.md`  
**Icon**: 📝

### Daily Journal

A journal entry with today's date and structured sections.

**Template ID**: `daily-journal`  
**Default Name**: `{yyyy}-{mm}-{dd}-journal.md`  
**Icon**: 📔

**Sections**:
- Today's Goals
- Notes
- Reflections

### Meeting Notes

Template for capturing meeting notes with attendees, agenda, and action items.

**Template ID**: `meeting-notes`  
**Default Name**: `{yyyy}-{mm}-{dd}-meeting.md`  
**Icon**: 🗓️

**Sections**:
- Attendees
- Agenda
- Discussion Notes
- Action Items
- Next Steps

### Project Document

Documentation template for project planning and tracking.

**Template ID**: `project-doc`  
**Default Name**: `{title}.md`  
**Icon**: 📋

**Sections**:
- Overview
- Goals
- Requirements
- Implementation
- References

### Data File

JSON data file template for structured data storage.

**Template ID**: `data-file`  
**Default Name**: `{title}.json`  
**Icon**: 📦

## Examples

The plugin includes a home dashboard example that demonstrates how to create a composite view with multiple embedded mini-views.

## Usage

### Creating Notes

1. Select the appropriate template (blank, journal, meeting, project)
2. The filename will be auto-generated based on the template pattern
3. Fill in the structured sections

### Creating a Dashboard

1. Use the "Home Dashboard" example as a starting point
2. Customize the layout by adding or removing rows
3. Reference other view files in the mini-view components
4. Adjust span values to control column widths (total of 12 per row)

## Date Patterns

Templates support date pattern substitution:
- `{yyyy}`: 4-digit year
- `{yy}`: 2-digit year
- `{mm}`: 2-digit month
- `{dd}`: 2-digit day
- `{month}`: Full month name
- `{mon}`: Abbreviated month name
- `{title}`: User-provided title

## Permissions

This plugin requires the following permissions:
- `read_files`: Read note files
- `write_files`: Create and update notes

## License

MIT License - See LICENSE file for details

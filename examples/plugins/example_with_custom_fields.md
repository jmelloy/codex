---
title: Task Management Entry
date: 2024-12-20
author: Project Manager
status: in_progress
priority: high
tags:
  - project
  - important
  - deadline
assigned_to: John Doe
deadline: 2024-12-31
---

# Task Management Entry

This example demonstrates custom frontmatter fields with specialized renderers.

## Custom Fields

The frontmatter above includes:

- **status**: Uses StatusRenderer for visual status indicators
- **priority**: Uses PriorityRenderer for priority levels
- Standard fields like **date**, **tags**, **author** use built-in renderers

## How It Works

When this markdown file is viewed in the Codex UI:

1. The backend API parses the frontmatter
2. Custom renderers (if registered) process special fields
3. The frontend FrontmatterViewer component displays them with appropriate styling

## Extending the System

To add your own custom renderers:

1. Create a renderer class inheriting from `FrontmatterRenderer`
2. Register it for specific keys or types
3. Update the frontend component to handle the new display type

See `MARKDOWN_PLUGIN_SYSTEM.md` for complete documentation.

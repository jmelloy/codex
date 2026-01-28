# Task Management Plugin

A comprehensive task management plugin for Codex with Kanban boards, task lists, and todo items.

## Features

- **Kanban Board**: Visual board with draggable cards organized in columns
- **Task List**: Simple checklist view with task completion
- **Todo Items**: Individual task files with metadata

## View Types

### Kanban Board

A visual board with draggable cards organized in columns. Perfect for project management and sprint planning.

**View Type**: `kanban`

**Configuration Options**:
- `columns`: Array of column definitions with id, title, and filter
- `card_fields`: Fields to display on cards
- `drag_drop`: Enable drag and drop (default: true)
- `editable`: Allow inline editing (default: true)

**Example**:
```yaml
---
type: view
view_type: kanban
title: Project Tasks
query:
  tags: [task]
config:
  columns:
    - id: todo
      title: To Do
      filter: { status: todo }
    - id: in-progress
      title: In Progress
      filter: { status: in-progress }
    - id: done
      title: Done
      filter: { status: done }
  card_fields:
    - description
    - priority
    - due_date
---
```

### Task List

Simple checklist view with task completion. Great for daily task management and mini-views.

**View Type**: `task-list`

**Configuration Options**:
- `compact`: Compact display mode (default: false)
- `show_details`: Show task details (default: true)
- `editable`: Allow checkbox toggling (default: true)
- `sort_by`: Sort order (priority, due_date, created_at)

**Example**:
```yaml
---
type: view
view_type: task-list
title: Today's Tasks
query:
  tags: [task]
  properties:
    due_date: "{{ todayStart }}"
config:
  compact: true
  show_details: true
  sort_by: priority
---
```

## Templates

### Task Board

Create a new kanban board for managing tasks.

**Template ID**: `task-board`  
**Default Name**: `task-board.cdx`  
**Icon**: 📋

### Task List

Create a simple task checklist.

**Template ID**: `task-list`  
**Default Name**: `tasks.cdx`  
**Icon**: ✅

### Todo Item

Create an individual todo task file.

**Template ID**: `todo-item`  
**Default Name**: `{title}.md`  
**Icon**: ☑️

## Custom Properties

This plugin defines the following custom frontmatter properties:

### `status`
- **Type**: string
- **Description**: Task status
- **Values**: backlog, todo, in-progress, review, done
- **Default**: todo

### `priority`
- **Type**: string
- **Description**: Task priority level
- **Values**: low, medium, high, critical
- **Default**: medium

### `due_date`
- **Type**: date
- **Description**: Task due date

### `assignee`
- **Type**: string
- **Description**: Person assigned to task

### `estimated_hours`
- **Type**: number
- **Description**: Estimated hours to complete

## Examples

The plugin includes example files demonstrating different task management approaches:

1. **Kanban Board** (`examples/kanban-board.cdx`): Full project task board with all status columns
2. **Today's Tasks** (`examples/task-list-today.cdx`): Filtered task list for today's tasks

## Usage

### Creating a Task

1. Use the "Todo Item" template to create a new task
2. Set the appropriate frontmatter properties (status, priority, due_date, etc.)
3. Add task details in the markdown body

### Creating a Board

1. Use the "Task Board" template to create a new kanban board
2. Customize the columns and filters in the frontmatter
3. Drag cards between columns to update task status

### Creating a Task List

1. Use the "Task List" template to create a new task list
2. Configure the query to filter specific tasks
3. Check off tasks as you complete them

## Permissions

This plugin requires the following permissions:
- `read_files`: Read task files
- `write_files`: Create and update tasks
- `modify_metadata`: Update task properties

## License

MIT License - See LICENSE file for details

# Agent Task System Documentation

## Overview

The Agent Task System provides infrastructure for AI agents to safely operate on files and directories within the Codex system. It includes:

1. **Markdown Format Standards** - Consistent file format with frontmatter and blocks
2. **Task System** - Manage agent operations and chat interactions
3. **Folder Configuration** - Hierarchical configuration with `.` directories
4. **Agent Sandbox** - Safe execution environment with verify/apply/rollback

## Markdown Format Standards

### File Structure

All files follow a standard markdown format:

```markdown
---
title: Document Title
date: 2024-12-20
author: Author Name
tags:
  - tag1
  - tag2
---

# Main Content

Regular markdown content goes here.

::: blockType
Content within a named block.
:::

More regular content.
```

### Frontmatter

- Enclosed in `---` delimiters
- Uses YAML format
- Contains metadata properties
- Located at the beginning of the file

### Content Blocks

- Enclosed in `:::` delimiters
- Named with a type identifier: `::: typeName`
- Can contain any markdown content
- Used to separate different types of information

### Usage Example

```python
from core.markdown import MarkdownDocument

# Parse a markdown file
doc = MarkdownDocument.parse(text)

# Access frontmatter
title = doc.get_frontmatter("title")
tags = doc.get_frontmatter("tags", [])

# Access blocks
note = doc.get_block("note")
all_warnings = doc.get_all_blocks("warning")

# Modify and save
doc.set_frontmatter("status", "published")
doc.add_block("info", "Additional information")
```

## Task System

### Task Types

- `AGENT_OPERATION` - Agent performing an operation
- `CHAT_INTERACTION` - Chat conversation with user
- `FILE_MODIFICATION` - File modification task
- `ANALYSIS` - Analysis task
- `CUSTOM` - Custom task type

### Task States

- `PENDING` - Task created, not started
- `RUNNING` - Task currently executing
- `COMPLETED` - Task finished successfully
- `FAILED` - Task failed with error
- `CANCELLED` - Task was cancelled

### Usage Example

```python
from core.tasks import TaskManager, TaskType, TaskStatus

# Initialize task manager
manager = TaskManager(Path("~/.codex/tasks"))

# Create a task
task = manager.create_task(
    task_id="task-001",
    task_type=TaskType.AGENT_OPERATION,
    title="Analyze notebook entries",
    description="Perform statistical analysis on entries",
    workspace_path="/workspace",
    notebook_id="nb-123",
)

# Add messages to task (for chat interactions)
task.add_message("user", "Please analyze the results")
task.add_message("assistant", "I found the following patterns...")

# Update task status
task.mark_running()
# ... perform work ...
task.mark_completed({"results": "analysis complete"})

# Save task
manager.update_task(task)
```

## Folder Configuration System

### Configuration Files

Each folder can have a `.` directory containing:

- `agents.md` - Agent configuration and instructions
- `properties.md` - Folder properties

### Hierarchical Configuration

Configuration is inherited from parent folders:

- Child folders inherit parent configuration
- Child values override parent values
- Explicit `inherit=False` disables inheritance

### Usage Example

```python
from core.folder_config import FolderConfig, ConfigManager

# Create folder configuration
config = FolderConfig(Path("/workspace/notebooks/experiments"))

# Set properties
config.set_property("environment", "production")
config.set_property("backup", True)

# Get properties (with inheritance)
env = config.get_property("environment")  # Returns "production"
inherited = config.get_property("global_setting")  # Checks parent folders

# Configure agents
config.set_agent_config({
    "model": "gpt-4",
    "temperature": 0.7
}, agent_name="analyzer")

# Get agent instructions
instructions = config.get_agent_instructions("analyzer")

# List all configured agents
agents = config.list_agents()
```

### Agent Configuration Format

Example `agents.md` file:

```markdown
---
default_model: gpt-4
default_temperature: 0.7
---

# General Agent Instructions

These instructions apply to all agents in this folder.

::: analyzer
model: claude-3-opus
temperature: 0.3

Analyzer-specific instructions:

- Focus on code quality
- Check for vulnerabilities
  :::

::: writer
model: gpt-4
temperature: 0.9

Writer-specific instructions:

- Use clear language
- Follow format standards
  :::
```

## Agent Sandbox System

### Sandbox Workflow

1. **Setup** - Clone source filesystem to sandbox
2. **Modify** - Agent makes changes in sandbox
3. **Verify** - Check if changes are safe to apply
4. **Apply** - Apply changes to source, or
5. **Rollback** - Discard changes and restore original

### Change Types

- `CREATE` - New file created
- `MODIFY` - Existing file modified
- `DELETE` - File deleted

### Safety Features

- All changes tracked with hashes
- Verification before applying
- Rollback capability
- Change persistence
- Diff summaries

### Usage Example

```python
from core.sandbox import AgentSandbox, SandboxManager

# Create sandbox
manager = SandboxManager(Path("/tmp/sandboxes"))
sandbox = manager.create_sandbox("agent-001", Path("/workspace"))

# Make changes in sandbox
sandbox.create_file("new_doc.md", b"# New Document\n\nContent here.")
sandbox.modify_file("existing.md", b"Updated content")
sandbox.delete_file("old_file.md")

# Get diff summary
summary = sandbox.get_diff_summary()
print(f"Created: {summary['created']}")
print(f"Modified: {summary['modified']}")
print(f"Deleted: {summary['deleted']}")

# Verify changes are safe
verification = sandbox.verify_changes()
if verification["safe"]:
    # Apply changes to source
    result = sandbox.apply_changes()
    if result["success"]:
        print("Changes applied successfully")
else:
    # Rollback changes
    sandbox.rollback()
    print("Changes rolled back")

# Cleanup
sandbox.cleanup()
```

## Complete Workflow Example

Here's a complete example of using all components together:

```python
from pathlib import Path
from core.tasks import TaskManager, TaskType
from core.folder_config import FolderConfig
from core.sandbox import AgentSandbox
from core.markdown import MarkdownDocument

# 1. Setup
workspace = Path("/workspace")
task_manager = TaskManager(workspace / ".lab" / "tasks")
config = FolderConfig(workspace / "notebooks")

# 2. Create task
task = task_manager.create_task(
    task_id="task-001",
    task_type=TaskType.AGENT_OPERATION,
    title="Generate documentation",
    workspace_path=str(workspace),
)

task.mark_running()

# 3. Get agent configuration
agent_config = config.get_agent_config("writer")
instructions = config.get_agent_instructions("writer")

# 4. Create sandbox
sandbox = AgentSandbox(
    workspace / "notebooks",
    workspace / ".lab" / "sandbox" / task.id
)
sandbox.setup()

try:
    # 5. Perform work in sandbox
    doc = MarkdownDocument(
        frontmatter={"title": "Generated Doc", "date": "2024-12-20"},
        content="# Documentation\n\nGenerated content here.",
    )
    doc.add_block("note", "This was automatically generated.")

    sandbox.create_file("generated.md", doc.to_markdown().encode())

    # 6. Verify and apply
    verification = sandbox.verify_changes()

    if verification["safe"]:
        result = sandbox.apply_changes()
        task.mark_completed({"files_created": result["applied"]})
    else:
        task.mark_failed("Changes are not safe to apply")
        sandbox.rollback()

except Exception as e:
    task.mark_failed(str(e))
    sandbox.rollback()
finally:
    sandbox.cleanup()
    task_manager.update_task(task)
```

## Best Practices

### For Markdown Files

1. Always include frontmatter with at least `title` and `date`
2. Use descriptive block types (note, warning, info, code, etc.)
3. Keep blocks focused on a single type of content
4. Use tags for categorization

### For Tasks

1. Use descriptive task titles
2. Include relevant context (workspace, notebook, page, entry IDs)
3. Add messages for chat interactions
4. Always update task status appropriately
5. Include error details when marking failed

### For Folder Configuration

1. Use `.` directories for configuration files
2. Document agent configurations clearly
3. Use inheritance to avoid repetition
4. Test configuration with `get_effective_config()`

### For Agent Sandboxes

1. Always verify before applying changes
2. Use rollback when verification fails
3. Clean up sandboxes after use
4. Save changes for persistence if needed
5. Track all file modifications

## Integration with Existing Codex

The agent task system integrates seamlessly with existing Codex features:

- **Workspaces** - Task manager can be initialized in workspace `.lab` directory
- **Notebooks/Pages** - Tasks can reference notebook and page IDs
- **Entries** - Tasks can be associated with specific entries
- **File System** - Sandboxes work with the file system and Git backup

## API Integration (Future)

Tasks and sandboxes can be exposed via the FastAPI endpoints:

```python
# Task endpoints
POST   /api/tasks                    # Create task
GET    /api/tasks/{task_id}          # Get task
PATCH  /api/tasks/{task_id}/status   # Update status
DELETE /api/tasks/{task_id}          # Delete task

# Sandbox endpoints
POST   /api/sandboxes                # Create sandbox
GET    /api/sandboxes/{sandbox_id}   # Get sandbox info
POST   /api/sandboxes/{sandbox_id}/verify    # Verify changes
POST   /api/sandboxes/{sandbox_id}/apply     # Apply changes
POST   /api/sandboxes/{sandbox_id}/rollback  # Rollback changes
DELETE /api/sandboxes/{sandbox_id}   # Delete sandbox
```

## Troubleshooting

### Common Issues

1. **Import Errors**

   - Ensure `pyyaml` is installed: `pip install pyyaml`
   - Check Python version >= 3.10

2. **Sandbox Permissions**

   - Ensure write permissions on sandbox directory
   - Check file ownership and permissions

3. **Configuration Not Found**

   - Verify `.` directory exists in folder
   - Check file names (`agents.md`, not `agent.md`)
   - Use `find_config_file()` to debug

4. **Task Persistence**
   - Ensure task storage directory is writable
   - Check JSON file format in `tasks.json`

## Further Reading

- See `examples/` directory for complete examples
- Check test files (`test_*.py`) for usage patterns
- Review agents.md specification in documentation

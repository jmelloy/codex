# Markdown-First Storage System

> **Note**: This document describes an **alternative/experimental storage mode** for Codex. The default and primary storage mode uses SQLite with content-addressable storage (see main [README.md](README.md) for details). The markdown-first approach described here is an alternative that stores all data in plain markdown files.

## Overview

The Codex system supports an alternative **markdown-first** storage approach where all data is stored in human-readable markdown files with YAML frontmatter, instead of relying on SQLite databases and JSON metadata files.

## Benefits

### Human-Readable
- All data stored in plain markdown files
- Easy to read, edit, and understand
- No need for database tools or SQL queries

### Git-Friendly
- Clean diffs for version control
- Easy collaboration and code review
- Merge conflicts are human-readable

### Portable
- Copy files anywhere - no database export needed
- Works with any markdown viewer/editor
- Platform-independent

### Simple
- No database migrations needed
- No complex ORM queries
- Just files and folders

### Extensible
- Easy to add custom frontmatter fields
- Support for images and other artifacts via markdown links
- Blocks for structured content

## File Structure

```
workspace/
├── config.yaml                 # Workspace configuration
├── notebooks/
│   ├── research-project/
│   │   ├── index.md           # Notebook metadata and page list
│   │   ├── 2024-12-21-day-1-experiments.md
│   │   └── 2024-12-22-day-2-results.md
│   └── experiments/
│       ├── index.md
│       └── 2024-12-20-initial-test.md
└── artifacts/                 # Referenced artifacts (images, data files, etc.)
    ├── image-001.png
    ├── results.json
    └── test-data.csv
```

## Markdown File Format

### Notebook Index (index.md)

```markdown
---
id: nb-44f35aa7653f
title: Research Project
description: My research notes
created_at: '2024-12-21T10:00:00'
updated_at: '2024-12-21T15:30:00'
tags:
  - research
  - experiments
settings:
  default_entry_type: custom
  auto_archive_days: 90
  archive_strategy: compress
metadata: {}
---

# Research Project

My research notes

## Pages

- [2024-12-21-day-1-experiments.md](2024-12-21-day-1-experiments.md)
- [2024-12-22-day-2-results.md](2024-12-22-day-2-results.md)
```

### Page File

```markdown
---
id: page-792efbe08881
notebook_id: nb-44f35aa7653f
title: Day 1 Experiments
date: '2024-12-21T10:00:00'
created_at: '2024-12-21T10:00:00'
updated_at: '2024-12-21T15:30:00'
narrative:
  goals: Test the new markdown storage system
  hypothesis: Markdown storage will be simpler than database storage
  observations: The system works well with clear readable files
  conclusions: Success! Markdown storage is much simpler
  next_steps: Add more features and test with real data
tags:
  - experiments
  - testing
metadata: {}
entries:
  - id: entry-2a97f51bf2db
    title: Test Experiment
    entry_type: custom
    created_at: '2024-12-21T11:00:00'
    status: created
    inputs:
      prompt: test prompt
      seed: '42'
    outputs:
      result: success
    artifacts: []
    metadata: {}
  - id: entry-b67d4b5e42d3
    title: Experiment with Artifact
    entry_type: api_call
    created_at: '2024-12-21T12:00:00'
    status: created
    inputs:
      url: https://api.example.com
      method: GET
    outputs:
      status_code: 200
      body: Success
    artifacts:
      - path: artifacts/response.json
        type: application/json
    metadata: {}
---

# Day 1 Experiments

## Goals

Test the new markdown storage system

## Hypothesis

Markdown storage will be simpler than database storage

## Observations

The system works well with clear readable files

## Conclusions

Success! Markdown storage is much simpler

## Next Steps

Add more features and test with real data

## Entries

### Test Experiment

**Type**: custom  
**Created**: 2024-12-21T11:00:00  
**Status**: created

**Inputs**:
```json
{
  "prompt": "test prompt",
  "seed": "42"
}
```

**Outputs**:
```json
{
  "result": "success"
}
```

### Experiment with Artifact

**Type**: api_call  
**Created**: 2024-12-21T12:00:00  
**Status**: created

**Inputs**:
```json
{
  "url": "https://api.example.com",
  "method": "GET"
}
```

**Outputs**:
```json
{
  "status_code": 200,
  "body": "Success"
}
```

**Artifacts**:
- [response.json](artifacts/response.json)
```

## CLI Usage

### Initialize Workspace

```bash
# Initialize a new markdown workspace
python -m cli.markdown_cli init /path/to/workspace --name "My Lab"
```

### Notebook Management

```bash
# Create a notebook
python -m cli.markdown_cli notebook create "Research Project" \
  --description "My research notes" \
  --tags research --tags experiments

# List notebooks
python -m cli.markdown_cli notebook list --verbose

# Show notebook details
python -m cli.markdown_cli notebook show nb-xxx
```

### Page Management

```bash
# Create a page
python -m cli.markdown_cli page create "Day 1 Experiments" \
  --notebook nb-xxx \
  --goals "Test the system" \
  --hypothesis "It will work"

# List pages in a notebook
python -m cli.markdown_cli page list --notebook nb-xxx

# Show page details
python -m cli.markdown_cli page show page-xxx --notebook nb-xxx

# Update page narrative
python -m cli.markdown_cli page update page-xxx \
  --notebook nb-xxx \
  --observations "Great results" \
  --conclusions "Success!"
```

### Entry Management

```bash
# Add an entry with inputs
python -m cli.markdown_cli entry add "Test Experiment" \
  --page page-xxx \
  --notebook nb-xxx \
  --type custom \
  --input "prompt=test prompt" \
  --input "seed=42"

# Add entry with outputs
python -m cli.markdown_cli entry add "API Call" \
  --page page-xxx \
  --notebook nb-xxx \
  --type api_call \
  --input "url=https://api.example.com" \
  --output "status=200"

# Add entry with artifact reference
python -m cli.markdown_cli entry add "Image Generation" \
  --page page-xxx \
  --notebook nb-xxx \
  --type comfyui \
  --artifact "artifacts/generated-image.png"

# List entries
python -m cli.markdown_cli entry list --page page-xxx --notebook nb-xxx
```

## Python API Usage

```python
from pathlib import Path
from core.markdown_storage import MarkdownWorkspace

# Initialize workspace
ws = MarkdownWorkspace.initialize(Path("/path/to/workspace"), "My Lab")

# Create notebook
notebook = ws.create_notebook(
    "Research Project",
    description="My research notes",
    tags=["research", "experiments"]
)

# Create page
page = notebook.create_page(
    "Day 1 Experiments",
    narrative={
        "goals": "Test the system",
        "hypothesis": "It will work"
    }
)

# Add entry
entry_id = page.add_entry(
    title="Test Experiment",
    entry_type="custom",
    inputs={"prompt": "test", "seed": "42"},
    outputs={"result": "success"},
    artifacts=[
        {"path": "artifacts/result.json", "type": "application/json"}
    ]
)

# Update narrative
page.update_narrative("observations", "The experiment was successful")
page.update_narrative("conclusions", "Results exceeded expectations")

# Save changes
page.save()
```

## Artifact Management

Artifacts (images, data files, etc.) are stored in the `artifacts/` directory and referenced in markdown:

### Images

```markdown
![Generated Image](artifacts/generated-image.png)
```

### Data Files

```markdown
- [Results JSON](artifacts/results.json)
- [Test Data CSV](artifacts/test-data.csv)
```

### In Entry Frontmatter

```yaml
artifacts:
  - path: artifacts/image-001.png
    type: image/png
  - path: artifacts/results.json
    type: application/json
```

## Migration from Database Storage

To migrate an existing database-based workspace to markdown storage:

1. Export notebooks, pages, and entries from the database
2. Create markdown files using the new format
3. Copy artifacts to the `artifacts/` directory
4. Update artifact references in markdown

(Migration utility coming soon)

## Best Practices

### Organization

- Use descriptive notebook names: "ML Research 2024" not "nb-123"
- Date-prefix pages: "2024-12-21-experiment-name.md"
- Keep artifacts in a flat `artifacts/` directory or organize by type

### Narrative

- Fill in narrative sections as you work
- Update observations and conclusions regularly
- Link between pages using markdown references

### Entries

- Use descriptive entry titles
- Include all relevant inputs for reproducibility
- Reference artifacts clearly
- Add metadata for searchability

### Version Control

- Commit after significant changes
- Use descriptive commit messages
- Review diffs before committing
- Keep artifacts in separate commits if large

## Comparison with Database Storage

| Feature | Database Storage | Markdown Storage |
|---------|------------------|------------------|
| Human-readable | ❌ SQLite binary | ✅ Plain text |
| Git diffs | ❌ Binary changes | ✅ Line-by-line |
| Portability | ❌ Requires export | ✅ Copy files |
| Editing | ❌ SQL or ORM only | ✅ Any editor |
| Migrations | ❌ Required | ✅ Not needed |
| Complexity | ❌ High | ✅ Low |
| Performance | ✅ Fast queries | ❌ Slower search |
| Indexing | ✅ Built-in | ❌ Manual |

## Future Enhancements

- [ ] Full-text search across markdown files
- [ ] Automatic artifact thumbnail generation
- [ ] Markdown lint/validation
- [ ] Template system for entry types
- [ ] Export to various formats (PDF, HTML, etc.)
- [ ] Integration with note-taking apps (Obsidian, Logseq)
- [ ] Web UI for markdown editing

## See Also

- [MARKDOWN_PLUGIN_SYSTEM.md](MARKDOWN_PLUGIN_SYSTEM.md) - Markdown rendering plugins
- [AGENT_SYSTEM.md](AGENT_SYSTEM.md) - Agent task system with markdown
- [examples/example_entry.md](examples/example_entry.md) - Example entry format

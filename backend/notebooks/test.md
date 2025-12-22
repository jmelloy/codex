---
title: Test Markdown Document
date: 2024-12-22
tags:
  - test
  - demo
  - markdown
author: Codex Agent
status: published
description: This is a test document to verify markdown rendering in the frontend
---

# Test Markdown Document

This is a test document to verify that the markdown frontmatter rendering system works correctly in the frontend.

## Features Being Tested

1. **Frontmatter Parsing** - YAML frontmatter should be parsed and displayed
2. **Rendered Fields** - Each field type should be displayed with appropriate styling:
   - Text fields (title, author)
   - Date fields (date)
   - List fields (tags)
   - Description (markdown content)

## Content Blocks

::: note
This is a note block that should be displayed separately from the main content.
:::

## Main Content

This is the main content of the markdown document. It should be displayed below the frontmatter viewer.

### Subsection

More content here with **bold** and *italic* text.

```python
# Code block example
def hello_world():
    print("Hello, World!")
```

## Conclusion

If you can see this rendered properly with the frontmatter displayed in a nice viewer component, then the markdown focus feature is working correctly!

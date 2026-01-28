# Block-Based Pages Architecture - Executive Summary

**Full Document**: See [BLOCK_BASED_PAGES.md](./BLOCK_BASED_PAGES.md) for comprehensive analysis.

---

## TL;DR

This document explores transforming Codex from a flat file system into a structured page-based system where pages contain ordered blocks (similar to Notion).

**Current**: `Workspace → Notebook → Files`  
**Proposed**: `Workspace → Notebook → Pages → Blocks (→ Files)`

---

## Three Implementation Options

### Option 2: Pure File-Based Blocks ⭐ **RECOMMENDED**

Each block is its own numbered file in a page directory.

**Pros**: 
- ✅ Maximum git-friendliness (everything in files)
- ✅ Filesystem-native, works with any tool
- ✅ Simple mental model (directories = pages, files = blocks)
- ✅ Zero database overhead
- ✅ Portable and transparent

**Cons**: 
- ⚠️ Renumbering files on reorder
- ⚠️ Limited inline content options

**Example**:
```
pages/experiment-2026-01-28/
  001-experiment-notes.md
  002-setup-photo.jpg
  003-observation.txt
  004-analysis.ipynb
  .page.json                    -- Metadata only
```

### Option 1: Hybrid File-Reference Blocks

Pages organize existing files as ordered blocks, with optional inline blocks.

**Pros**: Good balance, flexible
**Cons**: Database complexity, needs .page.json export

**Example**:
```
Page: "Experiment Log - 2026-01-28"
  ├─ Block 1: File reference → experiment_notes.md
  ├─ Block 2: File reference → setup_photo.jpg
  ├─ Block 3: Inline text → "Key observation: temperature stable"
  └─ Block 4: File reference → analysis.ipynb
```

### Option 3: Database-First Blocks (Notion-style)

Blocks are primarily database records, files referenced when needed.

**Pros**: Maximum flexibility, enables real-time collaboration, nested blocks  
**Cons**: Complex, database-heavy, harder to version control

---

## Comparison Matrix

| Aspect | Current (Files Only) | Option 2 (File-Based) ⭐ | Option 1 (Hybrid) | Option 3 (Database-First) |
|--------|---------------------|----------------------|-------------------|---------------------------|
| **Simplicity** | ✅ Very Simple | ✅ Simple | ⚠️ Moderate | ❌ Complex |
| **Performance** | ✅ Fast | ✅ Fast | ⚠️ Good | ❌ Query-heavy |
| **Git-Friendly** | ✅ Perfect | ✅ Perfect | ⚠️ Good (need .page.json) | ❌ Poor |
| **Flexibility** | ❌ Limited | ⚠️ Moderate | ✅ Good balance | ✅ Maximum |
| **Real-time Collab** | ❌ File conflicts | ❌ File conflicts | ⚠️ Better | ✅ Excellent |
| **Structure** | ❌ Flat only | ✅ Pages + Blocks | ✅ Pages + Blocks | ✅ Nested blocks |
| **Backward Compat** | N/A | ✅ Fully compatible | ✅ Fully compatible | ❌ Breaking change |
| **Tool Integration** | ✅ Any tool | ✅ Any tool | ⚠️ API/UI only | ⚠️ API/UI only |

---

## Recommended Approach

**Start with Option 2 (Pure File-Based Blocks)**

### Implementation Phases

#### Phase 1: Directory-Based Pages (3-6 months)
- Create `pages/` directory structure convention
- Implement `.page.json` metadata format
- API endpoints for page directory operations
- Frontend pages view
- **Status**: Opt-in, coexists with file browser

#### Phase 2: Numbered Block Files (6-12 months)
- Implement `NNN-name.ext` naming convention
- API for block file operations (add, reorder via rename, delete)
- Frontend block renderer (sorted by filename)
- Drag-and-drop reordering (renames files)
- **Status**: Users can organize files into ordered pages

#### Phase 3: Enhanced Tooling (12+ months)
- CLI tools for page/block management
- Templates for common page types
- Git integration optimizations
- Batch operations for reordering
- **Status**: Mature file-based page system

### Rollback Safety

Pure filesystem approach means:
- Pages are just directories (can be browsed/edited with any tool)
- Blocks are just files (can be managed with standard commands)
- .page.json is optional metadata (pages work without it)
- Zero database dependencies (minimal schema for indexing only)
- Can abandon feature and still access all content

---

## Key Benefits

1. **Experiment Logs**: Combine notes, images, data, notebooks in single cohesive page
2. **Daily Notes**: Mix inline observations with file references chronologically
3. **Literature Review**: Structured synthesis of multiple sources
4. **Project Planning**: All planning materials in one view
5. **Code Documentation**: Literate programming style docs

---

## Key Challenges

1. **File Renaming**: Reordering requires renaming files with new numeric prefixes
2. **Inline Content**: Limited to small text files (001-note.txt) rather than rich database content
3. **Bulk Operations**: Moving multiple blocks requires multiple file renames

---

## Decision Criteria

**Implement file-based blocks if**:
- Users frequently need to organize related files together
- Narrative structure matters (experiments, reports, tutorials)
- Order of presentation is important
- Git-friendliness is paramount
- Command-line/tool compatibility is essential

**Consider hybrid/database approach if**:
- Rich inline content is critical
- Real-time collaboration is needed
- Complex nested structures required
- UI-first approach acceptable

---

## Next Steps

1. **Gather feedback** on file-based approach from users
2. **Prototype** Phase 1 (directory structure + .page.json)
3. **User testing** with small group using file tools
4. **Iterate** based on feedback
5. **Full implementation** if validated

---

## File Structure Preview

```
workspace/
  notebook1/
    pages/
      experiment-2026-01-28/
        001-intro.md
        002-setup-photo.jpg
        003-observation.md
        004-analysis.ipynb
        .page.json              -- Optional metadata
    files/
      standalone-doc.md         -- Traditional files
```

## .page.json Format

```json
{
  "id": "uuid",
  "title": "Experiment Log - 2026-01-28",
  "description": "Initial protein synthesis trial",
  "created_time": "2026-01-28T10:00:00Z",
  "last_edited_time": "2026-01-28T14:30:00Z",
  "blocks": [
    {"position": 1, "file": "001-intro.md", "type": "markdown"},
    {"position": 2, "file": "002-setup-photo.jpg", "type": "image"},
    {"position": 3, "file": "003-observation.md", "type": "markdown"},
    {"position": 4, "file": "004-analysis.ipynb", "type": "notebook"}
  ]
}
```

## Minimal Database Schema

```sql
-- Optional index table for search (files already in file_metadata)
CREATE TABLE pages (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL,
    directory_path VARCHAR(512) NOT NULL,  -- 'pages/experiment-2026-01-28'
    title VARCHAR(255),
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP
);
```

**Note**: No separate blocks table needed - blocks are just files with numeric prefixes. The file_metadata table already tracks all files.
);
```

---

## API Endpoints Preview

```
# Pages (directory operations)
POST   /api/v1/notebooks/{notebook_id}/pages          -- Create page directory
GET    /api/v1/notebooks/{notebook_id}/pages          -- List page directories
GET    /api/v1/pages/{page_id}                        -- Read directory + .page.json
PUT    /api/v1/pages/{page_id}                        -- Update .page.json
DELETE /api/v1/pages/{page_id}                        -- Remove directory

# Blocks (file operations within page directory)
POST   /api/v1/pages/{page_id}/blocks                 -- Create numbered file
PUT    /api/v1/pages/{page_id}/blocks/reorder         -- Rename files with new numbers
DELETE /api/v1/pages/{page_id}/blocks/{block_id}      -- Delete file
```

---

## References

- Full analysis: [BLOCK_BASED_PAGES.md](./BLOCK_BASED_PAGES.md)
- Notion API Docs: https://developers.notion.com/
- Current Codex Architecture: [README.md](../../README.md)
- Notebook Migrations: [NOTEBOOK_MIGRATIONS.md](../NOTEBOOK_MIGRATIONS.md)

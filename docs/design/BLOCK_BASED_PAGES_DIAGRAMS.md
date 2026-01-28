# Block-Based Pages: Visual Comparison

This document provides visual representations of the three implementation options discussed in [BLOCK_BASED_PAGES.md](./BLOCK_BASED_PAGES.md).

---

## Current Architecture (No Blocks)

```
┌─────────────────────────────────────────────┐
│ User                                         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Workspace                                    │
│ - path: /home/user/lab                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Notebook                                     │
│ - name: "ML Experiments"                    │
│ - .codex/notebook.db                        │
└─────────────────┬───────────────────────────┘
                  │
                  ├─► experiment_notes.md
                  ├─► setup_photo.jpg
                  ├─► analysis.ipynb
                  └─► results.csv
```

**Characteristics:**
- Flat file structure
- Metadata in notebook.db
- No organizational hierarchy within notebooks
- Git-friendly, filesystem-native

---

## Option 2: Pure File-Based Blocks ⭐ **RECOMMENDED**

```
┌─────────────────────────────────────────────┐
│ Workspace                                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Notebook                                     │
│ - .codex/notebook.db (lightweight index)    │
└─────────────────┬───────────────────────────┘
                  │
                  ├─ pages/
                  │  └─ experiment-1/
                  │     ├─ 001-experiment-notes.md
                  │     ├─ 002-setup-photo.jpg
                  │     ├─ 003-observation.txt
                  │     ├─ 004-analysis.ipynb
                  │     └─ .page.json
                  │
                  └─ files/ (traditional loose files)
                     └─ results.csv
```

**`.page.json` example:**
```json
{
  "id": "page-uuid",
  "title": "Experiment 1",
  "description": "Initial protein synthesis trial",
  "created_time": "2026-01-28T10:00:00Z",
  "blocks": [
    {"position": 1, "file": "001-experiment-notes.md", "type": "document"},
    {"position": 2, "file": "002-setup-photo.jpg", "type": "image"},
    {"position": 3, "file": "003-observation.txt", "type": "text"},
    {"position": 4, "file": "004-analysis.ipynb", "type": "notebook"}
  ]
}
```

**Characteristics:**
- Directory per page
- Numbered prefixes enforce ordering (filesystem-native)
- Metadata in .page.json file (version controlled)
- 100% git-friendly
- Works with any file browser/tool
- Renumbering files when reordering
- No database complexity for blocks

**Filesystem Operations:**

```bash
# Create a page
mkdir pages/experiment-1
echo '{"id": "uuid", "title": "Experiment 1"}' > pages/experiment-1/.page.json

# Add blocks
cp ~/data/notes.md pages/experiment-1/001-notes.md
cp ~/images/setup.jpg pages/experiment-1/002-setup.jpg

# Reorder (move block 2 to position 1)
git mv pages/experiment-1/001-notes.md pages/experiment-1/002-notes.md
git mv pages/experiment-1/002-setup.jpg pages/experiment-1/001-setup.jpg
```

---

## Option 1: Hybrid File-Reference Blocks

```
┌─────────────────────────────────────────────┐
│ Notebook                                     │
│ - .codex/notebook.db (pages, blocks tables) │
└─────────────────┬───────────────────────────┘
                  │
                  ├─ Pages ─────────────────────┐
                  │                             │
                  │  ┌─────────────────────┐   │
                  │  │ Page: "Experiment 1" │   │
                  │  ├─────────────────────┤   │
                  │  │ Block 1 (pos: 1)    │   │
                  │  │  type: file_ref     │───┼──► files/experiment_notes.md
                  │  │  file_id: abc123    │   │
                  │  ├─────────────────────┤   │
                  │  │ Block 2 (pos: 2)    │   │
                  │  │  type: file_ref     │───┼──► files/setup_photo.jpg
                  │  │  file_id: def456    │   │
                  │  ├─────────────────────┤   │
                  │  │ Block 3 (pos: 3)    │   │
                  │  │  type: inline_text  │   │
                  │  │  content: "Note..." │   │
                  │  ├─────────────────────┤   │
                  │  │ Block 4 (pos: 4)    │   │
                  │  │  type: file_ref     │───┼──► files/analysis.ipynb
                  │  │  file_id: ghi789    │   │
                  │  └─────────────────────┘   │
                  │                             │
                  └─ Files ─────────────────────┤
                     - experiment_notes.md      │
                     - setup_photo.jpg          │
                     - analysis.ipynb           │
                     - results.csv              │
```

**Database Schema:**

```sql
CREATE TABLE pages (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP
);

CREATE TABLE blocks (
    id UUID PRIMARY KEY,
    page_id UUID NOT NULL REFERENCES pages(id),
    block_type VARCHAR(50) NOT NULL,  -- 'file_reference', 'inline_text', etc.
    file_id UUID REFERENCES file_metadata(id),  -- NULL for inline blocks
    content JSONB,  -- For inline content
    position INTEGER NOT NULL,
    created_time TIMESTAMP,
    UNIQUE(page_id, position)
);
```

**Characteristics:**
- Pages organize files as ordered blocks
- Blocks can reference files OR contain inline content
- Files can exist with or without being in a page
- Database tracks ordering and relationships
- Need .page.json export for git-friendliness

---

## Option 3: Database-First Blocks (Notion-style)

```
┌─────────────────────────────────────────────┐
│ Notebook                                     │
│ - .codex/notebook.db (PRIMARY storage)      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │ Blocks (Database)  │
         └────────┬───────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐   ┌────────┐   ┌────────┐
│ Block  │   │ Block  │   │ Block  │
│ type:  │   │ type:  │   │ type:  │
│ page   │   │ heading│   │ text   │
│        │   │ content│   │ content│
│        │   │ "Intro"│   │ "..."  │
└───┬────┘   └────────┘   └────────┘
    │
    ├─► Block (type: file, file_ref: → experiment_notes.md)
    ├─► Block (type: image, file_ref: → setup_photo.jpg)
    └─► Block (type: text, content: "Inline observation")
```

**Database Schema:**

```sql
CREATE TABLE blocks (
    id UUID PRIMARY KEY,
    block_type VARCHAR(50),  -- 'page', 'text', 'heading', 'file', 'image', ...
    parent_id UUID REFERENCES blocks(id),  -- NULL for top-level pages
    notebook_id UUID,
    content JSONB,  -- Type-specific content
    file_reference UUID,  -- For file-backed blocks
    position INTEGER,
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP
);

-- Everything is a block:
-- - Pages are blocks with type='page'
-- - Headings are blocks with type='heading'
-- - File references are blocks with type='file'
-- - Inline text is blocks with type='text'
```

**Characteristics:**
- Single universal block abstraction
- Enables nested blocks (blocks within blocks)
- Supports Notion-like rich editing
- Database is source of truth
- Less git-friendly (need export for version control)
- Complex queries for hierarchy

---

## Feature Comparison Table

| Feature | Current | Option 2 (File-Based) ⭐ | Option 1 (Hybrid) | Option 3 (DB-First) |
|---------|---------|----------------------|-------------------|---------------------|
| **Storage Model** | Files only | Files + .page.json | Files + DB refs | DB primary |
| **Page Concept** | ❌ None | ✅ Directory | ✅ DB table | ✅ Special block |
| **Block Concept** | ❌ None | ⚠️ Implicit (files) | ✅ DB table | ✅ Universal entity |
| **Inline Content** | ❌ File only | ❌ File only | ✅ JSONB field | ✅ JSONB field |
| **Nested Blocks** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Reorder Speed** | N/A | Slow (rename files) | Fast (DB update) | Fast (DB update) |
| **Git Versioning** | ✅ Perfect | ✅ Native | ⚠️ Need export | ❌ Export required |
| **Query Complexity** | Simple | Simple | Moderate | Complex (recursive) |
| **API Calls** | 1 (get file) | 1-2 (dir + files) | 2-3 (page + blocks + files) | Many (recursive tree) |
| **Backward Compat** | N/A | ✅ Full | ✅ Full | ❌ Breaking |
| **Real-time Collab** | ❌ Hard | ❌ Hard | ⚠️ Possible | ✅ Excellent |

---

## Data Flow Diagrams

### Option 2: Page Render Flow (File-Based) ⭐

```
1. Client requests page
   │
   ▼
2. API: Read pages/experiment-1/.page.json
   │
   ▼
3. API: For each block in .page.json:
   │   ├─► Read pages/experiment-1/001-file.md
   │   ├─► Read pages/experiment-1/002-file.jpg
   │   └─► ...
   │
   ▼
4. Return JSON with file contents
   │
   ▼
5. Client renders blocks in order
```

### Option 1: Page Render Flow (Hybrid)

```
1. Client requests page
   │
   ▼
2. API: SELECT * FROM pages WHERE id = ?
   │
   ▼
3. API: SELECT * FROM blocks WHERE page_id = ? ORDER BY position
   │
   ├─► For each file-reference block:
   │   └─► SELECT * FROM file_metadata WHERE id = block.file_id
   │
   └─► For inline blocks: content in blocks.content
   │
   ▼
4. API: Combine into page structure
   │
   ▼
5. Return JSON:
   {
     "page": {...},
     "blocks": [
       {"type": "file_reference", "file": {...}},
       {"type": "inline_text", "content": "..."},
       ...
     ]
   }
   │
   ▼
6. Client renders blocks in order
```

### Option 3: Page Render Flow (Database-First)

```
1. Client requests page
   │
   ▼
2. API: SELECT * FROM blocks WHERE id = ? AND type = 'page'
   │
   ▼
3. API: Recursive query for child blocks
   WITH RECURSIVE children AS (
     SELECT * FROM blocks WHERE parent_id = ?
     UNION ALL
     SELECT b.* FROM blocks b
     JOIN children c ON b.parent_id = c.id
   )
   SELECT * FROM children ORDER BY position;
   │
   ├─► For file-backed blocks:
   │   └─► Read file from filesystem
   │
   └─► For inline blocks: content in blocks.content
   │
   ▼
4. Build hierarchical structure
   │
   ▼
5. Return nested JSON
   │
   ▼
6. Client renders recursive tree
```

---

## Migration Paths

### Option 1 Migration (Recommended)

```
Phase 1: Add Pages (Non-Breaking)
┌────────────────┐
│ Current        │  ─┐
│ Files only     │   │
└────────────────┘   │ Add pages table
                     │ Add UI for pages
┌────────────────┐   │ Files still work
│ Files + Pages  │  ─┘
│ (coexist)      │
└────────────────┘

Phase 2: Add Blocks (Opt-In)
┌────────────────┐
│ Files + Pages  │  ─┐
└────────────────┘   │ Add blocks table
                     │ Allow file refs in blocks
┌────────────────┐   │ Files still independent
│ Pages w/ Blocks│  ─┘
│ + Loose Files  │
└────────────────┘

Phase 3: Inline Blocks (Optional)
┌────────────────┐
│ Pages w/ Blocks│  ─┐
└────────────────┘   │ Support inline content
                     │ Add block editor
┌────────────────┐   │ Export blocks to files
│ Full Block     │  ─┘
│ Editing        │
└────────────────┘
```

**Rollback at any phase**: Drop new tables, continue with files

---

## Recommendation Summary

### Choose Option 1 (Hybrid) if you want:

✅ **Best of both worlds**
- File-based strengths preserved
- Structured organization added
- Incremental adoption path

✅ **Low risk**
- Backward compatible
- Opt-in feature
- Easy rollback

✅ **Future-ready**
- Foundation for rich features
- Can evolve to Option 3 later
- Doesn't lock you in

### Choose Option 2 (File-Based) if you want:

✅ **Maximum git-friendliness**
- Everything in files
- Native version control
- No database dependencies

⚠️ **Limitations**
- Awkward inline content
- Slow reordering
- Less flexible

### Choose Option 3 (DB-First) if you want:

✅ **Notion-like experience**
- Rich nested blocks
- Real-time collaboration
- Maximum flexibility

❌ **Tradeoffs**
- High complexity
- Breaking change
- Less portable

---

## Conclusion

**Start with Option 2 (Pure File-Based Blocks)** to get:
- 100% git-friendliness and portability
- Works with any file tool or CLI
- Zero database overhead
- Simple, transparent architecture
- Full backward compatibility

This approach lets you:
1. **Ship quickly** - Minimal implementation (directories + naming convention)
2. **Stay simple** - No complex database queries or state management
3. **Tool-friendly** - Users can work with standard file commands
4. **Git-native** - Perfect version control and history
5. **Evolve later** - Can add database layer if inline content becomes essential

See [BLOCK_BASED_PAGES.md](./BLOCK_BASED_PAGES.md) for complete analysis and implementation details.

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

## Option 1: Hybrid File-Reference Blocks ⭐ **RECOMMENDED**

```
┌─────────────────────────────────────────────┐
│ User                                         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Workspace                                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
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
                  │  │  type: file_ref     │───┼──► experiment_notes.md
                  │  │  file_id: abc123    │   │
                  │  ├─────────────────────┤   │
                  │  │ Block 2 (pos: 2)    │   │
                  │  │  type: file_ref     │───┼──► setup_photo.jpg
                  │  │  file_id: def456    │   │
                  │  ├─────────────────────┤   │
                  │  │ Block 3 (pos: 3)    │   │
                  │  │  type: inline_text  │   │
                  │  │  content: "Note..." │   │
                  │  ├─────────────────────┤   │
                  │  │ Block 4 (pos: 4)    │   │
                  │  │  type: file_ref     │───┼──► analysis.ipynb
                  │  │  file_id: ghi789    │   │
                  │  └─────────────────────┘   │
                  │                             │
                  └─ Files (still accessible) ──┤
                     - experiment_notes.md      │
                     - setup_photo.jpg          │
                     - analysis.ipynb           │
                     - results.csv (not in page)│
                                                 │
Database: ──────────────────────────────────────┘
  pages (id, notebook_id, title, description)
  blocks (id, page_id, type, file_id, content, position)
  file_metadata (id, path, hash, title, ...)
```

**Characteristics:**
- Pages are organizational containers
- Blocks reference existing files OR contain inline content
- Files can exist with or without being in a page
- Backward compatible (files still accessible directly)
- Database tracks ordering and relationships

**Database Queries:**

```sql
-- Get page with all blocks
SELECT p.*, b.* FROM pages p
LEFT JOIN blocks b ON b.page_id = p.id
WHERE p.id = 'page-uuid'
ORDER BY b.position;

-- Get all pages in notebook
SELECT * FROM pages WHERE notebook_id = 'notebook-uuid';

-- Find which pages contain a file
SELECT p.* FROM pages p
JOIN blocks b ON b.page_id = p.id
WHERE b.file_id = 'file-uuid';
```

---

## Option 2: Pure File-Based Blocks

```
┌─────────────────────────────────────────────┐
│ Workspace                                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Notebook                                     │
│ - .codex/notebook.db (lighter, mostly index)│
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
                  └─ files/ (loose files)
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
- Numbered prefixes enforce ordering
- Metadata in .page.json file (version controlled)
- Very git-friendly
- Renumbering files required when reordering

---

## Option 3: Database-First Blocks (Notion-style)

```
┌─────────────────────────────────────────────┐
│ Workspace                                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
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

| Feature | Current | Option 1 (Hybrid) | Option 2 (File-Based) | Option 3 (DB-First) |
|---------|---------|-------------------|----------------------|---------------------|
| **Storage Model** | Files only | Files + DB refs | Files + .page.json | DB primary |
| **Page Concept** | ❌ None | ✅ DB table | ✅ Directory | ✅ Special block |
| **Block Concept** | ❌ None | ✅ DB table | ⚠️ Implicit | ✅ Universal entity |
| **Inline Content** | ❌ File only | ✅ JSONB field | ❌ File only | ✅ JSONB field |
| **Nested Blocks** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Reorder Speed** | N/A | Fast (DB update) | Slow (rename files) | Fast (DB update) |
| **Git Versioning** | ✅ Perfect | ⚠️ Need .page.json export | ✅ Native | ❌ Export required |
| **Query Complexity** | Simple | Moderate | Simple | Complex (recursive) |
| **API Calls** | 1 (get file) | 2-3 (page + blocks + files) | 1-2 (dir + files) | Many (recursive tree) |
| **Backward Compat** | N/A | ✅ Full | ⚠️ Migration needed | ❌ Breaking |
| **Real-time Collab** | ❌ Hard | ⚠️ Possible | ❌ Hard | ✅ Excellent |

---

## Data Flow Diagrams

### Option 1: Page Render Flow

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

### Option 2: Page Render Flow

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

### Option 3: Page Render Flow

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

**Start with Option 1 (Hybrid File-Reference Blocks)** to get:
- 80% of Notion's organizational benefits
- 100% of current file-based benefits
- Minimal risk and complexity
- Clear evolution path

This approach lets you:
1. **Ship quickly** - Build on existing infrastructure
2. **Learn from users** - Understand what features matter most
3. **Iterate** - Evolve based on real usage patterns
4. **Rollback safely** - Drop feature if it doesn't work out

See [BLOCK_BASED_PAGES.md](./BLOCK_BASED_PAGES.md) for complete analysis and implementation details.

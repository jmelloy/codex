# Block-Based Pages Architecture - Executive Summary

**Full Document**: See [BLOCK_BASED_PAGES.md](./BLOCK_BASED_PAGES.md) for comprehensive analysis.

---

## TL;DR

This document explores transforming Codex from a flat file system into a structured page-based system where pages contain ordered blocks (similar to Notion).

**Current**: `Workspace → Notebook → Files`  
**Proposed**: `Workspace → Notebook → Pages → Blocks (→ Files)`

---

## Three Implementation Options

### Option 1: Hybrid File-Reference Blocks ⭐ **RECOMMENDED**

Pages organize existing files as ordered blocks, with optional inline blocks.

**Pros**: 
- ✅ Preserves file-based strengths (git-friendly, portable)
- ✅ Adds structure without breaking existing workflows
- ✅ Backward compatible (opt-in)
- ✅ Manageable complexity

**Example**:
```
Page: "Experiment Log - 2026-01-28"
  ├─ Block 1: File reference → experiment_notes.md
  ├─ Block 2: File reference → setup_photo.jpg
  ├─ Block 3: Inline text → "Key observation: temperature stable"
  └─ Block 4: File reference → analysis.ipynb
```

### Option 2: Pure File-Based Blocks

Each block is its own numbered file in a page directory.

**Pros**: Filesystem-native, automatic ordering  
**Cons**: Renumbering on reorder, awkward for inline content

**Example**:
```
pages/experiment-2026-01-28/
  001-experiment-notes.md
  002-setup-photo.jpg
  003-observation.txt
  004-analysis.ipynb
  .page.json
```

### Option 3: Database-First Blocks (Notion-style)

Blocks are primarily database records, files referenced when needed.

**Pros**: Maximum flexibility, enables real-time collaboration, nested blocks  
**Cons**: Complex, database-heavy, harder to version control

---

## Comparison Matrix

| Aspect | Current (Files Only) | Option 1 (Hybrid) | Option 2 (File-Based) | Option 3 (Database-First) |
|--------|---------------------|-------------------|----------------------|---------------------------|
| **Simplicity** | ✅ Very Simple | ⚠️ Moderate | ⚠️ Moderate | ❌ Complex |
| **Performance** | ✅ Fast | ⚠️ Good | ✅ Fast | ❌ Query-heavy |
| **Git-Friendly** | ✅ Perfect | ⚠️ Good (need .page.json) | ✅ Perfect | ❌ Poor |
| **Flexibility** | ❌ Limited | ✅ Good balance | ⚠️ Moderate | ✅ Maximum |
| **Real-time Collab** | ❌ File conflicts | ⚠️ Better | ❌ File conflicts | ✅ Excellent |
| **Structure** | ❌ Flat only | ✅ Pages + Blocks | ✅ Pages + Blocks | ✅ Nested blocks |
| **Backward Compat** | N/A | ✅ Fully compatible | ⚠️ Needs migration | ❌ Breaking change |

---

## Recommended Approach

**Start with Option 1 (Hybrid File-Reference Blocks)**

### Implementation Phases

#### Phase 1: Add Pages (3-6 months)
- New `pages` table in notebook databases
- API endpoints for page CRUD
- Frontend pages view
- **Status**: Opt-in, coexists with file browser

#### Phase 2: Add Blocks (6-12 months)
- New `blocks` table with file references
- API for block operations (add, reorder, delete)
- Frontend block renderer and editor
- **Status**: Users can organize files into pages

#### Phase 3: Inline Blocks (12+ months)
- Support inline block types (text, code, quotes)
- Rich block editor
- Auto-export large blocks to files
- **Status**: Full page-based authoring

### Rollback Safety

Each phase is independent and backward compatible:
- Phase 1 only: Pages are optional organizational tool
- Phase 2 only: Blocks just reference existing files
- Can drop feature at any phase without data loss

---

## Key Benefits

1. **Experiment Logs**: Combine notes, images, data, notebooks in single cohesive page
2. **Daily Notes**: Mix inline observations with file references chronologically
3. **Literature Review**: Structured synthesis of multiple sources
4. **Project Planning**: All planning materials in one view
5. **Code Documentation**: Literate programming style docs

---

## Key Challenges

1. **Complexity**: Three-level hierarchy vs simple files
2. **Performance**: Extra queries for page + blocks + files
3. **Mental Model**: Users must learn pages vs files vs blocks
4. **Sync**: Block order in DB, content on filesystem
5. **Migration**: Must support mixed mode (files + pages)

---

## Decision Criteria

**Implement blocks if**:
- Users frequently need to organize related files together
- Narrative structure matters (experiments, reports, tutorials)
- Order of presentation is important
- Mix of file types and inline notes is common

**Don't implement blocks if**:
- Users prefer simple file management
- Performance is critical concern
- Git/filesystem parity is non-negotiable
- Target users are command-line oriented

---

## Next Steps

1. **Gather feedback** on this proposal from users
2. **Prototype** Phase 1 (pages table + basic UI)
3. **User testing** with small group
4. **Iterate** based on feedback
5. **Full implementation** if validated

---

## Database Schema Preview

```sql
-- Phase 1: Pages
CREATE TABLE pages (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP
);

-- Phase 2: Blocks
CREATE TABLE blocks (
    id UUID PRIMARY KEY,
    page_id UUID NOT NULL REFERENCES pages(id),
    block_type VARCHAR(50) NOT NULL,  -- 'file_reference', 'inline_text', etc.
    file_id UUID REFERENCES file_metadata(id),  -- NULL for inline blocks
    content JSONB,  -- For inline content and metadata
    position INTEGER NOT NULL,  -- Ordering within page
    created_time TIMESTAMP,
    UNIQUE(page_id, position)
);
```

---

## API Endpoints Preview

```
# Pages
POST   /api/v1/notebooks/{notebook_id}/pages
GET    /api/v1/notebooks/{notebook_id}/pages
GET    /api/v1/pages/{page_id}
PUT    /api/v1/pages/{page_id}
DELETE /api/v1/pages/{page_id}

# Blocks
POST   /api/v1/pages/{page_id}/blocks
PUT    /api/v1/blocks/{block_id}
DELETE /api/v1/blocks/{block_id}
PUT    /api/v1/pages/{page_id}/blocks/reorder
```

---

## References

- Full analysis: [BLOCK_BASED_PAGES.md](./BLOCK_BASED_PAGES.md)
- Notion API Docs: https://developers.notion.com/
- Current Codex Architecture: [README.md](../../README.md)
- Notebook Migrations: [NOTEBOOK_MIGRATIONS.md](../NOTEBOOK_MIGRATIONS.md)

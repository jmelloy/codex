# Block-Based Pages Architecture

**Document Purpose**: This document explores the concept of a "page" being a shared collection of entries/blocks, where each block is an individual file. This is similar to how Notion works at the database level.

**Date**: 2026-01-28  
**Status**: Design Exploration

---

## Table of Contents

1. [Current Codex Architecture](#current-codex-architecture)
2. [Notion's Block Architecture](#notions-block-architecture)
3. [Block-Based Pages in Codex](#block-based-pages-in-codex)
4. [Implementation Considerations](#implementation-considerations)
5. [Migration Strategy](#migration-strategy)
6. [Use Cases and Benefits](#use-cases-and-benefits)
7. [Challenges and Tradeoffs](#challenges-and-tradeoffs)
8. [Recommendations](#recommendations)

---

## Current Codex Architecture

### Hierarchy

```
User → Workspace → Notebook → Files
```

### Key Characteristics

- **File-centric**: The primary unit of content is a file
- **Flat structure within notebooks**: Files exist directly in notebook directories
- **Metadata-driven**: SQLite databases store metadata, while actual content lives in files
- **No "pages" or "entries"**: These concepts don't exist in the current system

### Storage Model

**System Database** (`codex_system.db`):
- Users, Workspaces, Notebooks, Tasks, Permissions

**Per-Notebook Database** (`notebook.db`):
- FileMetadata (title, description, type, content hash)
- Tags and FileTag relationships
- SearchIndex for full-text search

**File Storage**:
- Actual content stored as files on the filesystem
- Multiple metadata formats supported (frontmatter, sidecars)
- Automatic file watching for change detection
- Git integration for versioning

---

## Notion's Block Architecture

### Overview

Notion treats everything as a **block** - the fundamental unit of content. A page is simply a special block that can contain other blocks.

### Key Concepts

#### 1. Block as Universal Unit

Every piece of content in Notion is a block:
- **Text blocks**: Paragraphs, headings, quotes
- **Media blocks**: Images, videos, files
- **Database blocks**: Tables, boards, galleries
- **Layout blocks**: Columns, dividers
- **Embed blocks**: External content
- **Page blocks**: Pages themselves are blocks

#### 2. Block Properties

Each block has:
- **Unique ID**: UUID identifying the block
- **Type**: What kind of block it is (text, heading, image, etc.)
- **Content**: The actual data/text/reference
- **Properties**: Type-specific metadata
- **Parent ID**: Reference to containing block/page
- **Children**: Array of child block IDs (for nested blocks)
- **Created/Modified timestamps**: Audit trail
- **Created by/Modified by**: User tracking

#### 3. Hierarchical Structure

```
Page (Block)
  ├─ Heading (Block)
  ├─ Text Paragraph (Block)
  ├─ Bulleted List (Block)
  │   ├─ List Item (Block)
  │   └─ List Item (Block)
  ├─ Image (Block)
  └─ Database (Block)
      ├─ Database Row (Block/Page)
      └─ Database Row (Block/Page)
```

#### 4. Database-Level Implementation

Notion likely uses a structure similar to:

```sql
-- Blocks table
CREATE TABLE blocks (
    id UUID PRIMARY KEY,
    type VARCHAR(50),
    parent_id UUID REFERENCES blocks(id),
    content JSONB,
    properties JSONB,
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP,
    created_by UUID REFERENCES users(id),
    last_edited_by UUID REFERENCES users(id)
);

-- Block relationships for ordering
CREATE TABLE block_children (
    parent_id UUID REFERENCES blocks(id),
    child_id UUID REFERENCES blocks(id),
    position INTEGER,
    PRIMARY KEY (parent_id, child_id)
);

-- Pages are just blocks with type='page'
-- Databases are blocks with type='database'
-- Database rows are blocks with type='page' and parent_id = database block
```

#### 5. Key Design Principles

- **Everything is a block**: Consistent abstraction reduces complexity
- **Nested structure**: Blocks can contain blocks (tree structure)
- **Ordering matters**: Position/sequence is tracked explicitly
- **Flexible content**: JSONB allows type-specific data
- **Real-time collaboration**: Block-level locking and updates
- **Efficient queries**: Indexed by parent_id for quick tree traversal

---

## Block-Based Pages in Codex

### Proposed Architecture

Introduce a **Page** entity that contains ordered **Blocks**, where each block can reference a file or be inline content.

### Conceptual Model

```
User → Workspace → Notebook → Page → Blocks (→ Files)
```

### Three Possible Approaches

#### **Option 1: Blocks as File References (Hybrid)**

Pages are organizational containers, blocks are pointers to files.

```
Page "Experiment Log - 2026-01-28"
  ├─ Block 1: File reference → /data/experiment_notes.md
  ├─ Block 2: File reference → /images/setup_photo.jpg
  ├─ Block 3: Inline text → "Key observation: temperature stable"
  └─ Block 4: File reference → /results/analysis.ipynb
```

**Database Schema**:

```sql
-- Pages table
CREATE TABLE pages (
    id UUID PRIMARY KEY,
    notebook_id UUID REFERENCES notebooks(id),
    title VARCHAR(255),
    description TEXT,
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Blocks table
CREATE TABLE blocks (
    id UUID PRIMARY KEY,
    page_id UUID REFERENCES pages(id),
    block_type VARCHAR(50),  -- 'file_reference', 'inline_text', 'inline_code', etc.
    file_id UUID REFERENCES file_metadata(id),  -- NULL for inline blocks
    content JSONB,  -- For inline content and block-specific properties
    position INTEGER,  -- Ordering within page
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP
);

CREATE INDEX idx_blocks_page_position ON blocks(page_id, position);
```

**Filesystem Structure**:

```
workspace/
  notebook1/
    files/
      experiment_notes.md
      setup_photo.jpg
      analysis.ipynb
    pages/
      experiment-2026-01-28.page.json  -- Page metadata + block ordering
    .codex/
      notebook.db  -- Contains FileMetadata, Pages, Blocks tables
```

#### **Option 2: Blocks as Individual Files (Pure File-Based)**

Each block is its own file, pages are just organizational metadata.

```
workspace/
  notebook1/
    pages/
      experiment-2026-01-28/
        001-intro.md              -- Block 1
        002-setup-photo.jpg       -- Block 2
        003-observation.md        -- Block 3
        004-analysis.ipynb        -- Block 4
        .page.json                -- Page metadata (title, description, block order)
```

**Database Schema**:

```sql
-- Pages table
CREATE TABLE pages (
    id UUID PRIMARY KEY,
    notebook_id UUID REFERENCES notebooks(id),
    directory_path VARCHAR(512),  -- Path to page directory
    title VARCHAR(255),
    description TEXT,
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP
);

-- Blocks table links files to pages
CREATE TABLE blocks (
    id UUID PRIMARY KEY,
    page_id UUID REFERENCES pages(id),
    file_id UUID REFERENCES file_metadata(id),
    position INTEGER,
    block_type VARCHAR(50),  -- Derived from file extension or explicit
    created_time TIMESTAMP
);
```

**Block Naming Convention**:
- `001-title.ext` - Position prefix ensures filesystem ordering matches logical order
- `.page.json` - Special metadata file containing page configuration

#### **Option 3: Blocks as Database Entities (Database-First)**

Following Notion's approach more closely - blocks are primarily database records.

```sql
-- Pages are special blocks
CREATE TABLE blocks (
    id UUID PRIMARY KEY,
    block_type VARCHAR(50),  -- 'page', 'text', 'file', 'image', 'code', etc.
    parent_id UUID REFERENCES blocks(id),  -- NULL for top-level pages
    notebook_id UUID REFERENCES notebooks(id),
    content JSONB,  -- Contains all block data
    file_reference UUID REFERENCES file_metadata(id),  -- For file-backed blocks
    position INTEGER,  -- Position within parent
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP,
    created_by UUID REFERENCES users(id),
    last_edited_by UUID REFERENCES users(id)
);

-- Recursive CTE for hierarchical queries
WITH RECURSIVE block_tree AS (
    SELECT * FROM blocks WHERE parent_id IS NULL
    UNION ALL
    SELECT b.* FROM blocks b
    INNER JOIN block_tree bt ON b.parent_id = bt.id
)
SELECT * FROM block_tree;
```

**Filesystem Interaction**:
- Large blocks (files, images, notebooks) still live on filesystem
- Small blocks (text, inline code) stored in JSONB
- `file_reference` column links blocks to `file_metadata` table

---

## Implementation Considerations

### 1. Query Performance

**Challenge**: Retrieving a full page with all blocks requires either:
- Multiple queries (N+1 problem)
- Complex JOINs with ordering
- Recursive queries for nested blocks

**Solutions**:
- **Eager loading**: Fetch page and all blocks in single query
- **Caching**: Cache full page structures in memory
- **Materialized paths**: Store full path in each block for quick hierarchy queries
- **Position indexing**: Compound index on `(page_id, position)` for ordering

### 2. Block Ordering

**Requirements**:
- Blocks must maintain explicit order within a page
- Reordering should be efficient (avoid updating all positions)
- Concurrent reordering must be handled

**Approaches**:

**A. Integer Position (Simple)**
```sql
position INTEGER
```
- Pros: Simple, human-readable
- Cons: Reordering requires updating multiple rows (shift positions)

**B. Fractional Positions (Notion-style)**
```sql
position REAL  -- e.g., 1.0, 1.5, 2.0, 2.25, 2.5, ...
```
- Pros: Insert between blocks without updating others (position = (prev + next) / 2)
- Cons: Can run out of precision over time, requires rebalancing

**C. Linked List**
```sql
previous_block_id UUID REFERENCES blocks(id)
next_block_id UUID REFERENCES blocks(id)
```
- Pros: O(1) reordering, no position updates
- Cons: More complex queries, harder to parallelize traversal

**Recommendation**: Start with **integer position** for simplicity, migrate to fractional if needed.

### 3. Block Types

**Inline Block Types** (stored in database):
- `text` - Rich text paragraph
- `heading` - H1, H2, H3, etc.
- `code` - Inline code snippet
- `quote` - Blockquote
- `list_item` - Bullet or numbered list item
- `divider` - Horizontal rule
- `equation` - LaTeX math

**File-Reference Block Types**:
- `file` - Generic file reference
- `image` - Image file
- `video` - Video file
- `audio` - Audio file
- `notebook` - Jupyter notebook
- `code_file` - Source code file
- `document` - Markdown/text document
- `data` - CSV, JSON, XML data file

**Special Block Types**:
- `page_link` - Reference to another page
- `database` - Embedded database view
- `embed` - External content (future)

### 4. Metadata and Frontmatter

**Current System**: Files have frontmatter/sidecar metadata

**With Blocks**: 
- Page metadata (title, description, tags) stored in `pages` table
- Block-level metadata in `blocks.content` JSONB field
- File-backed blocks still support frontmatter (merged with block metadata)

**Priority**: Block metadata > File frontmatter > Defaults

### 5. File Watching and Sync

**Challenge**: When a file changes on disk, which blocks reference it?

**Solution**:
```sql
-- Query blocks referencing a file
SELECT b.* FROM blocks b
WHERE b.file_reference = (
    SELECT id FROM file_metadata WHERE path = '/path/to/file.md'
);
```

**Watcher Logic**:
1. File change detected
2. Update `file_metadata` table (hash, modified time)
3. Find all blocks referencing this file
4. Update page `last_edited_time` for all parent pages
5. Invalidate caches for affected pages

### 6. Git Integration

**Current System**: Automatic git commits for file changes

**With Blocks**:
- Still commit file changes
- Page structure changes (block ordering, additions, deletions) stored in database
- Consider: Export page structure to `.page.json` files for version control
- Commit `.page.json` alongside content files

### 7. Search and Indexing

**Current System**: Full-text search on file content

**With Blocks**:
- **Option A**: Continue file-level search, return matching pages
- **Option B**: Block-level search index (search within page granularity)

```sql
CREATE TABLE block_search_index (
    block_id UUID REFERENCES blocks(id),
    content_fts TEXT,  -- Full-text search field
    FULLTEXT KEY ft_content (content_fts)
);
```

### 8. Real-Time Collaboration (Future)

Block-level structure enables:
- **Operational Transform** or **CRDTs** for block-level sync
- **Block-level locking**: Multiple users can edit different blocks simultaneously
- **Conflict resolution**: Easier than file-level merging

---

## Migration Strategy

### Phase 1: Introduce Pages (Non-Breaking)

1. Add `pages` table to notebook databases
2. Add API endpoints for page CRUD
3. Frontend: Add "Pages" view alongside existing file browser
4. Allow users to create pages optionally
5. Pages and files coexist independently

**Migration**: None needed (additive feature)

### Phase 2: Introduce Blocks (Hybrid Mode)

1. Add `blocks` table to notebook databases
2. Implement file-reference blocks
3. API: Fetch page with ordered blocks
4. Frontend: Render pages as sequence of blocks
5. Users can add existing files to pages as blocks

**Migration**: Optional - users choose to organize files into pages

### Phase 3: Block-First Editing (Optional)

1. Implement inline block types
2. Add block-level editing in frontend
3. Allow creating blocks directly (without backing files)
4. Consider: Auto-export large blocks to files

**Migration**: Gradual - users can create new content as blocks or files

### Rollback Strategy

- Each phase is opt-in and backward compatible
- Pages table can be dropped without affecting file access
- Blocks table can be dropped without losing file data
- Users can continue using file-only workflow indefinitely

---

## Use Cases and Benefits

### 1. Experiment Logs

**Current**: Create multiple files for each aspect of experiment

**With Blocks**:
```
Page: "Protein Synthesis Experiment - Trial 5"
  ├─ Block: hypothesis.md
  ├─ Block: equipment-setup.jpg
  ├─ Block: inline text: "Initial observations..."
  ├─ Block: raw-data.csv
  ├─ Block: analysis.ipynb
  ├─ Block: inline text: "Conclusions..."
  └─ Block: results-figure.png
```

**Benefit**: Single cohesive view of all experiment assets, ordered logically

### 2. Daily Notes

**Current**: One large markdown file per day

**With Blocks**:
```
Page: "Lab Notes - 2026-01-28"
  ├─ Block: inline text: "Morning: Started protein purification"
  ├─ Block: gel-image.jpg
  ├─ Block: inline text: "Afternoon: Analyzed results"
  ├─ Block: analysis.ipynb
  └─ Block: inline text: "Next steps: Repeat with higher concentration"
```

**Benefit**: Mix inline notes with file references, maintain chronological order

### 3. Literature Review

**Current**: Separate files for each paper, hard to organize

**With Blocks**:
```
Page: "CRISPR Literature Review"
  ├─ Block: inline text: "## Overview"
  ├─ Block: page_link: "Paper: Doudna 2012"
  ├─ Block: inline text: "Key takeaway: ..."
  ├─ Block: page_link: "Paper: Zhang 2013"
  ├─ Block: inline text: "Comparison: ..."
  └─ Block: comparison-table.md
```

**Benefit**: Structured synthesis of multiple sources

### 4. Project Planning

**Current**: Difficult to link task lists with supporting documents

**With Blocks**:
```
Page: "Q1 2026 Project Plan"
  ├─ Block: inline text: "## Objectives"
  ├─ Block: objectives.md
  ├─ Block: inline text: "## Timeline"
  ├─ Block: gantt-chart.png
  ├─ Block: inline text: "## Resources"
  └─ Block: budget.xlsx
```

**Benefit**: All planning materials in one structured view

### 5. Code Documentation

**Current**: README files separate from code

**With Blocks**:
```
Page: "API Authentication System"
  ├─ Block: inline text: "## Overview"
  ├─ Block: auth.py
  ├─ Block: inline text: "## Usage Example"
  ├─ Block: example.py
  ├─ Block: inline text: "## Tests"
  └─ Block: test_auth.py
```

**Benefit**: Literate programming style documentation

---

## Challenges and Tradeoffs

### Challenges

#### 1. Increased Complexity

- **Current**: Simple file → metadata mapping
- **With Blocks**: Three-level hierarchy (pages → blocks → files)
- **Impact**: More database queries, more complex UI, steeper learning curve

#### 2. Performance Overhead

- **Page Rendering**: Must fetch page + blocks + files (multiple joins)
- **Block Reordering**: Potentially many row updates
- **Search**: Must search across files AND inline blocks

#### 3. Mental Model Shift

- **Current Users**: Comfortable with file-based organization
- **New Model**: Must understand pages vs files vs blocks
- **Risk**: Confusion if not designed carefully

#### 4. File System Sync

- **Issue**: Block order and page structure in database, content on filesystem
- **Problem**: Hard to represent page structure in git (need `.page.json` export)
- **Conflict**: What if user renames/moves files outside app?

#### 5. Backward Compatibility

- **Existing Notebooks**: Have no pages/blocks
- **Migration**: Must support mixed mode (files + pages)
- **Complexity**: Two code paths for content access

### Tradeoffs

| Aspect | File-Only | Hybrid (File-Ref Blocks) | Database-First Blocks |
|--------|-----------|--------------------------|----------------------|
| **Simplicity** | ✅ Simple | ⚠️ Moderate | ❌ Complex |
| **Performance** | ✅ Fast file access | ⚠️ Extra queries | ❌ Many queries |
| **Flexibility** | ❌ Rigid | ✅ Good balance | ✅ Maximum flexibility |
| **Git-Friendly** | ✅ All in files | ⚠️ Need `.page.json` | ❌ DB state hard to version |
| **Real-time Collab** | ❌ File-level conflicts | ⚠️ Better but limited | ✅ Block-level sync |
| **Rich Editing** | ❌ Basic | ⚠️ Hybrid | ✅ Full Notion-like |
| **Mobile-Friendly** | ✅ Sync files | ⚠️ Sync files + DB | ❌ DB-heavy |

---

## Recommendations

### Short-Term (Next 3-6 Months)

**Implement Option 1: Hybrid File-Reference Blocks**

#### Why?
- **Preserves current strengths**: Files remain primary storage (git-friendly, portable)
- **Adds structure**: Pages provide organization without breaking existing workflows
- **Low risk**: Backward compatible, opt-in feature
- **Manageable complexity**: Reuses existing file infrastructure

#### Implementation Plan

1. **Database Schema Addition**:
   ```sql
   -- Add to notebook.db migrations
   CREATE TABLE pages (
       id UUID PRIMARY KEY,
       notebook_id UUID NOT NULL,
       title VARCHAR(255) NOT NULL,
       description TEXT,
       created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       last_edited_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       created_by UUID
   );

   CREATE TABLE blocks (
       id UUID PRIMARY KEY,
       page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
       block_type VARCHAR(50) NOT NULL,
       file_id UUID REFERENCES file_metadata(id) ON DELETE SET NULL,
       content JSONB,
       position INTEGER NOT NULL,
       created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       last_edited_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(page_id, position)
   );

   CREATE INDEX idx_blocks_page ON blocks(page_id);
   CREATE INDEX idx_blocks_file ON blocks(file_id);
   ```

2. **API Endpoints**:
   ```
   POST   /api/v1/notebooks/{notebook_id}/pages
   GET    /api/v1/notebooks/{notebook_id}/pages
   GET    /api/v1/pages/{page_id}
   PUT    /api/v1/pages/{page_id}
   DELETE /api/v1/pages/{page_id}
   
   POST   /api/v1/pages/{page_id}/blocks
   PUT    /api/v1/blocks/{block_id}
   DELETE /api/v1/blocks/{block_id}
   PUT    /api/v1/pages/{page_id}/blocks/reorder
   ```

3. **Frontend Components**:
   - `PagesView.vue` - List pages in notebook
   - `PageDetailView.vue` - Display page with ordered blocks
   - `BlockRenderer.vue` - Render individual blocks (file or inline)
   - `BlockEditor.vue` - Add/edit/remove blocks

4. **Core Features**:
   - Create pages
   - Add file references as blocks
   - Add inline text blocks
   - Reorder blocks (drag-and-drop)
   - Delete blocks (doesn't delete file, just reference)
   - Search pages and blocks

### Medium-Term (6-12 Months)

**Evaluate adoption and iterate**:

- Gather user feedback on pages/blocks feature
- Monitor performance (query times, database size)
- Identify most-used block types
- Consider adding more inline block types (code, lists, quotes)
- Improve block editor (rich text, formatting)

### Long-Term (12+ Months)

**Decision Point**: If pages/blocks are successful and heavily used:

**Option A: Stay Hybrid**
- Keep file-reference model
- Enhance with better block types
- Focus on performance optimization

**Option B: Move to Database-First** (Option 3)
- Migrate toward Notion-like architecture
- Implement nested blocks
- Add real-time collaboration
- Consider CRDT-based sync

**Option C: Simplify**
- If adoption is low, consider deprecating
- Keep as optional power-user feature
- Focus on core file-based strengths

---

## Conclusion

The block-based pages concept offers significant potential for organizing related files and inline content into cohesive narratives. However, it introduces complexity that must be carefully managed.

**Recommended Approach**: Start with a **hybrid file-reference block system** (Option 1) that:
- Preserves Codex's file-centric strengths
- Adds optional page organization
- Remains git-friendly and portable
- Provides foundation for future enhancement
- Allows users to opt-in gradually

This approach balances innovation with pragmatism, providing value to users who need structured organization while not forcing a mental model shift on those who prefer simple file management.

The architecture is designed to be **evolutionary** - each phase can be evaluated independently, and the system can remain stable at any level without requiring completion of the full vision.

---

## Appendix A: Notion's Actual Implementation (Research)

Based on reverse engineering Notion's API and public information:

### Block Structure

```json
{
  "object": "block",
  "id": "c02fc1d3-db8b-45c5-a222-27595b15aea7",
  "type": "paragraph",
  "created_time": "2023-03-10T14:30:00.000Z",
  "last_edited_time": "2023-03-10T14:30:00.000Z",
  "has_children": false,
  "paragraph": {
    "rich_text": [
      {
        "type": "text",
        "text": {
          "content": "This is a paragraph block."
        }
      }
    ],
    "color": "default"
  }
}
```

### Key Observations

1. **Type-Specific Content**: Each block type has its own structure under the type key
2. **Rich Text Format**: Text content uses a complex array of styled segments
3. **Has Children Flag**: Indicates if block contains nested blocks
4. **Flat Storage with Relations**: Likely stores blocks flat with parent_id references
5. **API-First**: Notion is API-first, web/mobile apps consume same API

### Performance Optimizations

- **Pagination**: API returns blocks in pages (100 at a time)
- **Lazy Loading**: Child blocks loaded on demand
- **Caching**: Aggressive client-side caching of block trees
- **WebSocket Updates**: Real-time updates pushed for active pages

---

## Appendix B: Alternative Architectures Considered

### Approach: Pure Markdown Extensions

**Concept**: Use markdown with special syntax for blocks

```markdown
# Experiment Log

::block[file|experiment_notes.md]

::block[image|setup_photo.jpg]

::block[text]
Key observation: temperature stable
::end

::block[file|analysis.ipynb]
```

**Pros**: Single file, git-friendly, portable
**Cons**: Custom syntax, hard to reorder, limited metadata

### Approach: Directory-Based Pages

**Concept**: Each page is a directory, blocks are numbered files

```
pages/
  experiment-log/
    001-experiment-notes.md
    002-setup-photo.jpg
    003-observation.txt
    004-analysis.ipynb
    .page.yaml  # Metadata
```

**Pros**: Filesystem-native, automatic ordering
**Cons**: Renumbering on reorder, awkward for inline content

### Approach: JSON-Based Page Files

**Concept**: Page is a JSON file with embedded/referenced content

```json
{
  "title": "Experiment Log",
  "blocks": [
    {"type": "file", "path": "experiment_notes.md"},
    {"type": "file", "path": "setup_photo.jpg"},
    {"type": "text", "content": "Key observation: temperature stable"},
    {"type": "file", "path": "analysis.ipynb"}
  ]
}
```

**Pros**: Structured, versionable, explicit ordering
**Cons**: Duplication (content in JSON and files), merge conflicts

---

## Appendix C: Comparison with Other Systems

### Jupyter Notebooks

- **Model**: Single file, cells as blocks
- **Strength**: Executable code + output in one document
- **Weakness**: Large files, merge conflicts, not hierarchical

### Obsidian

- **Model**: File-per-note, backlinks for connections
- **Strength**: Pure markdown, git-friendly, local-first
- **Weakness**: No built-in block structure, relationships are links only

### Roam Research / Logseq

- **Model**: Block-based outliner, each bullet is a block
- **Strength**: Nested blocks, bidirectional links, block references
- **Weakness**: Proprietary format (EDN), not file-based

### Confluence

- **Model**: Pages with rich content, attachments separate
- **Strength**: Established collaboration features
- **Weakness**: Database-heavy, not git-friendly, slow

### Codex Position

**Unique Value**: Hybrid approach that respects filesystem while adding structure

- Like Obsidian: File-based, git-friendly
- Like Notion: Structured pages with blocks
- Like Jupyter: Mix content types in ordered sequence
- Like Git: Full version history and collaboration

---

## References

1. Notion API Documentation: https://developers.notion.com/
2. Block-Based Editors: ProseMirror, Slate, TipTap
3. CRDTs for Collaboration: Yjs, Automerge
4. Hierarchical Data in SQL: Nested Sets, Materialized Path, Closure Tables
5. Content-Addressable Storage: Git, IPFS

# File-Based Pages Architecture

**Purpose**: Design for implementing page/block organization using pure filesystem structures.

**Date**: 2026-01-28  
**Status**: Design Proposal

---

## Overview

This document proposes a **pure file-based approach** to organizing content into pages with ordered blocks, similar to Notion's page structure but using directories and numbered files instead of database complexity.

### Current Codex Architecture

```
Workspace → Notebook → Files (flat structure)
```

### Proposed Architecture

```
Workspace → Notebook → Pages (directories) → Blocks (numbered files)
```

---

## Design Principles

1. **File-First**: Everything is a file, no hidden database state
2. **Git-Friendly**: Perfect version control with standard git tools
3. **Tool-Agnostic**: Works with any file browser, CLI, or editor
4. **Zero Overhead**: Minimal database (optional index table only)
5. **Transparent**: Users can see and manipulate structure directly

---

## Implementation

### Directory Structure

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
      standalone-doc.md         -- Traditional flat files (coexist)
    .codex/
      notebook.db               -- Minimal index
```

### File Naming Convention

**Format**: `NNN-descriptive-name.ext`

- `NNN` = 001-999 (determines display order)
- Descriptive name for clarity
- Standard file extension

**Examples**:
- `001-hypothesis.md`
- `002-experiment-setup.jpg`
- `003-raw-data.csv`
- `004-analysis.ipynb`

### Page Metadata (.page.json)

Optional file providing page-level information:

```json
{
  "id": "uuid-v4",
  "title": "Experiment Log - 2026-01-28",
  "description": "Initial protein synthesis trial",
  "created_time": "2026-01-28T10:00:00Z",
  "last_edited_time": "2026-01-28T14:30:00Z",
  "tags": ["experiment", "protein-synthesis"],
  "blocks": [
    {"position": 1, "file": "001-hypothesis.md", "type": "markdown"},
    {"position": 2, "file": "002-setup.jpg", "type": "image"},
    {"position": 3, "file": "003-data.csv", "type": "data"},
    {"position": 4, "file": "004-analysis.ipynb", "type": "notebook"}
  ]
}
```

**Note**: `.page.json` is optional. Pages work without it by reading directory contents in numeric order.

---

## Database Schema

### Minimal Index (Optional)

```sql
-- Optional table for search/indexing only
CREATE TABLE pages (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL,
    directory_path VARCHAR(512) NOT NULL,  -- e.g., 'pages/experiment-2026-01-28'
    title VARCHAR(255),
    description TEXT,
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP,
    UNIQUE(notebook_id, directory_path)
);

CREATE INDEX idx_pages_notebook ON pages(notebook_id);
CREATE INDEX idx_pages_path ON pages(directory_path);
```

**No blocks table needed** - blocks are just files, already indexed in `file_metadata` table.

---

## API Design

### Page Operations

```
POST   /api/v1/notebooks/{notebook_id}/pages
       Creates page directory and optional .page.json

GET    /api/v1/notebooks/{notebook_id}/pages
       Lists all page directories in notebook

GET    /api/v1/pages/{page_id}
       Reads directory, .page.json (if exists), and lists blocks

PUT    /api/v1/pages/{page_id}
       Updates .page.json metadata

DELETE /api/v1/pages/{page_id}
       Removes page directory and contents
```

### Block Operations

```
POST   /api/v1/pages/{page_id}/blocks
       Creates a new numbered file in page directory
       Auto-assigns next available number

PUT    /api/v1/pages/{page_id}/blocks/reorder
       Renames files with new numeric prefixes
       Body: [{"file": "001-intro.md", "new_position": 2}, ...]

DELETE /api/v1/pages/{page_id}/blocks/{block_id}
       Deletes the file
```

---

## User Workflows

### Creating a Page

**Via UI/API**:
1. User creates page with title "Experiment Log"
2. System creates `pages/experiment-log/` directory
3. System creates `.page.json` with metadata
4. User adds files as blocks

**Via CLI/Filesystem**:
```bash
# Create page directory
mkdir -p notebook1/pages/experiment-log

# Add blocks (files with numeric prefixes)
cp ~/notes.md notebook1/pages/experiment-log/001-notes.md
cp ~/photo.jpg notebook1/pages/experiment-log/002-photo.jpg

# Optional: Create metadata
echo '{"title": "Experiment Log"}' > notebook1/pages/experiment-log/.page.json
```

### Reordering Blocks

**Via UI/API**:
- Drag-and-drop interface
- API renames files with new numbers

**Via CLI/Filesystem**:
```bash
# Move block 2 to position 1
cd notebook1/pages/experiment-log
mv 001-notes.md temp.md
mv 002-photo.jpg 001-photo.jpg
mv temp.md 002-notes.md
```

Or use `git mv` for git history preservation.

### Adding Blocks

**Via UI/API**:
- Upload/create new file
- System assigns next number (e.g., 005-new-file.md)

**Via CLI/Filesystem**:
```bash
# Find next available number
ls pages/experiment-log/*.* | tail -1  # Shows 004-something.md

# Copy new file with next number
cp ~/new-data.csv pages/experiment-log/005-new-data.csv
```

---

## Use Cases

### 1. Experiment Logs

```
pages/protein-synthesis-trial-5/
  001-hypothesis.md         -- Initial theory
  002-equipment-list.md     -- Materials needed
  003-setup-photo.jpg       -- Lab setup
  004-procedure.md          -- Step-by-step process
  005-raw-data.csv          -- Measurements
  006-analysis.ipynb        -- Data analysis
  007-results-figure.png    -- Visualization
  008-conclusions.md        -- Findings and next steps
  .page.json
```

### 2. Daily Research Notes

```
pages/lab-notes-2026-01-28/
  001-morning-summary.md
  002-meeting-notes.md
  003-gel-electrophoresis.jpg
  004-unexpected-result.md
  005-followup-questions.md
  .page.json
```

### 3. Literature Review

```
pages/crispr-literature-review/
  001-overview.md
  002-doudna-2012.pdf
  003-doudna-notes.md
  004-zhang-2013.pdf
  005-zhang-notes.md
  006-comparison-table.md
  007-synthesis.md
  .page.json
```

### 4. Project Documentation

```
pages/api-authentication-docs/
  001-overview.md
  002-architecture-diagram.png
  003-auth-flow.md
  004-auth.py              -- Source code
  005-usage-example.py
  006-test-auth.py
  007-troubleshooting.md
  .page.json
```

---

## Implementation Phases

### Phase 1: Basic Structure (3-6 months)

**Goals**:
- Implement page directory creation
- Support `.page.json` metadata format
- Basic API endpoints (create, list, get, delete pages)
- Frontend page browser view

**Deliverables**:
- Users can create page directories via UI
- Pages listed alongside traditional files
- Opt-in feature (traditional flat files still work)

### Phase 2: Block Management (6-12 months)

**Goals**:
- Numbered file convention support
- Block reordering via file renaming
- Drag-and-drop UI for reordering
- Batch operations

**Deliverables**:
- Users can add files to pages with auto-numbering
- Visual reordering of blocks
- Efficient rename operations

### Phase 3: Enhanced Tooling (12+ months)

**Goals**:
- CLI tools for page/block management
- Page templates
- Git integration optimizations
- Import/export utilities

**Deliverables**:
- `codex page create "Title"` command
- `codex block add file.md` command
- Template system for common page types
- Migration tools for existing files

---

## Technical Considerations

### Performance

**Advantages**:
- ✅ Fast filesystem operations
- ✅ No complex queries
- ✅ Standard file I/O

**Considerations**:
- Renaming many files (reordering) is O(n)
- Solution: Batch rename operations, optimize with single API call

### Git Integration

**Advantages**:
- ✅ Perfect git history (every file change tracked)
- ✅ Standard `git mv` for renames
- ✅ Easy branching and merging
- ✅ `.page.json` versioned like any file

**Considerations**:
- Renaming shows as delete + add in some git UIs
- Solution: Use `git mv` which preserves history

### File Watcher

**Implementation**:
- Watch page directories for changes
- Update `.page.json` if needed
- Refresh UI when files added/removed/renamed
- Use existing file watcher infrastructure

### Search and Indexing

**Implementation**:
- Index page metadata in `pages` table
- Files already indexed in `file_metadata` table
- Search spans both flat files and page blocks
- Page results show context (which page contains result)

---

## Migration Strategy

### From Flat Files

**No migration needed** - files continue to work:
- Existing flat files in `files/` or root directory
- Pages in `pages/` directory
- Both accessible and searchable

**Optional migration**:
```bash
# User decides to organize files into page
codex page create "Project X"
codex block add file1.md --page "Project X"
codex block add file2.jpg --page "Project X"
```

### Backward Compatibility

- ✅ All existing APIs continue to work
- ✅ File browser shows both flat files and pages
- ✅ Search works across both structures
- ✅ Tags work for both files and pages

---

## Comparison with Alternative Approaches

### Option 1: Hybrid File-Reference Blocks

**Approach**: Database tracks page/block relationships, files remain separate

**Pros**:
- Supports inline content (stored in database)
- Fast reordering (just update position integer)

**Cons**:
- Database complexity (pages + blocks tables)
- Need `.page.json` export for git-friendliness
- Two sources of truth (database + filesystem)

**Why we chose file-based instead**:
- Simpler architecture
- Perfect git integration without export step
- Transparent to users and tools

### Option 3: Database-First Blocks (Notion-style)

**Approach**: Everything is a database record (universal block abstraction)

**Pros**:
- Maximum flexibility
- Nested blocks support
- Real-time collaboration ready

**Cons**:
- Complex recursive queries
- Database is source of truth (hard to version)
- Not tool-agnostic (requires API access)

**Why we chose file-based instead**:
- Much simpler to implement and maintain
- Works with standard tools
- Better aligns with Codex's file-first philosophy

---

## Open Questions

1. **Inline content**: How to handle small text snippets?
   - Option A: Create small text files (e.g., `001-note.txt`)
   - Option B: Store in `.page.json` (hybrid approach)
   - **Recommendation**: Start with Option A (pure file-based)

2. **Collision handling**: What if user manually creates conflicting numbers?
   - Detect conflicts on page load
   - Show warning and offer to renumber
   - API prevents conflicts automatically

3. **Large pages**: Performance with 100+ blocks?
   - Pagination in UI (load blocks in chunks)
   - Lazy loading of file contents
   - Most pages expected to have <20 blocks

4. **Nested pages**: Should pages contain other pages?
   - Not in initial implementation
   - Could add subdirectories later if needed
   - Keep simple for now

---

## Success Metrics

### Adoption Metrics
- Number of pages created
- Average blocks per page
- Percentage of users creating pages (vs only flat files)

### Usage Patterns
- Most common page types/templates
- Average page lifetime
- Reordering frequency

### Technical Metrics
- API response times
- File operation performance
- Search performance (pages vs flat files)

---

## Next Steps

1. **Gather feedback** on this design
2. **Prototype** Phase 1 implementation
   - Create page directory structure
   - Implement `.page.json` format
   - Basic API endpoints
3. **User testing** with small group
4. **Iterate** based on feedback
5. **Full implementation** if validated

---

## Conclusion

The pure file-based approach offers:

✅ **Simplicity** - Directories and numbered files, no database complexity  
✅ **Transparency** - Users can see and manipulate structure directly  
✅ **Git-Friendly** - Perfect version control with standard tools  
✅ **Tool-Agnostic** - Works with any file browser, CLI, or editor  
✅ **Zero Overhead** - Minimal database (optional index only)  
✅ **Backward Compatible** - Coexists with traditional flat files  

This design aligns with Codex's file-first philosophy while adding valuable organizational structure for users who need it. The system remains simple, transparent, and accessible whether users interact via UI, API, or directly with the filesystem.

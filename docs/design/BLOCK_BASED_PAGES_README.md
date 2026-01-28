# Block-Based Pages Documentation

This directory contains comprehensive documentation exploring how Codex could implement a page/block architecture similar to Notion.

## Quick Navigation

### 🚀 Start Here

**New to this concept?** Start with the [Executive Summary](BLOCK_BASED_PAGES_SUMMARY.md) for a quick overview.

**Want visuals?** Check out the [Visual Diagrams](BLOCK_BASED_PAGES_DIAGRAMS.md) for architecture comparisons and data flow.

**Need full details?** Read the complete [Architecture Document](BLOCK_BASED_PAGES.md).

### 📚 Documents

| Document | Length | Purpose |
|----------|--------|---------|
| [**BLOCK_BASED_PAGES.md**](BLOCK_BASED_PAGES.md) | 881 lines | Complete analysis with research, implementation details, and recommendations |
| [**BLOCK_BASED_PAGES_SUMMARY.md**](BLOCK_BASED_PAGES_SUMMARY.md) | 208 lines | Executive summary with comparison matrix and key decisions |
| [**BLOCK_BASED_PAGES_DIAGRAMS.md**](BLOCK_BASED_PAGES_DIAGRAMS.md) | 446 lines | Visual architecture diagrams and data flow examples |

**Total:** 1,535 lines of comprehensive documentation

---

## What's Inside

### Current Architecture Analysis
- File-centric model (Workspace → Notebook → Files)
- Database schema and storage patterns
- Strengths and limitations

### Notion's Block Model
- Everything-as-a-block approach
- Hierarchical structure
- Database implementation patterns
- Key design principles

### Three Implementation Options

#### ⭐ Option 2: Pure File-Based Blocks (RECOMMENDED)
- Each block is a numbered file
- Page directories
- Maximum git-friendliness
- Zero database overhead

#### Option 1: Hybrid File-Reference Blocks
- Pages organize files as ordered blocks
- Optional inline blocks
- Backward compatible
- Database tracks ordering

#### Option 3: Database-First Blocks (Notion-style)
- Universal block abstraction
- Nested blocks
- Real-time collaboration ready

### Implementation Details
- Database schemas for all options
- Query patterns and performance considerations
- Block ordering strategies
- File watching and sync
- Git integration
- Search indexing
- Migration paths

### Use Cases
- Experiment logs
- Daily notes
- Literature reviews
- Project planning
- Code documentation

### Challenges & Tradeoffs
- Complexity analysis
- Performance implications
- Mental model shifts
- Backward compatibility
- Git integration considerations

---

## Key Recommendation

**Implement Option 2: Pure File-Based Blocks**

This approach offers:
- ✅ 100% git-friendly and portable
- ✅ Works with any file tool/CLI
- ✅ Zero database overhead
- ✅ Simple, transparent architecture
- ✅ Fully backward compatible

### Implementation Timeline

```
Phase 1 (3-6 months)
  └─ Directory structure + .page.json format
     └─ Users can create page directories

Phase 2 (6-12 months)
  └─ Numbered file convention + reordering API
     └─ Users can organize files with numeric prefixes

Phase 3 (12+ months)
  └─ Enhanced tooling and templates
     └─ Mature file-based page system
```

Each phase is independent and rollback-safe.

---

## Quick Reference

### File Structure (Option 2)

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

### .page.json Format (Option 2)

```json
{
  "id": "uuid",
  "title": "Experiment Log - 2026-01-28",
  "description": "Initial protein synthesis trial",
  "created_time": "2026-01-28T10:00:00Z",
  "blocks": [
    {"position": 1, "file": "001-intro.md", "type": "markdown"},
    {"position": 2, "file": "002-setup-photo.jpg", "type": "image"},
    {"position": 3, "file": "003-observation.md", "type": "markdown"},
    {"position": 4, "file": "004-analysis.ipynb", "type": "notebook"}
  ]
}
```

### Minimal Database Schema (Option 2)

```sql
-- Optional index table for search
CREATE TABLE pages (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL,
    directory_path VARCHAR(512) NOT NULL,
    title VARCHAR(255),
    created_time TIMESTAMP,
    last_edited_time TIMESTAMP
);
-- No blocks table needed - blocks are just files
```

### API Endpoints (Option 2)

```
# Pages (directory operations)
POST   /api/v1/notebooks/{notebook_id}/pages          -- Create directory
GET    /api/v1/notebooks/{notebook_id}/pages          -- List directories
GET    /api/v1/pages/{page_id}                        -- Read dir + .page.json
PUT    /api/v1/pages/{page_id}                        -- Update .page.json
DELETE /api/v1/pages/{page_id}                        -- Remove directory

# Blocks (file operations)
POST   /api/v1/pages/{page_id}/blocks                 -- Create numbered file
PUT    /api/v1/pages/{page_id}/blocks/reorder         -- Rename files
DELETE /api/v1/pages/{page_id}/blocks/{block_id}      -- Delete file
```

---

## Comparison Matrix

| Aspect | Current | Option 2 ⭐ | Option 1 | Option 3 |
|--------|---------|----------|----------|----------|
| **Simplicity** | ✅ | ✅ | ⚠️ | ❌ |
| **Performance** | ✅ | ✅ | ⚠️ | ❌ |
| **Git-Friendly** | ✅ | ✅ | ⚠️ | ❌ |
| **Flexibility** | ❌ | ⚠️ | ✅ | ✅ |
| **Structure** | ❌ | ✅ | ✅ | ✅ |
| **Real-time Collab** | ❌ | ❌ | ⚠️ | ✅ |
| **Tool Integration** | ✅ | ✅ | ⚠️ | ⚠️ |

Legend: ✅ Excellent | ⚠️ Good | ❌ Limited

---

## Next Steps

1. **Review** - Discuss file-based approach with team
2. **Feedback** - Gather user input on directory/file structure
3. **Prototype** - Build Phase 1 (directory structure + .page.json)
4. **Test** - User testing with file tools and CLI
5. **Iterate** - Refine based on feedback
6. **Implement** - Full rollout if validated

---

## Questions?

For questions or discussions about this architecture:
1. Review the [main document](BLOCK_BASED_PAGES.md) for detailed analysis
2. Check the [diagrams](BLOCK_BASED_PAGES_DIAGRAMS.md) for visual explanations
3. Open an issue in the repository for specific questions

---

**Document Created:** 2026-01-28  
**Status:** Design Exploration  
**Related:** [Notebook Migrations](../NOTEBOOK_MIGRATIONS.md), [Dynamic Views](./dynamic-views.md)

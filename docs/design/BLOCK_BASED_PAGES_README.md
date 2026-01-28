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

#### ⭐ Option 1: Hybrid File-Reference Blocks (RECOMMENDED)
- Pages organize files as ordered blocks
- Optional inline blocks
- Backward compatible
- Git-friendly

#### Option 2: Pure File-Based Blocks
- Each block is a numbered file
- Page directories
- Maximum git-friendliness

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

**Implement Option 1: Hybrid File-Reference Blocks**

This approach offers the best balance of:
- ✅ File-based strengths preserved
- ✅ Structured organization added
- ✅ Backward compatible (opt-in)
- ✅ Foundation for future features
- ✅ Manageable complexity

### Implementation Timeline

```
Phase 1 (3-6 months)
  └─ Add pages table and UI
     └─ Users can create pages alongside files

Phase 2 (6-12 months)
  └─ Add blocks with file references
     └─ Users can organize files into pages

Phase 3 (12+ months)
  └─ Add inline block types
     └─ Full page-based authoring
```

Each phase is independent and rollback-safe.

---

## Quick Reference

### Database Schema (Option 1)

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
    block_type VARCHAR(50) NOT NULL,
    file_id UUID REFERENCES file_metadata(id),
    content JSONB,
    position INTEGER NOT NULL,
    created_time TIMESTAMP,
    UNIQUE(page_id, position)
);
```

### API Endpoints (Option 1)

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

## Comparison Matrix

| Aspect | Current | Option 1 | Option 2 | Option 3 |
|--------|---------|----------|----------|----------|
| **Simplicity** | ✅ | ⚠️ | ⚠️ | ❌ |
| **Performance** | ✅ | ⚠️ | ✅ | ❌ |
| **Git-Friendly** | ✅ | ⚠️ | ✅ | ❌ |
| **Flexibility** | ❌ | ✅ | ⚠️ | ✅ |
| **Structure** | ❌ | ✅ | ✅ | ✅ |
| **Real-time Collab** | ❌ | ⚠️ | ❌ | ✅ |

Legend: ✅ Excellent | ⚠️ Good | ❌ Limited

---

## Next Steps

1. **Review** - Discuss documentation with team
2. **Feedback** - Gather user input on the concept
3. **Prototype** - Build Phase 1 (pages table + UI)
4. **Test** - User testing with small group
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

# Frontend Blocks Migration Evaluation

## Current State

The backend completed a full unification of files/folders into a single `Block` model (migrations 007-010, March 2026). The `file_metadata` table has been dropped; everything is now in `blocks`. However, the **frontend still carries significant legacy file/folder code** alongside the newer block-based code, resulting in dual code paths, fallback logic, and adapter layers.

## Architecture Layers with Duplication

### 1. Service Layer (`services/codex.ts`)

| Legacy | Block-based | Status |
|--------|-------------|--------|
| `FolderMetadata` interface (lines 24-34) | `Block` interface (lines 58-97) | **Redundant** — Block covers all folder fields |
| `SubfolderMetadata` interface (lines 36-46) | `Block` with `block_type: "page"` | **Redundant** |
| `FolderWithFiles` interface (lines 48-56) | `Block` with `children` | **Hybrid** — mixes `is_page`, `page_block_id`, `blocks` into folder response |
| `folderService.get()` | `blockService.getBlock()` + `getChildren()` | **Redundant** — both hit `/folders/` and `/blocks/` endpoints |
| `folderService.updateProperties()` | `blockService.updateProperties()` | **Redundant** |
| `folderService.delete()` | `blockService.deleteBlock()` | **Redundant** |

**Recommendation**: Remove `folderService`, `FolderMetadata`, `SubfolderMetadata`. Replace `FolderWithFiles` with a `PageView` type derived from `Block`.

### 2. Store Layer (`stores/workspace.ts`)

**Parallel state:**

| Legacy State | Block State | Purpose |
|-------------|-------------|---------|
| `currentFile` (ref) | `currentBlock` (ref) | Currently viewed item |
| `currentFolder` (ref) | `currentPageMeta` (ref) | Currently viewed page/folder metadata |
| `fileTrees` (Map) | Built from `blockService.getTree()` | Sidebar tree — already unified |
| `fileLoading` | `blockLoading` | Loading indicators |
| `folderLoading` | (none) | Folder-specific loading |

**Parallel actions (high duplication):**

| Legacy Action | Block Action | Overlap |
|--------------|-------------|---------|
| `selectFile()` (line 261) | `selectBlock()` (line 783) | selectBlock already handles leaf blocks |
| `selectFolder()` (line 514) | `selectBlock()` for pages | selectBlock handles pages too |
| `fetchFolderContents()` (line 175) | `fetchPageBlocks()` (line 626) | Both load children of a container |
| `fetchRootContents()` (line 232) | `fetchBlockTree()` (line 761) | fetchBlockTree supersedes |
| `saveFile()` (line 303) | `updateBlock()` (line ?) | Same underlying API |
| `createFile()` (line 339) | `createPage()` (line 646) | createFile already delegates to blockService |
| `deleteFile()` (line 361) | `deleteBlock()` (line 724) | Both use blockService.deleteBlock |
| `saveFolderProperties()` (line 536) | `updateBlock()` via blockService | folder version uses legacy folderService |
| `deleteFolder()` (line 584) | `deleteBlock()` | folder version uses legacy folderService |

**Fallback patterns (fragile):**
- `fetchFolderContents()` tries block API, catches error, falls back to `folderService.get()` (lines 185-210)
- `fetchRootContents()` tries `blockService.getTree()`, catches error, falls back to legacy (lines 244-246)
- WebSocket handler references both `currentBlock` and `currentFile` (lines 421-427)

**Recommendation**: Consolidate to a single `currentBlock` ref and `selectBlock()` action. Remove `currentFile`, `currentFolder`, `selectFile()`, `selectFolder()`, and all fallback branches.

### 3. View Layer (`views/HomeView.vue`)

Three conditional branches for content display (lines 506-706):

```
1. v-if="currentFile"                              → FileHeader + content viewers
2. v-else-if="currentFolder && currentFolder.is_page" → BlockView (page editor)
3. v-else-if="currentFolder"                         → Legacy folder view
```

This should collapse to two:

```
1. v-if="currentBlock.block_type === 'page'"  → BlockView (page editor)
2. v-else-if="currentBlock"                    → Content viewer (markdown, image, code, etc.)
```

**Additional duplication in HomeView:**
- `buildFileUrl()` and `buildFolderUrl()` — identical URL construction (lines 965-979)
- Route restoration tries `blockService.resolveLink()` then falls back to `selectFolder()` (lines 1034-1040)
- Sidebar rendering has separate branches for `node.type === 'folder'` vs file (lines 305-382)

### 4. Tree Utilities (`utils/fileTree.ts`)

`FileTreeNode` is an adapter type that bridges blocks to a tree format the sidebar understands:

```typescript
interface FileTreeNode {
  name: string
  path: string
  type: "file" | "folder"          // Legacy concept
  block_id?: string                 // Block concept
  block_type?: string               // Block concept
  isPage?: boolean                  // Redundant with block_type === "page"
  file?: Block                      // Wraps the actual block
  folderMeta?: { ... }             // Duplicates block properties
}
```

**Functions with dual-mode logic:**
- `blockTreeToFileTree()` — converts blocks into FileTreeNode (adapter)
- `buildFileTree()` — builds tree from flat file list (fully legacy, unused if block tree works)
- `mergeFolderContents()` — merges legacy folder API response into tree
- `insertFolderNode()` — inserts folder with `SubfolderMetadata`

**Recommendation**: Replace `FileTreeNode` with `Block` directly (blocks already have `children`, `parent_block_id`, `block_type`). The tree structure is native to the block model.

### 5. Components

| Component | Current State | Migration Path |
|-----------|--------------|----------------|
| `BlockView.vue` | Block-native, no legacy code | **Keep as-is** |
| `FileHeader.vue` | Accepts `Block` but named/styled for "files" | Rename to `BlockHeader.vue`, simplify |
| `FilePropertiesPanel.vue` | Dual-mode: handles both `currentFile` and `currentBlock` with manual field mapping (lines 744-771) | Unify to accept `Block` only |
| `FileTreeItem.vue` | Renders `FileTreeNode` with `isPage` checks | Rewrite to render `Block` tree directly |
| `MarkdownViewer.vue` | Block-native via plugin system | **Keep as-is** |

## Migration Plan

### Phase 1: Remove `folderService` and Legacy Interfaces

**Files**: `services/codex.ts`
- Delete `FolderMetadata`, `SubfolderMetadata` interfaces
- Delete `folderService` (3 methods)
- Simplify `FolderWithFiles` into a `PageWithChildren` type or remove entirely
- **Risk**: Low. All folder operations already have block equivalents.
- **Backend**: Verify `/folders/` routes can be deprecated. The block routes cover all operations.

### Phase 2: Unify Store State

**Files**: `stores/workspace.ts`
- Replace `currentFile` + `currentFolder` with single `currentBlock: ref<Block | null>`
- Add computed: `isPage = computed(() => currentBlock.value?.block_type === 'page')`
- Add `currentPageChildren: ref<Block[]>` (rename from `currentPageBlocks`)
- Remove: `selectFile()`, `selectFolder()`, `fetchFolderContents()`, `fetchRootContents()`
- Remove: `saveFolderProperties()`, `deleteFolder()`, `clearFolderSelection()`
- Keep: `selectBlock()` as the single entry point (it already handles both cases)
- Remove all try/catch fallback branches to legacy services
- **Risk**: Medium. Many components reference `currentFile`/`currentFolder`. Requires coordinated updates.

### Phase 3: Simplify Tree Layer

**Files**: `utils/fileTree.ts`
- Option A: Replace `FileTreeNode` with `Block` directly (blocks already have hierarchy)
- Option B: Slim down `FileTreeNode` to only add UI state (expanded, selected) on top of `Block`
- Remove `buildFileTree()`, `mergeFolderContents()`, `insertFolderNode()` (legacy functions)
- Keep `blockTreeToFileTree()` only if Option B, otherwise remove
- **Risk**: Medium. Sidebar rendering and drag-drop depend on `FileTreeNode` shape.

### Phase 4: Simplify View Layer

**Files**: `views/HomeView.vue`, `components/FileHeader.vue`, `components/FilePropertiesPanel.vue`, `components/FileTreeItem.vue`
- Collapse three-branch content display to two (page vs leaf block)
- Merge `buildFileUrl()` and `buildFolderUrl()` into `buildBlockUrl()`
- Simplify route restoration to only use `blockService.resolveLink()`
- Rename `FileHeader` → `BlockHeader`, `FilePropertiesPanel` → `BlockPropertiesPanel`
- Update `FileTreeItem` to work with `Block` (or slim `TreeNode`) instead of `FileTreeNode`
- **Risk**: Low-medium. Primarily template and prop changes.

### Phase 5: Backend Cleanup

**Files**: `backend/codex/api/routes/folders.py`, `backend/codex/api/routes/files.py`
- Deprecate `/folders/` routes (add deprecation headers)
- Redirect or alias remaining `/files/` routes to `/blocks/` equivalents
- Eventually remove the route files entirely
- **Risk**: Low if frontend no longer calls them.

## Metrics

| Metric | Before | After (Est.) |
|--------|--------|-------------|
| Service interfaces | 4 (Block, FolderMetadata, SubfolderMetadata, FolderWithFiles) | 1 (Block) |
| Service objects | 3 (blockService, folderService, searchService) | 2 (blockService, searchService) |
| Store state refs | 7 (currentFile, currentFolder, currentBlock, currentPageBlocks, currentPageMeta, currentPageBlockId, blockLoading + fileLoading + folderLoading) | 4 (currentBlock, currentPageChildren, currentPageBlockId, loading) |
| Store actions (file/folder) | ~12 | 0 (consolidated into block actions) |
| Store actions (block) | ~8 | ~8 (unchanged, now the only path) |
| Conditional branches in HomeView | 3 content paths + fallback logic | 2 content paths, no fallbacks |
| Tree adapter types | FileTreeNode (29 fields) | Block + UI state (or direct Block usage) |
| Lines removable (est.) | — | ~400-600 across store, services, utils |

## Key Decision: FileTreeNode vs Direct Block Usage

The biggest architectural decision is whether the sidebar tree should use `Block` objects directly or a thin wrapper:

**Option A: Direct Block usage**
- Pro: No adapter layer, no conversion, single source of truth
- Con: Need to add UI state (expanded, selected, loading) somewhere — possibly a separate Map

**Option B: Thin TreeNode wrapper**
- Pro: Clean separation of data vs UI state, familiar pattern
- Con: Still requires conversion, but much simpler than current `FileTreeNode`

**Recommendation**: Option B with a minimal wrapper:
```typescript
interface TreeNode {
  block: Block
  children: TreeNode[]
  expanded: boolean
  selected: boolean
}
```

This preserves the tree's UI state separately while referencing the canonical `Block` object.

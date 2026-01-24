# Dynamic Views Design Document

**Version:** 1.1
**Date:** 2026-01-24
**Status:** Implemented (v1)

## Executive Summary

Dynamic Views introduce a new document type in Codex that can execute queries, aggregate content, and render interactive visualizations. Unlike static markdown files, dynamic views execute at render-time to display live data from the workspace, supporting use cases like kanban boards, photo galleries, rollup reports, and composable dashboards.

## Goals

1. **Query & Aggregate**: Enable views to query files across notebooks by metadata, tags, dates, and content
2. **Dynamic Rendering**: Support specialized view types (kanban, gallery, calendar, etc.)
3. **Composability**: Allow embedding mini-views within dashboards
4. **Interactivity**: Enable editing through views (e.g., changing task status, reordering items)
5. **Extensibility**: Provide a framework for custom view types

## Non-Goals

- Real-time collaboration (out of scope for v1)
- Complex data transformations (use simple aggregation queries)
- External API integrations (future enhancement, weather example deferred)

---

## Architecture Overview

### Component Stack

```
┌─────────────────────────────────────────────┐
│        Frontend View Components             │
│  (KanbanView, GalleryView, RollupView)     │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│         View Runtime Engine                 │
│  - Parse view definitions (.cdx files)      │
│  - Execute queries                          │
│  - Render components                        │
│  - Handle interactions                      │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│         Query & Aggregation API             │
│  - Advanced file filtering                  │
│  - Tag-based queries                        │
│  - Date range queries                       │
│  - Property-based filtering                 │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│      Existing Codex Data Layer              │
│  (Workspace, Notebook, FileMetadata)        │
└─────────────────────────────────────────────┘
```

---

## View Definition Format

### File Type: `.cdx` (Codex Dynamic View)

Dynamic views are stored as `.cdx` files with YAML frontmatter + JavaScript/Vue configuration:

```yaml
---
type: view
view_type: kanban
title: Project Tasks
description: Kanban board of all tasks
query:
  tags: [task, todo]
  properties:
    status: [todo, in-progress, done]
  sort: created_at desc
config:
  columns:
    - id: todo
      title: To Do
      filter: { status: todo }
    - id: in-progress
      title: In Progress
      filter: { status: in-progress }
    - id: done
      title: Done
      filter: { status: done }
  groupBy: status
  editable: true
---
# Optional markdown content or instructions
This board shows all tasks across the workspace.
```

### Alternative: MDX-style Format

For more complex views with embedded logic:

```mdx
---
type: view
view_type: dashboard
title: Daily Dashboard
---

<script setup>
const tasks = query({ tags: ['task'], properties: { due: 'today' } })
const weather = externalData('weather', { location: 'current' })
const journal = query({ path: 'journal/2026-01-22.md' })
</script>

<Dashboard>
  <Row>
    <Column span={8}>
      <TaskList :items="tasks" view="compact" />
    </Column>
    <Column span={4}>
      <WeatherWidget :data="weather" />
    </Column>
  </Row>
  <Row>
    <Column span={12}>
      <JournalEntry :file="journal" />
    </Column>
  </Row>
</Dashboard>
```

**Decision**: Start with YAML frontmatter for v1 (simpler parsing, less security risk), add MDX in v2 if needed.

---

## Query & Data Layer

### Query API Extension

Add new endpoint: `GET /api/v1/query?workspace_id=X`

**Query Schema:**

```typescript
interface ViewQuery {
  // Scope
  notebook_ids?: number[]; // Limit to specific notebooks
  paths?: string[]; // Limit to specific paths (glob support)

  // Filtering
  tags?: string[]; // Files with ALL these tags
  tags_any?: string[]; // Files with ANY of these tags
  file_types?: string[]; // Filter by file type

  // Property filtering
  properties?: {
    // Filter by frontmatter properties
    [key: string]: any | any[]; // Exact match or "in" match
  };
  properties_exists?: string[]; // Files with these properties defined

  // Date filtering
  created_after?: string; // ISO date
  created_before?: string;
  modified_after?: string;
  modified_before?: string;

  // Date properties
  date_property?: string; // Property name (e.g., "due_date")
  date_after?: string; // Filter by property date
  date_before?: string;

  // Content filtering
  content_search?: string; // Full-text search

  // Sorting & pagination
  sort?: string; // "created_at desc", "title asc", "properties.priority desc"
  limit?: number;
  offset?: number;

  // Aggregation
  group_by?: string; // Group results by property
}

interface QueryResult {
  files: FileMetadata[];
  groups?: {
    // If group_by specified
    [key: string]: FileMetadata[];
  };
  total: number;
  limit: number;
  offset: number;
}
```

### Implementation

**Backend**: `backend/api/routes/query.py`

```python
@router.get("/")
async def query_files(
    workspace_id: int,
    query: ViewQuery,
    current_user: User = Depends(get_current_user)
):
    # 1. Verify workspace access
    workspace = verify_workspace_access(workspace_id, current_user)

    # 2. Get all notebooks in workspace (or filtered subset)
    notebooks = get_notebooks(workspace, query.notebook_ids)

    # 3. Query each notebook's DB
    results = []
    for notebook in notebooks:
        session = get_notebook_session(notebook)

        # Build SQLAlchemy query
        q = session.query(FileMetadata)

        # Apply filters
        if query.tags:
            q = q.join(FileTag).join(Tag).filter(Tag.name.in_(query.tags))

        if query.properties:
            for key, value in query.properties.items():
                # JSON path query: properties->key = value
                q = q.filter(
                    FileMetadata.properties[key].astext == str(value)
                )

        if query.created_after:
            q = q.filter(FileMetadata.created_at >= query.created_after)

        # ... more filters

        results.extend(q.all())

    # 4. Sort and paginate
    results = apply_sort(results, query.sort)
    total = len(results)
    results = results[query.offset:query.offset + query.limit]

    # 5. Group if requested
    groups = None
    if query.group_by:
        groups = group_by_property(results, query.group_by)

    return QueryResult(
        files=results,
        groups=groups,
        total=total,
        limit=query.limit,
        offset=query.offset
    )
```

**Frontend**: `frontend/src/services/query.ts`

```typescript
export interface QueryService {
  execute(workspaceId: number, query: ViewQuery): Promise<QueryResult>;
}

export const queryService: QueryService = {
  async execute(workspaceId, query) {
    const response = await api.get("/query", {
      params: { workspace_id: workspaceId },
      data: query,
    });
    return response.data;
  },
};
```

---

## View Types

### 1. Kanban Board

**File**: `projects/tasks.cdx`

```yaml
---
type: view
view_type: kanban
title: Project Tasks
query:
  tags: [task]
config:
  columns:
    - id: backlog
      title: Backlog
      filter: { status: backlog }
    - id: todo
      title: To Do
      filter: { status: todo }
    - id: in-progress
      title: In Progress
      filter: { status: in-progress }
    - id: done
      title: Done
      filter: { status: done }
  card_fields:
    - title
    - description
    - tags
    - due_date
  drag_drop: true
  editable: true
---
```

**Component**: `KanbanView.vue`

- Renders columns based on config
- Groups files by `status` property
- Drag-drop updates file's `status` property
- Click card to open in editor

### 2. Photo Gallery

**File**: `photos/gallery.cdx`

```yaml
---
type: view
view_type: gallery
title: Photo Gallery
query:
  file_types: [image/png, image/jpeg, image/gif]
  paths: ["photos/**/*"]
  sort: file_created_at desc
config:
  layout: grid
  columns: 4
  thumbnail_size: 300
  show_metadata: true
  lightbox: true
---
```

**Component**: `GalleryView.vue`

- Grid layout of image thumbnails
- Click to open lightbox
- Show EXIF data from frontmatter
- Support for captions from `description`

### 3. Rollup Report

**File**: `reports/weekly-rollup.cdx`

```yaml
---
type: view
view_type: rollup
title: Weekly Activity Report
query:
  created_after: "{{ startOfWeek }}"
  created_before: "{{ endOfWeek }}"
  sort: created_at desc
config:
  group_by: created_at
  group_format: day
  show_stats: true
  sections:
    - title: New Tasks
      filter: { tags: [task] }
    - title: Journal Entries
      filter: { tags: [journal] }
    - title: Notes
      filter: { file_types: [markdown] }
---
```

**Component**: `RollupView.vue`

- Groups files by date
- Shows daily sections with file lists
- Statistics summary (counts, tags)
- Expandable sections

### 4. Dashboard (Composite)

**File**: `home/dashboard.cdx`

```yaml
---
type: view
view_type: dashboard
title: Daily Dashboard
layout:
  - type: row
    components:
      - type: mini-view
        span: 8
        view: tasks/today.cdx
      - type: mini-view
        span: 4
        view: widgets/weather.cdx
  - type: row
    components:
      - type: mini-view
        span: 12
        view: journal/today.cdx
---
```

**Component**: `DashboardView.vue`

- Grid system (12-column)
- Embeds other `.cdx` views
- Each mini-view is isolated
- Responsive layout

### 5. Novel Cork Board

**File**: `novel/outline.cdx`

```yaml
---
type: view
view_type: corkboard
title: Novel Outline
query:
  paths: ["novel/chapters/**/*.md"]
  sort: properties.chapter_number asc
config:
  group_by: chapter
  card_style: notecard
  layout: freeform
  draggable: true
  editable: true
  card_fields:
    - scene_number
    - characters
    - summary
---
```

**Component**: `CorkboardView.vue`

- Free-form canvas with draggable cards
- Group by chapter (swim lanes)
- Each card is a scene/section
- Drag to reorder scenes
- Visual styling (cork background, pinned notes)

---

## View Runtime Engine

### Frontend: `frontend/src/components/views/ViewRenderer.vue`

Main component that:

1. Loads `.cdx` file content
2. Parses frontmatter (query + config)
3. Executes query via API
4. Renders appropriate view component
5. Handles interactions (edits, drag-drop)

```vue
<template>
  <component
    :is="viewComponent"
    :data="queryResults"
    :config="viewConfig"
    @update="handleUpdate"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { parseViewDefinition } from "@/services/viewParser";
import { queryService } from "@/services/query";
import KanbanView from "./KanbanView.vue";
import GalleryView from "./GalleryView.vue";
import RollupView from "./RollupView.vue";
import DashboardView from "./DashboardView.vue";
import CorkboardView from "./CorkboardView.vue";

const props = defineProps<{
  fileId: number;
  workspaceId: number;
}>();

const viewDefinition = ref(null);
const queryResults = ref(null);
const loading = ref(true);

// Load view definition
const loadView = async () => {
  const file = await fileService.get(props.fileId, props.workspaceId);
  viewDefinition.value = parseViewDefinition(file.content);

  // Execute query
  queryResults.value = await queryService.execute(
    props.workspaceId,
    viewDefinition.value.query,
  );

  loading.value = false;
};

// Map view type to component
const viewComponent = computed(() => {
  switch (viewDefinition.value?.view_type) {
    case "kanban":
      return KanbanView;
    case "gallery":
      return GalleryView;
    case "rollup":
      return RollupView;
    case "dashboard":
      return DashboardView;
    case "corkboard":
      return CorkboardView;
    default:
      return null;
  }
});

const viewConfig = computed(() => viewDefinition.value?.config || {});

// Handle updates from view (e.g., drag-drop)
const handleUpdate = async (event: ViewUpdateEvent) => {
  const { fileId, updates } = event;

  // Update file properties
  const file = await fileService.get(fileId, props.workspaceId);
  await fileService.update(fileId, props.workspaceId, {
    properties: { ...file.properties, ...updates },
  });

  // Refresh query
  await loadView();
};

watch(() => props.fileId, loadView, { immediate: true });
</script>
```

### View Parser: `frontend/src/services/viewParser.ts`

```typescript
import matter from "gray-matter";

export interface ViewDefinition {
  type: "view";
  view_type: string;
  title: string;
  description?: string;
  query: ViewQuery;
  config: Record<string, any>;
  layout?: any[];
  content?: string; // Markdown content after frontmatter
}

export function parseViewDefinition(content: string): ViewDefinition {
  const { data, content: markdown } = matter(content);

  // Validate required fields
  if (data.type !== "view") {
    throw new Error("Not a valid view definition");
  }

  // Process template variables in query (e.g., {{ startOfWeek }})
  const query = processQueryTemplates(data.query);

  return {
    type: data.type,
    view_type: data.view_type,
    title: data.title,
    description: data.description,
    query,
    config: data.config || {},
    layout: data.layout,
    content: markdown,
  };
}

function processQueryTemplates(query: ViewQuery): ViewQuery {
  // Replace template variables with computed values
  const replacements = {
    "{{ startOfWeek }}": startOfWeek().toISOString(),
    "{{ endOfWeek }}": endOfWeek().toISOString(),
    "{{ today }}": new Date().toISOString(),
    // ... more templates
  };

  return JSON.parse(
    JSON.stringify(query).replace(
      /\{\{\s*(\w+)\s*\}\}/g,
      (match, key) => replacements[`{{ ${key} }}`] || match,
    ),
  );
}
```

---

## Interactivity & Editing

### Update Flow

When a user interacts with a view (e.g., drags a card in kanban):

1. **Event**: View component emits `@update` event

   ```typescript
   emit("update", {
     fileId: 123,
     updates: { status: "in-progress" },
   });
   ```

2. **Handler**: `ViewRenderer` handles update
   - Loads current file
   - Merges updates into properties
   - Calls `fileService.update()`

3. **Backend**: `PUT /api/v1/files/{id}`
   - Updates file frontmatter
   - Writes to disk
   - Creates git commit
   - Updates FileMetadata

4. **Refresh**: View re-executes query and re-renders

### Editable Fields

Each view type defines which fields are editable:

- **Kanban**: `status`, `priority`, `assignee` (via drag-drop or inline edit)
- **Gallery**: `description`, `tags` (via metadata panel)
- **Rollup**: Read-only (click to open in editor)
- **Corkboard**: `scene_number`, `summary`, position (via drag-drop)

### Validation

- Property schema validation (optional, defined in view config)
- Constraint checking (e.g., status must be one of [todo, in-progress, done])
- Optimistic updates with rollback on error

---

## Embedding & Composition

### Mini-Views

A mini-view is a compact version of a full view, designed for embedding:

```yaml
# tasks/today.cdx - Full view
---
type: view
view_type: task-list
title: Today's Tasks
query:
  tags: [task]
  properties:
    due_date: "{{ today }}"
config:
  compact: false
  show_details: true
---
# tasks/today-mini.cdx - Mini version
---
type: view
view_type: task-list
title: Today's Tasks
query:
  tags: [task]
  properties:
    due_date: "{{ today }}"
config:
  compact: true
  show_details: false
  max_items: 5
---
```

### Dashboard Composition

Dashboard views reference other `.cdx` files:

```yaml
---
type: view
view_type: dashboard
title: Home
layout:
  - type: row
    components:
      - type: mini-view
        span: 6
        view: tasks/today-mini.cdx
      - type: mini-view
        span: 6
        view: tasks/upcoming-mini.cdx
  - type: row
    components:
      - type: mini-view
        span: 12
        view: journal/recent.cdx
---
```

**Component**: `MiniViewContainer.vue`

```vue
<template>
  <div class="mini-view" :style="{ gridColumn: `span ${span}` }">
    <ViewRenderer
      :file-id="viewFileId"
      :workspace-id="workspaceId"
      :compact="true"
    />
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  viewPath: string; // e.g., "tasks/today-mini.cdx"
  span: number; // Grid span (1-12)
  workspaceId: number;
}>();

// Resolve view path to file ID
const viewFileId = await resolveViewPath(props.viewPath, props.workspaceId);
</script>
```

---

## Implementation Status

### ✅ Phase 1: Foundation - COMPLETED

**Backend:**

- [x] Add `.cdx` file type support (`api/routes/files.py`, `core/watcher.py`)
- [x] Implement query API endpoint (`/api/v1/query`)
  - [x] Basic filtering (tags, properties, dates)
  - [x] Sorting and pagination
  - [x] Group-by support
  - [x] JSON property queries with SQLite json_extract
  - [x] Path filtering with glob patterns
  - [x] Content search (title/description)
- [x] Add property validation helpers (`core/property_validator.py`)
  - [x] Property schema validation
  - [x] View definition validation
  - [x] Type checking and constraints

**Frontend:**

- [x] Create `ViewRenderer.vue` component with lazy loading
- [x] Implement view parser (`viewParser.ts`)
  - [x] YAML frontmatter parsing
  - [x] Template variable processing
  - [x] Validation
- [x] Add query service (`queryService.ts`)
- [x] Update file tree to show `.cdx` files with icon (📊)
- [x] View path resolution service (`viewPathResolver.ts`)

**Testing:**

- [x] Unit tests for query API (`test_query_api.py`)
  - [x] Helper functions (sorting, filtering, grouping)
  - [x] Path filtering with glob patterns
- [x] Unit tests for property validator (`test_property_validator.py`)
- [x] Frontend view parser tests (`viewParser.test.ts`)
- [x] Frontend view renderer tests (`ViewRenderer.test.ts`)
- [x] View path resolver tests (`viewPathResolver.test.ts`)

### ✅ Phase 2: Core Views - COMPLETED

**Frontend Components:**

- [x] `KanbanView.vue` - Kanban board with drag-drop
  - [x] Multi-column layout
  - [x] Card rendering with configurable fields
  - [x] Click to open in editor
- [x] `TaskListView.vue` - Simple task list (for mini-views)
  - [x] Compact mode
  - [x] Checkbox completion
  - [x] Priority sorting
- [x] `RollupView.vue` - Date-grouped rollup
  - [x] Date grouping by day
  - [x] Statistics display
  - [x] Expandable sections
- [x] `NoteCard.vue` - Reusable card component for views

**Features:**

- [x] Drag-and-drop property updates (KanbanView)
- [x] Auto-refresh on updates
- [x] Error handling and loading states
- [x] Property merge on update

**Testing:**

- [x] Component tests for view renderer
- [x] Integration with query API

### ✅ Phase 3: Advanced Views - COMPLETED

**Frontend Components:**

- [x] `GalleryView.vue` - Image gallery with lightbox
  - [x] Grid layout (configurable columns)
  - [x] Lightbox viewer
  - [x] Metadata display
- [x] `CorkboardView.vue` - Free-form canvas
  - [x] Swimlane layout by chapter/group
  - [x] Notecard styling
  - [x] Draggable cards
- [ ] `CalendarView.vue` - Calendar view (deferred to v2)

**Features:**

- [x] Lightbox with image viewer
- [x] Free-form positioning (swimlanes)
- [ ] Image thumbnail generation (using browser rendering)
- [ ] EXIF data extraction (deferred to v2)

### ✅ Phase 4: Dashboards - COMPLETED

**Frontend:**

- [x] `DashboardView.vue` - Grid layout
  - [x] Row-based layout system
  - [x] Configurable column spans
- [x] `MiniViewContainer.vue` - Embeddable views
  - [x] Compact mode support
  - [x] View path resolution
- [x] View path resolution service
  - [x] Resolve .cdx paths to file IDs
  - [x] Cross-notebook view references

**Features:**

- [x] Responsive grid system (12-column)
- [x] View nesting (depth limit enforced)
- [x] Dashboard layout configuration

**Examples:**

- [x] Create example views (`examples/views/`)
  - [x] kanban-board.cdx
  - [x] task-list-today.cdx
  - [x] weekly-rollup.cdx
  - [x] photo-gallery.cdx
  - [x] novel-outline.cdx
  - [x] home-dashboard.cdx
- [x] Documentation for custom views (`examples/views/README.md`)

### 🚧 Phase 5: Polish & Documentation - IN PROGRESS

**UI/UX:**

- [ ] View creation wizard (see "UI for Creating/Viewing Dynamic Views" section below)
- [ ] Template gallery UI component
- [ ] Keyboard shortcuts for views
- [x] Dark mode support (inherited from app theme)

**Documentation:**

- [x] User guide for creating views (`examples/views/README.md`)
- [x] Query syntax reference (in examples README)
- [x] View type reference (in examples README)
- [x] Example gallery (6 example .cdx files)
- [x] API reference (in this document)
- [x] Template variables documentation

**Performance:**

- [x] Query optimization (DB-level filtering and sorting)
- [x] Lazy loading for view components
- [ ] View result caching (deferred to v2)
- [ ] Virtual scrolling for large lists (deferred to v2)

---

## Summary of Completed Features

### Backend (100% Complete)
- ✅ Full query API with advanced filtering
- ✅ Property validation system
- ✅ .cdx file type recognition
- ✅ JSON property queries
- ✅ Comprehensive test coverage

### Frontend (95% Complete)
- ✅ All 6 core view types implemented (kanban, task-list, rollup, gallery, corkboard, dashboard)
- ✅ View renderer with lazy loading
- ✅ View parser with template variables
- ✅ Query service integration
- ✅ Drag-and-drop updates
- ✅ 6 example views with documentation
- ⏳ UI for creating new views (see next section)

### Not Implemented (Deferred to v2)
- ⏸️ Calendar view
- ⏸️ External API integrations (weather, etc.)
- ⏸️ MDX-style views with embedded scripts
- ⏸️ Real-time collaboration
- ⏸️ View result caching
- ⏸️ Virtual scrolling for large datasets
- ⏸️ Image thumbnail generation
- ⏸️ EXIF data extraction

---

## UI for Creating/Viewing Dynamic Views

### Current State

Dynamic views can currently be created manually by:
1. Creating a new `.cdx` file in any notebook
2. Writing YAML frontmatter with view definition
3. Saving the file
4. Opening the file to view it

The file tree displays `.cdx` files with a 📊 icon and clicking them opens the ViewRenderer component.

### Proposed UI Enhancements

#### 1. New View Creation Wizard

**Location**: Add "New View" button to notebook/folder context menu

**Workflow**:
```
File Tree Context Menu → New → Dynamic View
↓
View Creation Modal
├─ Step 1: Choose Template
│  ├─ Kanban Board
│  ├─ Task List
│  ├─ Photo Gallery
│  ├─ Rollup Report
│  ├─ Corkboard
│  ├─ Dashboard
│  └─ Blank View
├─ Step 2: Configure View
│  ├─ View Name/Title
│  ├─ View Type (from template)
│  ├─ Query Configuration
│  │  ├─ Tags Filter (multi-select)
│  │  ├─ Properties Filter (key-value pairs)
│  │  ├─ Date Range (with template variables)
│  │  └─ Sort Options
│  └─ View-Specific Config
│     ├─ Kanban: Define columns
│     ├─ Gallery: Layout options
│     ├─ Dashboard: Layout grid
│     └─ etc.
└─ Step 3: Preview & Create
   ├─ Preview generated YAML
   ├─ File path selection
   └─ Create button
```

**Implementation Approach**:
- Create `CreateViewModal.vue` component
- Create `ViewTemplateSelector.vue` for step 1
- Create `ViewConfigForm.vue` for step 2
- Create view template definitions in `frontend/src/utils/viewTemplates.ts`
- Add context menu item to `FileTreeItem.vue`

#### 2. View Template Library

**Component**: `ViewTemplateGallery.vue`

**Features**:
- Display available view templates with descriptions and previews
- Filter templates by category (productivity, creative, analytics)
- One-click template instantiation
- Template metadata:
  - Name, description, icon
  - Use case examples
  - Required frontmatter properties
  - Screenshots or mockups

**Template Storage**:
```typescript
// frontend/src/utils/viewTemplates.ts
export interface ViewTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: 'productivity' | 'creative' | 'analytics' | 'dashboard';
  viewType: string;
  defaultConfig: ViewConfig;
  defaultQuery: ViewQuery;
  requiredProperties?: string[];
  example?: string; // Path to example .cdx file
}

export const VIEW_TEMPLATES: ViewTemplate[] = [
  {
    id: 'kanban-board',
    name: 'Kanban Board',
    description: 'Visual task board with drag-and-drop columns',
    icon: '📋',
    category: 'productivity',
    viewType: 'kanban',
    defaultConfig: {
      columns: [
        { id: 'todo', title: 'To Do', filter: { status: 'todo' } },
        { id: 'in-progress', title: 'In Progress', filter: { status: 'in-progress' } },
        { id: 'done', title: 'Done', filter: { status: 'done' } }
      ],
      drag_drop: true,
      editable: true
    },
    defaultQuery: {
      tags: ['task'],
      sort: 'created_at desc'
    },
    requiredProperties: ['status'],
    example: 'examples/views/kanban-board.cdx'
  },
  // ... more templates
];
```

#### 3. Inline View Editor

**Enhancement to ViewRenderer**:
- Add "Edit View Definition" button in view header
- Modal editor with syntax-highlighted YAML
- Live preview of changes
- Save button to update .cdx file

**Component**: `ViewDefinitionEditor.vue`
```vue
<template>
  <div class="view-editor">
    <div class="editor-header">
      <h3>Edit View Definition</h3>
      <button @click="save">Save Changes</button>
      <button @click="cancel">Cancel</button>
    </div>
    
    <div class="editor-layout">
      <!-- Left: YAML editor -->
      <div class="yaml-editor">
        <CodeMirror 
          v-model="yamlContent"
          :extensions="[yaml()]"
          @change="validateYaml"
        />
      </div>
      
      <!-- Right: Live preview -->
      <div class="view-preview">
        <ViewRenderer 
          v-if="validDefinition"
          :file-id="previewFileId"
          :workspace-id="workspaceId"
          :notebook-id="notebookId"
        />
        <div v-else class="error-message">
          {{ validationError }}
        </div>
      </div>
    </div>
  </div>
</template>
```

#### 4. Query Builder UI

**Component**: `QueryBuilder.vue`

**Features**:
- Visual query construction (no YAML required)
- Tag selector with autocomplete
- Property filter builder with operators
- Date range picker with template variable options
- Sort field selector
- Real-time result count preview

**Layout**:
```
┌─────────────────────────────────────────┐
│ Query Builder                            │
├─────────────────────────────────────────┤
│ 📂 Scope                                 │
│   ☐ All notebooks                       │
│   ☑ Specific notebooks: [Dropdown]     │
│   Path pattern: "**/*.md" [Clear]      │
├─────────────────────────────────────────┤
│ 🏷️  Tags                                │
│   Match: ○ All ● Any                    │
│   [task] [urgent] [+Add]                │
├─────────────────────────────────────────┤
│ 📋 Properties                            │
│   status = "todo" [×]                   │
│   priority in ["high", "critical"] [×]  │
│   [+Add Property Filter]                │
├─────────────────────────────────────────┤
│ 📅 Date Filters                         │
│   Created after: [Date Picker]          │
│     or use template: [startOfWeek ▼]   │
│   Modified before: [Date Picker]        │
├─────────────────────────────────────────┤
│ 🔍 Full-text Search                     │
│   Search in title/description:          │
│   [_________________________]           │
├─────────────────────────────────────────┤
│ 📊 Sort & Limit                         │
│   Sort by: [created_at ▼] [desc ▼]    │
│   Limit: [100] results                  │
├─────────────────────────────────────────┤
│ Results: 42 files match this query      │
│                                          │
│ [Preview Results] [Use This Query]      │
└─────────────────────────────────────────┘
```

#### 5. View Configuration Forms

**View-Specific Config UIs**:

**KanbanConfigForm.vue**:
- Add/remove/reorder columns
- Configure column filters
- Select card fields to display
- Enable/disable drag-drop and editing

**GalleryConfigForm.vue**:
- Grid vs. masonry layout
- Number of columns slider
- Thumbnail size
- Show/hide metadata
- Enable/disable lightbox

**RollupConfigForm.vue**:
- Group by field selector
- Group format (day/week/month)
- Show statistics toggle
- Section configuration (add/remove sections)

**DashboardConfigForm.vue**:
- Visual grid layout editor
- Drag-and-drop row/component arrangement
- Component span configuration
- View path selector with autocomplete

#### 6. Context Menu Actions for .cdx Files

**Enhanced FileTreeItem.vue**:
```typescript
// Right-click context menu for .cdx files
const viewContextMenu = [
  { label: 'Open View', icon: '👁️', action: 'open' },
  { label: 'Edit Definition', icon: '✏️', action: 'editDefinition' },
  { label: 'Duplicate View', icon: '📋', action: 'duplicate' },
  { label: 'Export View', icon: '📤', action: 'export' },
  { label: 'Delete View', icon: '🗑️', action: 'delete' },
  { separator: true },
  { label: 'Refresh Query', icon: '🔄', action: 'refresh' },
  { label: 'View Properties', icon: 'ℹ️', action: 'properties' }
];
```

#### 7. View Properties Panel

**Enhancement to FilePropertiesPanel.vue**:

When a .cdx file is selected, show additional view-specific metadata:
- View type and title
- Query summary (e.g., "23 files with tag 'task'")
- Last refreshed timestamp
- View configuration summary
- Quick actions (edit, duplicate, refresh)

#### 8. View Navigation Breadcrumbs

**In ViewRenderer header**:
```
Home > Projects > views > task-board.cdx
[📊 Kanban Board] [⚙️ Edit] [🔄 Refresh] [⋮ More]
```

### Implementation Priority

**Phase 5A (High Priority - Immediate)**:
1. ✅ Basic file creation support (already exists via manual .cdx creation)
2. 🎯 Context menu "New View" option in FileTreeItem.vue
3. 🎯 Simple CreateViewModal with template selection
4. 🎯 ViewTemplateGallery component
5. 🎯 View templates definitions file

**Phase 5B (Medium Priority - Next Sprint)**:
6. QueryBuilder component for visual query construction
7. View-specific configuration forms
8. Inline view definition editor
9. Enhanced context menu for .cdx files

**Phase 5C (Nice-to-Have - Future)**:
10. Visual dashboard layout editor
11. View export/import functionality
12. Template marketplace/sharing
13. View preview in file tree tooltip

### Mockup Descriptions

#### Create View Modal
```
┌────────────────────────────────────────────┐
│  Create New Dynamic View            [×]    │
├────────────────────────────────────────────┤
│                                             │
│  Step 1: Choose a Template                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                             │
│  📋 Kanban Board    📝 Task List           │
│  Visual task board  Simple checklist       │
│  [Select]           [Select]               │
│                                             │
│  📸 Photo Gallery   📊 Rollup Report       │
│  Image grid view    Activity summary       │
│  [Select]           [Select]               │
│                                             │
│  📌 Corkboard       🎛️  Dashboard          │
│  Scene planner      Composite view         │
│  [Select]           [Select]               │
│                                             │
│  ⚡ Start from scratch                     │
│  [Select]                                   │
│                                             │
│              [Cancel]  [Next →]            │
└────────────────────────────────────────────┘
```

#### Template Details
```
┌────────────────────────────────────────────┐
│  Create Kanban Board                [×]    │
├────────────────────────────────────────────┤
│                                             │
│  Step 2: Configure Your View               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                             │
│  View Name                                  │
│  [Project Task Board____________]          │
│                                             │
│  Description (optional)                     │
│  [Track project tasks by status_]          │
│                                             │
│  📂 Save Location                          │
│  Notebook: [My Notebook        ▼]         │
│  Path: [views/________________]            │
│                                             │
│  🔍 Query Files                            │
│  ┌──────────────────────────────────────┐  │
│  │ Match files with tag: [task]        │  │
│  │ Sort by: [created_at ▼] [desc ▼]   │  │
│  │ [Configure Advanced Query...]       │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  📋 Kanban Columns                         │
│  ┌──────────────────────────────────────┐  │
│  │ • To Do (status=todo)         [Edit]│  │
│  │ • In Progress (status=in-progress) │  │
│  │ • Done (status=done)          [Edit]│  │
│  │ [+Add Column]                       │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ☑ Enable drag and drop                   │
│  ☑ Allow inline editing                   │
│                                             │
│         [← Back]  [Cancel]  [Create]      │
└────────────────────────────────────────────┘
```

### Technical Implementation Notes

1. **CreateViewModal.vue**: Multi-step modal using state machine pattern
2. **ViewTemplates**: Store templates in TypeScript file, load dynamically
3. **Query Builder**: Use form validation with Vuelidate or similar
4. **Preview**: Use ViewRenderer in read-only mode
5. **Save**: Call fileService.create() with generated YAML content
6. **Validation**: Reuse existing validateViewDefinition() from viewParser.ts

---

---

## Technical Considerations

### Security

1. **Query Injection**: Sanitize all query parameters to prevent SQL injection
2. **Path Traversal**: Validate view paths (no `../` escapes)
3. **Property Access**: Limit which properties can be edited via views
4. **Sandboxing**: If MDX is added later, use secure sandbox for script execution

### Performance

1. **Query Optimization**:
   - Index frequently queried properties (tags, dates)
   - Use SQLite FTS5 for full-text search
   - Cache query results for dashboard mini-views (5-minute TTL)

2. **Rendering**:
   - Virtual scrolling for large lists (kanban with 100+ cards)
   - Lazy loading for gallery images
   - Debounce drag-drop updates

3. **Scalability**:
   - Pagination for queries returning >100 files
   - Limit dashboard to max 12 mini-views
   - Warn on expensive queries (full-text search across all notebooks)

### Backward Compatibility

- `.cdx` files are just text files with frontmatter (like markdown)
- If view rendering fails, fall back to showing raw content in markdown viewer
- Existing markdown files unaffected

### Edge Cases

1. **Circular References**: Dashboard A embeds B, B embeds A
   - Solution: Limit nesting depth to 2, detect cycles

2. **Missing Files**: View references non-existent file
   - Solution: Show placeholder with "View not found"

3. **Invalid Queries**: Query returns no results
   - Solution: Show empty state with helpful message

4. **Concurrent Updates**: Two users edit same file via different views
   - Solution: Use optimistic locking (check file hash before update)

### Future Enhancements

1. **External Data Sources**:
   - Weather API integration
   - Git commit history views
   - RSS feed aggregators

2. **Advanced Query Language**:
   - JSON path queries (e.g., `properties.tags[*] contains 'urgent'`)
   - Calculated fields (e.g., `days_until_due = due_date - today`)
   - Joins across notebooks (e.g., show tasks + related notes)

3. **View Sharing**:
   - Export view definition
   - Import from template library
   - Publish to community marketplace

4. **Real-Time Updates**:
   - WebSocket connection for live updates
   - Multi-user collaboration indicators

---

## Example Use Cases

### Use Case 1: Project Management

**Structure:**

```
workspace/
  projects/
    tasks/
      backend-tasks.md      (type: view, status: todo)
      frontend-tasks.md     (type: view, status: in-progress)
      design-tasks.md       (type: view, status: done)
    board.cdx               (kanban view)
    sprint-plan.cdx         (rollup by week)
    dashboard.cdx           (composite dashboard)
```

**board.cdx:**

```yaml
---
type: view
view_type: kanban
title: Sprint Board
query:
  tags: [task]
  properties:
    sprint: current
config:
  columns:
    - id: todo
      title: To Do
      filter: { status: todo }
    - id: in-progress
      title: In Progress
      filter: { status: in-progress }
    - id: review
      title: Review
      filter: { status: review }
    - id: done
      title: Done
      filter: { status: done }
  drag_drop: true
  editable: true
---
```

### Use Case 2: Novel Writing

**Structure:**

```
workspace/
  novel/
    chapters/
      chapter-01/
        scene-01.md         (chapter: 1, scene: 1, characters: [Alice, Bob])
        scene-02.md         (chapter: 1, scene: 2, characters: [Alice])
      chapter-02/
        scene-01.md         (chapter: 2, scene: 1, characters: [Bob, Carol])
    outline.cdx             (corkboard view)
    timeline.cdx            (calendar view)
    characters.cdx          (gallery of character profiles)
```

**outline.cdx:**

```yaml
---
type: view
view_type: corkboard
title: Novel Outline
query:
  paths: ["novel/chapters/**/*.md"]
  sort: properties.chapter asc, properties.scene asc
config:
  group_by: chapter
  card_fields:
    - scene
    - characters
    - summary
    - word_count
  layout: swimlanes
  draggable: true
  editable: true
---
```

### Use Case 3: Research Journal

**Structure:**

```
workspace/
  research/
    journal/
      2026-01-20.md         (date: 2026-01-20, tags: [experiment, results])
      2026-01-21.md         (date: 2026-01-21, tags: [analysis])
      2026-01-22.md         (date: 2026-01-22, tags: [planning])
    weekly-summary.cdx      (rollup by week)
    experiments.cdx         (filter by tag: experiment)
    dashboard.cdx           (current week + recent entries)
```

**weekly-summary.cdx:**

```yaml
---
type: view
view_type: rollup
title: This Week in Research
query:
  paths: ["research/journal/*.md"]
  created_after: "{{ startOfWeek }}"
  created_before: "{{ endOfWeek }}"
  sort: created_at asc
config:
  group_by: created_at
  group_format: day
  show_stats: true
  stats:
    - label: Total Entries
      value: "{{ count(files) }}"
    - label: Experiments Run
      value: "{{ count(files where tags contains 'experiment') }}"
---
```

---

## API Reference

### Query Endpoint

**`GET /api/v1/query`**

**Query Parameters:**

- `workspace_id` (required): Workspace ID

**Request Body** (JSON):

```json
{
  "notebook_ids": [1, 2],
  "tags": ["task", "urgent"],
  "properties": {
    "status": "todo",
    "priority": ["high", "critical"]
  },
  "created_after": "2026-01-01T00:00:00Z",
  "sort": "created_at desc",
  "limit": 50,
  "offset": 0,
  "group_by": "status"
}
```

**Response:**

```json
{
  "files": [
    {
      "id": 1,
      "notebook_id": 1,
      "path": "tasks/task-1.md",
      "filename": "task-1.md",
      "title": "Implement feature X",
      "properties": {
        "status": "todo",
        "priority": "high",
        "due_date": "2026-01-25"
      },
      "created_at": "2026-01-20T10:00:00Z"
    }
  ],
  "groups": {
    "todo": [...],
    "in-progress": [...],
    "done": [...]
  },
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

### File Update Endpoint

**`PATCH /api/v1/files/{file_id}/properties`**

Update only properties without modifying content:

**Request Body:**

```json
{
  "properties": {
    "status": "in-progress",
    "updated_by": "user-123"
  },
  "merge": true
}
```

**Response:**

```json
{
  "id": 1,
  "properties": {
    "status": "in-progress",
    "priority": "high",
    "updated_by": "user-123"
  }
}
```

---

## Open Questions

1. **Query Language Complexity**: Should we support advanced operators (AND/OR/NOT) or keep it simple?
   - **Recommendation**: Start simple (implicit AND), add operators in v2 if needed

2. **View Permissions**: Should views have separate permissions from underlying files?
   - **Recommendation**: No, inherit file permissions (if user can't read file, it won't appear in view)

3. **View Versioning**: Should `.cdx` files be version-controlled separately?
   - **Recommendation**: Yes, treat like any other file (git commits)

4. **Performance Budget**: What's acceptable query time for large workspaces?
   - **Recommendation**: <500ms for queries returning <100 files, warn on slower queries

5. **MDX Security**: If we add MDX, how do we sandbox script execution?
   - **Recommendation**: Defer to v2, start with YAML-only

---

## Success Metrics

1. **Adoption**: 50% of users create at least one dynamic view within first month
2. **Usage**: Dynamic views account for 25% of page views in the app
3. **Performance**: 95th percentile query time <1s
4. **Reliability**: <1% error rate on view rendering
5. **Feedback**: Positive sentiment on view feature (user interviews)

---

## Alternatives Considered

### Alternative 1: Markdown Extensions

Use markdown with special syntax blocks:

````markdown
# Project Board

```codex-view:kanban
query:
  tags: [task]
config:
  columns: [todo, in-progress, done]
```
````

````

**Pros:** Familiar markdown format
**Cons:** Limited flexibility, hard to compose, parsing complexity
**Decision:** Rejected - `.cdx` format provides clearer separation

### Alternative 2: Embedded React/Vue Components

Allow embedding Vue components directly in markdown:

```markdown
# Dashboard

<TaskBoard :query="{ tags: ['task'] }" />
<WeatherWidget location="current" />
````

**Pros:** Maximum flexibility, reuse existing components
**Cons:** Security risk, requires component registration, steep learning curve
**Decision:** Consider for v2 with proper sandboxing

### Alternative 3: SQL-Based Views

Let users write SQL queries directly:

```sql
SELECT * FROM files
WHERE tags LIKE '%task%'
AND properties->>'status' = 'todo'
ORDER BY created_at DESC
```

**Pros:** Powerful, familiar to developers
**Cons:** Exposes DB schema, security risk, not user-friendly
**Decision:** Rejected - use declarative query language instead

---

## Appendix

### A. View Type Registry

Maintain a registry of available view types:

```typescript
// frontend/src/components/views/registry.ts

export const VIEW_TYPES = {
  kanban: {
    component: () => import("./KanbanView.vue"),
    name: "Kanban Board",
    description: "Organize items in columns",
    icon: "board",
    configSchema: {
      columns: "array",
      card_fields: "array",
      drag_drop: "boolean",
    },
  },
  gallery: {
    component: () => import("./GalleryView.vue"),
    name: "Gallery",
    description: "Display images in grid",
    icon: "image",
    configSchema: {
      columns: "number",
      thumbnail_size: "number",
      lightbox: "boolean",
    },
  },
  // ... more types
};
```

### B. Template Library

Pre-built templates for common use cases:

```typescript
export const VIEW_TEMPLATES = {
  "task-board": {
    name: "Task Board",
    description: "Kanban board for task management",
    content: `---
type: view
view_type: kanban
title: My Tasks
query:
  tags: [task]
config:
  columns:
    - { id: todo, title: "To Do", filter: { status: todo } }
    - { id: doing, title: "Doing", filter: { status: doing } }
    - { id: done, title: "Done", filter: { status: done } }
  drag_drop: true
---`,
  },
  // ... more templates
};
```

### C. Migration Path

For existing users with task/todo markdown files:

1. Detect files with task-like properties (status, due_date)
2. Suggest creating kanban view
3. Auto-generate `.cdx` file with appropriate query
4. Show onboarding tutorial

---

**End of Design Document**

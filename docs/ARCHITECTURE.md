# Codex Architecture Guide

**Version:** 1.0 | **Date:** 2026-02-16 | **Status:** Current

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Database Design](#database-design)
6. [API Design](#api-design)
7. [Security Architecture](#security-architecture)
8. [Plugin System](#plugin-system)
9. [Scalability & Performance](#scalability--performance)
10. [Deployment Architecture](#deployment-architecture)
11. [Key Design Decisions](#key-design-decisions)
12. [Recommendations](#recommendations)

## Overview

Codex is a hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations. It follows a three-tier architecture with a unique two-database design pattern.

### Core Principles

- **File-System as Source of Truth**: The filesystem is authoritative; databases mirror state
- **Hierarchical Organization**: Workspace → Notebook → Files provides clear boundaries
- **Async-First**: Non-blocking I/O throughout the stack
- **Plugin-Driven Extensibility**: Views, themes, and integrations are pluggable
- **Real-Time Synchronization**: WebSocket events and filesystem watchers

### Technology Stack

**Backend:**
- Python 3.13+ with FastAPI for REST APIs
- SQLModel (SQLAlchemy 2.0 + Pydantic) for ORM
- SQLite for databases (system + per-notebook)
- Watchdog for filesystem monitoring
- GitPython for version control integration

**Frontend:**
- Vue.js 3 with Composition API
- TypeScript for type safety
- Pinia for state management
- Vite for build tooling
- Tailwind CSS for styling

**Infrastructure:**
- Docker & Docker Compose for containerization
- Nginx for production reverse proxy
- Alembic for database migrations

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Client Layer                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │  Browser   │  │   Mobile   │  │  Desktop   │   │
│  │    App     │  │    (TBD)   │  │   (TBD)    │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘   │
└────────┼────────────────┼────────────────┼──────────┘
         │                │                │
         └────────────────┴────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │      HTTP/WebSocket             │
         └────────────────┬────────────────┘
                          │
┌─────────────────────────▼─────────────────────────┐
│              Application Layer                     │
│  ┌──────────────────────────────────────────────┐ │
│  │          FastAPI Backend (Python)            │ │
│  │  ┌────────────┐  ┌────────────┐            │ │
│  │  │  API       │  │  WebSocket │            │ │
│  │  │  Routes    │  │  Manager   │            │ │
│  │  └────┬───────┘  └────┬───────┘            │ │
│  │       │               │                     │ │
│  │  ┌────▼───────────────▼───────┐            │ │
│  │  │   Business Logic Layer      │            │ │
│  │  │   (Watcher, Git, Metadata)  │            │ │
│  │  └────┬────────────────────────┘            │ │
│  └───────┼─────────────────────────────────────┘ │
└──────────┼───────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────┐
│               Data Layer                          │
│  ┌──────────────┐  ┌──────────────┐             │
│  │   System DB  │  │  Notebook    │             │
│  │  (SQLite)    │  │  DBs         │             │
│  │              │  │  (per-notebook│             │
│  │  - Users     │  │   SQLite)    │             │
│  │  - Workspaces│  │              │             │
│  │  - Tasks     │  │  - Files     │             │
│  │  - Plugins   │  │  - Tags      │             │
│  │  - Agents    │  │  - Search    │             │
│  └──────────────┘  └──────────────┘             │
│                                                   │
│  ┌───────────────────────────────────────────┐  │
│  │         Filesystem Storage                 │  │
│  │   (Files, Images, Notebooks, Plugins)     │  │
│  └───────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

### Request Flow

**Standard HTTP Request:**
```
1. Client → Nginx → FastAPI
2. FastAPI → Auth Middleware (JWT validation)
3. FastAPI → Route Handler
4. Route Handler → Database Query
5. Route Handler → Filesystem Operation (if needed)
6. FastAPI → Response (JSON)
7. Response → Client
```

**WebSocket Event Flow:**
```
1. File System Change
2. Watchdog Detects → FileOperationQueue
3. Queue Processor (batched, 5s intervals)
4. Metadata Update → Notebook DB
5. WebSocket Broadcast → Connected Clients
6. Client UI Update (reactive)
```

## Backend Architecture

### Directory Structure

```
backend/codex/
├── api/
│   ├── auth.py              # JWT authentication utilities
│   ├── schemas.py           # Pydantic models (API contracts)
│   ├── schemas_agent.py     # Agent-specific schemas
│   └── routes/              # FastAPI routers
│       ├── users.py         # User management & auth
│       ├── workspaces.py    # Workspace CRUD
│       ├── notebooks.py     # Notebook operations
│       ├── files.py         # File operations
│       ├── folders.py       # Folder metadata
│       ├── search.py        # Full-text search
│       ├── tasks.py         # Background task queue
│       ├── agents.py        # AI agent management
│       ├── plugins.py       # Plugin registry
│       ├── integrations.py  # Plugin integration endpoints
│       ├── query.py         # Advanced query API
│       └── ws.py            # WebSocket endpoint
├── core/
│   ├── watcher.py           # Filesystem change detection
│   ├── metadata.py          # Metadata parsing (frontmatter, sidecars)
│   ├── git_manager.py       # Git integration
│   ├── git_lock_manager.py  # Git operation locking
│   ├── websocket.py         # WebSocket connection management
│   ├── link_resolver.py     # Internal link resolution
│   ├── property_validator.py # Metadata validation
│   ├── custom_blocks.py     # Custom markdown blocks
│   └── logging.py           # Structured logging
├── db/
│   ├── database.py          # Session management & initialization
│   ├── migrations.py        # Migration utilities
│   └── models/
│       ├── base.py          # Base SQLModel classes
│       ├── system.py        # System DB models (User, Workspace, Task)
│       └── notebook.py      # Notebook DB models (FileMetadata, Tag)
├── agents/
│   ├── __init__.py
│   ├── manager.py           # Agent orchestration
│   ├── scope_guard.py       # Permission boundaries
│   └── providers/           # LLM provider adapters
├── plugins/
│   ├── loader.py            # Plugin discovery & loading
│   ├── models.py            # Plugin data models
│   └── executor.py          # Plugin execution
├── scripts/
│   ├── seed_test_data.py    # Test data generation
│   └── migrate_db.py        # Manual migration utilities
├── migrations/
│   ├── workspace/           # System DB Alembic migrations
│   └── notebook/            # Notebook DB Alembic migrations
└── main.py                  # Application entry point
```

### Layer Responsibilities

**API Layer** (`api/`)
- Request validation via Pydantic schemas
- Authentication and authorization
- HTTP response formatting
- Error handling and status codes

**Business Logic Layer** (`core/`)
- Filesystem watching and synchronization
- Metadata parsing from various formats
- Git version control integration
- WebSocket event broadcasting
- Link resolution and validation

**Data Access Layer** (`db/`)
- Database session management
- ORM model definitions
- Migration management
- Query optimization

**Extension Layer** (`agents/`, `plugins/`)
- Plugin loading and execution
- AI agent orchestration
- External integrations
- Tool routing for agents

### Key Components

#### 1. Application Initialization (`main.py`)

**Lifespan Management:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_system_db()
    await connection_manager.start_broadcast_loop()
    loader = PluginLoader(plugins_dir)
    loader.load_all_plugins()
    await asyncio.to_thread(_start_notebook_watchers_sync)
    
    yield
    
    # Shutdown
    stop_all_watchers()
    await connection_manager.stop_broadcast_loop()
```

**Features:**
- System database initialization
- Plugin discovery and registration
- Filesystem watcher startup for all notebooks
- WebSocket connection lifecycle
- Graceful shutdown

#### 2. Filesystem Watcher (`core/watcher.py`)

**Architecture:**
```python
class NotebookWatcher(FileSystemEventHandler):
    """Watches a notebook directory for file changes."""
    
    def __init__(self, notebook_path, notebook_db_path):
        self.operation_queue = FileOperationQueue(
            notebook_db_path=notebook_db_path,
            process_interval=5.0  # Batch changes every 5 seconds
        )
```

**Operation Queue:**
- Batches rapid file changes (prevents DB hammering)
- Deduplicates events (e.g., save = modify + modify)
- Processes in background thread
- Updates metadata in notebook database

**Event Types:**
- File created → Parse metadata, create FileMetadata record
- File modified → Update metadata, content hash, timestamps
- File deleted → Mark as deleted (soft delete)
- File moved → Update path, preserve history

#### 3. Metadata Parser (`core/metadata.py`)

**Supported Formats:**

1. **Markdown Frontmatter:**
```yaml
---
title: Experiment Log
tags: [ml, pytorch]
date: 2024-01-01
status: in-progress
---
```

2. **JSON Sidecar** (`.filename.json`):
```json
{
  "title": "Experiment Log",
  "tags": ["ml", "pytorch"],
  "properties": {
    "status": "in-progress"
  }
}
```

3. **XML Sidecar** (`.filename.xml`):
```xml
<metadata>
  <title>Experiment Log</title>
  <tags>
    <tag>ml</tag>
    <tag>pytorch</tag>
  </tags>
</metadata>
```

4. **Markdown Sidecar** (`.filename.md`):
```markdown
# Metadata
Title: Experiment Log
Tags: ml, pytorch
```

**Parser Selection:**
- Frontmatter for `.md` files (detected by `---` delimiter)
- Sidecar files matched by naming convention
- Priority: frontmatter > JSON > XML > MD sidecar

#### 4. WebSocket Manager (`core/websocket.py`)

**Connection Management:**
```python
class ConnectionManager:
    active_connections: Dict[str, Set[WebSocket]]  # notebook_id → websockets
    
    async def broadcast_to_notebook(
        self, 
        notebook_id: str, 
        message: Dict[str, Any]
    ):
        """Broadcast event to all clients watching a notebook."""
```

**Event Types:**
- `file_created` - New file detected
- `file_modified` - File content or metadata changed
- `file_deleted` - File removed
- `metadata_updated` - Metadata refreshed

**Client Reconnection:**
- Clients track last event timestamp
- On reconnect, request events since timestamp
- Server sends catch-up events

#### 5. Git Integration (`core/git_manager.py`)

**Features:**
- Auto-commit on file changes
- Excludes binary files (images, videos)
- Commit message format: `"Auto-commit: <filename>"`
- Git LFS support for large files
- Branch management for experiments

**Locking Mechanism (`git_lock_manager.py`):**
```python
class GitLockManager:
    """Prevents concurrent git operations on same repository."""
    
    @asynccontextmanager
    async def acquire_lock(self, repo_path: Path):
        # File-based lock with timeout
        # Prevents race conditions in multi-threaded watchers
```

## Frontend Architecture

### Directory Structure

```
frontend/src/
├── main.ts                  # Application entry point
├── App.vue                  # Root component
├── router/
│   └── index.ts             # Vue Router configuration
├── stores/
│   ├── auth.ts              # Authentication state
│   ├── workspace.ts         # Current workspace context
│   ├── theme.ts             # Theme management
│   ├── agent.ts             # Agent state
│   └── integration.ts       # Integration state
├── services/
│   ├── api.ts               # Axios HTTP client
│   ├── auth.ts              # Auth service
│   ├── codex.ts             # Codex-specific API client
│   ├── queryService.ts      # Query execution
│   ├── pluginRegistry.ts    # Plugin registration
│   ├── pluginLoader.ts      # Plugin dynamic loading
│   ├── viewPluginService.ts # View component loading
│   └── websocket.ts         # WebSocket client
├── views/
│   ├── WorkspaceList.vue    # Workspace browser
│   ├── NotebookView.vue     # Notebook file browser
│   ├── FileView.vue         # File viewer/editor
│   ├── AgentChat.vue        # Agent conversation UI
│   └── SettingsView.vue     # User settings
├── components/
│   ├── views/
│   │   ├── ViewRenderer.vue   # .cdx view renderer
│   │   └── DashboardView.vue  # Dashboard container
│   ├── editor/
│   │   ├── MarkdownEditor.vue # Markdown editing
│   │   └── CodeEditor.vue     # Code editing
│   ├── files/
│   │   ├── FileList.vue       # File browser
│   │   └── FileTree.vue       # Tree navigation
│   └── common/
│       ├── Modal.vue          # Modal dialogs
│       ├── Toast.vue          # Notifications
│       └── Spinner.vue        # Loading indicators
├── utils/
│   ├── date.ts              # Date formatting
│   ├── validation.ts        # Input validation
│   ├── fileTree.ts          # Tree utilities
│   └── contentType.ts       # MIME type detection
└── style.css                # Global styles
```

### State Management (Pinia)

**Auth Store:**
```typescript
interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
}

// Actions: login(), logout(), register(), refreshToken()
```

**Workspace Store:**
```typescript
interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspace: Workspace | null
  currentNotebook: Notebook | null
}

// Actions: fetchWorkspaces(), selectWorkspace(), createNotebook()
```

**Theme Store:**
```typescript
interface ThemeState {
  themes: Theme[]
  activeTheme: string
  customCSS: string
}

// Actions: loadTheme(), applyTheme(), setCustomCSS()
```

### Service Layer

**API Client (`services/api.ts`):**
```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' }
})

// Request interceptor: Add auth token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor: Handle 401, refresh token
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Redirect to login
    }
    return Promise.reject(error)
  }
)
```

**WebSocket Client (`services/websocket.ts`):**
```typescript
class WebSocketService {
  private socket: WebSocket | null
  private reconnectAttempts = 0
  
  connect(notebookId: string) {
    this.socket = new WebSocket(`ws://.../ws/${notebookId}`)
    
    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data)
      this.handleMessage(message)
    }
    
    this.socket.onclose = () => {
      this.reconnect()
    }
  }
  
  private reconnect() {
    // Exponential backoff
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000)
    setTimeout(() => this.connect(this.notebookId), delay)
  }
}
```

### Plugin System Integration

**Plugin Registry (`services/pluginRegistry.ts`):**
```typescript
interface PluginManifest {
  id: string
  name: string
  version: string
  views?: ViewDefinition[]
  themes?: ThemeDefinition[]
  integrations?: IntegrationDefinition[]
}

class PluginRegistry {
  private plugins: Map<string, PluginManifest>
  
  async registerPlugin(manifest: PluginManifest) {
    // Validate manifest
    // Load view components
    // Register theme CSS
    // Register integration endpoints
  }
}
```

**View Plugin Service (`services/viewPluginService.ts`):**
```typescript
class ViewPluginService {
  private viewComponents: Map<string, Component>
  
  async loadViewComponent(viewType: string): Promise<Component> {
    // Dynamic import from plugins directory
    const module = await import(`/plugins/${pluginId}/components/${viewType}.vue`)
    return module.default
  }
  
  getComponent(viewType: string): Component | null {
    return this.viewComponents.get(viewType)
  }
}
```

### View Rendering

**ViewRenderer Component:**
```vue
<script setup lang="ts">
// Parse .cdx file YAML frontmatter
const viewDef = parseViewDefinition(fileContent)

// Load plugin component
const ViewComponent = await viewPluginService.getComponent(viewDef.view_type)

// Execute query
const queryResults = await queryService.execute(viewDef.query)

// Render with props
</script>

<template>
  <component 
    :is="ViewComponent"
    :data="queryResults"
    :config="viewDef.config"
    @update="handleUpdate"
  />
</template>
```

## Database Design

### Two-Database Pattern

Codex uses a unique dual-database architecture to achieve scalability while maintaining simplicity:

1. **System Database** - Global entities (users, workspaces)
2. **Notebook Databases** - Per-notebook data (files, tags, search)

### System Database Schema

**Location:** `codex_system.db` (SQLite)

**Tables:**

```sql
-- User authentication and profiles
CREATE TABLE user (
    id TEXT PRIMARY KEY,  -- ULID
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workspaces (top-level organization)
CREATE TABLE workspace (
    id TEXT PRIMARY KEY,  -- ULID
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    path TEXT NOT NULL,  -- Filesystem path
    description TEXT,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES user (id)
);

-- Workspace permissions (RBAC)
CREATE TABLE workspace_permission (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- owner, editor, viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id),
    FOREIGN KEY (user_id) REFERENCES user (id),
    UNIQUE (workspace_id, user_id)
);

-- Notebook registration (references filesystem)
CREATE TABLE notebook (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,  -- Relative to workspace
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id),
    UNIQUE (workspace_id, path)
);

-- Background task queue
CREATE TABLE task (
    id TEXT PRIMARY KEY,
    workspace_id TEXT,
    notebook_id TEXT,
    agent_id TEXT,
    type TEXT NOT NULL,  -- agent_execution, indexing, etc.
    status TEXT NOT NULL,  -- pending, running, completed, failed
    input_data TEXT,  -- JSON
    output_data TEXT,  -- JSON
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id),
    FOREIGN KEY (notebook_id) REFERENCES notebook (id)
);

-- Plugin registry
CREATE TABLE plugin (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    plugin_type TEXT NOT NULL,  -- view, theme, integration
    manifest TEXT NOT NULL,  -- JSON
    enabled BOOLEAN DEFAULT TRUE,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Per-workspace plugin configuration
CREATE TABLE plugin_config (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    config TEXT,  -- JSON
    enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id),
    FOREIGN KEY (plugin_id) REFERENCES plugin (id),
    UNIQUE (workspace_id, plugin_id)
);

-- Encrypted plugin secrets (API keys, tokens)
CREATE TABLE plugin_secret (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    key TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id),
    FOREIGN KEY (plugin_id) REFERENCES plugin (id),
    UNIQUE (workspace_id, plugin_id, key)
);

-- AI agent definitions
CREATE TABLE agent (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    provider TEXT NOT NULL,  -- openai, anthropic, etc.
    model TEXT NOT NULL,
    system_prompt TEXT,
    tools TEXT,  -- JSON array
    config TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspace (id)
);

-- Agent execution sessions
CREATE TABLE agent_session (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    notebook_id TEXT,
    status TEXT NOT NULL,  -- active, completed, failed
    messages TEXT,  -- JSON array
    actions TEXT,  -- JSON array (audit log)
    token_usage TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent (id),
    FOREIGN KEY (notebook_id) REFERENCES notebook (id)
);
```

### Notebook Database Schema

**Location:** `<notebook_path>/.codex/notebook.db` (SQLite per notebook)

**Tables:**

```sql
-- File metadata and tracking
CREATE TABLE file_metadata (
    id TEXT PRIMARY KEY,  -- ULID
    path TEXT NOT NULL UNIQUE,  -- Relative to notebook root
    filename TEXT NOT NULL,
    extension TEXT,
    size INTEGER,
    mime_type TEXT,
    
    -- Content tracking
    content_hash TEXT,  -- SHA256 for change detection
    last_modified TIMESTAMP,
    
    -- Metadata from frontmatter/sidecars
    title TEXT,
    properties TEXT,  -- JSON (flexible metadata)
    
    -- Git integration
    git_tracked BOOLEAN DEFAULT FALSE,
    git_commit_hash TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP  -- Soft delete
);

-- Tag definitions
CREATE TABLE tag (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File-tag relationships (many-to-many)
CREATE TABLE file_tag (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES file_metadata (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE CASCADE,
    UNIQUE (file_id, tag_id)
);

-- Full-text search index (FTS5)
CREATE VIRTUAL TABLE search_index USING fts5(
    file_id UNINDEXED,
    path UNINDEXED,
    title,
    content,
    tags
);
```

### Database Isolation & References

**Cross-Database References:**
- System DB stores `notebook_id` (ULID)
- Notebook DB stores `notebook_id` as metadata (for reverse lookup)
- File operations query both:
  1. System DB: Validate workspace/notebook permissions
  2. Notebook DB: Fetch file metadata

**Example Query Flow:**
```python
# 1. Get notebook info from system DB
notebook = session.exec(
    select(Notebook).where(Notebook.id == notebook_id)
).first()

# 2. Get notebook DB session
notebook_session = get_notebook_session(notebook.db_path)

# 3. Query file metadata
files = notebook_session.exec(
    select(FileMetadata).where(FileMetadata.deleted_at == None)
).all()
```

### Migration Management

**Alembic Configuration (`alembic.ini`):**
```ini
[alembic:workspace]
script_location = codex/migrations/workspace
version_locations = codex/migrations/workspace/versions

[alembic:notebook]
script_location = codex/migrations/notebook
version_locations = codex/migrations/notebook/versions
```

**Migration Commands:**
```bash
# System DB migrations
alembic -n workspace upgrade head
alembic -n workspace revision -m "Add new table"

# Notebook DB migrations (applied to all notebooks)
alembic -n notebook upgrade head
alembic -n notebook revision -m "Add search index"
```

**Auto-Migration on Startup:**
- System DB: Migrated during `init_system_db()`
- Notebook DBs: Migrated when watcher starts for each notebook
- Detects pre-Alembic databases and stamps with base revision

### Indexes and Performance

**System DB Indexes:**
```sql
CREATE INDEX idx_workspace_owner ON workspace (owner_id);
CREATE INDEX idx_notebook_workspace ON notebook (workspace_id);
CREATE INDEX idx_task_status ON task (status, created_at);
CREATE INDEX idx_agent_session_agent ON agent_session (agent_id);
```

**Notebook DB Indexes:**
```sql
CREATE INDEX idx_file_path ON file_metadata (path);
CREATE INDEX idx_file_updated ON file_metadata (updated_at DESC);
CREATE INDEX idx_file_tag_file ON file_tag (file_id);
CREATE INDEX idx_file_tag_tag ON file_tag (tag_id);
```

**Query Optimization:**
- Full-text search uses FTS5 virtual table
- Soft deletes filtered with `WHERE deleted_at IS NULL`
- Compound indexes for common query patterns

## API Design

### REST API Principles

**Base URL:** `/api/v1/`

**Design Patterns:**
- Resource-oriented URLs
- HTTP verbs for actions (GET, POST, PUT, PATCH, DELETE)
- Hierarchical nesting for related resources
- Consistent error responses
- Pagination for list endpoints
- HATEOAS links for navigation (planned)

### Authentication

**Endpoints:**
```
POST   /api/v1/users/token      # Login (returns JWT)
POST   /api/v1/users/register   # Create new user
GET    /api/v1/users/me         # Current user profile
PUT    /api/v1/users/me         # Update profile
DELETE /api/v1/users/me         # Delete account
```

**Authentication Flow:**
```
1. Client sends credentials to /users/token
2. Server validates with password hash
3. Server generates JWT (30 min expiry)
4. Client stores token in localStorage
5. Client includes in Authorization header:
   "Authorization: Bearer <token>"
```

### Resource Endpoints

**Workspaces:**
```
GET    /api/v1/workspaces/              # List workspaces
POST   /api/v1/workspaces/              # Create workspace
GET    /api/v1/workspaces/{id}          # Get workspace
GET    /api/v1/workspaces/{slug}        # Get by slug
PUT    /api/v1/workspaces/{id}          # Update workspace
DELETE /api/v1/workspaces/{id}          # Delete workspace
GET    /api/v1/workspaces/{id}/members  # List members
POST   /api/v1/workspaces/{id}/members  # Add member
```

**Notebooks:**
```
GET    /api/v1/notebooks/                           # List notebooks (filtered by workspace)
POST   /api/v1/notebooks/                           # Create notebook
GET    /api/v1/notebooks/{id}                       # Get notebook
PUT    /api/v1/notebooks/{id}                       # Update notebook
DELETE /api/v1/notebooks/{id}                       # Delete notebook
GET    /api/v1/notebooks/{id}/files                 # List files
POST   /api/v1/notebooks/{id}/initialize            # Initialize git + db
POST   /api/v1/notebooks/{id}/sync                  # Force sync
```

**Files:**
```
GET    /api/v1/files/                    # List files (query params)
POST   /api/v1/files/                    # Create file
GET    /api/v1/files/{id}                # Get file content + metadata
PUT    /api/v1/files/{id}                # Update file
DELETE /api/v1/files/{id}                # Delete file
PATCH  /api/v1/files/{id}                # Partial update (metadata only)
GET    /api/v1/files/{id}/history        # Git history
POST   /api/v1/files/{id}/restore        # Restore from commit
POST   /api/v1/files/resolve-link        # Resolve [[link]]
```

**Folders:**
```
GET    /api/v1/folders/                  # List folders
POST   /api/v1/folders/                  # Create folder
GET    /api/v1/folders/{path}            # Get folder + children
DELETE /api/v1/folders/{path}            # Delete folder
```

**Search:**
```
GET    /api/v1/search/                   # Full-text search
GET    /api/v1/search/tags               # Search by tags
POST   /api/v1/search/advanced           # Complex query
```

**Query (Dynamic Views):**
```
POST   /api/v1/query/execute             # Execute view query
POST   /api/v1/query/aggregate           # Aggregate query
GET    /api/v1/query/schema              # Query schema
```

**Tasks:**
```
GET    /api/v1/tasks/                    # List tasks
POST   /api/v1/tasks/                    # Create task
GET    /api/v1/tasks/{id}                # Get task
PATCH  /api/v1/tasks/{id}                # Update status
DELETE /api/v1/tasks/{id}                # Cancel task
```

**Agents:**
```
GET    /api/v1/agents/                   # List agents
POST   /api/v1/agents/                   # Create agent
GET    /api/v1/agents/{id}               # Get agent
PUT    /api/v1/agents/{id}               # Update agent
DELETE /api/v1/agents/{id}               # Delete agent
POST   /api/v1/agents/{id}/sessions      # Start session
GET    /api/v1/agents/{id}/sessions/{sid} # Get session
POST   /api/v1/agents/{id}/sessions/{sid}/messages  # Send message
```

**Plugins:**
```
GET    /api/v1/plugins/                  # List plugins
POST   /api/v1/plugins/register          # Register plugin
POST   /api/v1/plugins/batch-register    # Register multiple
GET    /api/v1/plugins/views             # List view types
GET    /api/v1/plugins/themes            # List themes
GET    /api/v1/plugins/{id}/config       # Get workspace config
PUT    /api/v1/plugins/{id}/config       # Update config
```

**Integrations (Plugin-Provided):**
```
POST   /api/v1/integrations/{plugin_id}/execute  # Execute integration
GET    /api/v1/integrations/{plugin_id}/status   # Integration status
```

### Request/Response Formats

**Standard Response:**
```json
{
  "data": { ... },
  "meta": {
    "request_id": "01H2...",
    "timestamp": "2026-02-16T18:00:00Z"
  }
}
```

**Error Response:**
```json
{
  "detail": "Workspace not found",
  "error_code": "WORKSPACE_NOT_FOUND",
  "meta": {
    "request_id": "01H2...",
    "timestamp": "2026-02-16T18:00:00Z"
  }
}
```

**Pagination:**
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "pages": 5
  }
}
```

### WebSocket API

**Connection:**
```javascript
ws://localhost:8000/api/v1/ws/{notebook_id}?token={jwt_token}
```

**Message Format:**
```json
{
  "type": "file_modified",
  "data": {
    "file_id": "01H2...",
    "path": "experiments/results.md",
    "timestamp": "2026-02-16T18:00:00Z"
  }
}
```

**Event Types:**
- `file_created`
- `file_modified`
- `file_deleted`
- `metadata_updated`
- `task_status_changed`
- `agent_message`

## Security Architecture

### Authentication Mechanisms

**JWT Token Authentication:**
```python
# Token structure
{
  "sub": "user_id",  # Subject (user ID)
  "exp": 1234567890, # Expiration (30 min)
  "iat": 1234567860, # Issued at
  "scope": "user"     # Access scope
}
```

**Password Security:**
- **Hashing**: PBKDF2-SHA256
- **Iterations**: 100,000
- **Salt**: Random per user
- **Storage**: `<algorithm>:<iterations>:<salt>:<hash>`

**Token Delivery:**
1. Response body (JSON)
2. Secure cookie (HttpOnly, SameSite=Strict)

### Authorization Model

**Permission Levels:**
```python
class WorkspaceRole:
    OWNER = "owner"      # Full control
    EDITOR = "editor"    # Read/write files
    VIEWER = "viewer"    # Read-only
```

**Permission Checks:**
```python
def check_workspace_access(user, workspace, required_role):
    permission = get_permission(user.id, workspace.id)
    if not permission:
        raise HTTPException(403, "Access denied")
    
    if role_hierarchy[permission.role] < role_hierarchy[required_role]:
        raise HTTPException(403, "Insufficient permissions")
```

### Agent Scope Guards

**Scope Restrictions:**
```python
class AgentScopeGuard:
    """Prevents agents from accessing data outside their workspace."""
    
    def validate_file_access(self, agent, file_path):
        # Ensure file_path is within agent's notebook
        if not file_path.is_relative_to(agent.notebook_path):
            raise SecurityError("Path outside scope")
```

**Tool Routing:**
- Agents can only read/write files in their notebook
- Cannot access system database
- Cannot modify workspace settings
- API calls proxied through integration endpoints

### Secret Management

**Plugin Secrets:**
```python
class PluginSecret(SQLModel):
    workspace_id: str
    plugin_id: str
    key: str
    encrypted_value: str  # Encrypted with Fernet
```

**Encryption:**
```python
from cryptography.fernet import Fernet

# Encryption key derived from SECRET_KEY
fernet = Fernet(derive_key(SECRET_KEY))
encrypted = fernet.encrypt(api_key.encode())
```

### Security Best Practices

**Implemented:**
✅ Parameterized SQL queries (SQLAlchemy/SQLModel)
✅ Path traversal prevention (`.resolve()` + validation)
✅ CORS configuration
✅ Request rate limiting (planned)
✅ Input validation (Pydantic schemas)
✅ Secure password hashing (PBKDF2)
✅ HTTPOnly cookies for tokens

**Recommended Improvements:**
⚠️ SECRET_KEY enforcement (remove default)
⚠️ CORS tightening for production
⚠️ CSP headers for frontend
⚠️ Rate limiting per user/IP
⚠️ Audit logging for sensitive operations
⚠️ Multi-factor authentication (MFA)
⚠️ API key rotation mechanism

### Vulnerability Mitigation

**SQL Injection:** Prevented via ORM parameterization
**XSS:** Sanitized output in Vue templates
**CSRF:** SameSite cookies + CORS
**Path Traversal:** Validated with `.resolve()` and scope checks
**Secrets Exposure:** Encrypted storage, no env var logging

## Plugin System

### Plugin Architecture

**Plugin Types:**
1. **View Plugins** - Custom UI components (Kanban, Gallery, etc.)
2. **Theme Plugins** - Visual styling packages
3. **Integration Plugins** - External API connections

**Plugin Structure:**
```
plugins/
├── my-plugin/
│   ├── manifest.yml            # Plugin metadata
│   ├── components/             # Vue components (views)
│   │   └── MyView.vue
│   ├── styles/                 # CSS (themes)
│   │   └── theme.css
│   ├── endpoints/              # Python modules (integrations)
│   │   └── api.py
│   └── README.md
```

### Plugin Manifest

**Example (`manifest.yml`):**
```yaml
id: my-plugin
name: My Custom Plugin
version: 1.0.0
author: John Doe
description: Custom view for project tracking

# View plugin
views:
  - type: project-board
    name: Project Board
    component: components/ProjectBoard.vue
    icon: board
    config_schema:
      type: object
      properties:
        columns:
          type: array
        show_dates:
          type: boolean

# Theme plugin
theme:
  name: Dark Mode
  styles: styles/dark.css
  variables:
    primary-color: "#1e1e1e"
    text-color: "#ffffff"

# Integration plugin
integrations:
  - type: jira
    name: Jira Integration
    endpoint: endpoints/jira.py
    config_schema:
      type: object
      properties:
        api_url:
          type: string
        api_key:
          type: string
```

### Plugin Lifecycle

**Discovery & Loading:**
```python
class PluginLoader:
    def load_all_plugins(self):
        for plugin_dir in self.plugins_path.iterdir():
            manifest = self.load_manifest(plugin_dir)
            plugin = Plugin(manifest=manifest)
            self.register_plugin(plugin)
```

**Registration:**
```bash
# Auto-registered on startup
# Or manually via API:
curl -X POST /api/v1/plugins/register \
  -H "Content-Type: application/json" \
  -d '{"manifest": {...}}'
```

**Activation:**
```python
# Per-workspace activation
PUT /api/v1/plugins/{plugin_id}/config
{
  "workspace_id": "01H2...",
  "enabled": true,
  "config": {
    "api_key": "...",
    "custom_setting": "value"
  }
}
```

### View Plugin Development

**Component Interface:**
```vue
<script setup lang="ts">
interface Props {
  data: any[]          // Query results
  config: ViewConfig   // User configuration
  notebook: Notebook   // Current notebook context
}

const emit = defineEmits<{
  update: [data: any]  // Emit updates (e.g., task status change)
  refresh: []          // Request data refresh
}>()
</script>

<template>
  <!-- Custom UI -->
</template>
```

**Build & Bundle:**
```bash
# Vue component compilation
vite build --config vite.plugin.config.js

# Output: components/MyView.js (bundled)
```

### Integration Plugin Development

**Endpoint Definition:**
```python
# endpoints/weather.py
from fastapi import APIRouter, Depends
from codex.api.auth import get_current_active_user

router = APIRouter()

@router.get("/current")
async def get_weather(
    location: str,
    user: User = Depends(get_current_active_user)
):
    # Fetch from external API
    api_key = get_plugin_secret(user.workspace_id, "weather-api", "api_key")
    weather_data = await fetch_weather(location, api_key)
    return weather_data
```

**Registration:**
```python
# Automatically mounted at:
# /api/v1/integrations/weather-api/current
```

### Theme Plugin Development

**Theme Structure:**
```css
/* styles/theme.css */
:root {
  --primary-color: #3b82f6;
  --background-color: #ffffff;
  --text-color: #1f2937;
  --border-color: #e5e7eb;
}

body {
  background: var(--background-color);
  color: var(--text-color);
}

/* Component overrides */
.workspace-header {
  border-bottom: 1px solid var(--border-color);
}
```

**Theme Metadata:**
```yaml
theme:
  name: Ocean Blue
  description: Calm blue color scheme
  styles: styles/theme.css
  preview: preview.png
  variables:
    primary-color: "#3b82f6"
    accent-color: "#10b981"
```

### Security Considerations

**Plugin Isolation:**
- Plugins run in main process (no sandboxing yet)
- Access to full API surface
- Recommended: Code review before installation

**Secret Storage:**
- API keys encrypted in database
- Never exposed in frontend
- Retrieved server-side for integration calls

**Permission Model:**
- Per-workspace enable/disable
- Owner/admin required for installation
- Viewers cannot configure plugins

## Scalability & Performance

### Current Scalability

**Single-Server Deployment:**
- SQLite system database
- Per-notebook SQLite databases
- File-based storage
- In-memory WebSocket connections
- Recommended: <100 notebooks, <10 concurrent users

### Bottlenecks & Solutions

#### 1. Database Concurrency

**Issue:** SQLite single-writer limitation

**Current Mitigation:**
- Per-notebook DBs distribute writes
- Write-ahead logging (WAL) mode
- Batched watcher updates (5s intervals)

**Future Solutions:**
- PostgreSQL for system DB
- Read replicas for queries
- Connection pooling

#### 2. Filesystem Watchers

**Issue:** Thread-per-notebook doesn't scale to 1000s

**Current Implementation:**
```python
# One watchdog observer per notebook
for notebook in notebooks:
    observer = Observer()
    observer.schedule(handler, notebook_path, recursive=True)
    observer.start()
```

**Future Solutions:**
- Single watchdog observer with multiplexing
- External file event service (S3 events, inotify cluster)
- Async watcher with `aiofiles`

#### 3. WebSocket Scalability

**Issue:** In-memory connection dict doesn't scale horizontally

**Current:**
```python
active_connections: Dict[str, Set[WebSocket]] = {}
```

**Future Solutions:**
- Redis pub/sub for cross-instance broadcasting
- Separate WebSocket service
- Message queue (RabbitMQ, Kafka)

#### 4. Search Performance

**Issue:** SQL LIKE queries slow on large datasets

**Current:** Basic SQL-based search

**Future Solutions:**
- Elasticsearch cluster
- Meilisearch for typo-tolerance
- Vector search for semantic similarity

### Performance Optimizations

**Implemented:**
✅ Async I/O throughout stack
✅ Database connection pooling
✅ Batched file operations
✅ Lazy loading of file content
✅ Indexed database columns
✅ WebSocket event coalescing

**Recommended:**
⚠️ Redis caching for frequent queries
⚠️ CDN for static assets
⚠️ HTTP/2 for multiplexing
⚠️ Service workers for offline capability
⚠️ Lazy-loaded Vue components
⚠️ Virtual scrolling for large lists

### Monitoring & Observability

**Current:**
✅ Request ID correlation
✅ Structured logging (JSON/colored)
✅ Configurable log levels

**Recommended:**
⚠️ APM integration (Sentry, DataDog, New Relic)
⚠️ Metrics collection (Prometheus)
⚠️ Distributed tracing (OpenTelemetry)
⚠️ Database query profiling
⚠️ Frontend performance monitoring (Web Vitals)

## Deployment Architecture

### Development Deployment

**Docker Compose:**
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8765:8000"
    volumes:
      - ./data:/app/data
      - ./plugins:/app/plugins
    environment:
      - DATABASE_URL=sqlite:///./data/codex_system.db
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=true

  frontend:
    build: ./frontend
    ports:
      - "8065:80"
    volumes:
      - ./plugins:/plugins
    depends_on:
      - backend
```

**Access Points:**
- Frontend: `http://localhost:8065`
- Backend API: `http://localhost:8765`
- API Docs: `http://localhost:8765/docs`

### Production Deployment

**Single-Server (Recommended for <100 users):**

```
┌─────────────────────────────────────┐
│         Cloud Provider               │
│  (DigitalOcean, AWS, GCP, Azure)    │
│                                      │
│  ┌──────────────────────────────┐  │
│  │    Load Balancer (Optional)   │  │
│  └─────────────┬─────────────────┘  │
│                │                     │
│  ┌─────────────▼─────────────────┐  │
│  │       Docker Host             │  │
│  │                               │  │
│  │  ┌──────────┐  ┌───────────┐ │  │
│  │  │  Nginx   │  │  Backend  │ │  │
│  │  │ (Reverse │◄─┤  (FastAPI)│ │  │
│  │  │  Proxy)  │  └───────────┘ │  │
│  │  └──────────┘                │  │
│  │                               │  │
│  │  ┌──────────────────────────┐ │  │
│  │  │   Persistent Volumes     │ │  │
│  │  │   - codex_system.db      │ │  │
│  │  │   - /data (notebooks)    │ │  │
│  │  │   - /plugins             │ │  │
│  │  └──────────────────────────┘ │  │
│  └───────────────────────────────┘  │
│                                      │
│  ┌───────────────────────────────┐  │
│  │   Backups (Automated)         │  │
│  │   - Database snapshots        │  │
│  │   - File storage sync         │  │
│  └───────────────────────────────┘  │
└──────────────────────────────────────┘
```

**Deployment Steps:**
```bash
# 1. Configure environment
cp .env.example .env
# Edit: SECRET_KEY, DATABASE_URL, etc.

# 2. Build images
docker-compose -f docker-compose.prod.yml build

# 3. Start services
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose exec backend alembic upgrade head

# 5. Create admin user
docker-compose exec backend python -m codex.scripts.create_admin
```

**Kubernetes (Recommended for >100 users):**

```yaml
# Simplified k8s architecture
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codex-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: codex-backend
  template:
    spec:
      containers:
      - name: backend
        image: codex-backend:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: codex-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: codex-secrets
              key: secret-key
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: codex-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: codex-backend-service
spec:
  selector:
    app: codex-backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### Infrastructure Components

**Database:**
- Development: SQLite
- Production: PostgreSQL RDS (AWS), Cloud SQL (GCP)
- Backups: Automated snapshots, point-in-time recovery

**File Storage:**
- Development: Local filesystem
- Production: EBS volumes (AWS), Persistent Disks (GCP), or S3/GCS

**Caching (Optional):**
- Redis for session storage
- CloudFront/CloudFlare CDN for static assets

**Monitoring:**
- CloudWatch (AWS), Stackdriver (GCP), DataDog
- Sentry for error tracking
- Prometheus + Grafana for metrics

### SSL/TLS Configuration

**Nginx with Let's Encrypt:**
```nginx
server {
    listen 443 ssl http2;
    server_name codex.example.com;

    ssl_certificate /etc/letsencrypt/live/codex.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/codex.example.com/privkey.pem;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Request-ID $request_id;
    }

    location /api/v1/ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Backup Strategy

**Database Backups:**
```bash
# Automated daily backups
0 2 * * * docker exec codex-backend python -m codex.scripts.backup_db

# Backup retention: 7 daily, 4 weekly, 12 monthly
```

**File Storage Backups:**
```bash
# Rsync to backup server
rsync -avz /data/workspaces/ backup-server:/backups/codex/

# Or S3 sync
aws s3 sync /data/workspaces/ s3://codex-backups/
```

### Disaster Recovery

**RTO (Recovery Time Objective):** <1 hour
**RPO (Recovery Point Objective):** <24 hours

**Recovery Steps:**
1. Provision new infrastructure (if needed)
2. Restore database from latest snapshot
3. Restore file storage from backup
4. Deploy application containers
5. Verify connectivity and functionality

## Key Design Decisions

### 1. Two-Database Pattern

**Decision:** System DB + per-notebook DBs

**Rationale:**
- **Scalability**: Notebooks can be distributed across storage
- **Isolation**: Corruption in one notebook doesn't affect others
- **Concurrency**: Distribute write load across databases
- **Flexibility**: Different notebooks can have different schemas (future)

**Tradeoffs:**
- Operational complexity (multiple databases to manage)
- Cross-notebook queries more difficult
- Migration management for all notebooks

### 2. File-System Source of Truth

**Decision:** Filesystem is authoritative, DB mirrors state

**Rationale:**
- **User Control**: Users can edit files with any tool
- **Git Integration**: Native git workflow support
- **Portability**: Easy to move/backup (just copy directory)
- **Transparency**: Users see actual files, not DB abstractions

**Tradeoffs:**
- Watcher complexity to keep DB in sync
- Potential for DB-filesystem drift
- Performance overhead of filesystem operations

### 3. SQLite (not PostgreSQL)

**Decision:** SQLite for both system and notebook databases

**Rationale:**
- **Simplicity**: Zero configuration, file-based
- **Portability**: Easy to move/backup
- **Performance**: Fast for read-heavy workloads
- **Embedded**: No separate database server needed

**Tradeoffs:**
- Single-server limitation
- Write concurrency limits
- No horizontal scaling without migration

### 4. Plugin-Based Extensibility

**Decision:** Manifest-based plugin system for views/themes/integrations

**Rationale:**
- **Flexibility**: Users can customize without core changes
- **Community**: Enable third-party contributions
- **Modularity**: Features can be added/removed independently
- **Customization**: Per-workspace plugin configuration

**Tradeoffs:**
- Security concerns (plugins run in main process)
- Version compatibility challenges
- Testing burden (plugin combinations)

### 5. Async FastAPI

**Decision:** Async-first backend with FastAPI

**Rationale:**
- **Concurrency**: Handle many concurrent connections
- **Modern**: Leverages Python 3.13+ async features
- **Performance**: Non-blocking I/O for network/disk operations
- **DX**: Auto-generated API docs, type validation

**Tradeoffs:**
- Async complexity (must be async-aware throughout)
- Thread-safety concerns with SQLite
- Learning curve for contributors

### 6. Vue 3 Composition API

**Decision:** Vue 3 with Composition API (not React)

**Rationale:**
- **Reactivity**: Built-in reactive state management
- **TypeScript**: Excellent TypeScript support
- **Performance**: Faster than Vue 2, smaller bundle
- **DX**: Single-file components, hot module reload

**Tradeoffs:**
- Smaller ecosystem than React
- Composition API learning curve
- Plugin system tied to Vue

### 7. Workspace → Notebook → Files Hierarchy

**Decision:** Three-level hierarchy for organization

**Rationale:**
- **Scalability**: Clear boundaries for permissions and data
- **Organization**: Natural mental model (project → experiment → files)
- **Isolation**: Notebooks are independent units
- **Permissions**: Workspace-level access control

**Tradeoffs:**
- Additional nesting complexity
- Moving between workspaces requires file copies
- Harder to implement global features (cross-workspace search)

## Recommendations

### Critical (Production-Ready)

1. **Environment-Based Secret Management**
   - Remove default `SECRET_KEY` fallback
   - Enforce environment variable for production
   - Use secrets manager (AWS Secrets Manager, Vault)

2. **CORS Tightening**
   - Replace `allow_origins=["*"]` with explicit domains
   - Configure for production environment

3. **Database Migration Path**
   - Document PostgreSQL migration procedure
   - Provide migration script from SQLite
   - Test multi-instance deployment

4. **Backup Automation**
   - Implement automated database backups
   - Configure file storage replication
   - Document disaster recovery procedures

### High Priority

5. **Full-Text Search Engine**
   - Integrate Elasticsearch or Meilisearch
   - Implement semantic search (vector embeddings)
   - Add search result highlighting

6. **Rate Limiting**
   - Add per-user API rate limiting
   - Implement IP-based rate limiting
   - Configure thresholds per endpoint

7. **Audit Logging**
   - Log all write operations
   - Track user actions for compliance
   - Implement log rotation and archival

8. **Watcher Resilience**
   - Implement async watchers
   - Add reconnection logic
   - Handle watcher failures gracefully

9. **End-to-End Testing**
   - Add Playwright/Cypress tests
   - Test critical user flows
   - Automate in CI/CD pipeline

### Medium Priority

10. **Plugin Sandboxing**
    - Isolate plugins in Web Workers (frontend)
    - Consider Deno for backend plugins
    - Implement permission model

11. **Schema Documentation**
    - Generate ER diagrams
    - Document migration patterns
    - Create database schema versioning guide

12. **Performance Monitoring**
    - Integrate APM (Sentry, DataDog)
    - Track frontend performance (Web Vitals)
    - Monitor database query performance

13. **API Response Caching**
    - Implement cache-control headers
    - Add ETags for conditional requests
    - Configure Redis caching layer

14. **WebSocket Reconnection**
    - Automatic client-side reconnect
    - Exponential backoff
    - Catch-up events on reconnect

### Nice to Have

15. **Multi-Factor Authentication**
    - TOTP support (Google Authenticator)
    - SMS backup codes
    - Recovery codes

16. **API Versioning Strategy**
    - Document API deprecation policy
    - Implement version negotiation
    - Support multiple API versions

17. **Soft Deletes**
    - Implement soft delete for all entities
    - Add undelete functionality
    - Configure retention policies

18. **Feature Flags**
    - Add feature flag system
    - Enable gradual rollouts
    - A/B testing capability

19. **Webhook Support**
    - Outbound webhooks for events
    - Webhook delivery tracking
    - Retry logic for failed deliveries

20. **Architecture Diagrams**
    - Create visual architecture diagrams
    - Document data flow
    - Sequence diagrams for key operations

---

## Conclusion

Codex demonstrates a **well-architected system** with thoughtful design decisions that balance simplicity, scalability, and extensibility. The two-database pattern, plugin system, and file-system-as-source-of-truth approach provide a solid foundation for growth.

**Strengths:**
- Clean separation of concerns
- Async-first architecture
- Comprehensive testing
- Excellent documentation
- Plugin extensibility

**Areas for Improvement:**
- Security hardening (secrets, CORS)
- Database scalability (PostgreSQL migration)
- Production observability
- End-to-end testing

The system is **production-ready for single-server deployments** and has a clear path to horizontal scalability for larger deployments.

---

*This document is maintained by the Codex development team. For questions or feedback, please open an issue in the repository.*

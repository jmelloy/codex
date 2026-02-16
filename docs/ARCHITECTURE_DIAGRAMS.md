# Codex Architecture Diagrams

This document contains visual representations of the Codex architecture using ASCII diagrams.

## System Architecture

### High-Level Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                  Codex System                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │                         Frontend (Vue.js)                         │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │   │
│   │  │  Views   │  │  Stores  │  │  Router  │  │  Plugin System  │  │   │
│   │  │          │  │  (Pinia) │  │          │  │                 │  │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └─────────────────┘  │   │
│   └─────────────────────┬────────────────────────────────────────────┘   │
│                         │ HTTP/REST + WebSocket                          │
│                         ▼                                                 │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │                      Backend (FastAPI)                           │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │   │
│   │  │   API    │  │   Core   │  │  Agents  │  │    Plugins      │  │   │
│   │  │  Routes  │  │ Services │  │  System  │  │    System       │  │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └─────────────────┘  │   │
│   └─────────────────────┬────────────────────────────────────────────┘   │
│                         │ SQLModel ORM                                    │
│                         ▼                                                 │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │                       Data Layer                                 │   │
│   │  ┌──────────────────────┐        ┌────────────────────────────┐ │   │
│   │  │  System Database     │        │  Notebook Databases        │ │   │
│   │  │  (codex_system.db)   │        │  (.codex/notebook.db)      │ │   │
│   │  │                      │        │                            │ │   │
│   │  │  - Users             │        │  - File Metadata           │ │   │
│   │  │  - Workspaces        │        │  - Tags                    │ │   │
│   │  │  - Permissions       │        │  - Search Index (FTS5)     │ │   │
│   │  │  - Notebooks (reg)   │        │  - Per notebook isolation  │ │   │
│   │  │  - Agents            │        │                            │ │   │
│   │  │  - Plugins           │        │                            │ │   │
│   │  └──────────────────────┘        └────────────────────────────┘ │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                         │                         │                       │
│                         ▼                         ▼                       │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │                    Infrastructure                                │   │
│   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │   │
│   │  │   SQLite    │  │  Filesystem  │  │  External Services     │  │   │
│   │  │  (storage)  │  │  (watched)   │  │  (APIs via plugins)    │  │   │
│   │  └─────────────┘  └──────────────┘  └────────────────────────┘  │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## Data Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│                            User                                │
│  - username, email, password_hash                              │
│  - is_active                                                   │
└──────────────────┬─────────────────────────────────────────────┘
                   │ owns/has permission to (1:N)
                   ▼
┌────────────────────────────────────────────────────────────────┐
│                         Workspace                              │
│  - name, slug, path                                            │
│  - owner_id, theme_setting                                     │
└──────────────────┬─────────────────────────────────────────────┘
                   │ contains (1:N)
                   ▼
┌────────────────────────────────────────────────────────────────┐
│                         Notebook                               │
│  - name, slug, path (relative to workspace)                    │
│  - description                                                 │
│  - Has own database: .codex/notebook.db                        │
└──────────────────┬─────────────────────────────────────────────┘
                   │ contains (1:N)
                   ▼
┌────────────────────────────────────────────────────────────────┐
│                      File Metadata                             │
│  - path, filename, content_type, size                          │
│  - title, description, properties (JSON)                       │
│  - file_hash (for change detection)                            │
│  - created_at, updated_at, deleted_at                          │
└──────────────────┬─────────────────────────────────────────────┘
                   │ has (M:N via file_tags)
                   ▼
┌────────────────────────────────────────────────────────────────┐
│                           Tag                                  │
│  - name                                                        │
│  - created_at                                                  │
└────────────────────────────────────────────────────────────────┘
```

## Request Flow

### File Read Request

```
1. User opens file in browser
   │
   ▼
2. Frontend: Vue component calls fileService.getFile(fileId)
   │
   ▼
3. HTTP GET /api/v1/files/{fileId}
   │
   ▼
4. Backend: Route handler validates JWT token
   │
   ▼
5. Backend: Check user has permission to workspace
   │
   ▼
6. Backend: Query notebook database for file metadata
   │
   ▼
7. Backend: Read file content from filesystem
   │
   ▼
8. Backend: Parse metadata (frontmatter/sidecar)
   │
   ▼
9. Backend: Return FileWithContent response
   │
   ▼
10. Frontend: Update file store, render in editor
```

### File Change Detection

```
1. User edits file in external editor (VSCode, etc.)
   │
   ▼
2. Filesystem: File modified event
   │
   ▼
3. Watchdog Observer: Detect change
   │
   ▼
4. NotebookWatcher: Add to FileOperationQueue
   │
   ▼
5. Queue: Batch operations (5 second window)
   │
   ▼
6. Queue Processor: Process batch
   │
   ├──► Parse metadata
   ├──► Update file_metadata table
   ├──► Update search index (FTS5)
   ├──► Git commit (if text file)
   └──► WebSocket: Broadcast change notification
        │
        ▼
7. Frontend: Receive WebSocket message
   │
   ▼
8. Frontend: Update file tree reactively
   │
   ▼
9. User sees updated file in browser
```

## Authentication Flow

```
┌──────────────┐                   ┌──────────────┐
│   Frontend   │                   │   Backend    │
└──────┬───────┘                   └──────┬───────┘
       │                                  │
       │  1. POST /api/v1/users/token    │
       │     {username, password}         │
       ├─────────────────────────────────►│
       │                                  │
       │                           2. Validate password
       │                              (PBKDF2 hash check)
       │                                  │
       │                           3. Generate JWT token
       │                              (exp: 30 minutes)
       │                                  │
       │  4. Return token + set cookie   │
       │◄─────────────────────────────────┤
       │     {access_token: "..."}        │
       │     Set-Cookie: access_token=... │
       │                                  │
       │  5. Store token in memory        │
       │     (Pinia auth store)           │
       │                                  │
       │  6. Subsequent requests          │
       │     Authorization: Bearer <token>│
       ├─────────────────────────────────►│
       │                                  │
       │                           7. Validate JWT
       │                              (signature, exp)
       │                                  │
       │                           8. Extract user ID
       │                                  │
       │                           9. Fetch user from DB
       │                                  │
       │  10. Return protected resource   │
       │◄─────────────────────────────────┤
       │                                  │
```

## Agent System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                          Agent Request                             │
│  POST /api/v1/sessions/{session_id}/messages                       │
│  {message: "List all markdown files in experiments/"}             │
└──────────────────────┬─────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Agent Engine                               │
│  - Load agent configuration (model, provider)                      │
│  - Decrypt API credentials (Fernet)                                │
│  - Create LiteLLM provider instance                                │
└──────────────────────┬─────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Scope Guard                                │
│  - Check agent permissions (can_read=True)                         │
│  - Validate path access (within scope folders)                     │
│  - Check file type restrictions                                    │
│  - Block if unauthorized                                           │
└──────────────────────┬─────────────────────────────────────────────┘
                       │ Authorized
                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Tool Router                                │
│  - Route to appropriate tool (list_files)                          │
│  - Execute tool with scoped context                                │
│  - Return results to LLM                                           │
└──────────────────────┬─────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                       LLM Provider                                 │
│  - Send prompt + tool results to LLM API                           │
│  - Stream response back                                            │
│  - Handle tool calls iteratively                                   │
└──────────────────────┬─────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                       Action Logger                                │
│  - Log action (type, target, allowed, timing)                      │
│  - Store in agent_action_logs table                                │
│  - Immutable audit trail                                           │
└──────────────────────┬─────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                     Response to Client                             │
│  {role: "assistant", content: "Found 5 files..."}                  │
└────────────────────────────────────────────────────────────────────┘
```

## Plugin System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        Plugin Lifecycle                            │
└────────────────────────────────────────────────────────────────────┘

1. Development
   │
   ├──► Plugin developer creates manifest.yml
   ├──► Developer writes Vue component (for views/themes)
   ├──► Developer writes Python code (for integrations)
   ├──► Build plugin: npm run build
   └──► Output: dist/plugin.js, manifest.yml

2. Registration
   │
   ├──► POST /api/v1/plugins/register
   ├──► Validate manifest (schema, ID, version)
   ├──► Store in plugins table
   └──► Return plugin_id

3. Installation (Workspace Level)
   │
   ├──► POST /api/v1/plugins/{plugin_id}/enable
   ├──► Create plugin_configs entry (workspace_id, plugin_id)
   ├──► Set enabled=true, config={}
   └──► Plugin available in workspace

4. Loading (Frontend)
   │
   ├──► Frontend: Fetch enabled plugins for workspace
   ├──► GET /api/v1/plugins?workspace_id={id}
   ├──► For each plugin:
   │    ├──► Dynamic import: import(`/plugins/${plugin_id}/dist/plugin.js`)
   │    ├──► Register component: app.component(plugin.name, plugin.component)
   │    └──► Store in pluginRegistry
   └──► Plugins ready for use

5. Execution (View Plugin Example)
   │
   ├──► User creates .cdx file: view_type: "kanban"
   ├──► Frontend: Render ViewRenderer component
   ├──► ViewRenderer: Look up "kanban" in plugin registry
   ├──► Load KanbanView component
   ├──► Execute view query (POST /api/v1/query)
   ├──► Pass results to KanbanView as props
   └──► Render interactive Kanban board

6. Execution (Integration Plugin Example)
   │
   ├──► User clicks "Fetch GitHub Issue"
   ├──► Frontend: POST /api/v1/plugins/integrations/{plugin_id}/execute
   ├──► Backend: IntegrationExecutor loads plugin
   ├──► Backend: Execute plugin code with config
   ├──► Backend: Log to plugin_api_logs
   ├──► Backend: Store result in integration_artifacts
   └──► Frontend: Display result to user
```

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                   Docker Compose (Development)                  │
│                                                                 │
│  ┌──────────────────────┐      ┌────────────────────────────┐ │
│  │  frontend-dev        │      │  backend-dev               │ │
│  │                      │      │                            │ │
│  │  - Node.js           │      │  - Python 3.13             │ │
│  │  - Vite dev server   │◄────►│  - FastAPI                 │ │
│  │  - Hot reload        │      │  - Uvicorn                 │ │
│  │  - Port: 5173        │      │  - Auto reload             │ │
│  │                      │      │  - Port: 8000              │ │
│  └──────────────────────┘      └────────────┬───────────────┘ │
│                                              │                 │
│                                              │                 │
│  ┌───────────────────────────────────────────▼───────────────┐ │
│  │              Shared Volumes                               │ │
│  │                                                           │ │
│  │  - ./data:/data                (workspaces & notebooks)  │ │
│  │  - ./codex_system.db           (system database)         │ │
│  │  - ./backend:/app/backend      (source code)             │ │
│  │  - ./frontend:/app/frontend    (source code)             │ │
│  │  - ./plugins:/plugins          (plugin directory)        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
```

### Production Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                   Docker Compose (Production)                   │
│                                                                 │
│  ┌──────────────────────┐      ┌────────────────────────────┐ │
│  │  nginx               │      │  backend                   │ │
│  │                      │      │                            │ │
│  │  - Static SPA        │      │  - Python 3.13             │ │
│  │  - Gzip compression  │◄────►│  - FastAPI                 │ │
│  │  - Proxy /api/*      │      │  - Uvicorn (4 workers)     │ │
│  │  - SSL/TLS           │      │  - Production config       │ │
│  │  - Port: 80/443      │      │  - Port: 8000 (internal)   │ │
│  │                      │      │                            │ │
│  └──────────────────────┘      └────────────┬───────────────┘ │
│                                              │                 │
│                                              │                 │
│  ┌───────────────────────────────────────────▼───────────────┐ │
│  │              Persistent Volumes                           │ │
│  │                                                           │ │
│  │  - /data (mounted from host or network storage)          │ │
│  │    ├── codex_system.db                                   │ │
│  │    ├── workspace1/                                       │ │
│  │    │   ├── notebook1/.codex/notebook.db                  │ │
│  │    │   └── notebook2/.codex/notebook.db                  │ │
│  │    └── workspace2/                                       │ │
│  │        └── ...                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Access:
- Application: http://your-domain.com or https://your-domain.com
- API: https://your-domain.com/api/v1/
```

## Database Migration Strategy

```
┌────────────────────────────────────────────────────────────────────┐
│                      Alembic Configuration                         │
│                       (alembic.ini)                                │
│                                                                    │
│  ┌──────────────────────────┐  ┌─────────────────────────────┐   │
│  │  [alembic:workspace]     │  │  [alembic:notebook]         │   │
│  │                          │  │                             │   │
│  │  script_location:        │  │  script_location:           │   │
│  │    migrations/workspace/ │  │    migrations/notebook/     │   │
│  │                          │  │                             │   │
│  │  sqlalchemy.url:         │  │  sqlalchemy.url:            │   │
│  │    codex_system.db       │  │    (dynamic per notebook)   │   │
│  └──────────────────────────┘  └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
                     │                           │
                     ▼                           ▼
┌─────────────────────────────┐    ┌──────────────────────────────┐
│  Workspace Migrations       │    │  Notebook Migrations         │
│  (System Database)          │    │  (Per-Notebook Databases)    │
│                             │    │                              │
│  001_initial.py             │    │  001_initial.py              │
│  002_add_agents.py          │    │  002_rename_frontmatter.py   │
│  003_add_plugins.py         │    │  003_add_file_hash.py        │
│  ...                        │    │  ...                         │
└─────────────────────────────┘    └──────────────────────────────┘
                     │                           │
                     ▼                           ▼
┌─────────────────────────────┐    ┌──────────────────────────────┐
│  codex_system.db            │    │  notebook1/.codex/notebook.db│
│                             │    │  notebook2/.codex/notebook.db│
│  - alembic_version          │    │  - alembic_version           │
│  - users                    │    │  - file_metadata             │
│  - workspaces               │    │  - tags                      │
│  - notebooks                │    │  - search_index              │
│  - agents                   │    │                              │
│  - plugins                  │    │                              │
│  - ...                      │    │                              │
└─────────────────────────────┘    └──────────────────────────────┘

Migration Execution:
- On startup: run_alembic_migrations() for system DB
- On notebook creation: run_notebook_alembic_migrations(path)
- Pre-Alembic DBs: Auto-detect and stamp with appropriate revision
```

## Security Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        Security Layers                             │
└────────────────────────────────────────────────────────────────────┘

Layer 1: Network Security
├─ CORS configuration (restrict origins)
├─ HTTPS enforcement (production)
└─ Firewall rules (port restrictions)

Layer 2: Authentication
├─ JWT tokens (30-minute expiration)
├─ HTTP-only cookies (CSRF protection)
├─ PBKDF2 password hashing (100,000 iterations)
└─ Token validation on every request

Layer 3: Authorization
├─ Workspace permissions (owner, editor, viewer)
├─ User-workspace relationship checks
└─ Row-level security in database queries

Layer 4: Agent Security
├─ Scope Guards (path, action, file type checks)
├─ Encrypted credentials (Fernet with SECRET_KEY)
├─ Permission enforcement (read, write, create, delete)
├─ Path traversal protection
└─ Action audit logging

Layer 5: Input Validation
├─ Pydantic schemas (type checking)
├─ SQL injection prevention (ORM)
├─ Path sanitization
└─ File type validation

Layer 6: Plugin Security
├─ Manifest validation
├─ Per-workspace enablement
├─ Frontend sandbox (Vue component scope)
└─ API rate limiting (integration plugins)

Layer 7: Audit & Monitoring
├─ Action logs (agent operations)
├─ API logs (integration calls)
├─ Request ID tracking
└─ Error logging
```

---

## Notation

These diagrams use the following conventions:

- **Boxes**: Components, services, or data stores
- **Arrows**: Data flow or dependencies
  - `→`: Unidirectional flow
  - `↔`: Bidirectional communication
  - `▼`: Sequential flow (top to bottom)
- **Nesting**: Containment (outer box contains inner boxes)
- **Dotted lines**: Optional or conditional paths

For more detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

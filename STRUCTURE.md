# Codex Project Structure

## Complete Directory Tree

```
codex/
├── .env.example                    # Environment configuration template
├── .gitignore                      # Git ignore rules
├── README.md                       # Project documentation
├── setup.sh                        # Development setup script
├── pyproject.toml                  # Python project configuration
├── Dockerfile                      # Backend Docker image
├── Dockerfile.frontend             # Frontend Docker image
├── docker-compose.yml              # Docker Compose configuration
│
├── backend/                        # Python backend package
│   ├── __init__.py
│   │
│   ├── api/                       # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py               # API entry point with lifespan, routes
│   │   ├── auth.py               # JWT authentication, password hashing
│   │   └── routes/               # API endpoints
│   │       ├── __init__.py
│   │       ├── workspaces.py     # Workspace CRUD operations
│   │       ├── notebooks.py      # Notebook operations (TODO)
│   │       ├── files.py          # File operations (TODO)
│   │       ├── search.py         # Search endpoints (TODO)
│   │       └── tasks.py          # Task management
│   │
│   ├── core/                     # Business logic
│   │   ├── __init__.py
│   │   ├── watcher.py           # File system monitoring with watchdog
│   │   ├── git_manager.py       # Git operations, auto-commit
│   │   └── metadata.py          # Frontmatter & sidecar parsers
│   │
│   └── db/                       # Database layer
│       ├── __init__.py
│       ├── models.py            # SQLModel ORM models
│       └── database.py          # Connection management
│
├── frontend/                     # Vue.js 3 + TypeScript frontend
│   ├── package.json             # Node dependencies
│   ├── tsconfig.json            # TypeScript configuration
│   ├── vite.config.ts           # Vite bundler config
│   ├── nginx.conf               # Production Nginx config
│   │
│   ├── public/                  # Static assets
│   │
│   └── src/
│       ├── main.ts              # App entry point with Pinia & Router
│       ├── App.vue              # Root component
│       ├── style.css            # Global styles
│       │
│       ├── views/               # Page components
│       │   ├── LoginView.vue    # Authentication page
│       │   └── HomeView.vue     # Main workspace view
│       │
│       ├── stores/              # Pinia state management
│       │   ├── auth.ts          # Authentication state
│       │   └── workspace.ts     # Workspace/notebook state
│       │
│       ├── services/            # API client services
│       │   ├── api.ts           # Axios client with interceptors
│       │   ├── auth.ts          # Auth service methods
│       │   └── codex.ts         # Workspace/notebook/file services
│       │
│       └── router/              # Vue Router
│           └── index.ts         # Route definitions & guards
│
└── tests/                       # Python tests
    ├── __init__.py
    └── test_api.py             # Basic API tests

```

## Key Features Implemented

### Backend (Python 3.14 + FastAPI)

- ✅ SQLModel ORM with dual database architecture
  - System database: users, workspaces, permissions, tasks
  - Notebook database: files, metadata, tags, search index
- ✅ JWT authentication with bcrypt password hashing
- ✅ RESTful API with automatic OpenAPI documentation
- ✅ File system watcher using watchdog
- ✅ Git integration with automatic change tracking
- ✅ Metadata parsers (frontmatter, JSON, XML, Markdown sidecars)
- ✅ Binary file detection and exclusion from git

### Frontend (Vue.js 3 + TypeScript)

- ✅ Vite-based development environment
- ✅ Vue Router with authentication guards
- ✅ Pinia state management
- ✅ Axios API client with token interceptors
- ✅ Login and workspace management views
- ✅ Responsive UI components

### DevOps

- ✅ Docker containerization for backend and frontend
- ✅ Docker Compose for multi-service orchestration
- ✅ Nginx configuration for production deployment
- ✅ Development and production modes

## API Endpoints

### Authentication

- `POST /token` - Get JWT access token
- `GET /users/me` - Get current user info

### Workspaces

- `GET /api/v1/workspaces/` - List user's workspaces
- `POST /api/v1/workspaces/` - Create new workspace
- `GET /api/v1/workspaces/{id}` - Get workspace details

### Tasks

- `GET /api/v1/tasks/?workspace_id={id}` - List tasks
- `POST /api/v1/tasks/` - Create task
- `GET /api/v1/tasks/{id}` - Get task
- `PUT /api/v1/tasks/{id}` - Update task status

### Notebooks, Files, Search (Stubs Ready)

- Notebook CRUD operations
- File management with metadata
- Full-text search and tag-based search

## Data Models

### System Database Models

- `User` - User accounts
- `Workspace` - Workspace containers
- `WorkspacePermission` - Access control
- `Task` - Agent task queue

### Notebook Database Models

- `Notebook` - Notebook metadata
- `FileMetadata` - File tracking with metadata
- `Tag` - Tagging system
- `SearchIndex` - Full-text search

## Development Workflow

1. **Setup**: Run `./setup.sh` to install dependencies
2. **Backend**: `uvicorn backend.api.main:app --reload --port 8000`
3. **Frontend**: `cd frontend && npm run dev`
4. **Docker**: `docker-compose up -d`

## Next Steps (TODOs in Code)

1. Implement notebook CRUD operations in `backend/api/routes/notebooks.py`
2. Implement file operations in `backend/api/routes/files.py`
3. Implement search functionality in `backend/api/routes/search.py`
4. Add file editor component to frontend
5. Integrate file watcher with API endpoints
6. Add tag management UI
7. Implement markdown editor with preview
8. Add user registration endpoint
9. Create Alembic migrations for database schema
10. Add comprehensive test coverage

## Technology Stack

**Backend:**

- FastAPI 0.115+
- SQLModel 0.0.22+
- Uvicorn (ASGI server)
- Watchdog 5.0+ (file monitoring)
- GitPython 3.1+ (git operations)
- python-frontmatter 1.1+ (metadata parsing)
- python-jose (JWT)
- passlib + bcrypt (password hashing)

**Frontend:**

- Vue.js 3.5+
- TypeScript 5.9+
- Vite 7.2+ (bundler)
- Vue Router 4
- Pinia (state management)
- Axios (HTTP client)

**Database:**

- SQLite 3 (system & per-notebook databases)
- Async SQLite support via aiosqlite

**Deployment:**

- Docker + Docker Compose
- Nginx (production proxy)

## File Patterns

### Metadata Storage Options

1. **Markdown Frontmatter**

   ```markdown
   ---
   title: Document Title
   tags: [tag1, tag2]
   ---

   Content...
   ```

2. **JSON Sidecar** (`.filename.json`)

   ```json
   {
     "title": "Document Title",
     "tags": ["tag1", "tag2"]
   }
   ```

3. **XML Sidecar** (`.filename.xml`)

   ```xml
   <metadata>
     <title>Document Title</title>
     <tags><tag>tag1</tag></tags>
   </metadata>
   ```

4. **Markdown Sidecar** (`.filename.md`)
   ```markdown
   ---
   title: Document Title
   ---

   Metadata description
   ```

All metadata formats are supported and automatically detected by the `MetadataParser` class.

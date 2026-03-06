# Codex - Copilot Agent Instructions

## Repository Overview

**Codex** is a hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations. It uses a **Workspace → Notebook → Files** hierarchy with SQLite for metadata indexing and filesystem-based content storage.

**Important Repository Notes:**

- The system uses a two-database pattern: system database for users/workspaces, and per-notebook databases for file metadata
- File content is stored in the filesystem with SQLite for indexing and metadata
- Alembic migrations are split into workspace and notebook migration paths

**Tech Stack:**

- **Backend**: Python 3.13+ with FastAPI, SQLModel, SQLite, Alembic migrations
- **Frontend**: Vue.js 3, TypeScript, Vite
- **Deployment**: Docker Compose with production/development configurations

**Project Type**: Full-stack web application with REST API and web UI

## Build, Test, and Validation Steps

### Python Backend

**Python Version Required**: 3.13+

**Installation Steps:**

```bash
# Install dependencies from backend directory
cd backend
pip install -e ".[dev]"

# Run tests
pytest -v

# Run single test file
pytest tests/test_api.py -v

# Run with coverage (as CI does)
pytest -v --cov=. --cov-report=term-missing

# Start backend server
python -m codex.main
# Or with uvicorn directly:
uvicorn codex.main:app --reload --port 8000

# Lint
ruff check .

# Format
black .

# Type check
mypy .
```

### Frontend

**Node Version Required**: 20+

**Build Steps:**

```bash
cd frontend

# Install dependencies
npm install

# Development server (port 5173)
npm run dev

# Build for production
npm run build

# Run tests
npm test -- --run

# Type check
npm run build  # vue-tsc runs as part of build
```

### Docker Deployment

**Development Deployment:**

```bash
docker compose up -d
# Backend: http://localhost:8765
# Frontend: http://localhost:8065
```

**Production Deployment:**

```bash
docker compose -f docker-compose.prod.yml up -d
```

### Database Migrations

The project uses Alembic for database migrations with two separate migration paths:

1. **System Database** (`codex_system.db`): Stores users, workspaces, workspace permissions, tasks, and notebook registrations. Managed by Alembic migrations in `backend/codex/migrations/workspace/`.

2. **Notebook Databases** (`.codex/notebook.db` per notebook): Stores file metadata, tags, and search indexes for each notebook. Managed by separate Alembic migrations in `backend/codex/migrations/notebook/`.

Both migration paths are configured in a single unified `backend/alembic.ini` file with named sections `[alembic:workspace]` and `[alembic:notebook]`.

## Project Layout

### Repository Structure

```
/
├── .github/
│   ├── workflows/          # CI/CD pipelines
│   └── copilot-instructions.md  # This file
├── backend/                # Python backend package
│   ├── codex/             # Main package
│   │   ├── main.py        # FastAPI app entry point
│   │   ├── api/           # API layer
│   │   │   ├── auth.py    # Authentication utilities
│   │   │   ├── schemas.py # API schemas
│   │   │   └── routes/    # REST endpoints
│   │   ├── core/          # Core business logic
│   │   │   ├── watcher.py       # Filesystem watcher
│   │   │   ├── metadata.py      # Metadata parsing
│   │   │   ├── git_manager.py   # Git operations
│   │   │   └── websocket.py     # WebSocket support
│   │   ├── db/            # Database layer
│   │   │   ├── database.py      # Session management
│   │   │   ├── migrations.py    # Migration utilities
│   │   │   └── models/          # SQLModel ORM models
│   │   │       ├── system.py    # User, Workspace, Task models
│   │   │       └── notebook.py  # FileMetadata, Tag models
│   │   ├── migrations/    # Alembic migrations
│   │   │   ├── workspace/ # System DB migrations
│   │   │   └── notebook/  # Notebook DB migrations
│   │   ├── agents/        # Agent system
│   │   ├── plugins/       # Plugin system
│   │   └── scripts/       # Utility scripts
│   ├── tests/             # Python tests (pytest)
│   ├── pyproject.toml     # Python package configuration
│   ├── alembic.ini        # Alembic configuration
│   └── Dockerfile         # Backend Docker image
├── frontend/              # Vue.js web application
│   ├── src/
│   │   ├── main.ts        # Vue app entry point
│   │   ├── router/        # Vue Router configuration
│   │   ├── stores/        # Pinia state management
│   │   ├── services/      # API client services
│   │   ├── views/         # Page components
│   │   └── components/    # Reusable components
│   ├── package.json       # Node dependencies and scripts
│   ├── vite.config.ts     # Vite bundler configuration
│   └── Dockerfile         # Frontend Docker image
├── plugins/               # Plugin directory
├── docs/                  # Documentation
├── docker-compose.yml     # Development Docker setup
└── README.md              # Project README
```

### Key Configuration Files

- **backend/pyproject.toml**: Python dependencies, project metadata, ruff linting config, pytest config
- **backend/alembic.ini**: Alembic configuration with workspace and notebook sections
- **frontend/package.json**: Frontend dependencies and build scripts
- **frontend/vite.config.ts**: Vite configuration including dev server (port 5173) and proxy settings

### CI/CD Pipeline

**GitHub Actions**:

- **Tests**: Run on push/PR to main or develop branches
- **Environment**: Ubuntu latest, Python 3.13+
- **Steps**:
  1. Checkout code
  2. Setup Python
  3. Install dependencies: `pip install -e ".[dev]"`
  4. Run tests: `pytest -v`

## Architecture

### Two-Database Pattern

The system uses two types of SQLite databases:

1. **System Database** (`codex_system.db`): Stores users, workspaces, workspace permissions, tasks, and notebook registrations. Managed by Alembic migrations in `backend/codex/migrations/workspace/`.

2. **Notebook Databases** (`.codex/notebook.db` per notebook): Stores file metadata, tags, and search indexes for each notebook. Managed by separate Alembic migrations in `backend/codex/migrations/notebook/`.

### Key Backend Components

- `backend/codex/main.py` - FastAPI app entry point with lifespan management for file watchers
- `backend/codex/api/routes/` - REST API endpoints (files, folders, notebooks, workspaces, search, tasks, query)
- `backend/codex/core/watcher.py` - Filesystem watcher that syncs file changes to notebook databases
- `backend/codex/core/metadata.py` - Parses metadata from frontmatter, JSON/XML/MD sidecars
- `backend/codex/db/models/system.py` - User, Workspace, WorkspacePermission, Task, Notebook models
- `backend/codex/db/models/notebook.py` - FileMetadata, Tag, FileTag, SearchIndex models
- `backend/codex/db/database.py` - Database session management for both system and notebook DBs

### Key Frontend Components

- `frontend/src/main.ts` - Vue app entry point
- `frontend/src/router/index.ts` - Vue Router configuration
- `frontend/src/stores/` - Pinia stores (auth, workspace, theme)
- `frontend/src/services/api.ts` - Axios-based API client
- `frontend/src/services/codex.ts` - Codex-specific API service

### API Routes Pattern

All API routes are prefixed with `/api/v1/`:

- `/api/v1/users/token` - Authentication
- `/api/v1/users/register` - User registration
- `/api/v1/users/me` - Current user profile
- `/api/v1/workspaces/` - Workspace CRUD
- `/api/v1/notebooks/` - Notebook CRUD
- `/api/v1/files/` - File operations
- `/api/v1/folders/` - Folder operations and metadata
- `/api/v1/search/` - Full-text search
- `/api/v1/tasks/` - Task queue for agents
- `/api/v1/query/` - Advanced query interface

## Testing

Backend tests are in `backend/tests/`. Key test files:

- `test_api.py` - Main API integration tests
- `test_workspaces.py` - Workspace operations
- `test_users.py` - User authentication
- `test_tasks.py` - Task queue
- `test_notebook_migrations.py` - Database migrations

Frontend tests are in `frontend/src/__tests__/` using Vitest.

## Code Style

- Python: Use black for formatting, ruff for linting (line length 120)
- TypeScript/Vue: Use prettier for formatting
- Python target version: 3.13
- Tests use pytest-asyncio with `asyncio_mode = "auto"`

## Common Development Commands

```bash
# Backend server (from backend directory)
cd backend
python -m codex.main
# Or with uvicorn:
uvicorn codex.main:app --reload --port 8000

# Frontend dev server (from frontend directory)
cd frontend
npm run dev  # Runs on http://localhost:5173

# Full stack with Docker
docker compose up -d
# Backend: http://localhost:8765
# Frontend: http://localhost:8065

# Run tests
cd backend
pytest -v

# Create test data
python -m codex.scripts.seed_test_data
# Test accounts: demo/demo123456, testuser/testpass123, scientist/lab123456
```

## Memory Usage

When using the memory tool to store facts about this codebase:

- **Be concise**: Store short, actionable statements (one or two sentences). Avoid lengthy explanations.
- **Focus on plans and inferences**: Record conclusions, design decisions, inferred conventions, and planned approaches—not raw observations or file contents.
- **Skip obvious facts**: Do not store things that are immediately apparent from reading the code or that can always be re-derived in a few seconds.
- **Prefer patterns over instances**: Capture the general rule or convention rather than a specific example.

Good memory entries:
- "All API routes are prefixed with `/api/v1/`. Authentication uses Bearer tokens."
- "Notebook DB migrations live in `backend/codex/migrations/notebook/`; system DB migrations in `backend/codex/migrations/workspace/`."

Poor memory entries (too verbose / not inferential):
- Long code snippets or file contents
- Simple facts already stated in README or docstrings

## Best Practices for Development

1. **Always install dependencies first** before running tests or making changes:
   ```bash
   cd backend
   pip install -e ".[dev]"
   ```

2. **Test your changes** by running the relevant test files:
   ```bash
   pytest tests/test_<module>.py -v
   ```

3. **For frontend changes**, run `npm run build` to ensure the build succeeds.

4. **Database changes** require Alembic migrations:
   - System DB migrations: `backend/codex/migrations/workspace/`
   - Notebook DB migrations: `backend/codex/migrations/notebook/`

5. **File watching**: The backend includes a filesystem watcher that automatically syncs file changes to the notebook database.

## Key Entry Points

- **Backend**: `backend/codex/main.py` - FastAPI app entry point
- **Frontend**: `frontend/src/main.ts` - Vue app entry point
- **Database models**: 
  - `backend/codex/db/models/system.py` - System database models
  - `backend/codex/db/models/notebook.py` - Notebook database models
- **API routes**: `backend/codex/api/routes/` - All REST endpoints
- **Tests**: `backend/tests/` - Comprehensive test suite

## Additional Resources

- **README.md**: Detailed architecture and project overview
- **CLAUDE.md**: Quick reference for Claude Code users
- **docs/**: Additional documentation on migrations, plugins, and architecture

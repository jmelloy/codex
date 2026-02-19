# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Codex is a hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations. It uses a Workspace → Notebook → Files hierarchy with SQLite for metadata indexing and filesystem-based content storage.

## Build and Development Commands

### Backend (Python 3.11+)

```bash
# Install dependencies (always run first)
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

### Frontend (Node.js 20+)

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

### Docker

```bash
# Development
docker compose up -d
# Backend: http://localhost:8765
# Frontend: http://localhost:8065

# Production
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes (Linode LKE)

```bash
# Initial cluster setup (installs ingress-nginx, cert-manager, creates secrets)
./scripts/setup-lke.sh --domain codex.example.com --email admin@example.com

# Deploy with Kustomize
kubectl apply -k k8s/overlays/staging      # staging
kubectl apply -k k8s/overlays/production   # production
```

CI/CD is handled by `.github/workflows/deploy.yml` which builds images to GHCR and deploys via Kustomize. See `k8s/` for manifests.

## Architecture

### Two-Database Pattern

The system uses two types of SQLite databases:

1. **System Database** (`codex_system.db`): Stores users, workspaces, workspace permissions, tasks, and notebook registrations. Managed by Alembic migrations in `backend/codex/migrations/workspace/`.

2. **Notebook Databases** (`.codex/notebook.db` per notebook): Stores file metadata, tags, and search indexes for each notebook. Managed by separate Alembic migrations in `backend/codex/migrations/notebook/`.

Both migration paths are configured in a single unified `backend/alembic.ini` file with named sections `[alembic:workspace]` and `[alembic:notebook]`.

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
- Python target version: 3.11
- Tests use pytest-asyncio with `asyncio_mode = "auto"`

## Test Data

The server must be running before using these scripts. All scripts use the HTTP API (no direct DB access).

```bash
cd backend

# Seed test users, workspaces, notebooks, and files
python -m codex.scripts.seed_test_data

# Clean up all test data (deletes users, workspaces, notebooks via API)
python -m codex.scripts.seed_test_data clean

# User management
python -m codex.scripts.user_manager register <username> <email> <password>
python -m codex.scripts.user_manager token <username> <password>
python -m codex.scripts.user_manager me --token <token>
```

Test accounts: `demo`/`demo123456`, `testuser`/`testpass123`, `scientist`/`lab123456`

**Environment variable**: Set `CODEX_API_URL` to override the default server URL (`http://localhost:8765`).

**Cleanup order**: The cleanup deletes all workspaces for each test user (which cascades to notebooks, files, and filesystem directories), then deletes the user account itself.

## Investigation & Debugging

When debugging or investigating issues, propose a hypothesis and a targeted fix within the first 2-3 file reads. Do not spend more than 5 minutes exploring the codebase without offering a concrete diagnosis or solution direction. If uncertain, present your top 2 hypotheses and ask the user which to pursue.

## Languages & Cross-Cutting Concerns

This project uses Python (FastAPI backend) and TypeScript/Vue (frontend). Primary languages: Python for backend/API, TypeScript for frontend components, YAML for configuration/fixtures. Always check both backend and frontend implications for changes.

## Frontend / Plugins

For frontend plugins and shared modules, always place files in the plugins directory (not frontend/src/) and use relative imports instead of ambiguous aliases like @/. Verify import resolution works in both the main frontend dev server and plugin build contexts.

## Frontend / Styling

When fixing CSS/theme issues, always identify which layer (base styles, theme-specific overrides, component scoped styles) is responsible before making changes. Inspect theme-specific CSS files first when a visual bug appears in only some themes.

## Version Control / Git

Before committing, run `git status` and `git diff --staged` to verify only the intended changes are staged. Do not assume the working tree is clean.
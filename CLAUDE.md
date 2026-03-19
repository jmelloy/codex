# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Codex is a hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations. It uses a Workspace → Notebook → Files hierarchy with SQLite for metadata indexing and filesystem-based content storage. The UI is read-only content display centered on a block/page tree (BlockView).

## Build and Development Commands

### Backend (Python 3.12+)

```bash
cd backend
pip install -e ".[dev]"
pytest -v                          # run tests
python -m codex.main               # start server (port 8000)
ruff check .                       # lint
black .                            # format
```

### Frontend (Node.js 20+)

```bash
cd frontend
npm install
npm run dev                        # dev server (port 5173)
npm run build                      # production build (includes vue-tsc type check)
npm test -- --run                  # run tests
```

### Docker

```bash
docker compose up -d               # Backend :8765, Frontend :8065
```

### Kubernetes (Linode LKE)

```bash
kubectl apply -k k8s/overlays/production
```

CI/CD: `.github/workflows/deploy.yml` builds images to GHCR and deploys via Kustomize.

## Architecture

### Two-Database Pattern

1. **System Database** (`codex_system.db`): Users, workspaces, permissions, tasks, notebook registrations. Alembic migrations in `backend/codex/migrations/workspace/`.

2. **Notebook Databases** (`.codex/notebook.db` per notebook): File metadata, tags, search indexes. Alembic migrations in `backend/codex/migrations/notebook/`.

Both configured in `backend/alembic.ini` with named sections `[alembic:workspace]` and `[alembic:notebook]`.

### Backend

- `backend/codex/main.py` - FastAPI app with lifespan management for file watchers
- `backend/codex/api/routes/` - REST API (files, folders, notebooks, workspaces, search, tasks, blocks, agents, plugins, integrations)
- `backend/codex/core/watcher.py` - Filesystem watcher syncing file changes to notebook databases
- `backend/codex/core/metadata.py` - Frontmatter and sidecar metadata parsing
- `backend/codex/db/models/` - SQLModel models (system.py, notebook.py)
- `backend/codex/plugins/` - Plugin registry, executor, models (themes + integrations only)
- `backend/plugins/` - Plugin assets (themes, opengraph, weather-api)

### Frontend

- `frontend/src/views/HomeView.vue` - Main view (read-only file/folder/block display)
- `frontend/src/stores/` - Pinia stores (auth, workspace, theme, integration)
- `frontend/src/services/codex.ts` - API service (workspaces, notebooks, files, folders, blocks, search)
- `frontend/src/services/pluginLoader.ts` - Loads theme/block plugins from `/api/v1/plugins/manifest`
- `frontend/src/components/MarkdownViewer.vue` - Markdown rendering with custom blocks

### API Routes

All prefixed with `/api/v1/`:
- `/users/` - Auth, registration, profile
- `/workspaces/` - Workspace CRUD
- `/workspaces/{ws}/notebooks/` - Notebook CRUD
- `/workspaces/{ws}/notebooks/{nb}/files/` - File CRUD, upload, history
- `/workspaces/{ws}/notebooks/{nb}/folders/` - Folder metadata
- `/workspaces/{ws}/notebooks/{nb}/blocks/` - Block/page operations
- `/workspaces/{ws}/search/` - Full-text search
- `/tasks/` - Task queue for agents
- `/plugins/manifest` - Plugin manifest for frontend
- `/plugins/assets/` - Plugin asset serving (CSS, JS)
- `/plugins/integrations/` - Integration API proxy

## Testing

Backend: `backend/tests/` with pytest. Key files: `test_api.py`, `test_files_api.py`, `test_integration.py`, `test_workspaces.py`.

Frontend: `frontend/src/__tests__/` with Vitest.

Note: Backend tests use `TestClient(app)` **without** the `with` context manager to avoid triggering lifespan/FSEvents watchers (which causes segfaults on macOS when accumulated).

## Code Style

- Python: black formatting, ruff linting, line length 120, target 3.12
- TypeScript/Vue: prettier formatting
- Tests: pytest-asyncio with `asyncio_mode = "auto"`

## Test Data

Server must be running. Scripts use HTTP API:

```bash
cd backend
python -m codex.scripts.seed_test_data        # seed
python -m codex.scripts.seed_test_data clean   # cleanup
```

Test accounts: `demo`/`demo123456`, `testuser`/`testpass123`, `scientist`/`lab123456`

Set `CODEX_API_URL` to override default (`http://localhost:8765`).

## Guidelines

- Propose a hypothesis within the first 2-3 file reads. If uncertain, present top 2 hypotheses and ask.
- Always check both backend and frontend implications for changes.
- When fixing CSS/theme issues, identify which layer (base, theme-specific, component scoped) is responsible. Check theme CSS files first for theme-specific bugs.
- Prefer git worktree for work.
- Before committing, run `git status` and `git diff --staged` to verify staged changes.
- Any PR that deletes more code than it adds is a good PR.

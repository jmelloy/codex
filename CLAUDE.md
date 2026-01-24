# Codex - Claude Code Instructions

> See also: `.github/copilot-instructions.md` for additional details and MCP server configuration.

## Project Overview

**Codex** is a hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations with full provenance and reproducibility. Structure: Workspace → Notebook → Page → Entry.

**Tech Stack:**

- **Backend**: Python 3.12+ with FastAPI, SQLAlchemy, SQLite, Alembic migrations
- **Frontend**: Vue.js 3, TypeScript, Vite
- **CLI**: Click-based command-line interface
- **Deployment**: Docker Compose

## Quick Commands

```bash
# Backend setup and testing
cd backend && pip install -e ".[dev]"
pytest backend/tests/ -v

# Frontend
cd frontend && npm install && npm run build

# Docker validation
./validate-docker.sh

# Start dev servers
docker compose up -d
# Frontend: http://localhost:5174
# Backend: http://localhost:8765
```

## Project Layout

```
backend/
├── api/           # FastAPI application (main.py entry point)
│   └── routes/    # REST endpoints
├── cli/           # CLI commands (main.py entry point)
├── core/          # Business logic (workspace, notebook, page, storage)
├── db/            # SQLAlchemy models, Alembic migrations
└── tests/         # pytest test suite

frontend/src/
├── views/         # Page components
├── components/    # Reusable components
├── stores/        # Pinia state management
└── router/        # Vue Router configuration
```

## Key Files

- **API entry**: `backend/api/main.py`
- **CLI entry**: `backend/cli/main.py`
- **DB models**: `backend/db/models.py`
- **Frontend entry**: `frontend/src/main.ts`
- **Config**: `pyproject.toml`, `frontend/package.json`

## Important Notes

- Primary storage: SQLite + content-addressable storage (not markdown-first)
- See `AGENT_SYSTEM.md` for the task/sandbox system
- Migrations run automatically on workspace initialization

## Database

Codex uses two SQLite databases:

- **System database** (`codex_system.db`): Users, workspaces, permissions, tasks, notebook metadata
- **Notebook databases** (per-workspace): File content and properties

Both databases use Alembic for schema migrations:

- **System migrations**: `backend/codex/alembic/versions/` - For users, workspaces, etc.
- **Notebook migrations**: `backend/codex/notebook_alembic/versions/` - For file storage

Migrations run automatically when initializing workspaces. To add a new migration:

```bash
# Create new system DB migration
cd backend/codex/alembic/versions
# Copy existing migration as template, update revision ID and down_revision
```

## Git Workflow

- **Commit and push regularly** when working on a feature branch (not main). This preserves work in progress and allows for easier recovery if something goes wrong.
- **Use git worktrees** for parallel work on multiple branches without switching contexts:

  ```bash
  # Create a worktree for a new branch
  git worktree add ../codex-feature feature-branch

  # List existing worktrees
  git worktree list

  # Remove a worktree when done
  git worktree remove ../codex-feature
  ```

## Testing

Expected: 251 tests pass, 63 warnings. Run: `pytest backend/tests/ -v`

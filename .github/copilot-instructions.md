# Codex - Copilot Agent Instructions

## Repository Overview

**Codex** is a hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations with full provenance and reproducibility. It's structured as Workspace → Notebook → Page → Entry.

**Important Repository Notes:**
- The primary storage mode uses SQLite + content-addressable storage (not markdown-first)
- The `cli.markdown_cli` module provides an alternative markdown-based CLI (experimental)
- See [AGENT_SYSTEM.md](AGENT_SYSTEM.md) for the implemented task/sandbox system
- See [agents.md](agents.md) for planned AI agent features (mostly not implemented yet)

**Tech Stack:**

- **Backend**: Python 3.12+ with FastAPI, SQLAlchemy, SQLite, Alembic migrations
- **Frontend**: Vue.js 3, TypeScript, Vite
- **CLI**: Click-based command-line interface
- **Deployment**: Docker Compose with production/development configurations
- **Size**: ~115MB repository with 56 Python files, 30 frontend files

**Project Type**: Full-stack web application with REST API, CLI tools, and web UI

## Build, Test, and Validation Steps

### Python Backend

**Python Version Required**: 3.12+ (3.14 in CI)

**Installation Steps (Always run in this order):**

```bash
# 1. Install dependencies (ALWAYS run before testing or building)
pip install -e ".[dev]"

# 2. Run tests (expected: 251 passed, 63 warnings about deprecated utcnow)
pytest tests/ -v

# 3. Lint code (will show some existing issues - only fix what you change)
ruff check backend/
```

**Known Linting Issues** (Do NOT fix unless you're changing those files):

- `backend/codex/cli/main.py:1020` - Import sorting issue
- `backend/codex/core/git_hooks.py` - Whitespace on blank lines (lines 306, 309, 326)
- `backend/codex/core/mac_windows.py:3` - Import sorting issue

### Frontend

**Node Version Required**: 24+ (tested with 24.0.0)

**Build Steps:**

```bash
cd frontend

# 1. Install dependencies (takes ~4 seconds)
npm install

# 2. Build for production (takes ~2 seconds, creates dist/ folder)
npm run build

# 3. Type check
npm run type-check

# 4. Development server
npm run dev  # Runs on port 5174
```

**Frontend Linting Note**: ESLint is configured in package.json but `npm run lint` will fail because there's no ESLint config file in the repository. Skip linting for frontend changes unless you add an ESLint configuration first.

### Docker Deployment

**Validate Docker Setup (ALWAYS run before docker compose):**

```bash
./validate-docker.sh
```

This checks all required files exist and Docker Compose configs are valid.

**Development Deployment:**

```bash
docker compose up -d
# Frontend: http://localhost:5174
# Backend API: http://localhost:8765
# API Docs: http://localhost:8765/docs
```

**Production Deployment:**

```bash
docker compose -f docker-compose.prod.yml up -d
# Frontend: http://localhost
# Backend API: http://localhost:8765
```

### Database Migrations

The project uses Alembic for database migrations. The migration system automatically runs when initializing a workspace. Database files are stored in `.lab/db/index.db` within each workspace.

**No manual migration commands needed** - migrations run automatically on workspace initialization.

## Project Layout

### Repository Structure

```
/
├── .github/workflows/test.yml    # CI: Python 3.14, pip install, pytest
├── backend/                       # Main Python package directory
│   ├── api/                      # FastAPI application
│   │   ├── main.py              # API entry point
│   │   ├── auth.py              # Authentication utilities
│   │   ├── routes/              # REST endpoints (notebooks, pages, search, markdown, auth, workspace)
│   │   └── websocket/           # WebSocket support (basic)
│   ├── cli/                     # CLI commands
│   │   ├── main.py              # Main CLI entry point (codex command)
│   │   ├── markdown_cli.py      # Alternative markdown-based CLI
│   │   └── commands/            # CLI subcommands directory
│   ├── core/                    # Core business logic
│   │   ├── workspace.py         # Workspace management
│   │   ├── notebook.py          # Notebook operations
│   │   ├── page.py              # Page operations
│   │   ├── storage.py           # Content-addressable storage
│   │   ├── git_hooks.py         # Git hook integration
│   │   ├── git_manager.py       # Git operations
│   │   ├── mac_windows.py       # macOS window tracking
│   │   ├── markdown.py          # Markdown parsing utilities
│   │   ├── markdown_indexer.py  # Markdown file indexing
│   │   ├── markdown_renderers.py # Frontmatter rendering plugins
│   │   ├── markdown_storage.py  # Alternative markdown storage
│   │   ├── folder_config.py     # Folder configuration system
│   │   ├── sandbox.py           # Agent sandbox for safe file operations
│   │   └── tasks.py             # Task management system
│   ├── db/                      # Database layer
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── operations.py        # Database operations
│   │   ├── migrate.py           # Migration utilities
│   │   └── migrations/          # Alembic migrations
│   └── tests/                   # Python tests (pytest)
├── frontend/                    # Vue.js web application
│       └── custom.py            # Custom text entries
├── frontend/                    # Vue.js web application
│   ├── src/
│   │   ├── views/               # Page components (NotebooksView, PageDetailView, etc.)
│   │   ├── components/          # Reusable components
│   │   ├── stores/              # Pinia state management
│   │   └── router/              # Vue Router configuration
│   ├── Dockerfile               # Production build
│   ├── Dockerfile.dev.frontend  # Development with hot reload
│   ├── nginx.conf               # Nginx configuration for production
│   ├── package.json             # Node dependencies and scripts
│   └── vite.config.ts           # Vite bundler configuration
├── tests/                       # Python tests (pytest)
│   ├── test_core.py             # Core functionality tests
│   ├── test_db_crud.py          # Database CRUD tests
│   ├── test_integrations.py    # Integration tests
│   ├── test_migrations.py       # Migration tests
│   └── test_*.py                # Other test modules
├── scripts/mac/                 # macOS-specific scripts for window tracking
├── pyproject.toml               # Python package configuration and dependencies
├── mise.toml                    # Development tool versions (Python 3.14, black)
├── build.sh                     # Build script (frontend build + pip install)
├── validate-docker.sh           # Docker validation script
├── docker-compose.yml           # Development Docker setup
├── docker-compose.prod.yml      # Production Docker setup
└── .env.example                 # Environment variable template
```

### Key Configuration Files

- **pyproject.toml**: Python dependencies, project metadata, ruff linting config, pytest config
- **mise.toml**: Specifies Python 3.14 and black for development
- **package.json**: Frontend dependencies and build scripts
- **.gitignore**: Excludes `.lab/`, `frontend/dist/`, `frontend/node_modules/`, Python cache files

### CI/CD Pipeline

**GitHub Actions** (`.github/workflows/test.yml`):

- **Triggers**: Push/PR to main or develop branches, manual dispatch
- **Environment**: Ubuntu latest, Python 3.14
- **Steps**:
  1. Checkout code
  2. Setup Python 3.14
  3. Install dependencies: `pip install -e ".[dev]"`
  4. Run tests: `pytest tests/ -v`
- **Expected Result**: 251 tests pass, 63 deprecation warnings (these are acceptable)

### Data Model

The system stores data in SQLite (`.lab/db/index.db`) with these main tables:

- **users**: User accounts for authentication
- **refresh_tokens**: JWT refresh tokens
- **notebooks**: Project-level containers
- **pages**: Session-level grouping with narrative fields
- **markdown_files**: Indexed markdown files with metadata
- **tags**: Tag system for categorization
- **notebook_tags**: Many-to-many relationship for notebook tags
- **page_tags**: Many-to-many relationship for page tags

**Note**: The current implementation uses markdown files for content storage with SQLite indexing. See [MARKDOWN_STORAGE.md](../MARKDOWN_STORAGE.md) for the alternative pure-markdown approach.

### Important Implementation Details

1. **Markdown + SQLite Hybrid**: The system uses markdown files for content with SQLite for indexing and metadata (see MarkdownFile model).

2. **Git Integration**: The system optionally integrates with Git via post-commit hooks to log commits to daily notes.

3. **Authentication**: JWT-based authentication with bcrypt password hashing. Each user has their own workspace.

4. **Workspace Initialization**: Always use `codex init <path>` to create a workspace before other operations.

5. **Agent System**: Task management, sandboxing, and folder configuration for AI agents (see AGENT_SYSTEM.md).

6. **Content Storage**: Files stored in workspace directories, optionally with content-addressable blob storage.

## Common Commands

```bash
# Initialize workspace
codex init ~/my-lab --name "My Laboratory"

# Create notebook
codex notebook create "AI Experiments" --description "ML experiments"

# Create page
codex page create "Initial Tests" --notebook "AI Experiments"

# Search entries
codex search --query "experiment"

# Start API server
uvicorn api.main:app --reload --port 8765

# Start full stack (dev)
docker compose up -d

# View help for any command
codex <command> --help
```

## Known Issues and Workarounds

1. **Frontend ESLint**: No ESLint config file exists. Skip `npm run lint` or add configuration first.

2. **Deprecation Warnings in Tests**: 63 warnings about `datetime.utcnow()` are expected - do NOT fix these unless specifically asked.

3. **Python 3.12 vs 3.14**: Local development may use Python 3.12, but CI uses 3.14. Both work fine.

4. **Docker Build Context**: When building, the frontend must be built separately inside its Dockerfile (see Dockerfile.dev.frontend).

5. **Ruff Linting**: Some existing linting issues in `git_hooks.py` and `mac_windows.py`. Only fix issues in code you're modifying.

## Best Practices for Agents

1. **Always install dependencies first** before running tests or making changes: `pip install -e ".[dev]"`

2. **Test your changes** by running the relevant test files: `pytest tests/test_<module>.py -v`

3. **Check Docker validation** if modifying Docker files: `./validate-docker.sh`

4. **For frontend changes**, run `npm run build` to ensure the build succeeds.

5. **Database changes** require Alembic migrations in `backend/codex/db/migrations/versions/`.

6. **Integration changes** must implement the `IntegrationBase` class and register with `IntegrationRegistry`.

7. **Do NOT commit**: `.lab/` directories, `frontend/dist/`, `frontend/node_modules/`, `__pycache__/`, `.venv/`

## Agent Efficiency Tips

- **Use these instructions first** before searching the codebase. Only search if the information here is incomplete or incorrect.
- **Key entry points**: `backend/codex/api/main.py` (API), `backend/codex/cli/main.py` (CLI)
- **Database schema**: `backend/codex/db/models.py`
- **Frontend entry**: `frontend/src/main.ts`, routing in `frontend/src/router/`
- **Tests are comprehensive**: Check `tests/` for examples of how to use the system
- **README.md has detailed architecture**: Refer to it for conceptual understanding

# Codex

A hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations with full provenance and reproducibility.

**Stack**: Python 3.13+ (FastAPI + SQLModel) • Vue.js 3 (TypeScript) • SQLite  
**Hierarchy**: Workspace → Notebook → Files

## Features

- **Multi-workspace** system with user authentication and permissions
- **File-based tracking** with flexible tagging and metadata (frontmatter, JSON/XML sidecars)
- **Automatic sync** via filesystem watcher with Git integration
- **Full-text search** with SQLite FTS5 indexing
- **Task queue** for agent and plugin workflows
- **REST API** with OpenAPI documentation

## Quick Start

### Prerequisites

- Python 3.13+ and Node.js 20+
- Docker and Docker Compose (for containerized deployment)

### Local Development

```bash
# Clone and setup
git clone <repository-url>
cd codex
cp .env.example .env

# Backend (Python 3.13+)
cd backend
pip install -e ".[dev]"
python -m codex.main              # or: uvicorn codex.main:app --reload

# Frontend (in new terminal, Node.js 20+)
cd frontend
npm install
npm run dev

# Create test data (optional)
python -m codex.scripts.seed_test_data
```

**Access**: Frontend at http://localhost:5173 • API at http://localhost:8000 • API Docs at http://localhost:8000/docs

See [TEST_CREDENTIALS.md](TEST_CREDENTIALS.md) for test user accounts.

### Docker Deployment

```bash
docker compose up -d
# Frontend: http://localhost:8065
# Backend: http://localhost:8765
```

## Development

### Testing

```bash
# Run backend tests
cd backend
pytest -v

# Run frontend tests  
cd frontend
npm test -- --run
```

### Code Quality

```bash
# Python
black backend/              # Format
ruff check backend/         # Lint
mypy backend/              # Type check

# Frontend
cd frontend
npm run build              # Build + type check
```

## Architecture

### Database Schema

**System DB** (`codex_system.db`): Users, workspaces, permissions, tasks, notebook registry  
**Notebook DBs** (`.codex/notebook.db` per notebook): File metadata, tags, search index

See [docs/](docs/) for detailed architecture documentation and [CLAUDE.md](CLAUDE.md) for development guidelines.

### Project Structure

```
codex/
├── backend/codex/         # Python backend (FastAPI + SQLModel)
│   ├── api/routes/       # REST API endpoints
│   ├── core/             # Business logic (watcher, git, metadata)
│   ├── db/               # Database models and migrations
│   ├── agents/           # Agent system
│   └── plugins/          # Plugin system
├── frontend/src/         # Vue.js 3 frontend (TypeScript)
│   ├── views/           # Page components
│   ├── stores/          # Pinia state management
│   └── services/        # API client
├── docs/                # Documentation
└── tests/               # Test suites
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Development commands and guidelines for AI assistants
- **[TEST_CREDENTIALS.md](TEST_CREDENTIALS.md)** - Test user accounts
- **[docs/design/](docs/design/)** - Design documents (plugin system, dynamic views, AI agents)
- **API Documentation** - Available at http://localhost:8000/docs when running

## License

MIT License

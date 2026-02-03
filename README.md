# Codex

A hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations with full provenance and reproducibility.

## Architecture

- **Backend**: Python 3.12 with FastAPI + SQLModel
- **Frontend**: Vue.js 3 with TypeScript and Vite
- **Hierarchy**: Workspace → Notebook → Files

## Features

### System Level

- User authentication and authorization
- Multi-workspace support with permission management
- Task management system for agent work
- RESTful API for all operations

### Notebook Level

- File-based data tracking with flexible tagging
- SQLite database for metadata and search indexing
- Automatic filesystem watcher for change detection
- Git integration with automatic versioning (excludes binary files)
- Support for multiple metadata formats:
  - Markdown frontmatter
  - JSON sidecar files
  - XML sidecar files
  - Markdown sidecar files

### Frontend

- Modern Vue.js interface
- Workspace and notebook management
- File browser and editor
- Tag-based organization
- Full-text search capabilities

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 24+
- Docker and Docker Compose (optional)

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd codex
   ```

2. **Set up environment**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install backend dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Install frontend dependencies**

   ```bash
   cd frontend
   npm install
   ```

5. **Run backend**

   ```bash
   uvicorn codex.main:app --reload --port 8000
   ```

6. **Run frontend** (in another terminal)

   ```bash
   cd frontend
   npm run dev
   ```

7. **Access the application**
   - Frontend: http://localhost:5165
   - API: http://localhost:8765
   - API Docs: http://localhost:8765/docs

8. **Load test data** (optional, recommended for testing)

   ```bash
   python -m codex.scripts.seed_test_data
   ```

   This creates three test users with sample workspaces and notebooks. See [TEST_CREDENTIALS.md](TEST_CREDENTIALS.md) for login details.

### Docker Deployment

1. **Start all services**

   ```bash
   docker-compose up -d
   ```

2. **Access the application**
   - Frontend: http://localhost
   - API: http://localhost:8000

## Project Structure

```
codex/
├── backend/                 # Python backend
│   ├── api/                # FastAPI application
│   │   ├── main.py        # API entry point
│   │   ├── auth.py        # Authentication utilities
│   │   └── routes/        # API route handlers
│   ├── core/              # Core business logic
│   │   ├── watcher.py     # File system watcher
│   │   ├── git_manager.py # Git integration
│   │   └── metadata.py    # Metadata parsers
│   └── db/                # Database layer
│       ├── models.py      # SQLModel definitions
│       └── database.py    # Database connections
├── frontend/              # Vue.js frontend
│   ├── src/
│   │   ├── views/        # Page components
│   │   ├── stores/       # Pinia state management
│   │   ├── services/     # API client services
│   │   └── router/       # Vue Router configuration
│   └── nginx.conf        # Nginx configuration for production
├── tests/                # Python tests
├── pyproject.toml        # Python project configuration
├── docker-compose.yml    # Docker composition
└── README.md            # This file
```

## Database Schema

### System Database

- **users**: User accounts
- **workspaces**: Workspace definitions
- **workspace_permissions**: User-workspace permissions
- **tasks**: Agent task queue

### Notebook Database (per-notebook)

- **notebooks**: Notebook metadata
- **file_metadata**: File tracking and metadata
- **tags**: Tag definitions
- **search_index**: Full-text search index

## API Endpoints

### Authentication

- `POST /token` - Login and get access token
- `GET /users/me` - Get current user info

### Workspaces

- `GET /api/v1/workspaces/` - List workspaces
- `POST /api/v1/workspaces/` - Create workspace
- `GET /api/v1/workspaces/{id}` - Get workspace

### Notebooks

- `GET /api/v1/notebooks/` - List notebooks
- `POST /api/v1/notebooks/` - Create notebook
- `GET /api/v1/notebooks/{id}` - Get notebook

### Files

- `GET /api/v1/files/` - List files
- `POST /api/v1/files/` - Create file
- `GET /api/v1/files/{id}` - Get file
- `PUT /api/v1/files/{id}` - Update file

### Search

- `GET /api/v1/search/` - Search files by query
- `GET /api/v1/search/tags` - Search files by tags

### Tasks

- `GET /api/v1/tasks/` - List tasks
- `POST /api/v1/tasks/` - Create task
- `GET /api/v1/tasks/{id}` - Get task
- `PUT /api/v1/tasks/{id}` - Update task

## Testing

### Test Users and Data

For testing, screenshots, and demonstrations, you can create test users with sample data:

```bash
python -m codex.scripts.seed_test_data
```

This creates three test accounts with workspaces, notebooks, and markdown files:

| Username    | Password      | Purpose                                 |
| ----------- | ------------- | --------------------------------------- |
| `demo`      | `demo123456`  | Full-featured account with ML notebooks |
| `testuser`  | `testpass123` | Simple account for basic testing        |
| `scientist` | `lab123456`   | Scientific research notebooks           |

See [TEST_CREDENTIALS.md](TEST_CREDENTIALS.md) for complete details.

To clean up test data:

```bash
python -m codex.scripts.seed_test_data clean
```

### Running Automated Tests

```bash
pytest tests/ -v
```

## Development

### Code Formatting

```bash
black backend/
```

### Linting

```bash
ruff check backend/
```

### Type Checking

```bash
mypy backend/
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

### Metadata Formats

#### Markdown Frontmatter

```markdown
---
title: My Document
tags: [experiment, analysis]
date: 2024-01-01
---

# Content here
```

#### JSON Sidecar (.filename.json)

```json
{
  "title": "My Document",
  "tags": ["experiment", "analysis"],
  "date": "2024-01-01"
}
```

#### XML Sidecar (.filename.xml)

```xml
<metadata>
  <title>My Document</title>
  <tags>
    <tag>experiment</tag>
    <tag>analysis</tag>
  </tags>
  <date>2024-01-01</date>
</metadata>
```

## Documentation

### Design Documents

- **[File-Based Pages Architecture](docs/design/FILE_BASED_PAGES.md)** - Pure file-based approach for organizing content into pages with ordered blocks
- **[Notebook Migrations](docs/NOTEBOOK_MIGRATIONS.md)** - Database migration strategy
- **[Filename Resolution](docs/FILENAME_RESOLUTION.md)** - File naming and resolution logic
- **[Markdown Extensions](docs/MARKDOWN_EXTENSIONS.md)** - Custom markdown features

### Additional Resources

- [Test Credentials](TEST_CREDENTIALS.md) - Test user accounts and sample data
- [Performance Improvements](PERFORMANCE_IMPROVEMENTS.md) - Optimization notes
- [Claude Instructions](CLAUDE.md) - Development guidelines for AI assistants
  Comprehensive design documents are available in the `/docs/design/` directory:

- **[Dynamic Views](docs/design/dynamic-views.md)** - Query-based dynamic views and visualizations
- **[Plugin System](docs/design/plugin-system.md)** - Extensible plugin architecture for views, themes, and integrations

## License

MIT License - see LICENSE file for details

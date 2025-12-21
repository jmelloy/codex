# Backend Directory

This directory contains the Python backend code for the Codex application.

## Structure

```
backend/
└── codex/              # Main Python package
    ├── api/           # FastAPI REST API endpoints
    ├── cli/           # Command-line interface
    ├── core/          # Core business logic
    ├── db/            # Database models and operations
    └── integrations/  # External service integrations
```

## Package Installation

The `codex` package is installed from this directory via the `pyproject.toml` configuration in the repository root:

```toml
[tool.setuptools.packages.find]
where = ["backend"]
include = ["codex*"]
```

When installed, the package is available as `codex` (not `backend.codex`), e.g.:

```python
from core.workspace import Workspace
from api.main import app
```

## Development

To install the package in development mode:

```bash
pip install -e .
```

This allows you to make changes to the code without reinstalling.

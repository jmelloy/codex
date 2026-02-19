# AGENTS.md

Instructions for AI agents working with this codebase.

## Setting Up Test Data

Before running any test data scripts, ensure the backend server is running:

```bash
cd backend
uvicorn codex.main:app --reload --port 8000
# Or via Docker: docker compose up -d
```

The default API URL is `http://localhost:8765`. Override with `CODEX_API_URL` if needed.

### Seeding

```bash
cd backend
python -m codex.scripts.seed_test_data
```

This creates three test users with workspaces, notebooks, and sample markdown files via the HTTP API. The script is idempotent: existing users/workspaces/notebooks are reused.

**Test accounts:**

| Username   | Password      | Email                  |
|------------|---------------|------------------------|
| demo       | demo123456    | demo@example.com       |
| testuser   | testpass123   | test@example.com       |
| scientist  | lab123456     | scientist@example.com  |

### Cleanup

```bash
cd backend
python -m codex.scripts.seed_test_data clean
```

Cleanup uses the HTTP API DELETE endpoints (not direct DB access):

1. Authenticates as each test user
2. Lists and deletes all workspaces via `DELETE /api/v1/workspaces/{id}` (cascades to notebooks, files, and filesystem directories)
3. Deletes the user account via `DELETE /api/v1/users/me`

### User Management CLI

```bash
cd backend

# Register a user
python -m codex.scripts.user_manager register <username> <email> <password>

# Get a bearer token
python -m codex.scripts.user_manager token <username> <password>

# Query current user info
python -m codex.scripts.user_manager me --token <token>
```

## API Authentication

All API calls (except registration and health check) require a bearer token:

```bash
# Get a token
TOKEN=$(python -m codex.scripts.user_manager token demo demo123456)

# Use it
curl -H "Authorization: Bearer $TOKEN" http://localhost:8765/api/v1/workspaces/
```

## Key API Endpoints

All routes are prefixed with `/api/v1/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/users/register` | Register a new user |
| POST   | `/users/token` | Get bearer token |
| GET    | `/users/me` | Current user profile |
| DELETE | `/users/me` | Delete current user (must delete workspaces first) |
| GET    | `/workspaces/` | List workspaces |
| POST   | `/workspaces/` | Create workspace |
| DELETE | `/workspaces/{id}` | Delete workspace (cascades to all contents) |
| GET    | `/workspaces/{id}/notebooks/` | List notebooks |
| POST   | `/workspaces/{id}/notebooks/` | Create notebook |
| DELETE | `/workspaces/{ws_id}/notebooks/{nb_id}` | Delete notebook |
| POST   | `/workspaces/{ws_id}/notebooks/{nb_slug}/files/` | Create file |
| DELETE | `/workspaces/{ws_id}/notebooks/{nb_id}/files/{file_id}` | Delete file |
| GET    | `/search/` | Full-text search |
| GET    | `/tasks/` | Task queue |
| GET    | `/query/` | Advanced query interface |

## Running Tests

```bash
cd backend
pytest -v                    # all tests
pytest tests/test_api.py -v  # specific file
```

Tests use an in-memory database and do not require a running server.

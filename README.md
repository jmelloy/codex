# Codex

A hierarchical digital laboratory journal system for tracking computational experiments, creative iterations, and technical investigations.

**Stack**: Python 3.13 / FastAPI + SQLModel · Vue.js 3 / TypeScript · SQLite · Docker · Kubernetes

**Hierarchy**: Workspace → Notebook → Files

## Quick Start

```bash
cp .env.example .env   # set SECRET_KEY at minimum
docker compose up -d
```

- App (dev frontend): http://localhost:8065
- API: http://localhost:8765
- API Docs: http://localhost:8765/docs

`docker compose up` runs the backend with hot-reload and the Vue dev server with HMR. The production Docker image builds the frontend and serves it as static files from the backend — no separate frontend container needed.

## Local Development (without Docker)

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn codex.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Testing

```bash
cd backend
pytest -v
```

Seed test data (server must be running):

```bash
python -m codex.scripts.seed_test_data
# Accounts: demo/demo123456  testuser/testpass123  scientist/lab123456
python -m codex.scripts.seed_test_data clean  # cleanup
```

## Production (Kubernetes)

Pushing to `main` builds and deploys automatically via GitHub Actions:

```bash
# First-time cluster setup (Linode LKE)
./k8s/setup-lke.sh --domain your-domain.example.com --email admin@example.com

# Manual deploy
kubectl apply -k k8s/overlays/production
```

The backend image includes the compiled frontend. Only two services run in k8s: `backend` and `plugin-service`.

## Project Structure

```
backend/       Python/FastAPI app — API routes, watchers, DB models, migrations
frontend/      Vue.js SPA — built into backend image for production
plugin-service/ Plugin distribution service
k8s/           Kubernetes manifests (Kustomize)
plugins/       Plugin directory
```

## API

All routes are prefixed `/api/v1/`. Interactive docs at `/docs`.

Key resources: `users`, `workspaces`, `notebooks`, `files`, `folders`, `search`, `tasks`, `agents`, `plugins`, `snippets`, `calendar`.

## Configuration

See `.env.example` for all environment variables. Required: `SECRET_KEY`.

## Documentation

Design docs in [`docs/design/`](docs/design/) — plugin system, dynamic views, AI agent integration.

## License

MIT

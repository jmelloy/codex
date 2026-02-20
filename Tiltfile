# -*- mode: Python -*-

# ============================================================
# Codex Tiltfile — local Kubernetes development with k3d
# ============================================================
#
# Prerequisites:
#   k3d, kubectl, tilt, helm
#
# Usage:
#   ./scripts/setup-k3d.sh   # one-time cluster setup
#   tilt up                   # start dev environment
#
# Or simply:
#   make dev-k8s
#
# Access:
#   Backend:  http://localhost:8765
#   Frontend: http://localhost:8065
#   Tilt UI:  http://localhost:10350
# ============================================================

load('ext://namespace', 'namespace_create')

# -- Configuration ------------------------------------------

# Local k3d registry (must match k3d-config.yaml)
REGISTRY = 'codex-registry.localhost:5111'

# -- Namespace ----------------------------------------------

namespace_create('codex')

# -- Kustomize manifests ------------------------------------

k8s_yaml(kustomize('k8s/overlays/dev'))

# -- Backend ------------------------------------------------

docker_build(
    REGISTRY + '/codex-backend',
    context='./backend',
    dockerfile='./backend/Dockerfile',
    live_update=[
        # Sync source code into the running container
        sync('./backend/codex', '/app/codex'),
        sync('./backend/alembic.ini', '/app/alembic.ini'),
        # Re-install if dependencies change (triggers full restart)
        run('uv pip install --system .', trigger=['./backend/pyproject.toml']),
    ],
)

# -- Frontend -----------------------------------------------

# Uses the production multi-stage Dockerfile.
# For Vite HMR, see frontend/Dockerfile.dev and Phase 5 in the
# migration plan (docs/k3d-tilt-migration-plan.md).
docker_build(
    REGISTRY + '/codex-frontend',
    context='./frontend',
    dockerfile='./frontend/Dockerfile',
    build_args={
        'VITE_API_BASE_URL': '/api',
        'PLUGINS_DIR': '/plugins',
    },
    live_update=[
        sync('./frontend/src', '/app/src'),
        sync('./frontend/public', '/app/public'),
        run('pnpm build', trigger=['./frontend/package.json']),
    ],
)

# -- Resource configuration ---------------------------------

k8s_resource(
    'backend',
    port_forwards=['8765:8000'],
    labels=['codex'],
)

k8s_resource(
    'frontend',
    port_forwards=['8065:80'],
    labels=['codex'],
)

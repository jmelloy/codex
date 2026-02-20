# Migration Plan: Docker Compose → k3d + Tilt for Local Development

## Motivation

The current local development workflow uses Docker Compose (`docker-compose.yml` + `docker-compose.override.yml`), while production deploys to Linode LKE via Kustomize (`k8s/`). This creates a gap: the Docker Compose environment doesn't exercise the same Kubernetes manifests, services, ingress, or ConfigMap/Secret patterns that production uses. Bugs in k8s configuration are only caught at deploy time.

**k3d** (k3s-in-Docker) provides a lightweight local Kubernetes cluster that runs inside Docker. **Tilt** watches source files, live-rebuilds container images, and applies k8s manifests with sub-second feedback loops. Together they let developers run the real k8s stack locally with the same hot-reload experience Docker Compose provides today.

### Goals

- Use the **same k8s manifests** (via Kustomize dev overlay) for local dev and production
- Preserve **hot-reload** for both backend (uvicorn `--reload`) and frontend (Vite dev server)
- Keep Docker Compose as an option for simple/quick startup (no removal)
- Provide a one-command `make dev-k8s` entrypoint

---

## Current Architecture Summary

| Component | Docker Compose (local) | Kubernetes (staging/prod) |
|-----------|----------------------|--------------------------|
| Backend | `./backend/Dockerfile`, port 8765→8000 | `k8s/base/backend-deployment.yml`, GHCR image |
| Frontend | `./frontend/Dockerfile` (nginx), port 8065→80 | `k8s/base/frontend-deployment.yml`, GHCR image |
| Frontend dev | Override: node:22 Vite dev server, port 5165→5173 | N/A |
| Config | `.env` file, env vars in compose | ConfigMap `codex-config` + Secret `codex-secrets` |
| Storage | Bind mount `./data:/app/data` | PVC `codex-data` (10–20Gi) |
| Ingress | N/A (direct port mapping) | nginx-ingress + cert-manager |
| Plugins | Bind mount `./plugins:/app/plugins` | emptyDir (no live plugins) |
| DB migrations | `alembic upgrade head` in CMD | Same, via container command |

---

## Phase 1: k3d Cluster Configuration

### 1.1 Create `k3d-config.yaml`

```yaml
# k3d-config.yaml — local development cluster
apiVersion: k3d.io/v1alpha5
kind: Simple
metadata:
  name: codex-dev
servers: 1
agents: 0
image: rancher/k3s:v1.31.4-k3s1
ports:
  # Map localhost:8080 → cluster port 80 (ingress HTTP)
  - port: 8080:80
    nodeFilters:
      - loadbalancer
  # Map localhost:8443 → cluster port 443 (ingress HTTPS)
  - port: 8443:443
    nodeFilters:
      - loadbalancer
registries:
  # Local registry so Tilt can push images without GHCR
  create:
    name: codex-registry.localhost
    host: "0.0.0.0"
    hostPort: "5111"
options:
  k3s:
    extraArgs:
      - arg: --disable=traefik
        nodeFilters:
          - server:*
```

**Key decisions:**
- **Disable Traefik**: k3s ships with Traefik, but the production stack uses nginx-ingress. Disabling Traefik lets us install nginx-ingress for parity.
- **Local registry**: Avoids pushing to GHCR during development. Tilt builds images and pushes to `codex-registry.localhost:5111`, which the k3d cluster can pull from directly.
- **Port mapping**: `localhost:8080` becomes the single entry point for the app, matching how ingress works in production (one host, path-based routing).

### 1.2 Create `scripts/setup-k3d.sh`

Bootstrap script that:
1. Checks for `k3d`, `kubectl`, `tilt`, `helm` prerequisites
2. Creates the cluster from `k3d-config.yaml` (idempotent)
3. Installs nginx-ingress controller via Helm (matching `scripts/setup-lke.sh`)
4. Creates the `codex` namespace
5. Creates `codex-secrets` with a generated dev SECRET_KEY
6. Prints the access URL

---

## Phase 2: Kustomize Dev Overlay

### 2.1 Create `k8s/overlays/dev/kustomization.yml`

A new overlay that adapts the base manifests for local development:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: codex

resources:
  - ../../base

# Images point to local k3d registry
images:
  - name: ghcr.io/OWNER/codex-backend
    newName: codex-registry.localhost:5111/codex-backend
    newTag: dev
  - name: ghcr.io/OWNER/codex-frontend
    newName: codex-registry.localhost:5111/codex-frontend
    newTag: dev

patches:
  # Remove ingress (Tilt handles port-forwarding)
  - target:
      kind: Ingress
      name: codex-ingress
    patch: |
      $patch: delete
      apiVersion: networking.k8s.io/v1
      kind: Ingress
      metadata:
        name: codex-ingress

  # Backend: single replica, relaxed probes, lower resources
  - target:
      kind: Deployment
      name: backend
    patch: |
      - op: replace
        path: /spec/replicas
        value: 1
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: 128Mi
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/memory
        value: 512Mi
      - op: replace
        path: /spec/template/spec/containers/0/readinessProbe/initialDelaySeconds
        value: 5
      - op: replace
        path: /spec/template/spec/containers/0/livenessProbe/initialDelaySeconds
        value: 30
      - op: replace
        path: /spec/template/spec/containers/0/livenessProbe/periodSeconds
        value: 60

  # Frontend: single replica
  - target:
      kind: Deployment
      name: frontend
    patch: |
      - op: replace
        path: /spec/replicas
        value: 1

  # PVC: smaller for dev
  - target:
      kind: PersistentVolumeClaim
      name: codex-data
    patch: |
      - op: replace
        path: /spec/resources/requests/storage
        value: 1Gi

  # ConfigMap: dev-friendly values
  - target:
      kind: ConfigMap
      name: codex-config
    patch: |
      - op: replace
        path: /data/DEBUG
        value: "true"
      - op: replace
        path: /data/LOG_LEVEL
        value: "DEBUG"
      - op: replace
        path: /data/LOG_FORMAT
        value: "colored"
```

**Key decisions:**
- **Delete ingress**: In local dev, Tilt's `k8s_resource(..., port_forwards=)` handles routing. No need for nginx-ingress or TLS.
- **Relaxed probes**: Avoids pod restarts during slow rebuilds.
- **Debug mode**: Colored logs, DEBUG=true, matching current Docker Compose dev experience.

---

## Phase 3: Tiltfile

### 3.1 Create `Tiltfile`

```python
# -*- mode: Python -*-

# ============================================================
# Codex Tiltfile — local Kubernetes development with k3d
# ============================================================
# Usage:
#   k3d cluster create --config k3d-config.yaml
#   tilt up
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
        # Restart uvicorn when dependencies change
        run('uv pip install --system .', trigger=['./backend/pyproject.toml']),
    ],
)

# -- Frontend -----------------------------------------------

# For dev, we build the production Dockerfile but use live_update
# for the static assets. Alternatively, a custom_build with
# Vite dev server could be used (see Phase 5 enhancement).
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
    resource_deps=['codex-config', 'codex-secrets', 'codex-data'],
)

k8s_resource(
    'frontend',
    port_forwards=['8065:80'],
    labels=['codex'],
    resource_deps=['backend'],
)
```

### 3.2 Live Update Strategy

The key advantage of Tilt is **live_update** — syncing changed files into the running container without a full image rebuild.

| Service | Trigger | Action |
|---------|---------|--------|
| Backend | `codex/**/*.py` changed | Sync into `/app/codex/`, uvicorn auto-reloads |
| Backend | `pyproject.toml` changed | Run `uv pip install --system .` then restart |
| Frontend | `src/**` changed | Sync into `/app/src/`, trigger `pnpm build` |
| Frontend | `package.json` changed | Full image rebuild |

**Note on backend command**: The backend deployment command is `alembic upgrade head && python -m codex.main`. For development, the Tiltfile could override this with a Kustomize patch to use `uvicorn codex.main:app --host 0.0.0.0 --port 8000 --reload` for better hot-reload. This would go in the dev overlay as an additional patch.

---

## Phase 4: Developer Scripts & Makefile

### 4.1 `scripts/setup-k3d.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Check prerequisites
for cmd in k3d kubectl tilt helm; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: $cmd is required but not installed."
    exit 1
  fi
done

CLUSTER_NAME="codex-dev"

# Create cluster (idempotent)
if k3d cluster list | grep -q "$CLUSTER_NAME"; then
  echo "Cluster '$CLUSTER_NAME' already exists."
else
  echo "Creating k3d cluster '$CLUSTER_NAME'..."
  k3d cluster create --config k3d-config.yaml
fi

# Wait for cluster to be ready
echo "Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=60s

# Install nginx-ingress (optional, for ingress testing)
if ! kubectl get namespace ingress-nginx &>/dev/null; then
  echo "Installing nginx-ingress controller..."
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
  helm repo update
  helm install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx --create-namespace \
    --set controller.publishService.enabled=true
fi

# Create namespace
kubectl create namespace codex --dry-run=client -o yaml | kubectl apply -f -

# Create dev secrets
if ! kubectl get secret codex-secrets -n codex &>/dev/null; then
  echo "Creating dev secrets..."
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  kubectl create secret generic codex-secrets \
    --namespace codex \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --from-literal=OPENGRAPH_IO_API_KEY="dev-placeholder" \
    --from-literal=GOOGLE_CLIENT_ID="dev-placeholder" \
    --from-literal=GOOGLE_CLIENT_SECRET="dev-placeholder"
fi

echo ""
echo "k3d cluster '$CLUSTER_NAME' is ready!"
echo ""
echo "Next steps:"
echo "  tilt up                    # Start development"
echo "  make dev-k8s               # Or use the Makefile target"
echo ""
echo "Access:"
echo "  Backend:  http://localhost:8765"
echo "  Frontend: http://localhost:8065"
echo "  Tilt UI:  http://localhost:10350"
```

### 4.2 Makefile additions

```makefile
# =============================================================================
# Kubernetes Local Development (k3d + Tilt)
# =============================================================================

# One-command setup: create cluster + start Tilt
dev-k8s: k3d-up
	tilt up

# Create/start the k3d cluster
k3d-up:
	@./scripts/setup-k3d.sh

# Stop Tilt and delete the k3d cluster
k3d-down:
	@echo "Deleting k3d cluster..."
	k3d cluster delete codex-dev

# Stop the cluster without deleting (preserves PVCs)
k3d-stop:
	@echo "Stopping k3d cluster..."
	k3d cluster stop codex-dev

# Resume a stopped cluster
k3d-start:
	@echo "Starting k3d cluster..."
	k3d cluster start codex-dev
```

---

## Phase 5: Enhanced Frontend Dev Experience (Optional)

The Phase 3 frontend setup rebuilds nginx static files on every change. For a faster inner loop matching the current Docker Compose dev experience (Vite HMR), an alternative approach:

### 5.1 Separate frontend-dev Dockerfile

Create `frontend/Dockerfile.dev`:

```dockerfile
FROM node:25-slim
WORKDIR /app
RUN npm install -g pnpm
COPY pnpm-lock.yaml package.json ./
RUN pnpm install
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]
```

### 5.2 Dev overlay patch for frontend

Add a patch in `k8s/overlays/dev/` that swaps the frontend container to use Vite dev server:

```yaml
# frontend-dev-patch.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  template:
    spec:
      containers:
        - name: frontend
          ports:
            - containerPort: 5173
              protocol: TCP
          readinessProbe:
            httpGet:
              port: 5173
          livenessProbe:
            httpGet:
              port: 5173
```

And update the frontend Service to target port 5173.

### 5.3 Updated Tiltfile fragment

```python
# Frontend with Vite HMR (dev mode)
docker_build(
    REGISTRY + '/codex-frontend',
    context='./frontend',
    dockerfile='./frontend/Dockerfile.dev',
    live_update=[
        sync('./frontend/src', '/app/src'),
        sync('./frontend/public', '/app/public'),
        sync('./frontend/index.html', '/app/index.html'),
    ],
)

k8s_resource(
    'frontend',
    port_forwards=['5165:5173'],
    labels=['codex'],
)
```

---

## Implementation Checklist

### Phase 1 — k3d cluster (do first)
- [ ] Install prerequisites: `k3d`, `tilt`, `helm`
- [ ] Create `k3d-config.yaml` at project root
- [ ] Create `scripts/setup-k3d.sh`
- [ ] Test: `./scripts/setup-k3d.sh` creates a working cluster
- [ ] Test: `kubectl get nodes` shows a Ready node

### Phase 2 — Kustomize dev overlay
- [ ] Create `k8s/overlays/dev/kustomization.yml`
- [ ] Test: `kubectl kustomize k8s/overlays/dev` renders valid YAML
- [ ] Verify images reference `codex-registry.localhost:5111`

### Phase 3 — Tiltfile
- [ ] Create `Tiltfile` at project root
- [ ] Test: `tilt up` builds images, pushes to local registry, deploys to k3d
- [ ] Verify backend live_update: edit a `.py` file → pod updates without rebuild
- [ ] Verify frontend rebuild on source change
- [ ] Verify port-forwards: backend on 8765, frontend on 8065

### Phase 4 — Developer ergonomics
- [ ] Add Makefile targets (`dev-k8s`, `k3d-up`, `k3d-down`, `k3d-stop`, `k3d-start`)
- [ ] Update `CLAUDE.md` with k3d/Tilt instructions
- [ ] Update `Makefile` help target

### Phase 5 — Frontend HMR (optional, can be done later)
- [ ] Create `frontend/Dockerfile.dev`
- [ ] Add frontend dev overlay patches (container port, service port, command)
- [ ] Update Tiltfile to use dev Dockerfile
- [ ] Verify Vite HMR works through the port-forward

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| k3d requires Docker running | Can't use if Docker daemon is down | Same requirement as Docker Compose; no regression |
| SQLite on PVC in k3d | Local PVC uses `rancher.io/local-path`; data lost on cluster delete | Document `k3d-stop`/`k3d-start` for preserving state; dev data is ephemeral anyway |
| Port conflicts with Docker Compose | Both try to bind 8765/8065 | Use different ports or document `docker compose down` before `tilt up` |
| Tilt learning curve | Developers need to learn new tool | Tilt UI is intuitive; provide `make dev-k8s` one-liner; keep Docker Compose as fallback |
| Image build speed | First build is slow (no cache in registry) | Tilt's live_update skips most rebuilds; `docker_build` uses layer caching |
| Plugin volume mounts | Plugins currently bind-mounted in Docker Compose | Use Tilt `sync()` or a hostPath mount in k3d for plugin dir |

---

## Migration Timeline

This is an additive change — Docker Compose continues to work. The rollout can be gradual:

1. **Phase 1–3**: Core functionality. Developers can try `tilt up` alongside existing Docker Compose.
2. **Phase 4**: Polish. Once validated, update docs and Makefile to promote k3d/Tilt as the recommended local workflow.
3. **Phase 5**: Optional. Only needed if the nginx-rebuild feedback loop on frontend changes feels too slow.

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `k3d-config.yaml` | Create | k3d cluster configuration |
| `Tiltfile` | Create | Tilt orchestration for local k8s dev |
| `k8s/overlays/dev/kustomization.yml` | Create | Dev-specific Kustomize overlay |
| `scripts/setup-k3d.sh` | Create | Cluster bootstrap script |
| `frontend/Dockerfile.dev` | Create (Phase 5) | Vite dev server Dockerfile |
| `Makefile` | Edit | Add `dev-k8s`, `k3d-*` targets |
| `CLAUDE.md` | Edit | Document k3d/Tilt workflow |
| `docker-compose.yml` | No change | Kept as-is for fallback |

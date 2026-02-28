#!/usr/bin/env bash
set -euo pipefail

# setup-k3d.sh — Bootstrap a k3d cluster for local Codex development.
#
# Usage:
#   ./scripts/setup-k3d.sh          # create cluster + install deps
#   ./scripts/setup-k3d.sh teardown # delete the cluster
#
# Prerequisites: k3d, kubectl, tilt, helm

CLUSTER_NAME="codex-dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# -- Helpers ------------------------------------------------

info()  { echo "==> $*"; }
error() { echo "ERROR: $*" >&2; exit 1; }

check_prereqs() {
    local missing=()
    for cmd in k3d kubectl tilt helm; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        error "Missing required tools: ${missing[*]}
Install them before continuing:
  k3d:     https://k3d.io/#installation
  kubectl: https://kubernetes.io/docs/tasks/tools/
  tilt:    https://docs.tilt.dev/install.html
  helm:    https://helm.sh/docs/intro/install/"
    fi
}

# -- Teardown -----------------------------------------------

if [ "${1:-}" = "teardown" ]; then
    info "Deleting k3d cluster '$CLUSTER_NAME'..."
    k3d cluster delete "$CLUSTER_NAME" 2>/dev/null || true
    echo "Cluster deleted."
    exit 0
fi

# -- Main ---------------------------------------------------

check_prereqs

# Create cluster (idempotent)
if k3d cluster list 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    info "Cluster '$CLUSTER_NAME' already exists."
    # Ensure it's running
    if ! k3d cluster list 2>/dev/null | grep "$CLUSTER_NAME" | grep -q "running"; then
        info "Starting stopped cluster..."
        k3d cluster start "$CLUSTER_NAME"
    fi
else
    info "Creating k3d cluster '$CLUSTER_NAME'..."
    k3d cluster create --config "$PROJECT_ROOT/k3d-config.yaml"
fi

# Wait for nodes
info "Waiting for cluster nodes to be Ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

# Install nginx-ingress controller (for production parity, optional)
if ! kubectl get namespace ingress-nginx &>/dev/null; then
    info "Installing nginx-ingress controller..."
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 2>/dev/null || true
    helm repo update
    helm install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx --create-namespace \
        --set controller.publishService.enabled=true \
        --wait --timeout 120s
else
    info "nginx-ingress already installed."
fi

# Create codex namespace
kubectl create namespace codex --dry-run=client -o yaml | kubectl apply -f -

# Create dev secrets (idempotent)
if ! kubectl get secret codex-secrets -n codex &>/dev/null; then
    info "Creating dev secrets..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    kubectl create secret generic codex-secrets \
        --namespace codex \
        --from-literal=SECRET_KEY="$SECRET_KEY" \
        --from-literal=OPENGRAPH_IO_API_KEY="dev-placeholder" \
        --from-literal=GOOGLE_CLIENT_ID="dev-placeholder" \
        --from-literal=GOOGLE_CLIENT_SECRET="dev-placeholder"
else
    info "Dev secrets already exist."
fi

echo ""
echo "================================================"
echo " k3d cluster '$CLUSTER_NAME' is ready!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  tilt up                    # Start development"
echo "  make dev-k8s               # Or use the Makefile target"
echo ""
echo "Access (after tilt up):"
echo "  Backend:  http://localhost:8765"
echo "  Frontend: http://localhost:8065"
echo "  Tilt UI:  http://localhost:10350"
echo ""

#!/usr/bin/env bash
#
# setup-lke.sh — Bootstrap a Linode Kubernetes Engine cluster for Codex.
#
# Prerequisites:
#   - kubectl configured with your LKE kubeconfig
#   - helm v3 installed
#   - At least 3 nodes with unformatted block devices for Rook-Ceph
#
# Usage:
#   ./k8s/setup-lke.sh [--domain codex.melloy.life] [--email admin@melloy.life]
#
set -euo pipefail

DOMAIN="${DOMAIN:-codex.melloy.life}"
EMAIL="${EMAIL:-admin@melloy.life}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --domain) DOMAIN="$2"; shift 2 ;;
    --email)  EMAIL="$2";  shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo "==> Setting up Codex on LKE"
echo "    Domain: ${DOMAIN}"
echo "    Email:  ${EMAIL}"
echo ""

# ── 1. Verify cluster access ────────────────────────────────────────────────
echo "==> Verifying cluster connectivity..."
kubectl cluster-info || { echo "ERROR: Cannot reach cluster. Check your kubeconfig."; exit 1; }
echo ""

# ── 2. Install NGINX Ingress Controller ─────────────────────────────────────
echo "==> Installing NGINX Ingress Controller..."
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 2>/dev/null || true
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/linode-loadbalancer-throttle"=5 \
  --wait

echo ""
echo "==> Waiting for LoadBalancer external IP..."
for i in $(seq 1 30); do
  EXTERNAL_IP=$(kubectl -n ingress-nginx get svc ingress-nginx-controller \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
  if [[ -n "${EXTERNAL_IP}" ]]; then
    echo "    External IP: ${EXTERNAL_IP}"
    break
  fi
  echo "    Waiting... (${i}/30)"
  sleep 10
done

if [[ -z "${EXTERNAL_IP:-}" ]]; then
  echo "WARNING: LoadBalancer IP not yet assigned. Check 'kubectl -n ingress-nginx get svc' later."
fi
echo ""

# ── 3. Install cert-manager for automatic TLS ───────────────────────────────
echo "==> Installing cert-manager..."
helm repo add jetstack https://charts.jetstack.io 2>/dev/null || true
helm repo update

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true \
  --wait

echo ""
echo "==> Creating Let's Encrypt ClusterIssuer..."
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ${EMAIL}
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - http01:
          ingress:
            class: nginx
EOF
echo ""

# ── 4. Install Rook-Ceph for shared storage (CephFS) ────────────────────────
echo "==> Installing Rook-Ceph operator..."
helm repo add rook-release https://charts.rook.io/release 2>/dev/null || true
helm repo update

helm upgrade --install rook-ceph rook-release/rook-ceph \
  --namespace rook-ceph \
  --create-namespace \
  --wait

echo ""
echo "==> Waiting for Rook-Ceph operator to be ready..."
kubectl -n rook-ceph rollout status deployment/rook-ceph-operator --timeout=300s

echo ""
echo "==> Creating CephCluster, CephFilesystem, and StorageClass..."
kubectl apply -k k8s/base/rook-ceph/

echo ""
echo "==> Waiting for CephCluster to become healthy (this may take several minutes)..."
for i in $(seq 1 60); do
  PHASE=$(kubectl -n rook-ceph get cephcluster rook-ceph \
    -o jsonpath='{.status.phase}' 2>/dev/null || echo "Pending")
  HEALTH=$(kubectl -n rook-ceph get cephcluster rook-ceph \
    -o jsonpath='{.status.ceph.health}' 2>/dev/null || echo "unknown")
  echo "    CephCluster phase: ${PHASE}, health: ${HEALTH} (${i}/60)"
  if [[ "${PHASE}" == "Ready" ]]; then
    echo "    CephCluster is ready."
    break
  fi
  sleep 15
done

echo ""
echo "==> Waiting for CephFS MDS to be active..."
for i in $(seq 1 30); do
  ACTIVE=$(kubectl -n rook-ceph get cephfilesystem codex-cephfs \
    -o jsonpath='{.status.phase}' 2>/dev/null || echo "Pending")
  echo "    CephFilesystem phase: ${ACTIVE} (${i}/30)"
  if [[ "${ACTIVE}" == "Ready" ]]; then
    echo "    CephFilesystem is ready."
    break
  fi
  sleep 10
done
echo ""

# ── 5. Create Codex namespace and secret ─────────────────────────────────────
echo "==> Creating codex namespace..."
kubectl create namespace codex 2>/dev/null || echo "    Namespace 'codex' already exists."

echo "==> Creating codex-secrets (if not present)..."
if ! kubectl -n codex get secret codex-secrets &>/dev/null; then
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
  kubectl -n codex create secret generic codex-secrets \
    --from-literal=SECRET_KEY="${SECRET_KEY}"
  echo "    Secret created. Store the SECRET_KEY somewhere safe."
else
  echo "    Secret 'codex-secrets' already exists, skipping."
fi
echo ""

# ── 6. Summary ───────────────────────────────────────────────────────────────
echo "=========================================="
echo " LKE cluster setup complete!"
echo "=========================================="
echo ""
echo "Infrastructure installed:"
echo "  - NGINX Ingress Controller (LoadBalancer)"
echo "  - cert-manager (Let's Encrypt TLS)"
echo "  - Rook-Ceph (CephFS shared storage)"
echo ""
echo "Next steps:"
echo "  1. Point DNS for '${DOMAIN}' to: ${EXTERNAL_IP:-<pending>}"
echo "  2. Update k8s/overlays/production/kustomization.yml with your domain"
echo "  3. Deploy with:  kubectl apply -k k8s/overlays/production"
echo "     Or push to main to trigger the GitHub Actions deploy workflow."
echo ""
echo "  To configure GitHub Actions, add these repository secrets:"
echo "    KUBECONFIG  — base64-encoded kubeconfig for your LKE cluster"
echo "                  Generate with: cat ~/.kube/config | base64 -w0"
echo ""
echo "  To tear down:  ./k8s/teardown-lke.sh"

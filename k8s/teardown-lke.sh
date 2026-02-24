#!/usr/bin/env bash
#
# teardown-lke.sh — Remove Codex and its infrastructure from a Linode LKE cluster.
#
# This reverses what setup-lke.sh installs:
#   1. Codex application (kustomize overlay)
#   2. cert-manager + ClusterIssuer
#   3. NGINX Ingress Controller (and its LoadBalancer)
#
# Prerequisites:
#   - kubectl configured with your LKE kubeconfig
#   - helm v3 installed
#
# Usage:
#   ./scripts/teardown-lke.sh [--keep-infra] [--yes]
#
set -euo pipefail

OVERLAY="production"
KEEP_INFRA=false
SKIP_CONFIRM=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --overlay)    OVERLAY="$2"; shift 2 ;;
    --keep-infra) KEEP_INFRA=true; shift ;;
    --yes|-y)     SKIP_CONFIRM=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

OVERLAY_DIR="k8s/overlays/${OVERLAY}"
if [[ ! -d "${OVERLAY_DIR}" ]]; then
  echo "ERROR: Overlay directory '${OVERLAY_DIR}' not found."
  echo "       Run from the repository root, e.g.: ./scripts/teardown-lke.sh"
  exit 1
fi

echo "==> Codex LKE Teardown"
echo "    Overlay:    ${OVERLAY}"
echo "    Keep infra: ${KEEP_INFRA}"
echo ""

# ── Confirm ───────────────────────────────────────────────────────────────────
if [[ "${SKIP_CONFIRM}" != true ]]; then
  echo "This will DELETE:"
  echo "  - All Codex workloads, services, and ingress"
  echo "  - PersistentVolumeClaims and their data (codex-data, postgres-data)"
  echo "  - The codex namespace and all resources within it"
  if [[ "${KEEP_INFRA}" != true ]]; then
    echo "  - cert-manager (namespace + CRDs)"
    echo "  - NGINX Ingress Controller (namespace + LoadBalancer)"
  fi
  echo ""
  read -r -p "Are you sure? [y/N] " response
  if [[ ! "${response}" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
  echo ""
fi

# ── 1. Verify cluster access ─────────────────────────────────────────────────
echo "==> Verifying cluster connectivity..."
kubectl cluster-info || { echo "ERROR: Cannot reach cluster. Check your kubeconfig."; exit 1; }
echo ""

# ── 2. Delete Codex application resources ─────────────────────────────────────
echo "==> Deleting Codex application (overlay: ${OVERLAY})..."
kubectl delete -k "${OVERLAY_DIR}" --ignore-not-found --wait=true 2>/dev/null || true
echo ""

# StatefulSet PVCs are not removed by kustomize delete — clean them up explicitly
echo "==> Deleting StatefulSet PVCs..."
kubectl -n codex delete pvc --selector=app.kubernetes.io/name=postgres --ignore-not-found 2>/dev/null || true
echo ""

# ── 3. Delete the codex namespace (catches anything left behind) ──────────────
echo "==> Deleting codex namespace..."
kubectl delete namespace codex --ignore-not-found --wait=true 2>/dev/null || true
echo ""

if [[ "${KEEP_INFRA}" == true ]]; then
  echo "==> Skipping infrastructure teardown (--keep-infra)."
  echo ""
else
  # ── 4. Remove cert-manager ──────────────────────────────────────────────────
  echo "==> Removing ClusterIssuer..."
  kubectl delete clusterissuer letsencrypt-prod --ignore-not-found 2>/dev/null || true

  echo "==> Uninstalling cert-manager..."
  helm uninstall cert-manager --namespace cert-manager --wait 2>/dev/null || true
  kubectl delete namespace cert-manager --ignore-not-found --wait=true 2>/dev/null || true

  # cert-manager CRDs linger after helm uninstall
  echo "==> Cleaning up cert-manager CRDs..."
  kubectl delete crd \
    certificates.cert-manager.io \
    certificaterequests.cert-manager.io \
    challenges.acme.cert-manager.io \
    clusterissuers.cert-manager.io \
    issuers.cert-manager.io \
    orders.acme.cert-manager.io \
    --ignore-not-found 2>/dev/null || true
  echo ""

  # ── 5. Remove NGINX Ingress Controller ──────────────────────────────────────
  echo "==> Uninstalling NGINX Ingress Controller..."
  helm uninstall ingress-nginx --namespace ingress-nginx --wait 2>/dev/null || true
  kubectl delete namespace ingress-nginx --ignore-not-found --wait=true 2>/dev/null || true
  echo ""
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo "=========================================="
echo " Teardown complete!"
echo "=========================================="
echo ""
if [[ "${KEEP_INFRA}" == true ]]; then
  echo "Codex application removed. Ingress and cert-manager are still running."
  echo "Re-deploy with:  kubectl apply -k ${OVERLAY_DIR}"
else
  echo "All Codex resources and cluster infrastructure removed."
  echo "To set up again:  ./scripts/setup-lke.sh"
fi
echo ""

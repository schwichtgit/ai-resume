#!/bin/bash
# Multi-architecture container build orchestrator.
# Delegates to per-service scripts (build-<service>.sh) so any one
# container can be rebuilt in isolation via task container:build:<service>.
#
# Usage:
#   ./build-all.sh [version] [--no-cache] [--skip-frontend]
#
# Examples:
#   ./build-all.sh                    # Build with tag 'latest'
#   ./build-all.sh v1.0.0             # Build with tag 'v1.0.0'
#   ./build-all.sh latest --no-cache  # Force rebuild without cache

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/container-build.sh
source "${SCRIPT_DIR}/lib/container-build.sh"
REPO_ROOT="$(container_build_repo_root)"
cd "${REPO_ROOT}"

require_podman

VERSION="${1:-latest}"
REGISTRY="${REGISTRY:-localhost}"
NO_CACHE=""
SKIP_FRONTEND=false

shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-cache) NO_CACHE="--no-cache" ;;
        --skip-frontend) SKIP_FRONTEND=true ;;
        *) ;;
    esac
    shift
done

export REGISTRY VERSION NO_CACHE

log_info "Building multi-arch containers for Hybrid Rust + Python setup"
log_info "Version: ${VERSION}"
log_info "Registry: ${REGISTRY}"
log_info "Platforms: linux/amd64, linux/arm64"
[[ -n "${NO_CACHE}" ]] && log_info "Cache: disabled"
echo ""

# Assemble the list of per-service builds to run.
services=()
if [[ "${SKIP_FRONTEND}" != "true" ]]; then
    services+=("frontend")
else
    log_warn "Skipping frontend build (--skip-frontend)"
fi
services+=("memvid" "api" "ingest")

total="${#services[@]}"
idx=0
for svc in "${services[@]}"; do
    idx=$((idx + 1))
    echo ""
    log_info "[${idx}/${total}] Delegating to scripts/build-${svc}.sh"
    # Pass through version + cache flag; per-service script honors REGISTRY from env.
    if [[ -n "${NO_CACHE}" ]]; then
        "${SCRIPT_DIR}/build-${svc}.sh" "${VERSION}" --no-cache
    else
        "${SCRIPT_DIR}/build-${svc}.sh" "${VERSION}"
    fi
done

echo ""
log_info "All containers built successfully"

echo ""
log_info "Manifest architectures:"
for img in ai-resume-frontend ai-resume-memvid ai-resume-api ai-resume-ingest; do
    if podman manifest exists "${REGISTRY}/${img}:${VERSION}" 2>/dev/null; then
        archs="$(podman manifest inspect "${REGISTRY}/${img}:${VERSION}" 2>/dev/null \
            | grep -o '"architecture": "[^"]*"' | cut -d'"' -f4 | tr '\n' ' ')"
        echo "  ${img}: ${archs:-unknown}"
    fi
done

echo ""
echo "To inspect manifests:"
for img in ai-resume-frontend ai-resume-memvid ai-resume-api ai-resume-ingest; do
    echo "  podman manifest inspect ${REGISTRY}/${img}:${VERSION}"
done

echo ""
echo "To save for transfer to edge server:"
for img in ai-resume-frontend ai-resume-memvid ai-resume-api ai-resume-ingest; do
    svc="${img#ai-resume-}"
    echo "  podman save --multi-image-archive ${REGISTRY}/${img}:${VERSION} -o ${svc}-${VERSION}.tar"
done

echo ""
echo "To run a quick smoke test:"
echo "  ./scripts/test-containers.sh"

echo ""
echo "To run locally with podman compose:"
echo "  cd deployment/"
echo "  podman compose up -d"

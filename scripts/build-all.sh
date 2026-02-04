#!/bin/bash
# Multi-architecture container build script for Hybrid Rust + Python setup
# Builds frontend (nginx+React), Rust memvid service, and Python API service
#
# Usage:
#   ./build-all.sh [version] [--no-cache] [--skip-frontend]
#
# Examples:
#   ./build-all.sh                    # Build with tag 'latest'
#   ./build-all.sh v1.0.0             # Build with tag 'v1.0.0'
#   ./build-all.sh latest --no-cache  # Force rebuild without cache

set -euo pipefail

VERSION="${1:-latest}"
REGISTRY="${REGISTRY:-localhost}"
NO_CACHE=""
SKIP_FRONTEND=false

# Parse additional arguments
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    log_error "podman is not installed. Please install podman first."
    exit 1
fi

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

log_info "Building multi-arch containers for Hybrid Rust + Python setup"
log_info "Version: ${VERSION}"
log_info "Registry: ${REGISTRY}"
log_info "Platforms: linux/amd64, linux/arm64"
[[ -n "$NO_CACHE" ]] && log_info "Cache: disabled"
echo ""

# Sync proto files from authoritative source before building
# Uses hard links to keep proto files synchronized across build contexts
log_info "Syncing proto files from authoritative source..."
mkdir -p api-service/proto/memvid/v1 memvid-service/proto/memvid/v1
ln -f proto/memvid/v1/memvid.proto api-service/proto/memvid/v1/memvid.proto 2>/dev/null || log_warn "Failed to link to api-service"
ln -f proto/memvid/v1/memvid.proto memvid-service/proto/memvid/v1/memvid.proto 2>/dev/null || log_warn "Failed to link to memvid-service"
log_info "✓ Proto files synced"
echo ""

# Build frontend (React SPA + nginx)
log_info "[1/3] Building frontend container..."
if [ "$SKIP_FRONTEND" = true ]; then
    log_warn "Skipping frontend build (--skip-frontend)"
elif [ -f "frontend/Dockerfile" ]; then
    # Remove existing manifest to avoid conflicts
    podman manifest rm "${REGISTRY}/ai-resume-frontend:${VERSION}" 2>/dev/null || true
    podman build \
        ${NO_CACHE} \
        --platform linux/amd64,linux/arm64 \
        --manifest "${REGISTRY}/ai-resume-frontend:${VERSION}" \
        -f frontend/Dockerfile \
        frontend/
    log_info "✓ Frontend built successfully"
else
    log_warn "frontend/Dockerfile not found, skipping"
fi
echo ""

# Build Rust memvid service
log_info "[2/3] Building Rust memvid service..."
if [ -f "memvid-service/Dockerfile" ]; then
    # Remove existing manifest to avoid conflicts
    podman manifest rm "${REGISTRY}/ai-resume-memvid:${VERSION}" 2>/dev/null || true
    podman build \
        ${NO_CACHE} \
        --platform linux/amd64,linux/arm64 \
        --manifest "${REGISTRY}/ai-resume-memvid:${VERSION}" \
        -f memvid-service/Dockerfile \
        memvid-service/
    log_info "✓ Rust service built successfully"
else
    log_warn "memvid-service/Dockerfile not found, skipping"
fi
echo ""

# Build Python API service
log_info "[3/3] Building Python API service..."
if [ -f "api-service/Dockerfile" ]; then
    # Remove existing manifest to avoid conflicts
    podman manifest rm "${REGISTRY}/ai-resume-api:${VERSION}" 2>/dev/null || true
    podman build \
        ${NO_CACHE} \
        --platform linux/amd64,linux/arm64 \
        --manifest "${REGISTRY}/ai-resume-api:${VERSION}" \
        -f api-service/Dockerfile \
        api-service/
    log_info "✓ Python service built successfully"
else
    log_warn "api-service/Dockerfile not found, skipping"
fi
echo ""

log_info "✓ All containers built successfully"
echo ""

# Show manifest info
log_info "Manifest architectures:"
for img in ai-resume-frontend ai-resume-memvid ai-resume-api; do
    if podman manifest exists "${REGISTRY}/${img}:${VERSION}" 2>/dev/null; then
        archs=$(podman manifest inspect "${REGISTRY}/${img}:${VERSION}" 2>/dev/null | grep -o '"architecture": "[^"]*"' | cut -d'"' -f4 | tr '\n' ' ')
        echo "  ${img}: ${archs:-unknown}"
    fi
done
echo ""

echo "To inspect manifests:"
echo "  podman manifest inspect ${REGISTRY}/ai-resume-frontend:${VERSION}"
echo "  podman manifest inspect ${REGISTRY}/ai-resume-memvid:${VERSION}"
echo "  podman manifest inspect ${REGISTRY}/ai-resume-api:${VERSION}"
echo ""
echo "To save for transfer to edge server:"
echo "  podman save --multi-image-archive ${REGISTRY}/ai-resume-frontend:${VERSION} -o frontend-${VERSION}.tar"
echo "  podman save --multi-image-archive ${REGISTRY}/ai-resume-memvid:${VERSION} -o memvid-${VERSION}.tar"
echo "  podman save --multi-image-archive ${REGISTRY}/ai-resume-api:${VERSION} -o api-${VERSION}.tar"
echo ""
echo "To run a quick smoke test:"
echo "  ./scripts/test-containers.sh"
echo ""
echo "To run locally with podman-compose:"
echo "  cd deployment/"
echo "  podman-compose up -d"

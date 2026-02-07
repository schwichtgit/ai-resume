#!/bin/bash
# Publish multi-arch OCI containers to a remote registry using skopeo
#
# Usage:
#   ./publish-containers.sh <registry> [version] [--dry-run] [--all|--frontend|--api|--memvid]
#
# Examples:
#   ./publish-containers.sh ghcr.io/schwichtgit          # Push all, tag 'latest'
#   ./publish-containers.sh ghcr.io/schwichtgit v1.2.0   # Push all, tag 'v1.2.0'
#   ./publish-containers.sh docker.io/frank --dry-run     # Preview without pushing
#   ./publish-containers.sh ghcr.io/schwichtgit latest --memvid  # Push only memvid
#
# Prerequisites:
#   - skopeo installed (brew install skopeo / dnf install skopeo)
#   - Local manifests built by scripts/build-all.sh
#   - Authenticated to target registry:
#       skopeo login ghcr.io -u USERNAME --password-stdin < token.txt
#       podman login ghcr.io -u USERNAME --password-stdin < token.txt

set -euo pipefail

# --- Arguments ---
REMOTE_REGISTRY="${1:-}"
VERSION="${2:-latest}"
LOCAL_REGISTRY="${REGISTRY:-localhost}"
DRY_RUN=false
PUSH_FRONTEND=false
PUSH_API=false
PUSH_MEMVID=false
PUSH_ALL=true

if [ -z "$REMOTE_REGISTRY" ]; then
    echo "Usage: $0 <registry> [version] [--dry-run] [--all|--frontend|--api|--memvid]"
    echo ""
    echo "  registry   Target registry path (e.g., ghcr.io/schwichtgit, docker.io/frank)"
    echo "  version    Image tag (default: latest)"
    echo ""
    echo "Options:"
    echo "  --dry-run    Show what would be pushed without actually pushing"
    echo "  --all        Push all images (default)"
    echo "  --frontend   Push only frontend"
    echo "  --api        Push only api"
    echo "  --memvid     Push only memvid"
    echo ""
    echo "Multiple selectors can be combined: --frontend --api"
    exit 1
fi

# Parse flags (skip first two positional args)
shift || true
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --frontend)
            PUSH_FRONTEND=true
            PUSH_ALL=false
            shift
            ;;
        --api)
            PUSH_API=true
            PUSH_ALL=false
            shift
            ;;
        --memvid)
            PUSH_MEMVID=true
            PUSH_ALL=false
            shift
            ;;
        --all)
            PUSH_ALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ "$PUSH_ALL" = true ]; then
    PUSH_FRONTEND=true
    PUSH_API=true
    PUSH_MEMVID=true
fi

# --- Colors ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

# --- Preflight checks ---
if ! command -v skopeo &> /dev/null; then
    log_error "skopeo is not installed"
    echo "  Install: brew install skopeo (macOS) or dnf install skopeo (Fedora)"
    exit 1
fi

if ! command -v podman &> /dev/null; then
    log_error "podman is not installed (needed to inspect local manifests)"
    exit 1
fi

# Image definitions: local_name -> remote_name
declare -a IMAGES=()
if [ "$PUSH_FRONTEND" = true ]; then
    IMAGES+=("ai-resume-frontend")
fi
if [ "$PUSH_MEMVID" = true ]; then
    IMAGES+=("ai-resume-memvid")
fi
if [ "$PUSH_API" = true ]; then
    IMAGES+=("ai-resume-api")
fi

echo ""
log_info "Publishing OCI containers"
log_info "  Source:  ${LOCAL_REGISTRY}/<image>:${VERSION}"
log_info "  Target:  ${REMOTE_REGISTRY}/<image>:${VERSION}"
log_info "  Images:  ${IMAGES[*]}"
[ "$DRY_RUN" = true ] && log_warn "DRY RUN - no images will be pushed"
echo ""

# --- Validate local manifests exist ---
MISSING=0
for IMG in "${IMAGES[@]}"; do
    LOCAL="${LOCAL_REGISTRY}/${IMG}:${VERSION}"
    if ! podman manifest exists "$LOCAL" 2>/dev/null; then
        log_error "Local manifest not found: ${LOCAL}"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    echo ""
    log_error "${MISSING} manifest(s) missing. Build first with:"
    echo "  ./scripts/build-all.sh ${VERSION}"
    exit 1
fi

log_info "All local manifests verified"
echo ""

# --- Publish each image ---
PUSHED=0
FAILED=0

for IMG in "${IMAGES[@]}"; do
    LOCAL="${LOCAL_REGISTRY}/${IMG}:${VERSION}"
    REMOTE="${REMOTE_REGISTRY}/${IMG}:${VERSION}"

    log_step "Publishing ${IMG}..."

    # Show manifest architectures
    ARCHS=$(podman manifest inspect "$LOCAL" 2>/dev/null \
        | grep -o '"architecture": "[^"]*"' \
        | cut -d'"' -f4 \
        | tr '\n' ', ' \
        | sed 's/,$//')
    log_info "  Architectures: ${ARCHS:-unknown}"
    log_info "  ${LOCAL} -> docker://${REMOTE}"

    if [ "$DRY_RUN" = true ]; then
        log_warn "  [dry-run] skopeo copy --all docker://${LOCAL} docker://${REMOTE}"
        PUSHED=$((PUSHED + 1))
        echo ""
        continue
    fi

    # Copy the manifest list (all architectures) to the remote registry
    if skopeo copy \
        --all \
        "containers-storage:${LOCAL}" \
        "docker://${REMOTE}" 2>&1; then
        log_info "  Pushed successfully"
        PUSHED=$((PUSHED + 1))
    else
        log_error "  Failed to push ${IMG}"
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

# --- Also tag as 'latest' if version is not 'latest' ---
if [ "$VERSION" != "latest" ] && [ "$FAILED" -eq 0 ] && [ "$DRY_RUN" = false ]; then
    echo ""
    log_step "Tagging ${VERSION} as 'latest'..."
    for IMG in "${IMAGES[@]}"; do
        REMOTE_VERSIONED="${REMOTE_REGISTRY}/${IMG}:${VERSION}"
        REMOTE_LATEST="${REMOTE_REGISTRY}/${IMG}:latest"
        log_info "  ${REMOTE_VERSIONED} -> ${REMOTE_LATEST}"
        if skopeo copy \
            --all \
            "docker://${REMOTE_VERSIONED}" \
            "docker://${REMOTE_LATEST}" 2>&1; then
            log_info "  Tagged ${IMG}:latest"
        else
            log_warn "  Failed to tag ${IMG}:latest (non-fatal)"
        fi
    done
elif [ "$VERSION" != "latest" ] && [ "$DRY_RUN" = true ]; then
    log_warn "[dry-run] Would also tag ${VERSION} as 'latest'"
fi

# --- Summary ---
echo ""
log_info "=== Publish Summary ==="
echo "  Pushed: ${PUSHED}"
echo "  Failed: ${FAILED}"
echo ""

if [ "$FAILED" -gt 0 ]; then
    log_error "Some images failed to publish"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check registry auth: skopeo login ${REMOTE_REGISTRY%%/*}"
    echo "  2. Check network connectivity"
    echo "  3. Verify repository permissions"
    exit 1
fi

if [ "$DRY_RUN" = false ]; then
    log_info "All images published successfully"
    echo ""
    echo "Verify with:"
    for IMG in "${IMAGES[@]}"; do
        echo "  skopeo inspect docker://${REMOTE_REGISTRY}/${IMG}:${VERSION}"
    done
    echo ""
    echo "Pull on deployment host:"
    for IMG in "${IMAGES[@]}"; do
        echo "  podman pull ${REMOTE_REGISTRY}/${IMG}:${VERSION}"
    done
    echo ""
    echo "Deploy with compose:"
    echo "  REGISTRY=${REMOTE_REGISTRY} VERSION=${VERSION} podman-compose -f deployment/compose.yaml up -d"
fi

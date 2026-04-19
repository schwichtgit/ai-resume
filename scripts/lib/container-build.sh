#!/bin/bash
# Shared helpers for per-service container build scripts.
# Source from scripts/build-<service>.sh.

# Colors (guarded against re-definition when sourced multiple times)
: "${GREEN:=$'\033[0;32m'}"
: "${YELLOW:=$'\033[1;33m'}"
: "${RED:=$'\033[0;31m'}"
: "${NC:=$'\033[0m'}"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Ensure podman is available
require_podman() {
    if ! command -v podman &>/dev/null; then
        log_error "podman is not installed. Please install podman first."
        exit 1
    fi
}

# Resolve the repository root relative to this library.
# Usage: REPO_ROOT="$(container_build_repo_root)"
container_build_repo_root() {
    local lib_dir
    lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "${lib_dir}/../.." && pwd
}

# Hard-link the authoritative proto into a service-local copy so the
# build context can see it. Safe to call for services that need proto.
sync_proto_into() {
    local target_service_dir="$1"
    local src="${REPO_ROOT}/proto/memvid/v1/memvid.proto"
    local dst_dir="${REPO_ROOT}/${target_service_dir}/proto/memvid/v1"
    mkdir -p "${dst_dir}"
    ln -f "${src}" "${dst_dir}/memvid.proto" 2>/dev/null \
        || log_warn "Failed to link proto into ${target_service_dir}"
}

# Build a single multi-arch container.
# Required env vars (set by caller before invoking):
#   SERVICE        - image suffix (e.g. frontend, api, memvid, ingest)
#   TITLE          - OCI title
#   DESCRIPTION    - OCI description
#   DOCKERFILE     - path to Dockerfile (repo-relative)
#   CONTEXT        - build context dir (repo-relative)
# Optional:
#   PLATFORMS      - default "linux/amd64,linux/arm64"
#   REGISTRY       - default "localhost"
#   VERSION        - default "latest"
#   NO_CACHE       - pass "--no-cache" to enable; default unset
build_one_container() {
    : "${SERVICE:?SERVICE not set}"
    : "${TITLE:?TITLE not set}"
    : "${DESCRIPTION:?DESCRIPTION not set}"
    : "${DOCKERFILE:?DOCKERFILE not set}"
    : "${CONTEXT:?CONTEXT not set}"

    local platforms="${PLATFORMS:-linux/amd64,linux/arm64}"
    local registry="${REGISTRY:-localhost}"
    local version="${VERSION:-latest}"
    local no_cache="${NO_CACHE:-}"
    local build_date
    local git_revision
    build_date="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    git_revision="$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || echo "unknown")"

    local manifest="${registry}/ai-resume-${SERVICE}:${version}"

    log_info "Building ${manifest}"
    log_info "  platforms: ${platforms}"
    log_info "  dockerfile: ${DOCKERFILE}"
    log_info "  context: ${CONTEXT}"
    [[ -n "${no_cache}" ]] && log_info "  cache: disabled"

    # Remove any stale manifest with the same tag
    podman manifest rm "${manifest}" 2>/dev/null || true

    # shellcheck disable=SC2086  # Intentional word-split on ${no_cache}
    podman build \
        ${no_cache} \
        --platform "${platforms}" \
        --manifest "${manifest}" \
        --build-arg "BUILD_VERSION=${version}" \
        --build-arg "BUILD_COMMIT=${git_revision}" \
        --annotation "org.opencontainers.image.title=ai-resume-${SERVICE}" \
        --annotation "org.opencontainers.image.description=${DESCRIPTION}" \
        --annotation "org.opencontainers.image.url=https://github.com/schwichtgit/ai-resume/pkgs/container/ai-resume-${SERVICE}" \
        --annotation "org.opencontainers.image.source=https://github.com/schwichtgit/ai-resume" \
        --annotation "org.opencontainers.image.documentation=https://github.com/schwichtgit/ai-resume#readme" \
        --annotation "org.opencontainers.image.version=${version}" \
        --annotation "org.opencontainers.image.created=${build_date}" \
        --annotation "org.opencontainers.image.revision=${git_revision}" \
        --annotation "org.opencontainers.image.licenses=PolyForm-Noncommercial-1.0.0 OR LicenseRef-Commercial" \
        --annotation "org.opencontainers.image.vendor=schwichtgit" \
        --annotation "org.opencontainers.image.authors=https://github.com/schwichtgit" \
        -f "${DOCKERFILE}" \
        "${CONTEXT}"

    log_info "Built ${manifest}"
}

# Parse "[version] [--no-cache]" from per-service script args.
# Sets globals VERSION and NO_CACHE.
parse_container_build_args() {
    VERSION="${1:-${VERSION:-latest}}"
    NO_CACHE="${NO_CACHE:-}"
    shift || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-cache) NO_CACHE="--no-cache" ;;
            *) ;;
        esac
        shift
    done
    export VERSION NO_CACHE
}

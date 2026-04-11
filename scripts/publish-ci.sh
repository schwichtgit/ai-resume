#!/bin/bash
# CI-optimized publish script for single-arch container images
#
# Subcommands:
#   push-arch   Push a single-arch image to a registry with arch suffix
#   merge       Create and push an OCI manifest list from arch-specific tags
#   tag-family  Apply semver tag family via server-side re-tagging
#   verify      Verify cosign signatures against GitHub Actions OIDC identities
#
# Usage:
#   scripts/publish-ci.sh push-arch  <registry> <image> <version> <arch> [--dry-run]
#   scripts/publish-ci.sh merge      <registry> <image> <version> [--digest-amd64 <digest>] [--digest-arm64 <digest>] [--dry-run]
#   scripts/publish-ci.sh tag-family <registry> <image> <version> [--dry-run]
#   scripts/publish-ci.sh verify     <registry> <image> <version> [--dry-run]
#   scripts/publish-ci.sh --help
#
# Examples:
#   scripts/publish-ci.sh push-arch ghcr.io/schwichtgit ai-resume-frontend v1.0.0 amd64
#   scripts/publish-ci.sh merge ghcr.io/schwichtgit ai-resume-frontend v1.0.0
#   scripts/publish-ci.sh merge ghcr.io/schwichtgit ai-resume-frontend v1.0.0 --digest-amd64 sha256:abc --digest-arm64 sha256:def
#   scripts/publish-ci.sh tag-family ghcr.io/schwichtgit ai-resume-frontend v1.0.0
#   scripts/publish-ci.sh verify ghcr.io/schwichtgit ai-resume-frontend v1.0.0
#   scripts/publish-ci.sh push-arch ghcr.io/schwichtgit ai-resume-frontend v1.0.0 arm64 --dry-run
#
# Prerequisites:
#   - podman installed (for push-arch and merge)
#   - skopeo installed (for tag-family)
#   - cosign installed (for verify)
#   - Authenticated to target registry

set -euo pipefail

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

# --- Usage ---
usage() {
    cat <<'EOF'
CI-optimized publish script for single-arch container images.

Subcommands:
  push-arch   Push a single-arch image to a registry with arch suffix
  merge       Create and push an OCI manifest list from arch-specific tags
  tag-family  Apply semver tag family via server-side re-tagging
  verify      Verify cosign signatures against GitHub Actions OIDC identities

Usage:
  scripts/publish-ci.sh push-arch  <registry> <image> <version> <arch> [--dry-run]
  scripts/publish-ci.sh merge      <registry> <image> <version> [--digest-amd64 <digest>] [--digest-arm64 <digest>] [--dry-run]
  scripts/publish-ci.sh tag-family <registry> <image> <version> [--dry-run]
  scripts/publish-ci.sh verify     <registry> <image> <version> [--dry-run]
  scripts/publish-ci.sh --help

Arguments:
  registry   Target registry path (e.g., ghcr.io/schwichtgit)
  image      Image name (e.g., ai-resume-frontend)
  version    Semver version tag (e.g., v1.2.3, v0.1.0-alpha.1)
  arch       Architecture (amd64 or arm64)

Options:
  --dry-run         Print commands without executing
  --digest-amd64    Digest for amd64 image (merge only, enables digest-based manifest add)
  --digest-arm64    Digest for arm64 image (merge only, enables digest-based manifest add)
  --help            Show this help message

Subcommand Details:

  push-arch:
    Pushes localhost/<image>:<version> to <registry>/<image>:<version>.<arch>
    Uses podman push for single-arch images built locally by CI.
    Captures and outputs the image digest as DIGEST=<value>.

  merge:
    Creates an OCI manifest list combining arch-specific images.
    When --digest-amd64 and --digest-arm64 are provided, adds images by digest
    for provenance-safe pinning. Otherwise falls back to tag-based references.
    Captures and outputs the manifest digest as MANIFEST_DIGEST=<value>.

  tag-family:
    Applies semver tag family via server-side re-tagging with skopeo copy --all.
    Pre-release (version contains '-'): sha-<short> + bare version only.
    Stable release: sha-<short> + bare version + minor tag + latest.

  verify:
    Verifies cosign signatures against GitHub Actions OIDC identities.
    Tries ci.yml workflow identity first, then release.yml as fallback.

Examples:
  scripts/publish-ci.sh push-arch ghcr.io/org img v1.0.0 amd64
  scripts/publish-ci.sh merge ghcr.io/org img v1.0.0
  scripts/publish-ci.sh merge ghcr.io/org img v1.0.0 --digest-amd64 sha256:abc --digest-arm64 sha256:def
  scripts/publish-ci.sh tag-family ghcr.io/org img v1.0.0
  scripts/publish-ci.sh verify ghcr.io/org img v1.0.0
  scripts/publish-ci.sh push-arch ghcr.io/org img v1.0.0 arm64 --dry-run
EOF
}

# --- Helpers ---
run_cmd() {
    local dry_run="$1"
    shift
    if [ "$dry_run" = true ]; then
        log_warn "  [dry-run] $*"
    else
        "$@"
    fi
}

# --- Subcommand: push-arch ---
cmd_push_arch() {
    local registry="${1:-}"
    local image="${2:-}"
    local version="${3:-}"
    local arch="${4:-}"
    local dry_run=false

    # Check for --dry-run in remaining args
    shift 4 || true
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run) dry_run=true; shift ;;
            *) log_error "Unknown option: $1"; exit 1 ;;
        esac
    done

    if [ -z "$registry" ] || [ -z "$image" ] || [ -z "$version" ] || [ -z "$arch" ]; then
        log_error "push-arch requires: <registry> <image> <version> <arch>"
        echo "Usage: $0 push-arch <registry> <image> <version> <arch> [--dry-run]"
        exit 1
    fi

    local local_ref="localhost/${image}:${version}"
    local remote_ref="${registry}/${image}:${version}.${arch}"

    echo ""
    log_step "push-arch: ${local_ref} -> ${remote_ref}"
    [ "$dry_run" = true ] && log_warn "DRY RUN - no images will be pushed"
    echo ""

    if [ "$dry_run" = true ]; then
        run_cmd "$dry_run" podman push --digestfile /tmp/digest.txt "${local_ref}" "docker://${remote_ref}"
        echo "DIGEST=sha256:dry-run-placeholder"
    else
        podman push --digestfile /tmp/digest.txt "${local_ref}" "docker://${remote_ref}"
        local digest
        digest=$(cat /tmp/digest.txt)
        echo "DIGEST=${digest}"
    fi

    echo ""
    log_info "push-arch complete"
}

# --- Subcommand: merge ---
cmd_merge() {
    local registry=""
    local image=""
    local version=""
    local digest_amd64=""
    local digest_arm64=""
    local dry_run=false

    # Parse flags and positional args
    local positional=()
    while [[ $# -gt 0 ]]; do
        case $1 in
            --digest-amd64) digest_amd64="$2"; shift 2 ;;
            --digest-arm64) digest_arm64="$2"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            -*) log_error "Unknown option: $1"; exit 1 ;;
            *) positional+=("$1"); shift ;;
        esac
    done

    registry="${positional[0]:-}"
    image="${positional[1]:-}"
    version="${positional[2]:-}"

    if [ -z "$registry" ] || [ -z "$image" ] || [ -z "$version" ]; then
        log_error "merge requires: <registry> <image> <version>"
        echo "Usage: $0 merge <registry> <image> <version> [--digest-amd64 <digest>] [--digest-arm64 <digest>] [--dry-run]"
        exit 1
    fi

    local manifest_ref="${registry}/${image}:${version}"
    local use_digests=false

    if [ -n "$digest_amd64" ] && [ -n "$digest_arm64" ]; then
        use_digests=true
    fi

    echo ""
    log_step "merge: creating manifest list ${manifest_ref}"

    if [ "$use_digests" = true ]; then
        log_info "  amd64: ${registry}/${image}@${digest_amd64}"
        log_info "  arm64: ${registry}/${image}@${digest_arm64}"
        log_info "  mode: digest-based (provenance-safe)"
    else
        log_info "  amd64: ${registry}/${image}:${version}.amd64"
        log_info "  arm64: ${registry}/${image}:${version}.arm64"
        log_info "  mode: tag-based (fallback)"
    fi
    [ "$dry_run" = true ] && log_warn "DRY RUN - no manifests will be created"
    echo ""

    run_cmd "$dry_run" podman manifest create "${manifest_ref}"

    if [ "$use_digests" = true ]; then
        run_cmd "$dry_run" podman manifest add "${manifest_ref}" "${registry}/${image}@${digest_amd64}"
        run_cmd "$dry_run" podman manifest add "${manifest_ref}" "${registry}/${image}@${digest_arm64}"
    else
        local amd64_ref="${registry}/${image}:${version}.amd64"
        local arm64_ref="${registry}/${image}:${version}.arm64"
        run_cmd "$dry_run" podman manifest add "${manifest_ref}" "docker://${amd64_ref}"
        run_cmd "$dry_run" podman manifest add "${manifest_ref}" "docker://${arm64_ref}"
    fi

    if [ "$dry_run" = true ]; then
        run_cmd "$dry_run" podman manifest push --all --digestfile /tmp/manifest-digest.txt "${manifest_ref}" "docker://${manifest_ref}"
        echo "MANIFEST_DIGEST=sha256:dry-run-placeholder"
    else
        podman manifest push --all --digestfile /tmp/manifest-digest.txt "${manifest_ref}" "docker://${manifest_ref}"
        local manifest_digest
        manifest_digest=$(cat /tmp/manifest-digest.txt)
        echo "MANIFEST_DIGEST=${manifest_digest}"
    fi

    echo ""
    log_info "merge complete"
}

# --- Subcommand: tag-family ---
cmd_tag_family() {
    local registry="${1:-}"
    local image="${2:-}"
    local version="${3:-}"
    local dry_run=false

    # Check for --dry-run in remaining args
    shift 3 || true
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run) dry_run=true; shift ;;
            *) log_error "Unknown option: $1"; exit 1 ;;
        esac
    done

    if [ -z "$registry" ] || [ -z "$image" ] || [ -z "$version" ]; then
        log_error "tag-family requires: <registry> <image> <version>"
        echo "Usage: $0 tag-family <registry> <image> <version> [--dry-run]"
        exit 1
    fi

    local bare_version="${version#v}"
    local sha_tag
    sha_tag="sha-$(git rev-parse --short HEAD)"
    local source_ref="docker://${registry}/${image}:${version}"

    # Build list of tags to apply
    declare -a tags=()

    if [[ "$bare_version" == *-* ]]; then
        # Pre-release: sha + bare version only
        log_step "Pre-release detected -- tagging with sha and bare version only"
        tags+=("$sha_tag")
        tags+=("$bare_version")
    else
        # Stable release: sha + bare version + minor + latest
        local minor_tag="${bare_version%.*}"
        log_step "Stable release detected -- applying semver tag family"
        tags+=("$sha_tag")
        tags+=("$bare_version")
        tags+=("$minor_tag")
        tags+=("latest")
    fi

    echo ""
    log_info "Source: ${source_ref}"
    log_info "Tags:   ${tags[*]}"
    [ "$dry_run" = true ] && log_warn "DRY RUN - no tags will be applied"
    echo ""

    for tag in "${tags[@]}"; do
        local target_ref="docker://${registry}/${image}:${tag}"
        run_cmd "$dry_run" skopeo copy --all "${source_ref}" "${target_ref}"
    done

    echo ""
    log_info "tag-family complete"
}

# --- Subcommand: verify ---
cmd_verify() {
    local registry="${1:-}"
    local image="${2:-}"
    local version="${3:-}"
    local dry_run=false

    # Check for --dry-run in remaining args
    shift 3 || true
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run) dry_run=true; shift ;;
            *) log_error "Unknown option: $1"; exit 1 ;;
        esac
    done

    if [ -z "$registry" ] || [ -z "$image" ] || [ -z "$version" ]; then
        log_error "verify requires: <registry> <image> <version>"
        echo "Usage: $0 verify <registry> <image> <version> [--dry-run]"
        exit 1
    fi

    local image_ref="${registry}/${image}:${version}"
    local oidc_issuer="https://token.actions.githubusercontent.com"
    local ci_identity="https://github.com/schwichtgit/ai-resume/.github/workflows/ci.yml@refs/heads/main"
    local release_identity="https://github.com/schwichtgit/ai-resume/.github/workflows/release.yml@refs/tags/${version}"

    echo ""
    log_step "verify: checking cosign signatures on ${image_ref}"
    [ "$dry_run" = true ] && log_warn "DRY RUN - no verification will be performed"
    echo ""

    if [ "$dry_run" = true ]; then
        log_info "Trying ci.yml workflow identity..."
        run_cmd "$dry_run" cosign verify \
            --certificate-identity "$ci_identity" \
            --certificate-oidc-issuer "$oidc_issuer" \
            "$image_ref"

        log_info "Trying release.yml workflow identity..."
        run_cmd "$dry_run" cosign verify \
            --certificate-identity "$release_identity" \
            --certificate-oidc-issuer "$oidc_issuer" \
            "$image_ref"
    else
        log_info "Trying ci.yml workflow identity..."
        if cosign verify \
            --certificate-identity "$ci_identity" \
            --certificate-oidc-issuer "$oidc_issuer" \
            "$image_ref" 2>&1; then
            log_info "Signature verified with ci.yml workflow identity"
        else
            log_warn "ci.yml identity failed, trying release.yml workflow identity..."
            if cosign verify \
                --certificate-identity "$release_identity" \
                --certificate-oidc-issuer "$oidc_issuer" \
                "$image_ref" 2>&1; then
                log_info "Signature verified with release.yml workflow identity"
            else
                log_error "Signature verification failed for both workflow identities"
                exit 1
            fi
        fi
    fi

    echo ""
    log_info "verify complete"
}

# --- Main ---
SUBCOMMAND="${1:-}"

case "$SUBCOMMAND" in
    --help|-h|"")
        usage
        exit 0
        ;;
    push-arch)
        shift
        cmd_push_arch "$@"
        ;;
    merge)
        shift
        cmd_merge "$@"
        ;;
    tag-family)
        shift
        cmd_tag_family "$@"
        ;;
    verify)
        shift
        cmd_verify "$@"
        ;;
    *)
        log_error "Unknown subcommand: $SUBCOMMAND"
        echo "Run '$0 --help' for usage."
        exit 1
        ;;
esac

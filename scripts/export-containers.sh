#!/bin/bash
# Export podman container images as OCI tar files for deployment to edge servers
#
# Usage:
#   ./export-containers.sh [version]
#
# Examples:
#   ./export-containers.sh              # Export all images tagged 'latest'
#   ./export-containers.sh v1.2.0       # Export all images tagged 'v1.2.0'
#
# Environment:
#   REGISTRY  Local registry prefix (default: localhost)
#
# Output:
#   deployment/<image>-<version>.tar for each container image

set -euo pipefail

# --- Arguments ---
VERSION="${1:-latest}"
REGISTRY="${REGISTRY:-localhost}"

# --- Project root ---
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/deployment"

# --- Colors ---
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# --- Images to export ---
IMAGES=(
    "ai-resume-frontend"
    "ai-resume-memvid"
    "ai-resume-api"
)

echo ""
echo "Exporting containers: ${REGISTRY}/ai-resume-*:${VERSION}"
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# --- Create output directory ---
mkdir -p "${OUTPUT_DIR}"

# --- Platform-aware file size function ---
file_size() {
    if stat -f%z "$1" 2>/dev/null; then
        return
    fi
    stat -c%s "$1" 2>/dev/null
}

# --- Export each image ---
FAILED=0
PASSED=0
TOTAL_SIZE=0

for IMG in "${IMAGES[@]}"; do
    SRC="${REGISTRY}/${IMG}:${VERSION}"
    TARFILE="${OUTPUT_DIR}/${IMG}-${VERSION}.tar"

    log_step "Exporting ${SRC} -> ${TARFILE}"

    # Export image as OCI tar archive
    if ! podman save --multi-image-archive "${SRC}" -o "${TARFILE}" 2>&1; then
        log_fail "podman save failed for ${IMG}"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Verify tar file exists
    if [ ! -f "${TARFILE}" ]; then
        log_fail "Tar file not created: ${TARFILE}"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Verify tar file size > 1000 bytes
    SIZE=$(file_size "${TARFILE}")
    if [ -z "${SIZE}" ] || [ "${SIZE}" -le 1000 ]; then
        log_fail "Tar file too small (${SIZE:-0} bytes): ${TARFILE}"
        FAILED=$((FAILED + 1))
        continue
    fi

    log_pass "${IMG} exported ($(numfmt --to=iec "${SIZE}" 2>/dev/null || echo "${SIZE} bytes"))"
    TOTAL_SIZE=$((TOTAL_SIZE + SIZE))
    PASSED=$((PASSED + 1))
done

# --- Summary ---
echo ""
echo "=== Export Summary ==="
echo "  Passed: ${PASSED}/${#IMAGES[@]}"
echo "  Failed: ${FAILED}/${#IMAGES[@]}"
TOTAL_HUMAN=$(numfmt --to=iec "${TOTAL_SIZE}" 2>/dev/null || echo "${TOTAL_SIZE} bytes")
echo "  Total size: ${TOTAL_HUMAN}"
echo ""

if [ "${FAILED}" -gt 0 ]; then
    log_fail "Some exports failed"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify images exist: podman images '${REGISTRY}/ai-resume-*'"
    echo "  2. Build first with: ./scripts/build-all.sh ${VERSION}"
    exit 1
fi

log_pass "All images exported to ${OUTPUT_DIR}/"
echo ""
echo "Deploy to edge server:"
echo "  scp ${OUTPUT_DIR}/ai-resume-*-${VERSION}.tar user@edge-host:/opt/containers/"
echo "  ssh user@edge-host 'for f in /opt/containers/ai-resume-*-${VERSION}.tar; do podman load -i \"\$f\"; done'"
exit 0

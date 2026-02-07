#!/bin/bash
# Unified release quality gate orchestrator
# Runs all validation phases and produces a go/no-go release decision
#
# Usage:
#   ./release-gate.sh [version] [--skip-build] [--skip-ingest] [--skip-live]
#
# Examples:
#   ./release-gate.sh                      # Run all phases with tag 'latest'
#   ./release-gate.sh v1.2.0               # Run all phases with tag 'v1.2.0'
#   ./release-gate.sh latest --skip-build  # Skip container build/export/smoke phases
#   ./release-gate.sh latest --skip-ingest # Skip ingest pipeline phase

set -uo pipefail

# --- Project root ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# --- Arguments ---
VERSION="${1:-latest}"
SKIP_BUILD=false
SKIP_INGEST=false
SKIP_LIVE=false

shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-ingest)
            SKIP_INGEST=true
            shift
            ;;
        --skip-live)
            SKIP_LIVE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# --- Colors ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

# --- Phase tracking ---
RESULTS=()

run_phase() {
    local name="$1"
    local description="$2"
    shift 2
    echo ""
    echo "============================================"
    echo "  Phase: $description"
    echo "============================================"
    if "$@"; then
        RESULTS+=("$name:PASS")
        log_pass "$description"
    else
        RESULTS+=("$name:FAIL")
        log_fail "$description"
    fi
}

skip_phase() {
    local name="$1"
    local description="$2"
    echo ""
    echo "============================================"
    echo "  Phase: $description"
    echo "============================================"
    RESULTS+=("$name:SKIP")
    log_skip "$description"
}

# --- Header ---
echo ""
echo "============================================"
echo "  RELEASE QUALITY GATE (v${VERSION})"
echo "============================================"
log_info "Project root: $PROJECT_ROOT"
log_info "Skip build:   $SKIP_BUILD"
log_info "Skip ingest:  $SKIP_INGEST"
log_info "Skip live:    $SKIP_LIVE"

# =============================================================================
# Phase 1: Container Build
# =============================================================================

if [ "$SKIP_BUILD" = true ]; then
    skip_phase "build" "Container Build"
else
    run_phase "build" "Container Build" \
        "$PROJECT_ROOT/scripts/build-all.sh" "$VERSION"
fi

# =============================================================================
# Phase 2: Tar Export
# =============================================================================

if [ "$SKIP_BUILD" = true ]; then
    skip_phase "export" "Tar Export"
else
    run_phase "export" "Tar Export" \
        "$PROJECT_ROOT/scripts/export-containers.sh" "$VERSION"
fi

# =============================================================================
# Phase 3: Fresh Ingest
# =============================================================================

if [ "$SKIP_INGEST" = true ]; then
    skip_phase "ingest" "Ingest Pipeline"
else
    run_phase "ingest" "Ingest Pipeline" \
        "$PROJECT_ROOT/scripts/test-ingest.sh"
fi

# =============================================================================
# Phase 4: Container Smoke Test
# =============================================================================

if [ "$SKIP_BUILD" = true ]; then
    skip_phase "smoke" "Container Smoke Test"
else
    run_phase "smoke" "Container Smoke Test" \
        "$PROJECT_ROOT/scripts/test-containers.sh" "$VERSION"
fi

# =============================================================================
# Phase 5: API E2E Tests (pytest)
# =============================================================================

if [ "$SKIP_LIVE" = true ]; then
    skip_phase "pytest" "API E2E (pytest)"
else
    run_phase "pytest" "API E2E (pytest)" \
        bash -c "cd '$PROJECT_ROOT/api-service' && source .venv/bin/activate && uv run pytest tests/test_e2e_api.py -v --tb=short"
fi

# =============================================================================
# Phase 6: Full-Stack Integration
# =============================================================================

if [ "$SKIP_LIVE" = true ]; then
    skip_phase "e2e" "Full-Stack Integration"
else
    run_phase "e2e" "Full-Stack Integration" \
        "$PROJECT_ROOT/scripts/test-e2e-integration.sh"
fi

# =============================================================================
# Phase 7: Release Decision
# =============================================================================

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

for result in "${RESULTS[@]}"; do
    status="${result##*:}"
    case "$status" in
        PASS) PASS_COUNT=$((PASS_COUNT + 1)) ;;
        FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
        SKIP) SKIP_COUNT=$((SKIP_COUNT + 1)) ;;
    esac
done

# Phase display mapping (ordered)
PHASE_LABELS=(
    "build:Container Build"
    "export:Tar Export"
    "ingest:Ingest Pipeline"
    "smoke:Container Smoke"
    "pytest:API E2E (pytest)"
    "e2e:Full-Stack"
)

echo ""
echo ""
echo "============================================"
echo "  RELEASE GATE SUMMARY (v${VERSION})"
echo "============================================"

phase_num=0
for entry in "${PHASE_LABELS[@]}"; do
    phase_num=$((phase_num + 1))
    key="${entry%%:*}"
    label="${entry#*:}"

    # Find matching result
    status="UNKNOWN"
    for result in "${RESULTS[@]}"; do
        rkey="${result%%:*}"
        rstatus="${result##*:}"
        if [ "$rkey" = "$key" ]; then
            status="$rstatus"
            break
        fi
    done

    # Color the status
    case "$status" in
        PASS) colored_status="${GREEN}PASS${NC}" ;;
        FAIL) colored_status="${RED}FAIL${NC}" ;;
        SKIP) colored_status="${YELLOW}SKIP${NC}" ;;
        *)    colored_status="$status" ;;
    esac

    printf "  Phase %d - %-22s: %b\n" "$phase_num" "$label" "$colored_status"
done

echo "============================================"

TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))
echo -e "  Passed: ${GREEN}${PASS_COUNT}${NC}  Failed: ${RED}${FAIL_COUNT}${NC}  Skipped: ${YELLOW}${SKIP_COUNT}${NC}  Total: ${TOTAL}"

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "  RESULT: ${GREEN}RELEASE READY${NC}"
    echo "============================================"
    exit 0
else
    echo -e "  RESULT: ${RED}RELEASE BLOCKED${NC}"
    echo "============================================"
    exit 1
fi

#!/bin/bash
# Monorepo quality verification script
# Walks through each service and runs appropriate quality checks
# Usage: ./scripts/verify-quality.sh [--fix] [--service=<name>]

set -euo pipefail

# Get the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
FIX_MODE=false
TARGET_SERVICE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --service=*)
            TARGET_SERVICE="${1#*=}"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--fix] [--service=<name>]"
            echo ""
            echo "Options:"
            echo "  --fix            Attempt to auto-fix issues"
            echo "  --service=<name> Only check specific service (frontend, api-service, ingest, memvid-service)"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

# Helper function to run a check
run_check() {
    local name="$1"
    local command="$2"
    local fix_command="${3:-}"
    local working_dir="${4:-$PROJECT_ROOT}"

    printf "  %-30s" "$name..."

    if $FIX_MODE && [[ -n "$fix_command" ]]; then
        if (cd "$working_dir" && eval "$fix_command" > /dev/null 2>&1); then
            echo -e "${GREEN}FIXED${NC}"
            ((TOTAL_PASSED++))
            return 0
        fi
    fi

    if (cd "$working_dir" && eval "$command" > /dev/null 2>&1); then
        echo -e "${GREEN}PASS${NC}"
        ((TOTAL_PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        ((TOTAL_FAILED++))
        return 1
    fi
}

# Helper function to skip a check
skip_check() {
    local name="$1"
    local reason="$2"

    printf "  %-30s" "$name..."
    echo -e "${YELLOW}SKIP${NC} ($reason)"
    ((TOTAL_SKIPPED++))
}

# Check frontend
check_frontend() {
    echo ""
    echo "=== Frontend (frontend/) ==="

    if [[ ! -d "$PROJECT_ROOT/frontend" ]]; then
        skip_check "All checks" "directory not found"
        return
    fi

    if [[ ! -d "$PROJECT_ROOT/frontend/node_modules" ]]; then
        skip_check "All checks" "node_modules not installed"
        echo "  Run: cd frontend && npm install"
        return
    fi

    local wd="$PROJECT_ROOT/frontend"

    if $FIX_MODE; then
        run_check "ESLint" "npm run lint" "npm run lint -- --fix" "$wd" || true
        run_check "Prettier" "npx prettier --check 'src/**/*.{ts,tsx}'" "npx prettier --write 'src/**/*.{ts,tsx}'" "$wd" || true
    else
        run_check "ESLint" "npm run lint" "" "$wd" || true
        run_check "Prettier" "npx prettier --check 'src/**/*.{ts,tsx}'" "" "$wd" || true
    fi

    run_check "TypeScript" "npx tsc --noEmit" "" "$wd" || true
    run_check "Tests" "npm test -- --run" "" "$wd" || true
    run_check "Build" "npm run build" "" "$wd" || true
}

# Check api-service
check_api_service() {
    echo ""
    echo "=== API Service (api-service/) ==="

    if [[ ! -d "$PROJECT_ROOT/api-service" ]]; then
        skip_check "All checks" "directory not found"
        return
    fi

    if [[ ! -d "$PROJECT_ROOT/api-service/.venv" ]]; then
        skip_check "All checks" ".venv not found"
        echo "  Run: cd api-service && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        return
    fi

    local wd="$PROJECT_ROOT/api-service"
    local venv_python="$wd/.venv/bin/python"
    local venv_ruff="$wd/.venv/bin/ruff"

    if [[ -x "$venv_ruff" ]]; then
        if $FIX_MODE; then
            run_check "Ruff lint" "$venv_ruff check ." "$venv_ruff check --fix ." "$wd" || true
            run_check "Ruff format" "$venv_ruff format --check ." "$venv_ruff format ." "$wd" || true
        else
            run_check "Ruff lint" "$venv_ruff check ." "" "$wd" || true
            run_check "Ruff format" "$venv_ruff format --check ." "" "$wd" || true
        fi
    else
        skip_check "Ruff checks" "ruff not installed in venv"
    fi

    run_check "Pytest" "$venv_python -m pytest --tb=no -q" "" "$wd" || true
}

# Check ingest
check_ingest() {
    echo ""
    echo "=== Ingest (ingest/) ==="

    if [[ ! -d "$PROJECT_ROOT/ingest" ]]; then
        skip_check "All checks" "directory not found"
        return
    fi

    if [[ ! -d "$PROJECT_ROOT/ingest/.venv" ]]; then
        skip_check "All checks" ".venv not found"
        echo "  Run: cd ingest && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        return
    fi

    local wd="$PROJECT_ROOT/ingest"
    local venv_ruff="$wd/.venv/bin/ruff"

    if [[ -x "$venv_ruff" ]]; then
        if $FIX_MODE; then
            run_check "Ruff lint" "$venv_ruff check ." "$venv_ruff check --fix ." "$wd" || true
            run_check "Ruff format" "$venv_ruff format --check ." "$venv_ruff format ." "$wd" || true
        else
            run_check "Ruff lint" "$venv_ruff check ." "" "$wd" || true
            run_check "Ruff format" "$venv_ruff format --check ." "" "$wd" || true
        fi
    else
        skip_check "Ruff checks" "ruff not installed in venv"
    fi
}

# Check memvid-service
check_memvid_service() {
    echo ""
    echo "=== Memvid Service (memvid-service/) ==="

    if [[ ! -d "$PROJECT_ROOT/memvid-service" ]]; then
        skip_check "All checks" "directory not found"
        return
    fi

    if [[ ! -f "$PROJECT_ROOT/memvid-service/Cargo.toml" ]]; then
        skip_check "All checks" "Cargo.toml not found"
        return
    fi

    if ! command -v cargo &> /dev/null; then
        skip_check "All checks" "cargo not installed"
        return
    fi

    local wd="$PROJECT_ROOT/memvid-service"

    if $FIX_MODE; then
        run_check "Rustfmt" "cargo fmt --check" "cargo fmt" "$wd" || true
    else
        run_check "Rustfmt" "cargo fmt --check" "" "$wd" || true
    fi

    run_check "Clippy" "cargo clippy -- -D warnings" "" "$wd" || true
    run_check "Build" "cargo build" "" "$wd" || true
    run_check "Tests" "cargo test" "" "$wd" || true
}

# Check docs
check_docs() {
    echo ""
    echo "=== Documentation ==="

    if command -v markdownlint &> /dev/null; then
        if $FIX_MODE; then
            run_check "Markdown lint" "markdownlint '**/*.md' --ignore node_modules --ignore '**/node_modules/**'" "markdownlint '**/*.md' --ignore node_modules --ignore '**/node_modules/**' --fix" "$PROJECT_ROOT" || true
        else
            run_check "Markdown lint" "markdownlint '**/*.md' --ignore node_modules --ignore '**/node_modules/**'" "" "$PROJECT_ROOT" || true
        fi
    else
        skip_check "Markdown lint" "markdownlint not installed"
    fi
}

# Main
echo "========================================"
echo "  Monorepo Quality Verification"
echo "========================================"
echo ""
echo "Project: $PROJECT_ROOT"
echo "Mode: $($FIX_MODE && echo 'Fix' || echo 'Check')"
if [[ -n "$TARGET_SERVICE" ]]; then
    echo "Target: $TARGET_SERVICE"
fi

# Run checks based on target
if [[ -z "$TARGET_SERVICE" ]]; then
    check_frontend
    check_api_service
    check_ingest
    check_memvid_service
    check_docs
else
    case "$TARGET_SERVICE" in
        frontend)
            check_frontend
            ;;
        api-service)
            check_api_service
            ;;
        ingest)
            check_ingest
            ;;
        memvid-service)
            check_memvid_service
            ;;
        docs)
            check_docs
            ;;
        *)
            echo "Unknown service: $TARGET_SERVICE"
            echo "Valid services: frontend, api-service, ingest, memvid-service, docs"
            exit 1
            ;;
    esac
fi

# Summary
echo ""
echo "========================================"
echo "  Summary"
echo "========================================"
echo -e "  Passed:  ${GREEN}$TOTAL_PASSED${NC}"
echo -e "  Failed:  ${RED}$TOTAL_FAILED${NC}"
echo -e "  Skipped: ${YELLOW}$TOTAL_SKIPPED${NC}"

if [[ $TOTAL_FAILED -gt 0 ]]; then
    echo ""
    echo -e "${RED}Quality checks failed!${NC}"
    if ! $FIX_MODE; then
        echo "Try running with --fix to auto-fix issues"
    fi
    exit 1
fi

echo ""
echo -e "${GREEN}All quality checks passed!${NC}"
exit 0

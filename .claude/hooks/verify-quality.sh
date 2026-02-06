#!/bin/bash
# Verify-quality hook: Run quality checks before stopping
# This hook is called when Claude Code is about to stop working

set -euo pipefail

# Read JSON input from stdin and check for infinite loop prevention
INPUT="$(cat)"
STOP_HOOK_ACTIVE="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stop_hook_active', False))" 2>/dev/null || echo "False")"
if [[ "$STOP_HOOK_ACTIVE" == "True" ]]; then
    exit 0
fi

# Get the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Running quality verification checks..."

FAILED=0
WARNINGS=0

# Helper function to run a check
run_check() {
    local name="$1"
    local command="$2"
    local working_dir="${3:-$PROJECT_ROOT}"

    echo -n "  Checking $name... "
    if (cd "$working_dir" && eval "$command" > /dev/null 2>&1); then
        echo "PASS"
        return 0
    else
        echo "FAIL"
        return 1
    fi
}

# Helper function for optional checks (warnings only)
run_optional_check() {
    local name="$1"
    local command="$2"
    local working_dir="${3:-$PROJECT_ROOT}"

    echo -n "  Checking $name... "
    if (cd "$working_dir" && eval "$command" > /dev/null 2>&1); then
        echo "PASS"
        return 0
    else
        echo "WARN"
        return 1
    fi
}

echo ""
echo "=== Frontend Checks (frontend/) ==="
if [[ -d "$PROJECT_ROOT/frontend" ]] && [[ -f "$PROJECT_ROOT/frontend/package.json" ]]; then
    # Check if node_modules exists
    if [[ -d "$PROJECT_ROOT/frontend/node_modules" ]]; then
        run_check "ESLint" "npm run lint" "$PROJECT_ROOT/frontend" || FAILED=$((FAILED + 1))
        run_check "TypeScript" "npx tsc --noEmit" "$PROJECT_ROOT/frontend" || FAILED=$((FAILED + 1))
        run_optional_check "Tests" "npm test -- --run" "$PROJECT_ROOT/frontend" || WARNINGS=$((WARNINGS + 1))
    else
        echo "  Skipping: node_modules not installed"
    fi
else
    echo "  Skipping: frontend directory not found"
fi

echo ""
echo "=== API Service Checks (api-service/) ==="
if [[ -d "$PROJECT_ROOT/api-service" ]]; then
    if [[ -d "$PROJECT_ROOT/api-service/.venv" ]]; then
        VENV_PYTHON="$PROJECT_ROOT/api-service/.venv/bin/python"
        VENV_RUFF="$PROJECT_ROOT/api-service/.venv/bin/ruff"

        if [[ -x "$VENV_RUFF" ]]; then
            run_check "Ruff lint" "$VENV_RUFF check ." "$PROJECT_ROOT/api-service" || FAILED=$((FAILED + 1))
            run_check "Ruff format" "$VENV_RUFF format --check ." "$PROJECT_ROOT/api-service" || FAILED=$((FAILED + 1))
        else
            echo "  Skipping ruff: not installed in venv"
        fi

        run_optional_check "Pytest" "$VENV_PYTHON -m pytest --tb=no -q" "$PROJECT_ROOT/api-service" || WARNINGS=$((WARNINGS + 1))
    else
        echo "  Skipping: .venv not found"
    fi
else
    echo "  Skipping: api-service directory not found"
fi

echo ""
echo "=== Ingest Checks (ingest/) ==="
if [[ -d "$PROJECT_ROOT/ingest" ]]; then
    if [[ -d "$PROJECT_ROOT/ingest/.venv" ]]; then
        VENV_RUFF="$PROJECT_ROOT/ingest/.venv/bin/ruff"

        if [[ -x "$VENV_RUFF" ]]; then
            run_check "Ruff lint" "$VENV_RUFF check ." "$PROJECT_ROOT/ingest" || FAILED=$((FAILED + 1))
            run_check "Ruff format" "$VENV_RUFF format --check ." "$PROJECT_ROOT/ingest" || FAILED=$((FAILED + 1))
        else
            echo "  Skipping ruff: not installed in venv"
        fi
    else
        echo "  Skipping: .venv not found"
    fi
else
    echo "  Skipping: ingest directory not found"
fi

echo ""
echo "=== Memvid Service Checks (memvid-service/) ==="
if [[ -d "$PROJECT_ROOT/memvid-service" ]] && [[ -f "$PROJECT_ROOT/memvid-service/Cargo.toml" ]]; then
    if command -v cargo &> /dev/null; then
        run_check "Cargo check" "cargo check" "$PROJECT_ROOT/memvid-service" || FAILED=$((FAILED + 1))
        run_check "Cargo clippy" "cargo clippy -- -D warnings" "$PROJECT_ROOT/memvid-service" || WARNINGS=$((WARNINGS + 1))
        run_optional_check "Cargo test" "cargo test --no-run" "$PROJECT_ROOT/memvid-service" || WARNINGS=$((WARNINGS + 1))
    else
        echo "  Skipping: cargo not found"
    fi
else
    echo "  Skipping: memvid-service directory not found"
fi

echo ""
echo "=== Summary ==="
echo "Failed checks: $FAILED"
echo "Warnings: $WARNINGS"

if [[ $FAILED -gt 0 ]]; then
    echo "" >&2
    echo "Quality checks failed. Please fix the issues before stopping." >&2
    exit 2
fi

if [[ $WARNINGS -gt 0 ]]; then
    echo ""
    echo "Some optional checks had warnings. Consider reviewing them."
fi

echo ""
echo "All required quality checks passed!"
exit 0

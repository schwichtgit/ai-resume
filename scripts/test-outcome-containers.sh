#!/bin/bash
set -euo pipefail
echo "=== Container Deployment Outcome Test ==="

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0

# Check 1: All Dockerfiles exist
echo "Check 1: Dockerfiles exist..."
for dir in frontend api-service memvid-service ingest; do
    if [ -f "$dir/Dockerfile" ]; then
        echo "  PASS: $dir/Dockerfile exists"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $dir/Dockerfile missing"
        FAIL=$((FAIL + 1))
    fi
done

# Check 2: compose.yaml exists
echo "Check 2: compose.yaml..."
if [ -f "deployment/compose.yaml" ]; then
    echo "  PASS: deployment/compose.yaml exists"
    PASS=$((PASS + 1))
else
    echo "  FAIL: deployment/compose.yaml missing"
    FAIL=$((FAIL + 1))
fi

# Check 3: Non-root users in Dockerfiles
echo "Check 3: Non-root users..."
for dir in frontend api-service memvid-service; do
    if grep -q "^USER" "$dir/Dockerfile"; then
        echo "  PASS: $dir uses non-root USER"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $dir missing USER directive"
        FAIL=$((FAIL + 1))
    fi
done

# Check 4: Health check support
echo "Check 4: Health check endpoints..."
if grep -q "HEALTHCHECK\|healthcheck\|/health" deployment/compose.yaml; then
    echo "  PASS: compose.yaml includes health checks"
    PASS=$((PASS + 1))
else
    echo "  FAIL: compose.yaml missing health checks"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1

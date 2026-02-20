#!/bin/bash
set -euo pipefail
echo "=== Portability Outcome Test ==="

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0

# Check 1: No hardcoded candidate data in frontend components/pages
# (Exclude hooks/utils where names appear only in JSDoc examples)
echo "Check 1: No hardcoded candidate names in frontend components..."
if ! grep -rq "Frank Schwichtenberg\|schwichtenberg" frontend/src/components/ frontend/src/pages/; then
    echo "  PASS: No hardcoded candidate names in components/pages"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Hardcoded candidate data found in components/pages"
    FAIL=$((FAIL + 1))
fi

# Check 2: API client uses API_BASE_URL (not hardcoded URLs)
echo "Check 2: API client is configurable..."
if grep -q "API_BASE_URL" frontend/src/lib/api-client.ts; then
    echo "  PASS: API client uses configurable base URL"
    PASS=$((PASS + 1))
else
    echo "  FAIL: API client has hardcoded URLs"
    FAIL=$((FAIL + 1))
fi

# Check 3: Profile data comes from API, not static imports
echo "Check 3: Profile data from API..."
if grep -q "getProfile" frontend/src/hooks/useProfile.ts; then
    echo "  PASS: Profile loaded from API"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Profile not loaded from API"
    FAIL=$((FAIL + 1))
fi

# Check 4: No hardcoded profile data in components (e.g., name="John")
echo "Check 4: Components use dynamic data from hooks..."
if grep -q "useProfile" frontend/src/pages/Index.tsx; then
    echo "  PASS: Index page uses useProfile hook"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Index page does not use useProfile hook"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1

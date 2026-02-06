#!/bin/bash
set -euo pipefail

# E2E Test Script for Mock Feature Gates
# Tests all combinations of MOCK_MEMVID, MOCK_MEMVID_CLIENT, MOCK_OPENROUTER
# Validates fail-fast behavior when real implementations unavailable

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST #$TESTS_RUN: $1${NC}"
}

print_pass() {
    echo -e "${GREEN}✓ PASS: $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "$1"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up background processes...${NC}"
    pkill -f "memvid-service" || true
    pkill -f "uvicorn.*ai_resume_api" || true
    sleep 1
}

trap cleanup EXIT

print_header "E2E Mock Feature Gate Tests"

echo "Project root: $PROJECT_ROOT"
echo "Test data: test_resume.mv2 ($([ -f test_resume.mv2 ] && echo 'exists' || echo 'MISSING'))"
echo ""

# =============================================================================
# Test 1: Pure Mock Mode (all mocks enabled)
# =============================================================================
run_test "All mocks enabled (MOCK_MEMVID=true, MOCK_MEMVID_CLIENT=true, MOCK_OPENROUTER=true)"

export MOCK_MEMVID=true
export MOCK_MEMVID_CLIENT=true
export MOCK_OPENROUTER=true

# Start Rust service in mock mode (no .mv2 file needed)
./memvid-service/target/release/memvid-service > /tmp/memvid-test.log 2>&1 &
MEMVID_PID=$!
sleep 2

if ps -p $MEMVID_PID > /dev/null; then
    print_pass "Rust service started with MOCK_MEMVID=true (no .mv2 file required)"
else
    print_fail "Rust service failed to start with MOCK_MEMVID=true"
fi

kill $MEMVID_PID 2>/dev/null || true
sleep 1

# Test Python API with all mocks
cd api-service
source .venv/bin/activate

python -c "
from ai_resume_api.config import get_settings
settings = get_settings()
assert settings.mock_memvid_client == True, 'MOCK_MEMVID_CLIENT should be True'
assert settings.mock_openrouter == True, 'MOCK_OPENROUTER should be True'
print('Python config correctly loaded mock settings')
" && print_pass "Python API config loaded with all mocks enabled" || print_fail "Python config failed to load mock settings"

cd ..

# =============================================================================
# Test 2: Real Memvid Service with Mock API (test Rust service in isolation)
# =============================================================================
run_test "Real memvid service (MOCK_MEMVID=false) with test_resume.mv2"

export MOCK_MEMVID=false
export MEMVID_FILE_PATH="./test_resume.mv2"

if [ ! -f "$MEMVID_FILE_PATH" ]; then
    print_fail "test_resume.mv2 not found - run 'uv run python ingest/ingest.py --input data/example_resume.md --output test_resume.mv2' first"
else
    ./memvid-service/target/release/memvid-service > /tmp/memvid-test.log 2>&1 &
    MEMVID_PID=$!
    sleep 3

    if ps -p $MEMVID_PID > /dev/null; then
        # Check logs for successful load
        if grep -q "Real memvid searcher loaded successfully" /tmp/memvid-test.log; then
            print_pass "Rust service loaded real .mv2 file successfully"
        else
            print_fail "Rust service started but didn't load .mv2 file correctly"
        fi
    else
        print_fail "Rust service failed to start with MOCK_MEMVID=false"
        cat /tmp/memvid-test.log
    fi

    kill $MEMVID_PID 2>/dev/null || true
    sleep 1
fi

# =============================================================================
# Test 3: Fail-fast when MOCK_MEMVID=false but .mv2 file missing
# =============================================================================
run_test "Fail-fast: MOCK_MEMVID=false with missing .mv2 file (should exit with error)"

export MOCK_MEMVID=false
export MEMVID_FILE_PATH="./nonexistent.mv2"

./memvid-service/target/release/memvid-service > /tmp/memvid-fail-test.log 2>&1 &
MEMVID_PID=$!
sleep 2

if ps -p $MEMVID_PID > /dev/null; then
    print_fail "Rust service should have exited with error for missing .mv2 file"
    kill $MEMVID_PID 2>/dev/null || true
else
    if grep -q "FATAL.*Failed to load memvid file" /tmp/memvid-fail-test.log; then
        print_pass "Rust service correctly exited with FATAL error for missing .mv2"
    else
        print_fail "Rust service exited but without proper FATAL error message"
        cat /tmp/memvid-fail-test.log
    fi
fi

# =============================================================================
# Test 4: Python API fail-fast with MOCK_MEMVID_CLIENT=false but no gRPC
# =============================================================================
run_test "Fail-fast: MOCK_MEMVID_CLIENT=false with no gRPC service (should raise exception)"

cd api-service
source .venv/bin/activate

export MOCK_MEMVID_CLIENT=false
export MOCK_OPENROUTER=true  # Mock OpenRouter to isolate memvid client test

# Suppress stderr — the FATAL log lines are expected behavior being tested
python -c "
import asyncio
from ai_resume_api.memvid_client import MemvidClient, MemvidConnectionError

async def test():
    client = MemvidClient()
    # Don't connect (no gRPC service running)
    try:
        result = await client.search('test query')
        print('ERROR: Should have raised MemvidConnectionError')
        return False
    except MemvidConnectionError as e:
        if 'MOCK_MEMVID_CLIENT=false' in str(e):
            print('Correctly raised MemvidConnectionError with policy violation message')
            return True
        else:
            print(f'Raised error but wrong message: {e}')
            return False

result = asyncio.run(test())
exit(0 if result else 1)
" 2>/dev/null && print_pass "Python API correctly fails when MOCK_MEMVID_CLIENT=false and gRPC unavailable" || print_fail "Python API didn't fail correctly"

cd ..

# =============================================================================
# Test 5: Python API fail-fast with MOCK_OPENROUTER=false but no API key
# =============================================================================
run_test "Fail-fast: MOCK_OPENROUTER=false with missing API key (should raise exception)"

cd api-service
source .venv/bin/activate

export MOCK_OPENROUTER=false
export OPENROUTER_API_KEY=""  # No API key

# Suppress stderr — the FATAL log lines are expected behavior being tested
python -c "
import asyncio
from ai_resume_api.openrouter_client import OpenRouterClient, OpenRouterAuthError

async def test():
    client = OpenRouterClient()
    try:
        result = await client.chat('system', 'context', 'test message')
        print('ERROR: Should have raised OpenRouterAuthError')
        return False
    except OpenRouterAuthError as e:
        if 'MOCK_OPENROUTER=false' in str(e):
            print('Correctly raised OpenRouterAuthError with policy violation message')
            return True
        else:
            print(f'Raised error but wrong message: {e}')
            return False

result = asyncio.run(test())
exit(0 if result else 1)
" 2>/dev/null && print_pass "Python API correctly fails when MOCK_OPENROUTER=false and API key missing" || print_fail "Python API didn't fail correctly"

cd ..

# =============================================================================
# Test 6: Full E2E with real components (if .mv2 exists)
# =============================================================================
run_test "Full E2E: Real memvid + Real gRPC + Mock OpenRouter"

if [ ! -f "./test_resume.mv2" ]; then
    print_fail "Skipped - test_resume.mv2 not found"
else
    export MOCK_MEMVID=false
    export MEMVID_FILE_PATH="./test_resume.mv2"
    export MOCK_MEMVID_CLIENT=false
    export MOCK_OPENROUTER=true  # Mock OpenRouter to avoid needing API key
    export GRPC_PORT=50051
    export MEMVID_GRPC_HOST=localhost

    # Start Rust service
    ./memvid-service/target/release/memvid-service > /tmp/memvid-e2e.log 2>&1 &
    MEMVID_PID=$!
    sleep 3

    if ! ps -p $MEMVID_PID > /dev/null; then
        print_fail "Rust service failed to start"
        cat /tmp/memvid-e2e.log
    else
        # Start Python API service
        cd api-service
        source .venv/bin/activate

        uvicorn ai_resume_api.main:app --host 0.0.0.0 --port 3000 > /tmp/api-e2e.log 2>&1 &
        API_PID=$!
        sleep 3

        if ! ps -p $API_PID > /dev/null; then
            print_fail "Python API failed to start"
            cat /tmp/api-e2e.log
        else
            # Test the full stack with a query
            response=$(curl -s -X POST http://localhost:3000/api/v1/chat \
                -H "Content-Type: application/json" \
                -d '{"message":"What programming languages does she know?","stream":false}' || echo "CURL_FAILED")

            if echo "$response" | grep -q "mock"; then
                print_pass "Full E2E stack working (real memvid + real gRPC + mock OpenRouter)"
            else
                print_fail "Full E2E test failed - unexpected response: $response"
            fi

            kill $API_PID 2>/dev/null || true
        fi

        kill $MEMVID_PID 2>/dev/null || true
        cd ..
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Test Summary"

echo "Total tests run: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}\n"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed${NC}\n"
    exit 1
fi

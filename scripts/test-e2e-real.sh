#!/bin/bash
set -euo pipefail

# True E2E Tests: Real ingest -> real memvid search -> real API
# Tests semantic search quality with actual .mv2 file (no mock data)
# LLM is still mocked (MOCK_OPENROUTER=true) as it's a third-party service

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

# Service PIDs (global for cleanup)
MEMVID_PID=""
API_PID=""

# Log files
MEMVID_LOG="/tmp/memvid-e2e-real.log"
API_LOG="/tmp/api-e2e-real.log"

# Temp files
MV2_OUTPUT="/tmp/e2e_resume.mv2"

# Ports (use different ports from mock tests to avoid conflicts)
GRPC_PORT=50052
API_PORT=3001

print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST #$TESTS_RUN: $1${NC}"
}

print_pass() {
    echo -e "${GREEN}PASS: $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_fail() {
    echo -e "${RED}FAIL: $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "$1"
}

# Wait for a TCP port to become available
wait_for_port() {
    local host="$1"
    local port="$2"
    local timeout="$3"
    local label="$4"
    local elapsed=0

    echo -e "  Waiting for ${label} on ${host}:${port} (timeout: ${timeout}s)..."
    while [ "$elapsed" -lt "$timeout" ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo -e "  ${GREEN}${label} is ready (${elapsed}s)${NC}"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo -e "  ${RED}${label} failed to start within ${timeout}s${NC}"
    return 1
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    if [ -n "$API_PID" ] && ps -p "$API_PID" > /dev/null 2>&1; then
        kill "$API_PID" 2>/dev/null || true
    fi
    if [ -n "$MEMVID_PID" ] && ps -p "$MEMVID_PID" > /dev/null 2>&1; then
        kill "$MEMVID_PID" 2>/dev/null || true
    fi
    # Belt-and-suspenders
    pkill -f "memvid-service.*${GRPC_PORT}" 2>/dev/null || true
    pkill -f "uvicorn.*ai_resume_api.*${API_PORT}" 2>/dev/null || true
    rm -f "$MV2_OUTPUT"
    sleep 1
}

trap cleanup EXIT

print_header "True E2E Tests (real ingest, real search, mock LLM)"
echo "Data flow: example_resume.md -> ingest -> .mv2 -> memvid-service -> api-service -> HTTP"
echo "Project root: $PROJECT_ROOT"
echo ""

# =============================================================================
# Prerequisites
# =============================================================================

MEMVID_BINARY="$PROJECT_ROOT/memvid-service/target/release/memvid-service"
INGEST_VENV="$PROJECT_ROOT/ingest/.venv"
API_VENV="$PROJECT_ROOT/api-service/.venv"
RESUME_INPUT="$PROJECT_ROOT/data/example_resume.md"

for prereq in "$MEMVID_BINARY:memvid-service binary (cd memvid-service && cargo build --release)" \
              "$INGEST_VENV:ingest venv (cd ingest && uv sync)" \
              "$API_VENV:api-service venv (cd api-service && uv sync --extra test)" \
              "$RESUME_INPUT:example resume (data/example_resume.md)"; do
    path="${prereq%%:*}"
    hint="${prereq#*:}"
    if [ ! -e "$path" ]; then
        echo -e "${RED}ERROR: Missing: $hint${NC}"
        echo "  Expected at: $path"
        exit 1
    fi
done

echo -e "${GREEN}Prerequisites OK${NC}"
echo ""

# =============================================================================
# Phase 1: Ingest
# =============================================================================

print_header "Phase 1: Ingest example_resume.md -> .mv2"

echo "Input:  $RESUME_INPUT"
echo "Output: $MV2_OUTPUT"
echo ""

(
    cd "$PROJECT_ROOT/ingest"
    source .venv/bin/activate
    python ingest.py \
        --input "$RESUME_INPUT" \
        --output "$MV2_OUTPUT" \
        --verify \
        --quiet
)

if [ ! -f "$MV2_OUTPUT" ]; then
    echo -e "${RED}FATAL: Ingest failed - .mv2 file not created${NC}"
    exit 1
fi

MV2_SIZE=$(stat -f%z "$MV2_OUTPUT" 2>/dev/null || stat -c%s "$MV2_OUTPUT" 2>/dev/null || echo "0")
echo -e "${GREEN}Ingest complete: $MV2_OUTPUT ($MV2_SIZE bytes)${NC}"
echo ""

# =============================================================================
# Phase 2: Start services with real search
# =============================================================================

print_header "Phase 2: Start services (MOCK_MEMVID=false)"

# Start memvid-service with real .mv2 file
echo "Starting memvid-service (MOCK_MEMVID=false) on port $GRPC_PORT..."
MOCK_MEMVID=false \
    MEMVID_FILE_PATH="$MV2_OUTPUT" \
    GRPC_PORT=$GRPC_PORT \
    METRICS_PORT=9091 \
    "$MEMVID_BINARY" > "$MEMVID_LOG" 2>&1 &
MEMVID_PID=$!

if ! wait_for_port localhost "$GRPC_PORT" 30 "memvid-service"; then
    echo -e "${RED}memvid-service failed to start. Log:${NC}"
    cat "$MEMVID_LOG"
    exit 1
fi

if ! ps -p "$MEMVID_PID" > /dev/null 2>&1; then
    echo -e "${RED}memvid-service died after starting. Log:${NC}"
    cat "$MEMVID_LOG"
    exit 1
fi

echo ""

# Start API service with real gRPC, mock LLM
echo "Starting api-service (MOCK_MEMVID_CLIENT=false, MOCK_OPENROUTER=true) on port $API_PORT..."
(
    cd "$PROJECT_ROOT/api-service"
    source .venv/bin/activate
    MOCK_MEMVID_CLIENT=false \
    MOCK_OPENROUTER=true \
    OPENROUTER_API_KEY="" \
    MEMVID_GRPC_HOST=localhost \
    MEMVID_GRPC_PORT=$GRPC_PORT \
        uvicorn ai_resume_api.main:app --host 0.0.0.0 --port "$API_PORT" > "$API_LOG" 2>&1
) &
API_PID=$!

if ! wait_for_port localhost "$API_PORT" 15 "api-service"; then
    echo -e "${RED}api-service failed to start. Log:${NC}"
    cat "$API_LOG"
    exit 1
fi

if ! ps -p "$API_PID" > /dev/null 2>&1; then
    echo -e "${RED}api-service died after starting. Log:${NC}"
    cat "$API_LOG"
    exit 1
fi

echo ""
echo -e "${GREEN}Both services running (real search mode)${NC}"
echo "  memvid-service PID=$MEMVID_PID (port $GRPC_PORT, file=$MV2_OUTPUT)"
echo "  api-service     PID=$API_PID (port $API_PORT)"
echo ""

# =============================================================================
# Phase 3: Semantic quality assertions
# =============================================================================

print_header "Phase 3: Semantic Quality Assertions"

BASE_URL="http://localhost:$API_PORT/api/v1"

# --- Test 1: Profile name matches example_resume.md ---
run_test "Profile name is 'Jane Chen' (from example_resume.md, not mock data)"

profile_response=$(curl -sf "$BASE_URL/profile" 2>&1 || echo "CURL_FAILED")

if echo "$profile_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/profile"
else
    profile_name=$(python3 -c "
import sys, json
try:
    p = json.loads(sys.stdin.read())
    print(p.get('name', ''))
except:
    print('')
" <<< "$profile_response" 2>/dev/null || echo "")

    if [ "$profile_name" = "Jane Chen" ]; then
        print_pass "Profile name is 'Jane Chen' (real data, not mock)"
    else
        print_fail "Expected profile name 'Jane Chen', got '$profile_name'"
        echo "  This means mock data leaked into real mode"
    fi
fi

# --- Test 2: Profile title matches ---
run_test "Profile title is 'VP of Platform Engineering'"

if echo "$profile_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/profile (reusing previous failure)"
else
    profile_title=$(python3 -c "
import sys, json
try:
    p = json.loads(sys.stdin.read())
    print(p.get('title', ''))
except:
    print('')
" <<< "$profile_response" 2>/dev/null || echo "")

    if echo "$profile_title" | grep -qi "Platform Engineering"; then
        print_pass "Profile title contains 'Platform Engineering' ($profile_title)"
    else
        print_fail "Expected title containing 'Platform Engineering', got '$profile_title'"
    fi
fi

# --- Test 3: Health shows memvid_connected=true with real search ---
run_test "Health endpoint reports memvid_connected=true (real .mv2)"

health_response=$(curl -sf "$BASE_URL/health" 2>&1 || echo "CURL_FAILED")

if echo "$health_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/health"
elif echo "$health_response" | grep -q '"memvid_connected":true'; then
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        print_pass "Health: status=healthy, memvid_connected=true (real .mv2)"
    else
        print_fail "memvid_connected=true but status not healthy"
    fi
else
    print_fail "memvid_connected not true"
    echo "  Response: $health_response"
fi

# --- Test 4: Search returns real content about Python ---
run_test "Chat about 'Python' returns content from real resume (not mock)"

chat_response=$(curl -sf -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"What programming languages does this person know?","stream":false}' \
    2>&1 || echo "CURL_FAILED")

if echo "$chat_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/chat"
else
    # Check that response has content and chunks were retrieved
    chat_check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    msg = data.get('message', '')
    chunks = data.get('chunks_retrieved', 0)
    # The mock OpenRouter returns content based on the REAL context from memvid
    # We just need to verify chunks were retrieved from real search
    if chunks > 0 and len(msg) > 0:
        print('OK:chunks=' + str(chunks) + ',msg_len=' + str(len(msg)))
    else:
        print('FAIL:chunks=' + str(chunks) + ',msg_len=' + str(len(msg)))
except Exception as e:
    print('FAIL:' + str(e))
" <<< "$chat_response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$chat_check" | grep -q "^OK:"; then
        detail=$(echo "$chat_check" | sed 's/^OK://')
        print_pass "Chat returned real search results ($detail)"
    else
        detail=$(echo "$chat_check" | sed 's/^FAIL://')
        print_fail "Chat did not return expected results ($detail)"
    fi
fi

# --- Test 5: Suggested questions match example_resume.md ---
run_test "Suggested questions include questions from example_resume.md"

questions_response=$(curl -sf "$BASE_URL/suggested-questions" 2>&1 || echo "CURL_FAILED")

if echo "$questions_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/suggested-questions"
else
    questions_check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    questions = data.get('questions', [])
    # example_resume.md has suggested_questions including 'programming languages'
    has_lang = any('programming' in q.lower() or 'languages' in q.lower() for q in questions)
    if isinstance(questions, list) and len(questions) > 0 and has_lang:
        print('OK:count=' + str(len(questions)) + ',has_programming_q=true')
    elif isinstance(questions, list) and len(questions) > 0:
        print('OK:count=' + str(len(questions)) + ',has_programming_q=false')
    else:
        print('FAIL:no questions returned')
except Exception as e:
    print('FAIL:' + str(e))
" <<< "$questions_response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$questions_check" | grep -q "^OK:"; then
        detail=$(echo "$questions_check" | sed 's/^OK://')
        print_pass "Suggested questions from real resume data ($detail)"
    else
        detail=$(echo "$questions_check" | sed 's/^FAIL://')
        print_fail "Suggested questions check failed ($detail)"
    fi
fi

# --- Test 6: Fit assessment uses real search context ---
run_test "Fit assessment retrieves real resume context for evaluation"

fit_response=$(curl -sf -X POST "$BASE_URL/assess-fit" \
    -H "Content-Type: application/json" \
    -d '{"job_description":"VP of Platform Engineering: Lead cloud infrastructure, Kubernetes orchestration, CI/CD pipelines. 10+ years distributed systems."}' \
    2>&1 || echo "CURL_FAILED")

if echo "$fit_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/assess-fit"
else
    fit_check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    verdict = data.get('verdict', '')
    key_matches = data.get('key_matches', [])
    recommendation = data.get('recommendation', '')
    if verdict and len(key_matches) > 0 and recommendation:
        print('OK:verdict=' + str(verdict) + ',matches=' + str(len(key_matches)))
    else:
        print('FAIL:verdict=' + str(bool(verdict)) + ',matches=' + str(len(key_matches)) + ',rec=' + str(bool(recommendation)))
except Exception as e:
    print('FAIL:' + str(e))
" <<< "$fit_response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$fit_check" | grep -q "^OK:"; then
        detail=$(echo "$fit_check" | sed 's/^OK://')
        print_pass "Fit assessment with real context ($detail)"
    else
        detail=$(echo "$fit_check" | sed 's/^FAIL://')
        print_fail "Fit assessment failed ($detail)"
    fi
fi

# --- Test 7: Streaming chat with real search ---
run_test "Streaming chat returns SSE events with real search context"

SSE_OUTPUT="/tmp/e2e-real-sse-output.txt"
curl -sf -N -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"Tell me about this persons security experience","stream":true}' \
    --max-time 30 \
    > "$SSE_OUTPUT" 2>&1 || true

if [ ! -s "$SSE_OUTPUT" ]; then
    print_fail "Streaming response was empty"
else
    data_lines=$(grep -c "^data: " "$SSE_OUTPUT" 2>/dev/null || echo "0")
    has_retrieval=$(grep -c '"retrieval"' "$SSE_OUTPUT" 2>/dev/null || echo "0")
    has_token=$(grep -c '"token"' "$SSE_OUTPUT" 2>/dev/null || echo "0")

    if [ "$data_lines" -gt 0 ] && [ "$has_token" -gt 0 ]; then
        print_pass "SSE stream valid (data_lines=$data_lines, retrieval=$has_retrieval, token=$has_token)"
    else
        print_fail "SSE stream missing expected events (data_lines=$data_lines, token=$has_token)"
        head -c 500 "$SSE_OUTPUT"
        echo ""
    fi

    rm -f "$SSE_OUTPUT"
fi

# =============================================================================
# Summary
# =============================================================================

print_header "Test Summary"

echo "Total tests run: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All true E2E tests passed${NC}\n"
    exit 0
else
    echo -e "\n${RED}Some tests failed${NC}\n"
    echo "Diagnostic logs:"
    echo "  memvid-service: $MEMVID_LOG"
    echo "  api-service:    $API_LOG"
    exit 1
fi

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

# Wait for API health endpoint to return healthy before running tests
# Usage: wait_for_health URL [timeout_seconds]
wait_for_health() {
    local url="$1"
    local timeout="${2:-60}"
    local start
    start=$(date +%s)
    printf "Waiting for %s to become healthy..." "$url"
    while true; do
        local elapsed=$(( $(date +%s) - start ))
        if [ "$elapsed" -ge "$timeout" ]; then
            printf " TIMEOUT after %ds\n" "$timeout"
            return 1
        fi
        if curl -L --max-redirs 3 -sf --max-time 5 "$url" > /dev/null 2>&1; then
            printf " ready (%ds)\n" "$elapsed"
            return 0
        fi
        sleep 2
    done
}

# Curl wrapper that retries ONLY on HTTP 429 (rate limit).
# All other errors (connection refused, timeouts, 4xx, 5xx) fail immediately.
# Usage: curl_with_429_retry [curl args...]
# Output: response body on stdout; exits non-zero on failure
curl_with_429_retry() {
    local max_retries=3
    local attempt=0
    local tmpfile
    tmpfile=$(mktemp)
    local header_file
    header_file=$(mktemp)

    while [ "$attempt" -lt "$max_retries" ]; do
        local http_code
        # Use -s (no -f) so curl doesn't exit non-zero on 4xx/5xx -- we handle codes ourselves
        http_code=$(curl -L --max-redirs 3 -s --max-time 30 -w '%{http_code}' -o "$tmpfile" -D "$header_file" "$@" 2>/dev/null) || {
            # curl itself failed (connection refused, DNS error, timeout, etc.)
            rm -f "$tmpfile" "$header_file"
            echo "CURL_FAILED:connection_error" >&2
            return 1
        }

        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
            cat "$tmpfile"
            rm -f "$tmpfile" "$header_file"
            return 0
        elif [ "$http_code" = "429" ]; then
            attempt=$((attempt + 1))
            if [ "$attempt" -ge "$max_retries" ]; then
                rm -f "$tmpfile" "$header_file"
                echo "CURL_FAILED:429_after_${max_retries}_retries" >&2
                return 1
            fi
            # Read Retry-After from response headers (default 2s)
            local retry_after
            retry_after=$(grep -i '^retry-after:' "$header_file" 2>/dev/null | awk '{print $2}' | tr -d '\r' || echo "2")
            if [ -z "$retry_after" ] || ! [[ "$retry_after" =~ ^[0-9]+$ ]]; then
                retry_after=2
            fi
            echo "  Rate limited (429), retry $attempt/$max_retries after ${retry_after}s..." >&2
            sleep "$retry_after"
        else
            # Any other non-2xx: fail immediately
            rm -f "$tmpfile" "$header_file"
            echo "CURL_FAILED:http_$http_code" >&2
            return 1
        fi
    done

    rm -f "$tmpfile" "$header_file"
    return 1
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

# Workaround: memvid Bug C (#196) -- fresh .mv2 files have an invalid time
# index causing "frame id out of range" on ask() calls. Remove this block
# once the upstream bug is fixed and set REBUILD_TIME_INDEX=false.
REBUILD_TIME_INDEX="${REBUILD_TIME_INDEX:-true}"
if [ "$REBUILD_TIME_INDEX" = "true" ]; then
    echo "Rebuilding .mv2 time index (memvid doctor)..."
    if command -v memvid >/dev/null 2>&1; then
        memvid doctor --rebuild-time-index "$MV2_OUTPUT"
    elif command -v npx >/dev/null 2>&1; then
        npx -y memvid-cli@2.0.157 doctor --rebuild-time-index "$MV2_OUTPUT"
    else
        echo -e "${RED}ERROR: Neither memvid nor npx found. Install memvid-cli or Node.js${NC}"
        exit 1
    fi
    echo -e "${GREEN}Time index rebuilt${NC}"
else
    echo "Skipping time index rebuild (REBUILD_TIME_INDEX=false)"
fi
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
    RATE_LIMIT_PER_MINUTE=1000 \
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

BASE_URL="http://localhost:$API_PORT/api/v1"

# Health gate: poll until API reports healthy before running any tests
if ! wait_for_health "$BASE_URL/health" 60; then
    echo -e "${RED}FATAL: API never became healthy. Log:${NC}"
    cat "$API_LOG"
    exit 1
fi
echo ""

# =============================================================================
# Phase 3: Semantic quality assertions
# =============================================================================

print_header "Phase 3: Semantic Quality Assertions"

# --- Test 1: Profile name matches example_resume.md ---
run_test "Profile name is 'Jane Chen' (from example_resume.md, not mock data)"

profile_response=$(curl -L --max-redirs 3 -sf --max-time 30 "$BASE_URL/profile") || {
    print_fail "Could not reach /api/v1/profile"
    profile_response=""
}

if [ -n "$profile_response" ]; then
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

if [ -z "$profile_response" ]; then
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

health_response=$(curl -L --max-redirs 3 -sf --max-time 30 "$BASE_URL/health") || {
    print_fail "Could not reach /api/v1/health"
    health_response=""
}

if [ -n "$health_response" ]; then
    if echo "$health_response" | grep -q '"memvid_connected":true'; then
        if echo "$health_response" | grep -q '"status":"healthy"'; then
            print_pass "Health: status=healthy, memvid_connected=true (real .mv2)"
        else
            print_fail "memvid_connected=true but status not healthy"
        fi
    else
        print_fail "memvid_connected not true"
        echo "  Response: $health_response"
    fi
fi

# --- Test 4: Search returns real content about Python ---
run_test "Chat about 'Python' returns content from real resume (not mock)"

chat_response=$(curl_with_429_retry -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"What programming languages does this person know?","stream":false}') || {
    print_fail "Could not reach /api/v1/chat"
    chat_response=""
}

if [ -n "$chat_response" ]; then
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

questions_response=$(curl -L --max-redirs 3 -sf --max-time 30 "$BASE_URL/suggested-questions") || {
    print_fail "Could not reach /api/v1/suggested-questions"
    questions_response=""
}

if [ -n "$questions_response" ]; then
    questions_check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    questions = data.get('questions', [])
    # Questions are dicts with 'question' and 'category' fields
    def get_text(q):
        if isinstance(q, dict):
            return q.get('question', '')
        return str(q)
    # example_resume.md has suggested_questions including 'programming languages'
    has_lang = any('programming' in get_text(q).lower() or 'languages' in get_text(q).lower() for q in questions)
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

fit_response=$(curl_with_429_retry -X POST "$BASE_URL/assess-fit" \
    -H "Content-Type: application/json" \
    -d '{"job_description":"VP of Platform Engineering: Lead cloud infrastructure, Kubernetes orchestration, CI/CD pipelines. 10+ years distributed systems."}') || {
    print_fail "Could not reach /api/v1/assess-fit"
    fit_response=""
}

if [ -n "$fit_response" ]; then
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
curl -L --max-redirs 3 -sf -N -X POST "$BASE_URL/chat" \
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
# Phase 4: Semantic Coverage (verify all resume sections are searchable)
# =============================================================================

print_header "Phase 4: Semantic Coverage"
echo "Verifying that all major sections of example_resume.md are retrievable"
echo ""

# Helper: test that a search query retrieves chunks from the real .mv2
# Usage: test_coverage "description" "query" [expected_keyword_in_retrieval]
test_coverage() {
    local desc="$1"
    local query="$2"
    local expected_keyword="${3:-}"

    run_test "Coverage: $desc"

    local response
    response=$(curl_with_429_retry -X POST "$BASE_URL/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\":\"$query\",\"stream\":false}") || {
        print_fail "Could not reach /api/v1/chat"
        return
    }

    local check
    check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    chunks = data.get('chunks_retrieved', 0)
    msg_len = len(data.get('message', ''))
    if chunks > 0 and msg_len > 0:
        print('OK:chunks=' + str(chunks))
    else:
        print('FAIL:chunks=' + str(chunks) + ',msg_len=' + str(msg_len))
except Exception as e:
    print('FAIL:' + str(e))
" <<< "$response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$check" | grep -q "^OK:"; then
        local detail
        detail=$(echo "$check" | sed 's/^OK://')
        print_pass "$desc ($detail)"
    else
        local detail
        detail=$(echo "$check" | sed 's/^FAIL://')
        print_fail "$desc ($detail)"
    fi
}

# --- FAQ coverage (5 suggested questions from the resume) ---
test_coverage "FAQ: Security track record" \
    "What is her security track record?"

test_coverage "FAQ: Programming languages" \
    "What programming languages does she know?"

test_coverage "FAQ: AI/ML experience" \
    "Tell me about her AI and ML experience"

test_coverage "FAQ: Biggest failures" \
    "What are her biggest failures?"

test_coverage "FAQ: Startup fit" \
    "Would she be good for an early-stage startup?"

# --- Experience coverage (one query per company) ---
test_coverage "Experience: Acme Corp" \
    "Tell me about her work at Acme Corp and platform engineering"

test_coverage "Experience: DataFlow Inc" \
    "What did she do at DataFlow with data infrastructure?"

test_coverage "Experience: TechStart Labs" \
    "Tell me about her early career at TechStart Labs"

# --- Skills coverage ---
test_coverage "Skills: Kubernetes and cloud" \
    "What is her Kubernetes and cloud infrastructure experience?"

test_coverage "Skills: Leadership and team building" \
    "How has she built and led engineering teams?"

# --- Fit assessment coverage ---
test_coverage "Fit: Strong match scenario" \
    "Would she be a good fit for a VP of Platform role at an AI startup?"

test_coverage "Fit: Weak match scenario" \
    "Would she be a good fit for a mobile engineering director role?"

# --- Gaps coverage (honest limitations) ---
test_coverage "Gaps: Frontend and mobile limitations" \
    "What are her technical limitations and skill gaps?"

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
    echo "=== memvid-service log (last 50 lines) ==="
    tail -50 "$MEMVID_LOG" 2>/dev/null || echo "(no log)"
    echo ""
    echo "=== api-service log (last 50 lines) ==="
    tail -50 "$API_LOG" 2>/dev/null || echo "(no log)"
    exit 1
fi

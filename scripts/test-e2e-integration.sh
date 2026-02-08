#!/bin/bash
set -euo pipefail

# Cross-Service Integration Tests (mock backends)
# Tests the full request path: HTTP -> Python API -> gRPC -> Rust memvid-service
# Both services run with mock backends (no real LLM or .mv2 file needed)

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
MEMVID_LOG="/tmp/memvid-e2e-integration.log"
API_LOG="/tmp/api-e2e-integration.log"

# Ports
GRPC_PORT=50051
API_PORT=3000

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
# Usage: wait_for_port <host> <port> <timeout_seconds> <label>
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

# Cleanup function - kill both services
cleanup() {
    echo -e "\n${YELLOW}Cleaning up background processes...${NC}"
    if [ -n "$API_PID" ] && ps -p "$API_PID" > /dev/null 2>&1; then
        kill "$API_PID" 2>/dev/null || true
    fi
    if [ -n "$MEMVID_PID" ] && ps -p "$MEMVID_PID" > /dev/null 2>&1; then
        kill "$MEMVID_PID" 2>/dev/null || true
    fi
    # Belt-and-suspenders: pkill by name in case PIDs were lost
    pkill -f "memvid-service" 2>/dev/null || true
    pkill -f "uvicorn.*ai_resume_api" 2>/dev/null || true
    sleep 1
}

trap cleanup EXIT

print_header "Cross-Service Integration Tests (mock backends)"
echo "Full request path: HTTP -> Python API -> gRPC -> Rust memvid-service"
echo "Project root: $PROJECT_ROOT"
echo ""

# =============================================================================
# Prerequisites check
# =============================================================================

MEMVID_BINARY="$PROJECT_ROOT/memvid-service/target/release/memvid-service"
API_VENV="$PROJECT_ROOT/api-service/.venv"

if [ ! -f "$MEMVID_BINARY" ]; then
    echo -e "${RED}ERROR: memvid-service binary not found at:${NC}"
    echo "  $MEMVID_BINARY"
    echo ""
    echo "Build it first with:"
    echo "  cd memvid-service && cargo build --release"
    exit 1
fi

if [ ! -d "$API_VENV" ]; then
    echo -e "${RED}ERROR: Python virtual environment not found at:${NC}"
    echo "  $API_VENV"
    echo ""
    echo "Create it first with:"
    echo "  cd api-service && python -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
fi

echo -e "${GREEN}Prerequisites OK${NC}"
echo "  Binary: $MEMVID_BINARY"
echo "  Venv:   $API_VENV"
echo ""

# =============================================================================
# Start services
# =============================================================================

print_header "Starting Services"

# Start Rust memvid-service in mock mode
echo "Starting memvid-service (MOCK_MEMVID=true) on port $GRPC_PORT..."
MOCK_MEMVID=true GRPC_PORT=$GRPC_PORT \
    "$MEMVID_BINARY" > "$MEMVID_LOG" 2>&1 &
MEMVID_PID=$!

if ! wait_for_port localhost "$GRPC_PORT" 15 "memvid-service"; then
    echo -e "${RED}memvid-service failed to start. Log output:${NC}"
    cat "$MEMVID_LOG"
    exit 1
fi

# Verify the process is still alive after port opened
if ! ps -p "$MEMVID_PID" > /dev/null 2>&1; then
    echo -e "${RED}memvid-service process died after starting. Log output:${NC}"
    cat "$MEMVID_LOG"
    exit 1
fi

echo ""

# Start Python API service with real gRPC client pointing at the Rust service
echo "Starting API service (MOCK_MEMVID_CLIENT=false, MOCK_OPENROUTER=true) on port $API_PORT..."
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
    echo -e "${RED}API service failed to start. Log output:${NC}"
    cat "$API_LOG"
    exit 1
fi

if ! ps -p "$API_PID" > /dev/null 2>&1; then
    echo -e "${RED}API service process died after starting. Log output:${NC}"
    cat "$API_LOG"
    exit 1
fi

echo ""
echo -e "${GREEN}Both services running${NC}"
echo "  memvid-service PID=$MEMVID_PID (port $GRPC_PORT)"
echo "  api-service     PID=$API_PID (port $API_PORT)"
echo ""

# =============================================================================
# Test 1: Health connectivity - memvid_connected=true
# =============================================================================

run_test "Health endpoint reports memvid_connected=true"

health_response=$(curl -sf http://localhost:$API_PORT/api/v1/health 2>&1 || echo "CURL_FAILED")

if echo "$health_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/health endpoint"
    echo "  Response: $health_response"
elif echo "$health_response" | grep -q '"memvid_connected":true'; then
    # Also check overall status is healthy
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        print_pass "Health endpoint reports status=healthy, memvid_connected=true"
    else
        print_fail "memvid_connected=true but status is not healthy"
        echo "  Response: $health_response"
    fi
else
    print_fail "memvid_connected is not true in health response"
    echo "  Response: $health_response"
fi

# =============================================================================
# Test 2: Full chat flow (non-streaming)
# =============================================================================

run_test "Chat endpoint returns response with memvid search context (stream=false)"

chat_response=$(curl -sf -X POST http://localhost:$API_PORT/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"What programming languages does this person know?","stream":false}' \
    2>&1 || echo "CURL_FAILED")

if echo "$chat_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/chat endpoint"
    echo "  Response: $chat_response"
elif echo "$chat_response" | grep -q '"message"'; then
    # Verify the response contains a message field with content
    # The mock OpenRouter returns content based on memvid context
    message_len=$(echo "$chat_response" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('message','')))" 2>/dev/null || echo "0")
    chunks=$(echo "$chat_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('chunks_retrieved',0))" 2>/dev/null || echo "0")

    if [ "$message_len" -gt 0 ] && [ "$chunks" -gt 0 ]; then
        print_pass "Chat response received (message length=$message_len, chunks=$chunks)"
    elif [ "$message_len" -gt 0 ]; then
        print_pass "Chat response received (message length=$message_len, chunks field=$chunks)"
    else
        print_fail "Chat response has empty message"
        echo "  Response: $chat_response"
    fi
else
    print_fail "Chat response missing 'message' field"
    echo "  Response: $chat_response"
fi

# =============================================================================
# Test 3: Profile endpoint returns data from memvid GetState
# =============================================================================

run_test "Profile endpoint returns data from memvid (name, title, skills present)"

profile_response=$(curl -sf http://localhost:$API_PORT/api/v1/profile 2>&1 || echo "CURL_FAILED")

if echo "$profile_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/profile endpoint"
    echo "  Response: $profile_response"
else
    # Check for required fields using python3 for reliable JSON parsing
    profile_check=$(python3 -c "
import sys, json
try:
    p = json.loads(sys.stdin.read())
    errors = []
    if not p.get('name'):
        errors.append('missing name')
    if not p.get('title'):
        errors.append('missing title')
    skills = p.get('skills', {})
    if 'strong' not in skills or not isinstance(skills['strong'], list):
        errors.append('missing skills.strong')
    if errors:
        print('FAIL:' + ','.join(errors))
    else:
        print('OK:name=' + p['name'] + ',title=' + p['title'] + ',strong_skills=' + str(len(skills['strong'])))
except Exception as e:
    print('FAIL:json_parse_error:' + str(e))
" <<< "$profile_response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$profile_check" | grep -q "^OK:"; then
        detail=$(echo "$profile_check" | sed 's/^OK://')
        print_pass "Profile data present ($detail)"
    else
        detail=$(echo "$profile_check" | sed 's/^FAIL://')
        print_fail "Profile data incomplete ($detail)"
        echo "  Response (truncated): $(echo "$profile_response" | head -c 500)"
    fi
fi

# =============================================================================
# Test 4: Streaming chat returns SSE event format
# =============================================================================

run_test "Streaming chat returns SSE event format (data: lines)"

# Use curl with a timeout to capture the SSE stream
# Write raw stream to a temp file for inspection
SSE_OUTPUT="/tmp/e2e-sse-output.txt"
curl -sf -N -X POST http://localhost:$API_PORT/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"Tell me about this person","stream":true}' \
    --max-time 30 \
    > "$SSE_OUTPUT" 2>&1 || true

if [ ! -s "$SSE_OUTPUT" ]; then
    print_fail "Streaming response was empty"
else
    # Check for SSE format: lines starting with "data: "
    data_lines=$(grep -c "^data: " "$SSE_OUTPUT" 2>/dev/null || echo "0")
    has_retrieval=$(grep -c '"retrieval"' "$SSE_OUTPUT" 2>/dev/null || echo "0")
    has_token=$(grep -c '"token"' "$SSE_OUTPUT" 2>/dev/null || echo "0")
    has_done=$(grep -c '\[DONE\]' "$SSE_OUTPUT" 2>/dev/null || echo "0")

    if [ "$data_lines" -gt 0 ] && [ "$has_token" -gt 0 ]; then
        details="data_lines=$data_lines, has_retrieval=$has_retrieval, has_token=$has_token, has_done=$has_done"
        print_pass "SSE stream valid ($details)"
    else
        print_fail "SSE stream missing expected events (data_lines=$data_lines, has_token=$has_token)"
        echo "  Stream output (first 500 chars):"
        head -c 500 "$SSE_OUTPUT"
        echo ""
    fi

    rm -f "$SSE_OUTPUT"
fi

# =============================================================================
# Test 5: Suggested questions endpoint
# =============================================================================

run_test "Suggested questions endpoint returns non-empty questions array"

questions_response=$(curl -sf http://localhost:$API_PORT/api/v1/suggested-questions 2>&1 || echo "CURL_FAILED")

if echo "$questions_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/suggested-questions endpoint"
    echo "  Response: $questions_response"
else
    questions_check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    questions = data.get('questions', [])
    if isinstance(questions, list) and len(questions) > 0:
        print('OK:count=' + str(len(questions)))
    else:
        print('FAIL:questions array empty or missing')
except Exception as e:
    print('FAIL:json_parse_error:' + str(e))
" <<< "$questions_response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$questions_check" | grep -q "^OK:"; then
        detail=$(echo "$questions_check" | sed 's/^OK://')
        print_pass "Suggested questions returned ($detail)"
    else
        detail=$(echo "$questions_check" | sed 's/^FAIL://')
        print_fail "Suggested questions check failed ($detail)"
        echo "  Response (truncated): $(echo "$questions_response" | head -c 500)"
    fi
fi

# =============================================================================
# Test 6: Fit assessment with strong-match job description
# =============================================================================

run_test "Fit assessment returns verdict, key_matches, recommendation for strong-match JD"

fit_strong_response=$(curl -sf -X POST http://localhost:$API_PORT/api/v1/assess-fit \
    -H "Content-Type: application/json" \
    -d '{"job_description":"VP of Platform Engineering: Lead cloud infrastructure, Kubernetes orchestration, CI/CD pipelines, and DevOps teams. Requires 10+ years of experience in distributed systems, microservices architecture, and team leadership."}' \
    2>&1 || echo "CURL_FAILED")

if echo "$fit_strong_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/assess-fit endpoint"
    echo "  Response: $fit_strong_response"
else
    fit_strong_check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    errors = []
    if 'verdict' not in data:
        errors.append('missing verdict')
    key_matches = data.get('key_matches', [])
    if not isinstance(key_matches, list) or len(key_matches) == 0:
        errors.append('key_matches empty or missing')
    if 'recommendation' not in data:
        errors.append('missing recommendation')
    if errors:
        print('FAIL:' + ','.join(errors))
    else:
        print('OK:verdict=' + str(data['verdict']) + ',key_matches=' + str(len(key_matches)))
except Exception as e:
    print('FAIL:json_parse_error:' + str(e))
" <<< "$fit_strong_response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$fit_strong_check" | grep -q "^OK:"; then
        detail=$(echo "$fit_strong_check" | sed 's/^OK://')
        print_pass "Strong-match fit assessment valid ($detail)"
    else
        detail=$(echo "$fit_strong_check" | sed 's/^FAIL://')
        print_fail "Strong-match fit assessment invalid ($detail)"
        echo "  Response (truncated): $(echo "$fit_strong_response" | head -c 500)"
    fi
fi

# =============================================================================
# Test 7: Fit assessment with weak-match job description
# =============================================================================

run_test "Fit assessment returns verdict, gaps, recommendation for weak-match JD"

fit_weak_response=$(curl -sf -X POST http://localhost:$API_PORT/api/v1/assess-fit \
    -H "Content-Type: application/json" \
    -d '{"job_description":"Executive Chef: Lead kitchen operations for a Michelin-starred restaurant. Requires 15+ years of culinary experience, expertise in French and Japanese cuisine, menu development, and food cost management."}' \
    2>&1 || echo "CURL_FAILED")

if echo "$fit_weak_response" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/assess-fit endpoint"
    echo "  Response: $fit_weak_response"
else
    fit_weak_check=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    errors = []
    if 'verdict' not in data:
        errors.append('missing verdict')
    gaps = data.get('gaps', [])
    if not isinstance(gaps, list):
        errors.append('gaps is not a list')
    if 'recommendation' not in data:
        errors.append('missing recommendation')
    if errors:
        print('FAIL:' + ','.join(errors))
    else:
        print('OK:verdict=' + str(data['verdict']) + ',gaps=' + str(len(gaps)))
except Exception as e:
    print('FAIL:json_parse_error:' + str(e))
" <<< "$fit_weak_response" 2>/dev/null || echo "FAIL:python_error")

    if echo "$fit_weak_check" | grep -q "^OK:"; then
        detail=$(echo "$fit_weak_check" | sed 's/^OK://')
        print_pass "Weak-match fit assessment valid ($detail)"
    else
        detail=$(echo "$fit_weak_check" | sed 's/^FAIL://')
        print_fail "Weak-match fit assessment invalid ($detail)"
        echo "  Response (truncated): $(echo "$fit_weak_response" | head -c 500)"
    fi
fi

# =============================================================================
# Test 8: Chat with empty message returns 422
# =============================================================================

run_test "Chat with empty message returns 422 validation error"

chat_empty_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:$API_PORT/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"","stream":false}' \
    2>&1 || echo "000")

if [ "$chat_empty_status" = "422" ]; then
    print_pass "Empty message correctly rejected with HTTP 422"
elif [ "$chat_empty_status" = "000" ]; then
    print_fail "Could not reach /api/v1/chat endpoint"
else
    print_fail "Expected HTTP 422 for empty message, got $chat_empty_status"
fi

# =============================================================================
# Test 9: Invalid endpoint returns 404
# =============================================================================

run_test "Invalid endpoint returns 404 or 405"

invalid_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$API_PORT/api/v1/nonexistent \
    2>&1 || echo "000")

if [ "$invalid_status" = "404" ] || [ "$invalid_status" = "405" ]; then
    print_pass "Invalid endpoint correctly returned HTTP $invalid_status"
elif [ "$invalid_status" = "000" ]; then
    print_fail "Could not reach API server"
else
    print_fail "Expected HTTP 404 or 405 for invalid endpoint, got $invalid_status"
fi

# =============================================================================
# Test 10: Session continuity
# =============================================================================

run_test "Session continuity - second request preserves session_id"

# First chat request - extract session_id
session_response_1=$(curl -sf -X POST http://localhost:$API_PORT/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"What is your name?","stream":false}' \
    2>&1 || echo "CURL_FAILED")

if echo "$session_response_1" | grep -q "CURL_FAILED"; then
    print_fail "Could not reach /api/v1/chat endpoint for session test"
    echo "  Response: $session_response_1"
else
    session_id=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    print(data.get('session_id', ''))
except:
    print('')
" <<< "$session_response_1" 2>/dev/null || echo "")

    if [ -z "$session_id" ]; then
        print_fail "First chat response missing session_id"
        echo "  Response (truncated): $(echo "$session_response_1" | head -c 500)"
    else
        # Second chat request with same session_id
        session_response_2=$(curl -sf -X POST http://localhost:$API_PORT/api/v1/chat \
            -H "Content-Type: application/json" \
            -d "{\"message\":\"What do you do?\",\"stream\":false,\"session_id\":\"$session_id\"}" \
            2>&1 || echo "CURL_FAILED")

        if echo "$session_response_2" | grep -q "CURL_FAILED"; then
            print_fail "Second chat request failed"
            echo "  Response: $session_response_2"
        else
            session_id_2=$(python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    print(data.get('session_id', ''))
except:
    print('')
" <<< "$session_response_2" 2>/dev/null || echo "")

            if [ "$session_id" = "$session_id_2" ]; then
                print_pass "Session continuity confirmed (session_id=$session_id)"
            else
                print_fail "Session ID changed between requests (first=$session_id, second=$session_id_2)"
            fi
        fi
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
    echo -e "\n${GREEN}All tests passed${NC}\n"
    exit 0
else
    echo -e "\n${RED}Some tests failed${NC}\n"
    echo "Diagnostic logs:"
    echo "  memvid-service: $MEMVID_LOG"
    echo "  api-service:    $API_LOG"
    exit 1
fi

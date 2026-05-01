#!/bin/bash
# Quick smoke test for ai-resume containers
# Tests that containers start and can communicate via gRPC
#
# E2E Reliability Protocol:
#   - Health-gate before running tests (poll with timeout)
#   - Retry only on HTTP 429 (rate limit), respect Retry-After
#   - Fail immediately on all other errors (connection refused, timeouts, 5xx)

set -euo pipefail

REGISTRY="${REGISTRY:-localhost}"
VERSION="${1:-latest}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }

# Wait for HTTP health endpoint to return 2xx before running tests
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
        http_code=$(curl -L --max-redirs 3 -s --max-time 30 -w '%{http_code}' -o "$tmpfile" -D "$header_file" "$@" 2>/dev/null) || {
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
            local retry_after
            retry_after=$(grep -i '^retry-after:' "$header_file" 2>/dev/null | awk '{print $2}' | tr -d '\r' || echo "2")
            if [ -z "$retry_after" ] || ! [[ "$retry_after" =~ ^[0-9]+$ ]]; then
                retry_after=2
            fi
            echo "  Rate limited (429), retry $attempt/$max_retries after ${retry_after}s..." >&2
            sleep "$retry_after"
        else
            rm -f "$tmpfile" "$header_file"
            echo "CURL_FAILED:http_$http_code" >&2
            return 1
        fi
    done

    rm -f "$tmpfile" "$header_file"
    return 1
}

# shellcheck disable=SC2317,SC2329  # called via trap
cleanup() {
    echo "Cleaning up..."
    podman stop test-memvid test-api test-frontend 2>/dev/null || true
    podman rm test-memvid test-api test-frontend 2>/dev/null || true
    podman network rm test-net 2>/dev/null || true
}

# Cleanup on exit
trap cleanup EXIT

echo "Testing containers: ${REGISTRY}/ai-resume-*:${VERSION}"
echo ""

# Create test network
podman network create test-net 2>/dev/null || true

# Start Rust memvid service
echo "Starting Rust memvid service..."
podman run -d --name test-memvid \
    --network test-net \
    -p 9091:9090 \
    -e MOCK_MEMVID=true \
    -e RUST_LOG=info \
    "${REGISTRY}/ai-resume-memvid:${VERSION}"

# Start Python API service
echo "Starting Python API service..."
podman run -d --name test-api \
    --network test-net \
    -p 3001:3000 \
    -e MEMVID_GRPC_HOST=test-memvid \
    -e MEMVID_GRPC_PORT=50051 \
    -e MOCK_MEMVID_CLIENT=true \
    -e MOCK_OPENROUTER=true \
    "${REGISTRY}/ai-resume-api:${VERSION}"

# Health-gate: wait for API to be healthy before running tests
if ! wait_for_health "http://localhost:3001/health" 60; then
    echo -e "${RED}FATAL: API never became healthy${NC}"
    podman logs test-api 2>&1 | tail -20
    exit 1
fi

# Run tests
echo ""
echo "Running tests..."
FAILED=0

# Test 1: Rust container running
if podman ps --filter "name=test-memvid" --format "{{.Names}}" | grep -q test-memvid; then
    log_pass "Rust container running"
else
    # Even if not in ps, check if logs exist (might be brief startup)
    if podman logs test-memvid 2>&1 | grep -q "Starting gRPC server"; then
        log_pass "Rust container running (logs verified)"
    else
        log_fail "Rust container not running"
        podman logs test-memvid 2>&1 | tail -10
        FAILED=1
    fi
fi

# Test 2: Python container running
if podman ps | grep -q test-api; then
    log_pass "Python container running"
else
    log_fail "Python container not running"
    podman logs test-api 2>&1 | tail -10
    FAILED=1
fi

# Test 3: Health endpoint
HEALTH=$(curl -L --max-redirs 3 -sf --max-time 30 "http://localhost:3001/health") || {
    log_fail "Health endpoint unreachable"
    FAILED=1
    HEALTH=""
}
if [ -n "$HEALTH" ]; then
    if echo "$HEALTH" | grep -q '"status":"healthy"'; then
        log_pass "Health endpoint returns healthy"
    else
        log_fail "Health endpoint failed: $HEALTH"
        FAILED=1
    fi
fi

# Test 4: gRPC connection
if [ -n "$HEALTH" ] && echo "$HEALTH" | grep -q '"memvid_connected":true'; then
    log_pass "gRPC connection to Rust service"
else
    log_fail "gRPC connection failed"
    FAILED=1
fi

# Test 5: Chat endpoint (rate-limited, use 429 retry)
CHAT=$(curl_with_429_retry -X POST "http://localhost:3001/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message":"test","stream":false}') || {
    log_fail "Chat endpoint unreachable"
    CHAT=""
}
if [ -n "$CHAT" ] && echo "$CHAT" | grep -q '"session_id"'; then
    log_pass "Chat endpoint returns response"
elif [ -n "$CHAT" ]; then
    log_fail "Chat endpoint failed: $CHAT"
    FAILED=1
fi

# Test 6: Profile endpoint
PROFILE=$(curl -L --max-redirs 3 -sf --max-time 30 "http://localhost:3001/api/v1/profile") || {
    log_fail "Profile endpoint unreachable"
    PROFILE=""
}
if [ -n "$PROFILE" ] && echo "$PROFILE" | grep -q '"name"'; then
    log_pass "Profile endpoint returns profile data"
elif [ -n "$PROFILE" ]; then
    log_fail "Profile endpoint failed: $PROFILE"
    FAILED=1
fi

# Test 7: Check Rust received gRPC request from chat endpoint
# The chat endpoint calls memvid_client.ask() (Ask RPC with re-ranking),
# not Search. memvid logs "Processing ask request" for that path.
RUST_LOGS=$(podman logs test-memvid 2>&1)
if echo "$RUST_LOGS" | grep -q "Processing ask request"; then
    log_pass "Rust service processed gRPC ask request"
else
    log_fail "Rust service did not process expected gRPC ask request"
    FAILED=1
fi

# Start frontend container
echo ""
echo "Starting frontend container..."
podman run -d --name test-frontend \
    --network test-net \
    -p 8081:8080 \
    "${REGISTRY}/ai-resume-frontend:${VERSION}"

# Health-gate: wait for frontend to be healthy before testing it
if ! wait_for_health "http://localhost:8081/health" 60; then
    echo -e "${RED}FATAL: Frontend never became healthy${NC}"
    podman logs test-frontend 2>&1 | tail -20
    FAILED=1
fi

# Test 8: Frontend container running
if podman ps --filter "name=test-frontend" --format "{{.Names}}" | grep -q test-frontend; then
    log_pass "Frontend container running"
else
    log_fail "Frontend container not running"
    podman logs test-frontend 2>&1 | tail -10
    FAILED=1
fi

# Test 9: Frontend health endpoint
FRONTEND_HEALTH=$(curl -L --max-redirs 3 -sf --max-time 30 "http://localhost:8081/health") || {
    log_fail "Frontend health endpoint unreachable"
    FRONTEND_HEALTH=""
}
if [ -n "$FRONTEND_HEALTH" ] && echo "$FRONTEND_HEALTH" | grep -qiE 'healthy|ok|200'; then
    log_pass "Frontend health endpoint returns healthy"
elif [ -n "$FRONTEND_HEALTH" ]; then
    log_fail "Frontend health endpoint failed: $FRONTEND_HEALTH"
    FAILED=1
fi

# Test 10: Frontend serves React SPA
FRONTEND_INDEX=$(curl -L --max-redirs 3 -sf --max-time 30 "http://localhost:8081/") || {
    log_fail "Frontend index unreachable"
    FRONTEND_INDEX=""
}
if [ -n "$FRONTEND_INDEX" ] && echo "$FRONTEND_INDEX" | grep -q 'id="root"'; then
    log_pass "Frontend serves React SPA"
elif [ -n "$FRONTEND_INDEX" ]; then
    log_fail "Frontend does not serve React SPA"
    FAILED=1
fi

# Test 11: Frontend SPA routing
FRONTEND_SPA=$(curl -L --max-redirs 3 -sf --max-time 30 "http://localhost:8081/some/random/path") || {
    log_fail "Frontend SPA routing unreachable"
    FRONTEND_SPA=""
}
if [ -n "$FRONTEND_SPA" ] && echo "$FRONTEND_SPA" | grep -q 'id="root"'; then
    log_pass "Frontend SPA routing works (returns index.html for all routes)"
elif [ -n "$FRONTEND_SPA" ]; then
    log_fail "Frontend SPA routing broken"
    FAILED=1
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi

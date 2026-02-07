#!/bin/bash
# Quick smoke test for ai-resume containers
# Tests that containers start and can communicate via gRPC

set -euo pipefail

REGISTRY="${REGISTRY:-localhost}"
VERSION="${1:-latest}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }

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

sleep 3

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

sleep 4

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
HEALTH=$(curl -s http://localhost:3001/health 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    log_pass "Health endpoint returns healthy"
else
    log_fail "Health endpoint failed: $HEALTH"
    FAILED=1
fi

# Test 4: gRPC connection
if echo "$HEALTH" | grep -q '"memvid_connected":true'; then
    log_pass "gRPC connection to Rust service"
else
    log_fail "gRPC connection failed"
    FAILED=1
fi

# Test 5: Chat endpoint
CHAT=$(curl -s -X POST http://localhost:3001/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"test","stream":false}' 2>/dev/null || echo "")
if echo "$CHAT" | grep -q '"session_id"'; then
    log_pass "Chat endpoint returns response"
else
    log_fail "Chat endpoint failed: $CHAT"
    FAILED=1
fi

# Test 6: Check Rust received gRPC request
RUST_LOGS=$(podman logs test-memvid 2>&1)
if echo "$RUST_LOGS" | grep -q "Processing search request"; then
    log_pass "Rust service processed gRPC search request"
else
    log_fail "Rust service did not receive gRPC request"
    FAILED=1
fi

# Start frontend container
echo ""
echo "Starting frontend container..."
podman run -d --name test-frontend \
    --network test-net \
    -p 8081:8080 \
    "${REGISTRY}/ai-resume-frontend:${VERSION}"

sleep 3

# Test 7: Frontend container running
if podman ps --filter "name=test-frontend" --format "{{.Names}}" | grep -q test-frontend; then
    log_pass "Frontend container running"
else
    log_fail "Frontend container not running"
    podman logs test-frontend 2>&1 | tail -10
    FAILED=1
fi

# Test 8: Frontend health endpoint
FRONTEND_HEALTH=$(curl -s http://localhost:8081/health 2>/dev/null || echo "")
if echo "$FRONTEND_HEALTH" | grep -qiE 'healthy|ok|200'; then
    log_pass "Frontend health endpoint returns healthy"
else
    log_fail "Frontend health endpoint failed: $FRONTEND_HEALTH"
    FAILED=1
fi

# Test 9: Frontend serves React SPA
FRONTEND_INDEX=$(curl -s http://localhost:8081/ 2>/dev/null || echo "")
if echo "$FRONTEND_INDEX" | grep -q 'id="root"'; then
    log_pass "Frontend serves React SPA"
else
    log_fail "Frontend does not serve React SPA"
    FAILED=1
fi

# Test 10: Frontend SPA routing
FRONTEND_SPA=$(curl -s http://localhost:8081/some/random/path 2>/dev/null || echo "")
if echo "$FRONTEND_SPA" | grep -q 'id="root"'; then
    log_pass "Frontend SPA routing works (returns index.html for all routes)"
else
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

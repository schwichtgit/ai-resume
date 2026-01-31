#!/bin/bash
# End-to-end integration test using podman-compose with real resume.mv2
# Tests the full stack: memvid service + API service + frontend
#
# Prerequisites:
#   - deployment/.env configured with OPENROUTER_API_KEY
#   - resume.mv2 created via ingest
#   - podman-compose installed in deployment/.venv

set -uo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

# Check prerequisites
log_info "Checking prerequisites..."

if [ ! -f "$DEPLOYMENT_DIR/.env" ]; then
    log_fail "deployment/.env not found"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/data/.memvid/resume.mv2" ]; then
    log_fail "data/.memvid/resume.mv2 not found"
    exit 1
fi

# Source deployment venv
log_info "Sourcing deployment environment..."
if [ ! -d "$DEPLOYMENT_DIR/.venv" ]; then
    log_fail "deployment/.venv not found"
    exit 1
fi

source "$DEPLOYMENT_DIR/.venv/bin/activate"

if ! command -v podman-compose &> /dev/null; then
    log_fail "podman-compose not found"
    exit 1
fi

# Create network if it doesn't exist
log_info "Setting up podman network..."
if ! podman network exists yellow-net; then
    podman network create yellow-net --subnet 192.168.100.0/24 --gateway 192.168.100.1 2>/dev/null || true
fi

# Load deployment .env and set variables
cd "$DEPLOYMENT_DIR"
export $(grep -v '^#' .env | xargs)
export PROJECT_BASE_DIR="$PROJECT_ROOT"

log_info "Configuration:"
echo "  Resume file: $PROJECT_BASE_DIR/data/.memvid/resume.mv2"
echo "  LLM Model: ${LLM_MODEL:-nvidia/nemotron-nano-9b-v2:free}"
echo "  Registry: ${REGISTRY:-localhost}"
echo ""

# Cleanup function
cleanup() {
    log_info "Stopping services..."
    podman-compose down 2>/dev/null || true
}

trap cleanup EXIT

# Start services
log_info "Starting services with podman-compose..."
podman-compose up -d

# Wait for services to be healthy
log_info "Waiting for services to become healthy..."
MAX_WAIT=60
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(podman ps --filter "name=ai-resume-" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "")

    MEMVID_HEALTHY=$(echo "$STATUS" | grep "ai-resume-memvid" | grep -q "(healthy)" && echo "yes" || echo "no")
    API_HEALTHY=$(echo "$STATUS" | grep "ai-resume-api" | grep -q "(healthy)" && echo "yes" || echo "no")
    FRONTEND_HEALTHY=$(echo "$STATUS" | grep "ai-resume-frontend" | grep -q "(healthy)" && echo "yes" || echo "no")

    if [ "$MEMVID_HEALTHY" = "yes" ] && [ "$API_HEALTHY" = "yes" ] && [ "$FRONTEND_HEALTHY" = "yes" ]; then
        break
    fi

    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

echo ""
echo "Service Health Status:"
podman ps --filter "name=ai-resume-" --format "table {{.Names}}\t{{.Status}}"
echo ""

# Verify all services are healthy
MEMVID_CHECK=$(podman ps --filter "name=ai-resume-memvid" --format "{{.Status}}" | grep -q "(healthy)" && echo "yes" || echo "no")
API_CHECK=$(podman ps --filter "name=ai-resume-api" --format "{{.Status}}" | grep -q "(healthy)" && echo "yes" || echo "no")
FRONTEND_CHECK=$(podman ps --filter "name=ai-resume-frontend" --format "{{.Status}}" | grep -q "(healthy)" && echo "yes" || echo "no")

TESTS_PASSED=0
TESTS_FAILED=0

if [ "$MEMVID_CHECK" = "yes" ]; then
    log_pass "Memvid service is healthy"
    ((TESTS_PASSED++))
else
    log_fail "Memvid service is NOT healthy"
    ((TESTS_FAILED++))
fi

if [ "$API_CHECK" = "yes" ]; then
    log_pass "API service is healthy"
    ((TESTS_PASSED++))
else
    log_fail "API service is NOT healthy"
    ((TESTS_FAILED++))
fi

if [ "$FRONTEND_CHECK" = "yes" ]; then
    log_pass "Frontend service is healthy"
    ((TESTS_PASSED++))
else
    log_fail "Frontend service is NOT healthy"
    ((TESTS_FAILED++))
fi

# Integration test: Test API endpoints from host (frontend is exposed on localhost:8080)
log_info "Running integration tests..."

# Give services a moment to fully initialize
sleep 2

# Test API profile endpoint through frontend (localhost:8080)
log_info "Testing API profile endpoint..."
PROFILE=$(curl -s http://localhost:8080/api/v1/profile 2>/dev/null || echo "")
if echo "$PROFILE" | grep -q "name"; then
    log_pass "API profile endpoint working via frontend"
    ((TESTS_PASSED++))
else
    log_fail "API profile endpoint not accessible"
    ((TESTS_FAILED++))
fi

# Verify memvid loaded real data from logs
log_info "Verifying memvid loaded real data..."
MEMVID_LOGS=$(podman-compose logs ai-resume-memvid 2>/dev/null | grep -i "real memvid" || echo "")
if echo "$MEMVID_LOGS" | grep -q "Real memvid"; then
    log_pass "Memvid loaded real resume.mv2 file"
    ((TESTS_PASSED++))
else
    log_fail "Memvid did not load real data"
    ((TESTS_FAILED++))
fi

echo ""
log_info "Test Summary:"
echo "  Passed: $TESTS_PASSED"
echo "  Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    log_pass "All integration tests passed!"
    echo ""
    echo "Services running on:"
    echo "  Frontend: http://localhost:8080"
    echo "  API: http://localhost:3000"
    echo ""
    exit 0
else
    log_fail "Some tests failed"
    echo ""
    echo "Service details:"
    podman ps --filter "name=ai-resume-" --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
    exit 1
fi

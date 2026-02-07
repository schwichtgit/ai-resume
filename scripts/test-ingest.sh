#!/bin/bash
# Run the ingest pipeline against example_resume.md and verify output
# Validates that ingest produces a valid .mv2 file of expected size

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Paths
INGEST_VENV="$PROJECT_ROOT/ingest/.venv"
INPUT_FILE="$PROJECT_ROOT/data/example_resume.md"
OUTPUT_FILE="$PROJECT_ROOT/data/.memvid/test_resume.mv2"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Prerequisite checks
log_info "Checking prerequisites..."

if [ ! -d "$INGEST_VENV" ]; then
    log_fail "Ingest venv not found at $INGEST_VENV"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    log_fail "Input file not found at $INPUT_FILE"
    exit 1
fi

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Remove previous test output if present
rm -f "$OUTPUT_FILE"

# Activate ingest venv
log_info "Activating ingest venv..."
source "$INGEST_VENV/bin/activate"

# Run ingest pipeline
log_info "Running ingest pipeline..."
log_info "  Input:  $INPUT_FILE"
log_info "  Output: $OUTPUT_FILE"
echo ""

if python "$PROJECT_ROOT/ingest/ingest.py" --input "$INPUT_FILE" --output "$OUTPUT_FILE" --verify; then
    log_pass "Ingest pipeline completed successfully"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    log_fail "Ingest pipeline exited with non-zero status"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Verify output file exists
if [ -f "$OUTPUT_FILE" ]; then
    log_pass "Output file exists: $OUTPUT_FILE"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    log_fail "Output file not found: $OUTPUT_FILE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Verify output file size > 100000 bytes
if [ -f "$OUTPUT_FILE" ]; then
    # macOS uses stat -f%z, Linux uses stat -c%s
    FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "0")
    if [ "$FILE_SIZE" -gt 100000 ]; then
        log_pass "Output file size: ${FILE_SIZE} bytes (> 100000)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Output file too small: ${FILE_SIZE} bytes (expected > 100000)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
fi

# Summary
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo ""
log_info "Test Summary: ${TESTS_PASSED}/${TOTAL} passed"

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi

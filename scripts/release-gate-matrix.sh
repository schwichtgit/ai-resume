#!/bin/bash
set -uo pipefail

echo "============================================"
echo "  Release Gate Matrix"
echo "============================================"
echo ""

PASS=0
FAIL=0
REPORT=""

run_gate() {
    local name="$1"
    local cmd="$2"
    local blocking="$3"

    echo "--- $name ---"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "  Result: PASS"
        REPORT="${REPORT}| ${name} | PASS | ${blocking} |\n"
        PASS=$((PASS + 1))
    else
        echo "  Result: FAIL"
        REPORT="${REPORT}| ${name} | FAIL | ${blocking} |\n"
        if [ "$blocking" = "Blocking" ]; then
            FAIL=$((FAIL + 1))
        fi
    fi
    echo ""
}

# Blocking gates
run_gate "Data Coverage (ingest)" \
    "cd ingest && source .venv/bin/activate && python -m pytest tests/test_outcome_data_coverage.py -v --tb=short -m slow 2>/dev/null" \
    "Blocking"

run_gate "Factual Accuracy (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_outcome_factual.py -v --tb=short 2>/dev/null" \
    "Blocking"

run_gate "Negative Testing (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_outcome_negative.py -v --tb=short 2>/dev/null" \
    "Blocking"

run_gate "Honesty & Gaps (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_outcome_honesty.py -v --tb=short 2>/dev/null" \
    "Blocking"

run_gate "Security Guardrails (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_outcome_security.py -v --tb=short 2>/dev/null" \
    "Blocking"

run_gate "Injection Scenarios (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_injection_scenarios.py -v --tb=short 2>/dev/null" \
    "Blocking"

run_gate "Stream Leakage (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_stream_leakage.py -v --tb=short 2>/dev/null" \
    "Blocking"

run_gate "E2E Quality (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_e2e_quality.py -v --tb=short -m e2e 2>/dev/null" \
    "Blocking"

run_gate "Portability" \
    "bash scripts/test-outcome-portability.sh 2>/dev/null" \
    "Blocking"

run_gate "Container Config" \
    "bash scripts/test-outcome-containers.sh 2>/dev/null" \
    "Blocking"

# Non-blocking gates (reported but don't fail the build)
run_gate "Latency NFR (api)" \
    "cd api-service && source .venv/bin/activate && python -m pytest tests/test_outcome_latency.py -v --tb=short -m e2e 2>/dev/null" \
    "Non-blocking"

run_gate "Frontend Tests" \
    "cd frontend && npm test -- --run 2>/dev/null" \
    "Non-blocking"

run_gate "Documentation Audit" \
    "bash scripts/verify-docs.sh 2>/dev/null" \
    "Non-blocking"

# Print report
echo "============================================"
echo "  Release Gate Report"
echo "============================================"
echo ""
echo "| Gate | Result | Type |"
echo "|------|--------|------|"
printf '%s' "$REPORT"
echo ""
echo "Blocking gates: $((PASS > 0 ? PASS : 0)) passed, $FAIL failed"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "RESULT: FAIL -- $FAIL blocking gate(s) did not pass"
    exit 1
fi

echo "RESULT: PASS -- all blocking gates passed"
exit 0

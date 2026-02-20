#!/bin/bash
set -euo pipefail

# Performance profiling for API endpoints
#
# E2E Reliability Protocol:
#   - Health-gate before profiling (poll with timeout)
#   - curl with --max-time to prevent hangs
#   - No blanket error masking

BASE_URL="${1:-http://localhost:8000}"
ITERATIONS="${2:-20}"

echo "=== Performance Profiling ==="
echo "Target: $BASE_URL"
echo "Iterations: $ITERATIONS"
echo ""

# Health-gate: verify service is reachable before profiling
printf "Checking service health..."
HEALTH_TIMEOUT=30
HEALTH_START=$(date +%s)
while true; do
    HEALTH_ELAPSED=$(( $(date +%s) - HEALTH_START ))
    if [ "$HEALTH_ELAPSED" -ge "$HEALTH_TIMEOUT" ]; then
        printf " TIMEOUT after %ds\n" "$HEALTH_TIMEOUT"
        echo "FATAL: Service at $BASE_URL is not healthy. Start the service first."
        exit 1
    fi
    if curl -L --max-redirs 3 -sf --max-time 5 "$BASE_URL/api/v1/health" > /dev/null 2>&1; then
        printf " ready (%ds)\n" "$HEALTH_ELAPSED"
        break
    fi
    sleep 2
done
echo ""

# Collect latency samples for health endpoint
echo "--- Health Endpoint ---"
HEALTH_TIMES=()
for i in $(seq 1 "$ITERATIONS"); do
    START=$(python3 -c "import time; print(time.monotonic())")
    HTTP_CODE=$(curl -L --max-redirs 3 -s --max-time 30 -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/health") || HTTP_CODE="000"
    END=$(python3 -c "import time; print(time.monotonic())")
    if [ "$HTTP_CODE" != "200" ]; then
        echo "  WARNING: iteration $i returned HTTP $HTTP_CODE"
    fi
    ELAPSED=$(python3 -c "print(round(($END - $START) * 1000, 1))")
    HEALTH_TIMES+=("$ELAPSED")
done

# Calculate percentiles
python3 -c "
import statistics
times = [float(t) for t in '${HEALTH_TIMES[*]}'.split()]
times.sort()
n = len(times)
print(f'  Samples: {n}')
print(f'  P50: {times[n//2]:.1f}ms')
print(f'  P95: {times[int(n*0.95)]:.1f}ms')
print(f'  P99: {times[int(n*0.99)]:.1f}ms')
print(f'  Min: {min(times):.1f}ms')
print(f'  Max: {max(times):.1f}ms')
"

# Collect latency samples for profile endpoint
echo ""
echo "--- Profile Endpoint ---"
PROFILE_TIMES=()
for i in $(seq 1 "$ITERATIONS"); do
    START=$(python3 -c "import time; print(time.monotonic())")
    HTTP_CODE=$(curl -L --max-redirs 3 -s --max-time 30 -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/profile") || HTTP_CODE="000"
    END=$(python3 -c "import time; print(time.monotonic())")
    if [ "$HTTP_CODE" != "200" ]; then
        echo "  WARNING: iteration $i returned HTTP $HTTP_CODE"
    fi
    ELAPSED=$(python3 -c "print(round(($END - $START) * 1000, 1))")
    PROFILE_TIMES+=("$ELAPSED")
done

python3 -c "
import statistics
times = [float(t) for t in '${PROFILE_TIMES[*]}'.split()]
times.sort()
n = len(times)
print(f'  Samples: {n}')
print(f'  P50: {times[n//2]:.1f}ms')
print(f'  P95: {times[int(n*0.95)]:.1f}ms')
print(f'  P99: {times[int(n*0.99)]:.1f}ms')
print(f'  Min: {min(times):.1f}ms')
print(f'  Max: {max(times):.1f}ms')
"

echo ""
echo "=== Profiling Complete ==="

#!/bin/bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
ITERATIONS="${2:-20}"

echo "=== Performance Profiling ==="
echo "Target: $BASE_URL"
echo "Iterations: $ITERATIONS"
echo ""

# Collect latency samples for health endpoint
echo "--- Health Endpoint ---"
HEALTH_TIMES=()
for i in $(seq 1 "$ITERATIONS"); do
    START=$(python3 -c "import time; print(time.monotonic())")
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/health" 2>/dev/null || echo "000")
    END=$(python3 -c "import time; print(time.monotonic())")
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
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/profile" 2>/dev/null || echo "000")
    END=$(python3 -c "import time; print(time.monotonic())")
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

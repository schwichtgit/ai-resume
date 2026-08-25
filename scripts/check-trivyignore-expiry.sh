#!/bin/bash
# Fail when a .trivyignore suppression has passed its revisit date.
#
# A suppression is a decision to accept a finding *for a while*. The revisit
# date is what makes that "for a while" rather than "forever" -- without it
# being enforced, entries age quietly and the suppression list slowly becomes
# a list of things nobody looks at any more. This turns that into a build
# failure on the week it lapses.
#
# Every non-comment entry must carry a "Revisit YYYY-MM-DD" marker. An entry
# without one is also a failure: an undated suppression can never expire.
#
# Usage: scripts/check-trivyignore-expiry.sh [path-to-.trivyignore]

set -euo pipefail

IGNORE_FILE="${1:-$(dirname "$0")/../.trivyignore}"

if [[ ! -f "$IGNORE_FILE" ]]; then
    echo "No .trivyignore at ${IGNORE_FILE}; nothing to check."
    exit 0
fi

TODAY=$(date -u +%Y-%m-%d)
EXPIRED=0
UNDATED=0
ACTIVE=0

while IFS= read -r line; do
    # Skip comments and blank lines.
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue

    ACTIVE=$((ACTIVE + 1))
    cve=$(echo "$line" | awk '{print $1}')

    if [[ "$line" =~ Revisit[[:space:]]+([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        revisit="${BASH_REMATCH[1]}"
        # String comparison is valid for zero-padded ISO-8601 dates.
        if [[ "$revisit" < "$TODAY" ]]; then
            echo "EXPIRED: ${cve} was due for review on ${revisit} (today ${TODAY})" >&2
            EXPIRED=$((EXPIRED + 1))
        fi
    else
        echo "UNDATED: ${cve} has no 'Revisit YYYY-MM-DD' marker" >&2
        UNDATED=$((UNDATED + 1))
    fi
done < "$IGNORE_FILE"

echo "Checked ${ACTIVE} active suppression(s) in ${IGNORE_FILE}"

if [[ $EXPIRED -gt 0 || $UNDATED -gt 0 ]]; then
    echo "" >&2
    echo "${EXPIRED} expired, ${UNDATED} undated." >&2
    echo "Re-review each: confirm the finding still exists and is still" >&2
    echo "unfixed/unreachable, then either drop the entry or re-date it." >&2
    exit 1
fi

echo "All suppressions are dated and within their review window."

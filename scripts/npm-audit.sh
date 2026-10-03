#!/bin/bash
# npm audit with a dated allowlist (frontend/.npm-audit-ignore).
#
# `npm audit` has no way to accept a single advisory: one unfixable finding
# fails every run, and a check that is always red stops being read. This
# runs the audit, drops advisories listed in the ignore file, and fails on
# anything left -- at any severity, as `--audit-level=low` did before.
#
# The ignore file follows the .trivyignore convention: one advisory ID per
# line with an inline reason and a "Revisit YYYY-MM-DD" date, enforced by
# scripts/check-trivyignore-expiry.sh. An entry also fails once npm stops
# reporting its advisory: a suppression for a finding that no longer exists
# is a blind spot, so it must be removed rather than left to linger.
#
# Usage: scripts/npm-audit.sh [frontend-dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$(cd "${1:-$SCRIPT_DIR/../frontend}" && pwd)"
IGNORE_FILE="$FRONTEND_DIR/.npm-audit-ignore"

if [[ -f "$IGNORE_FILE" ]]; then
    "$SCRIPT_DIR/check-trivyignore-expiry.sh" "$IGNORE_FILE"
    IGNORED=$(grep -vhE '^[[:space:]]*#|^[[:space:]]*$' "$IGNORE_FILE" | awk '{print $1}' | sort -u)
else
    IGNORED=""
fi

# npm audit exits non-zero whenever it finds anything; the JSON is the result.
REPORT=$(npm --prefix "$FRONTEND_DIR" audit --json 2>/dev/null) || true

if ! echo "$REPORT" | jq -e '.vulnerabilities' >/dev/null 2>&1; then
    echo "npm audit did not produce a report:" >&2
    echo "$REPORT" | jq -r '.error.summary? // .' >&2 2>/dev/null || echo "$REPORT" >&2
    exit 1
fi

# One line per advisory: "<GHSA id> <severity> <package>". Advisories are the
# object entries in each vulnerability's `via`; string entries only name the
# dependency that carries them.
FOUND=$(echo "$REPORT" | jq -r '
    [.vulnerabilities[].via[] | objects
     | "\(.url | split("/") | last) \(.severity) \(.name)"]
    | unique | .[]')

FAILED=0

while read -r id severity pkg; do
    [[ -z "$id" ]] && continue
    if grep -qxF "$id" <<<"$IGNORED"; then
        echo "accepted: $id ($severity, $pkg) -- see $(basename "$IGNORE_FILE")"
    else
        echo "VULNERABLE: $id ($severity, $pkg)" >&2
        FAILED=$((FAILED + 1))
    fi
done <<<"$FOUND"

while read -r id; do
    [[ -z "$id" ]] && continue
    if ! grep -q "^$id " <<<"$FOUND"; then
        echo "STALE: $id is in $(basename "$IGNORE_FILE") but npm audit no longer reports it; remove the entry" >&2
        FAILED=$((FAILED + 1))
    fi
done <<<"$IGNORED"

if [[ $FAILED -gt 0 ]]; then
    echo "" >&2
    echo "npm audit: $FAILED problem(s). Run 'npm audit' in $(basename "$FRONTEND_DIR") for details." >&2
    exit 1
fi

echo "npm audit: no unaccepted vulnerabilities."

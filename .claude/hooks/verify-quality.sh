#!/bin/bash
# Verify-quality hook: run quality checks before Claude Code stops.
#
# Reference implementation for upstream cpf CR:
#   .specify/proposals/cr-ci-base-scaffold-issues.md#4
#
# Strategy: Tier-1 Taskfile delegation.
#   The repo's own Taskfile knows how each service's venv, toolchain, and
#   exclusions are wired. Calling `task lint` / `task test` avoids the
#   PATH-based tool resolution that breaks in polyglot monorepos (e.g.
#   picking up deployment/'s pytest when scanning ingest/).
#
# Severity contract (preserved from the previous per-service script):
#   ERROR     -> `task lint` failure. Blocks Stop (exit 2).
#   WARNING   -> `task test` failure. Non-blocking, surfaced at end.
#   INFO      -> noisy sub-command output (warnings from underlying tools
#                that don't flip their own exit code: ESLint warning lines,
#                Rust build notes, prettier/markdown clean diffs, etc.).
#
# `task` itself is exit-code binary, so per-linter warning/error semantics
# are owned by each linter:
#   - ESLint: warnings print but exit 0 unless --max-warnings tripped.
#   - Clippy: `-D warnings` promotes warnings to errors (memvid:lint).
#   - Ruff / Mypy / Prettier / markdownlint / shellcheck: strict, exit 0
#     means clean. This matches CI behavior.

set -euo pipefail

# Infinite-loop guard
INPUT="$(cat)"
STOP_HOOK_ACTIVE="$(echo "$INPUT" | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('stop_hook_active', False))" \
    2>/dev/null || echo "False")"
if [[ "$STOP_HOOK_ACTIVE" == "True" ]]; then
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Ensure rustup-managed cargo is reachable for memvid lint / test.
if [[ -d "$HOME/.cargo/bin" ]]; then
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Preconditions for Tier-1 delegation.
if ! command -v task >/dev/null 2>&1; then
    echo "verify-quality: 'task' not installed; skipping quality checks" >&2
    exit 0
fi
if [[ ! -f "$PROJECT_ROOT/Taskfile.yml" ]]; then
    echo "verify-quality: no Taskfile.yml at $PROJECT_ROOT; skipping quality checks" >&2
    exit 0
fi

echo "Running quality verification via Taskfile delegation..."

FAILED=0
WARNINGS=0

echo ""
echo "=== task lint (blocking) ==="
if ! (cd "$PROJECT_ROOT" && task lint); then
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=== task test (advisory) ==="
if ! (cd "$PROJECT_ROOT" && task test); then
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "=== Summary ==="
echo "Blocking failures: $FAILED"
echo "Advisory warnings: $WARNINGS"

if [[ $FAILED -gt 0 ]]; then
    echo "" >&2
    echo "Lint failures must be fixed before stopping." >&2
    exit 2
fi

if [[ $WARNINGS -gt 0 ]]; then
    echo ""
    echo "Tests have failures (non-blocking). Review before committing."
fi

echo ""
echo "All required quality checks passed."
exit 0

#!/bin/bash
set -euo pipefail

# Install git hooks and make Claude Code hooks executable.
# This script resolves hook sources relative to its own location,
# so it works correctly when projected into any host project.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/hooks"

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || { echo "Not in a git repository." >&2; exit 1; })

echo "Installing hooks for: $PROJECT_ROOT"

# Copy git hooks
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
mkdir -p "$GIT_HOOKS_DIR"

for hook in pre-commit commit-msg; do
    src="$HOOKS_DIR/$hook"
    dst="$GIT_HOOKS_DIR/$hook"
    if [[ -f "$src" ]]; then
        cp "$src" "$dst"
        chmod +x "$dst"
        echo "  Installed: $hook"
    else
        echo "  Skipped (not found): $src"
    fi
done

# Make Claude Code hooks executable
if [[ -d "$PROJECT_ROOT/.claude/hooks" ]]; then
    chmod +x "$PROJECT_ROOT"/.claude/hooks/*.sh 2>/dev/null || true
    echo "  Claude Code hooks made executable."
fi

echo "Done."

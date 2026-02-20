#!/bin/bash
# Format-changed hook: Auto-format modified files on session stop
# Runs BEFORE verify-quality.sh so formatted code passes lint checks
# This avoids the PostToolUse formatting problem where prettier
# reformats files between Edit calls, breaking old_string matching.

set -euo pipefail

# Read JSON input from stdin and check for infinite loop prevention
INPUT="$(cat)"
STOP_HOOK_ACTIVE="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stop_hook_active', False))" 2>/dev/null || echo "False")"
if [[ "$STOP_HOOK_ACTIVE" == "True" ]]; then
    exit 0
fi

# Get the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Collect all changed files (staged + unstaged vs HEAD)
CHANGED_FILES=$(
    { git diff --name-only HEAD 2>/dev/null || git diff --name-only; } | sort -u
)

if [[ -z "$CHANGED_FILES" ]]; then
    exit 0
fi

echo "Formatting changed files..."

FORMATTED=0

while IFS= read -r FILE; do
    # Skip if file doesn't exist (deleted files)
    FULL_PATH="$PROJECT_ROOT/$FILE"
    if [[ ! -f "$FULL_PATH" ]]; then
        continue
    fi

    case "$FILE" in
        *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.scss|*.html|*.md|*.yaml|*.yml)
            if [[ -f "$PROJECT_ROOT/frontend/package.json" ]] && command -v npx &>/dev/null; then
                (cd "$PROJECT_ROOT/frontend" && npx prettier --write "$FULL_PATH" >/dev/null 2>&1) || true
                FORMATTED=$((FORMATTED + 1))
            fi
            ;;
        *.py)
            if command -v ruff &>/dev/null; then
                ruff format "$FULL_PATH" >/dev/null 2>&1 || true
                ruff check --fix "$FULL_PATH" >/dev/null 2>&1 || true
                FORMATTED=$((FORMATTED + 1))
            fi
            ;;
        *.rs)
            if command -v rustfmt &>/dev/null; then
                rustfmt "$FULL_PATH" >/dev/null 2>&1 || true
                FORMATTED=$((FORMATTED + 1))
            fi
            ;;
        *.sh)
            if command -v shfmt &>/dev/null; then
                shfmt -w "$FULL_PATH" >/dev/null 2>&1 || true
                FORMATTED=$((FORMATTED + 1))
            fi
            ;;
    esac
done <<< "$CHANGED_FILES"

if [[ $FORMATTED -gt 0 ]]; then
    echo "  Formatted $FORMATTED file(s)"
fi

exit 0

#!/bin/bash
# Post-edit hook: Auto-format files after Claude Code edits
# This hook runs after file modifications to ensure consistent formatting

set -euo pipefail

# Claude Code hooks receive JSON on stdin, not as positional arguments.
# For PostToolUse hooks, the JSON structure is:
# { "tool_name": "Write", "tool_input": { "file_path": "/path/to/file" }, "tool_output": "..." }
INPUT=$(cat /dev/stdin 2>/dev/null) || true

if [[ -z "$INPUT" ]]; then
    # No input provided, nothing to format
    exit 0
fi

# Parse the file_path from the JSON input using python3
EDITED_FILE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except (json.JSONDecodeError, KeyError, TypeError):
    print('')
" 2>/dev/null) || true

if [[ -z "$EDITED_FILE" ]]; then
    # Could not parse file path from JSON, allow execution
    exit 0
fi

# Get the project root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Determine file type and run appropriate formatter
case "$EDITED_FILE" in
    *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.scss|*.html|*.md)
        # JavaScript/TypeScript files - use prettier if available
        if command -v npx &> /dev/null; then
            # Check if we're in a directory with prettier config
            if [[ -f "$PROJECT_ROOT/frontend/package.json" ]]; then
                cd "$PROJECT_ROOT/frontend"
                npx prettier --write "$EDITED_FILE" 2>/dev/null || true
            elif [[ -f "$PROJECT_ROOT/package.json" ]]; then
                cd "$PROJECT_ROOT"
                npx prettier --write "$EDITED_FILE" 2>/dev/null || true
            fi
        fi
        ;;
    *.py)
        # Python files - use ruff if available
        if command -v ruff &> /dev/null; then
            ruff format "$EDITED_FILE" 2>/dev/null || true
            ruff check --fix "$EDITED_FILE" 2>/dev/null || true
        elif command -v black &> /dev/null; then
            black "$EDITED_FILE" 2>/dev/null || true
        fi
        ;;
    *.rs)
        # Rust files - use rustfmt if available
        if command -v rustfmt &> /dev/null; then
            rustfmt "$EDITED_FILE" 2>/dev/null || true
        fi
        ;;
    *.sh)
        # Shell scripts - use shfmt if available
        if command -v shfmt &> /dev/null; then
            shfmt -w "$EDITED_FILE" 2>/dev/null || true
        fi
        ;;
    *.yaml|*.yml)
        # YAML files - use prettier if available
        if command -v npx &> /dev/null && [[ -f "$PROJECT_ROOT/frontend/package.json" ]]; then
            cd "$PROJECT_ROOT/frontend"
            npx prettier --write "$EDITED_FILE" 2>/dev/null || true
        fi
        ;;
esac

exit 0

#!/bin/bash
# Install Git hooks for the ai-resume project
# Usage: ./scripts/install-hooks.sh

set -euo pipefail

# Get the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Installing Git hooks for ai-resume..."
echo "Project root: $PROJECT_ROOT"
echo ""

# Configure git to use .githooks/ as the hooks directory
echo "Setting core.hooksPath to .githooks/ ..."
git config core.hooksPath .githooks
echo "  Done: git config core.hooksPath = .githooks"

# Ensure .githooks scripts are executable
echo ""
echo "=== Making .githooks scripts executable ==="
for hook_file in "$PROJECT_ROOT/.githooks"/*; do
    if [[ -f "$hook_file" ]] && [[ ! "$hook_file" =~ \.sample$ ]]; then
        chmod +x "$hook_file"
        echo "  Made executable: $(basename "$hook_file")"
    fi
done

echo ""
echo "=== Claude Code Hooks ==="

# Check for Claude Code hooks
CLAUDE_HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"
if [[ -d "$CLAUDE_HOOKS_DIR" ]]; then
    echo "Making Claude Code hooks executable..."
    for hook_file in "$CLAUDE_HOOKS_DIR"/*.sh; do
        if [[ -f "$hook_file" ]]; then
            chmod +x "$hook_file"
            echo "  Made executable: $(basename "$hook_file")"
        fi
    done
else
    echo "No Claude Code hooks directory found"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Active hooks (from .githooks/):"
for hook_file in "$PROJECT_ROOT/.githooks"/*; do
    if [[ -f "$hook_file" ]] && [[ ! "$hook_file" =~ \.sample$ ]]; then
        echo "  - $(basename "$hook_file")"
    fi
done

echo ""
echo "To skip hooks temporarily, use: git commit --no-verify"
echo "To uninstall, run: git config --unset core.hooksPath"

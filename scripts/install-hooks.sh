#!/bin/bash
# Install Git hooks for the ai-resume project
# Usage: ./scripts/install-hooks.sh

set -euo pipefail

# Get the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "Installing Git hooks for ai-resume..."
echo "Project root: $PROJECT_ROOT"
echo ""

# Ensure .git/hooks directory exists
mkdir -p "$GIT_HOOKS_DIR"

# Function to install a hook
install_hook() {
    local hook_name="$1"
    local source_path="$PROJECT_ROOT/scripts/hooks/$hook_name"
    local target_path="$GIT_HOOKS_DIR/$hook_name"

    # Check if source exists in scripts/hooks/
    if [[ -f "$source_path" ]]; then
        echo "Installing $hook_name from scripts/hooks/..."
        cp "$source_path" "$target_path"
        chmod +x "$target_path"
        echo "  Installed: $target_path"
    elif [[ -f "$target_path" ]] && [[ ! -f "$target_path.sample" ]]; then
        # Hook already exists (not a sample file)
        echo "Hook $hook_name already exists, making executable..."
        chmod +x "$target_path"
        echo "  Updated: $target_path"
    else
        echo "Skipping $hook_name (source not found)"
    fi
}

# Install standard hooks
HOOKS=(
    "pre-commit"
    "commit-msg"
    "pre-push"
    "post-merge"
)

for hook in "${HOOKS[@]}"; do
    install_hook "$hook"
done

echo ""
echo "=== Making existing hooks executable ==="

# Make any existing hooks executable
for hook_file in "$GIT_HOOKS_DIR"/*; do
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
echo "Installed hooks:"
for hook_file in "$GIT_HOOKS_DIR"/*; do
    if [[ -f "$hook_file" ]] && [[ ! "$hook_file" =~ \.sample$ ]]; then
        echo "  - $(basename "$hook_file")"
    fi
done

echo ""
echo "To skip hooks temporarily, use: git commit --no-verify"
echo "To uninstall, delete the hook files from .git/hooks/"

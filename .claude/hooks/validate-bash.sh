#!/bin/bash
# Validate-bash hook: Block dangerous commands before execution
# This hook is called before Claude Code executes bash commands

set -euo pipefail

# Claude Code hooks receive JSON on stdin, not as positional arguments.
# For PreToolUse hooks, the JSON structure is:
# { "tool_name": "Bash", "tool_input": { "command": "..." } }
INPUT=$(cat /dev/stdin 2>/dev/null) || true

if [[ -z "$INPUT" ]]; then
    # No input provided, nothing to validate
    exit 0
fi

# Parse the command from the JSON input using python3
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except (json.JSONDecodeError, KeyError, TypeError):
    print('')
" 2>/dev/null) || true

if [[ -z "$COMMAND" ]]; then
    # Could not parse command from JSON, allow execution
    exit 0
fi

# Define dangerous patterns to block
DANGEROUS_PATTERNS=(
    # Destructive file operations
    "rm -rf /"
    "rm -rf /*"
    "rm -rf ~"
    "rm -rf \$HOME"

    # Force push operations
    "git push --force"
    "git push -f"
    "git push origin.*--force"
    "git push origin.*-f"

    # Hard reset operations
    "git reset --hard"
    "git clean -fd"
    "git checkout \."
    "git restore \."

    # Dangerous permissions
    "chmod -R 777"
    "chmod 777"

    # Disk operations
    "> /dev/sd"
    "mkfs\."
    "dd if=/dev/zero"
    "dd if=/dev/random"

    # Network attacks
    ":(){ :|:& };:"  # Fork bomb

    # Environment variable manipulation
    "unset PATH"
    "PATH="

    # Dangerous downloads and execution
    "curl.*\| sh"
    "curl.*\| bash"
    "wget.*\| sh"
    "wget.*\| bash"
)

# Check for dangerous patterns
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        echo "BLOCKED: Command matches dangerous pattern: $pattern"
        echo "Command: $COMMAND"
        exit 1
    fi
done

# Check for main/master force push specifically
if echo "$COMMAND" | grep -qE "git push.*(--force|-f).*main|git push.*(--force|-f).*master"; then
    echo "BLOCKED: Force push to main/master is not allowed"
    echo "Command: $COMMAND"
    exit 1
fi

# All checks passed
exit 0

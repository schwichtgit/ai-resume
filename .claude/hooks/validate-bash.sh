#!/bin/bash
# Validate-bash hook: Block dangerous commands before execution
# This hook is called before Claude Code executes bash commands

set -uo pipefail

# Claude Code hooks receive JSON on stdin, not as positional arguments.
# For PreToolUse hooks, the JSON structure is:
# { "tool_name": "Bash", "tool_input": { "command": "..." } }
INPUT=$(cat /dev/stdin 2>/dev/null) || true

if [[ -z "$INPUT" ]]; then
    # No input provided, nothing to validate
    exit 0
fi

# Parse the command from the JSON input using python3
COMMAND=$(printf '%s\n' "$INPUT" | python3 -c "
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

# Define dangerous literal patterns (checked with grep -F, fixed-string)
LITERAL_PATTERNS=(
    # Destructive file operations
    "rm -rf /"
    "rm -rf /*"
    "rm -rf ~"

    # Force push operations
    "git push --force"
    "git push -f"

    # Hard reset operations
    "git reset --hard"
    "git clean -fd"

    # Dangerous permissions
    "chmod -R 777"
    "chmod 777"

    # Disk operations
    "> /dev/sd"
    "dd if=/dev/zero"
    "dd if=/dev/random"

    # Network attacks
    ":(){ :|:& };:"  # Fork bomb

    # Environment variable manipulation
    "unset PATH"

)

# Define dangerous regex patterns (checked with grep -E, extended regex)
# shellcheck disable=SC2016  # literal regex patterns, not variable expansion
REGEX_PATTERNS=(
    'rm -rf \$HOME'
    'git push origin .*(--force|-f[[:space:]]|-f$)'
    'git checkout \.$'
    'git restore \.$'
    'mkfs\.'
    'curl.*\| sh'
    'curl.*\| bash'
    'wget.*\| sh'
    'wget.*\| bash'
)

# Check literal patterns (safe, no ERE interpretation)
for pattern in "${LITERAL_PATTERNS[@]}"; do
    if printf '%s\n' "$COMMAND" | grep -qF "$pattern"; then
        echo "BLOCKED: Command matches dangerous pattern: $pattern" >&2
        echo "Command: $COMMAND" >&2
        exit 2
    fi
done

# Check regex patterns
for pattern in "${REGEX_PATTERNS[@]}"; do
    if printf '%s\n' "$COMMAND" | grep -qE "$pattern"; then
        echo "BLOCKED: Command matches dangerous pattern: $pattern" >&2
        echo "Command: $COMMAND" >&2
        exit 2
    fi
done

# Check for main/master force push specifically
if printf '%s\n' "$COMMAND" | grep -qE 'git push.*(--force|-f).*\b(main|master)\b'; then
    echo "BLOCKED: Force push to main/master is not allowed" >&2
    echo "Command: $COMMAND" >&2
    exit 2
fi

# All checks passed
exit 0

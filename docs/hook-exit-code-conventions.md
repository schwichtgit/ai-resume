# Claude Code Hook Exit Code Conventions

## Problem Statement

Claude Code hooks that use `exit 1` to block tool calls do not actually block
anything. The tool still executes, and the user sees a "PreToolUse:Bash hook
error" message on every invocation. This document explains the correct exit code
semantics, the antipattern, and the fix.

## Exit Code Reference

Claude Code command hooks communicate intent through three exit code classes:

| Exit Code | Meaning            | Stdout Handling                                | Stderr Handling                     | Tool Execution |
| --------- | ------------------ | ---------------------------------------------- | ----------------------------------- | -------------- |
| **0**     | Success (allow)    | Parsed as JSON feedback; shown in verbose mode | Ignored                             | Proceeds       |
| **2**     | Block (deny)       | Ignored (JSON not parsed)                      | Fed back to Claude as error context | **Blocked**    |
| **Other** | Error (unexpected) | Ignored                                        | Shown in verbose mode               | **Proceeds**   |

### Per-Event Exit 2 Behavior

Exit 2 only blocks events that represent future actions. Events that report
things that already happened cannot be blocked.

| Hook Event           | Can Block? | Exit 2 Effect                                         |
| -------------------- | ---------- | ----------------------------------------------------- |
| `PreToolUse`         | Yes        | Blocks the tool call                                  |
| `PermissionRequest`  | Yes        | Denies the permission                                 |
| `UserPromptSubmit`   | Yes        | Blocks prompt processing and erases the prompt        |
| `Stop`               | Yes        | Prevents Claude from stopping; conversation continues |
| `SubagentStop`       | Yes        | Prevents the subagent from stopping                   |
| `TeammateIdle`       | Yes        | Prevents the teammate from going idle                 |
| `TaskCompleted`      | Yes        | Prevents the task from being marked completed         |
| `PostToolUse`        | No         | Shows stderr to Claude (tool already ran)             |
| `PostToolUseFailure` | No         | Shows stderr to Claude (tool already failed)          |
| `Notification`       | No         | Shows stderr to user only                             |
| `SubagentStart`      | No         | Shows stderr to user only                             |
| `SessionStart`       | No         | Shows stderr to user only                             |
| `SessionEnd`         | No         | Shows stderr to user only                             |
| `PreCompact`         | No         | Shows stderr to user only                             |

## The Antipattern: `exit 1` for Blocks

### Symptoms

- "PreToolUse:Bash hook error" displayed on every Bash command execution
- Dangerous commands are NOT actually blocked -- the tool still executes
- Block explanation goes to stdout, where Claude Code ignores it on non-zero exit
- Noisy UX: every command shows an error, not just blocked ones

### Root Cause

`exit 1` is classified as a "non-blocking error" (the "other" category in the
exit code table). Claude Code treats it as an unexpected hook failure, not a
deliberate block. Two things go wrong:

1. The tool **still executes** because only exit 2 blocks.
2. The error is **displayed to the user** as a hook error on every invocation,
   because the hook fails to parse JSON input when the command is safe and the
   script hits an error path.

### Before (Broken)

From commit `dd557cd` -- the original `validate-bash.sh`:

```bash
#!/bin/bash
set -euo pipefail

# BUG: Reads from $1 instead of stdin
COMMAND="${1:-}"

if [[ -z "$COMMAND" ]]; then
    echo "No command provided to validate"
    exit 0
fi

# ... pattern matching ...

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        # BUG 1: stdout, not stderr -- Claude never sees this
        echo "BLOCKED: Command matches dangerous pattern: $pattern"
        echo "Command: $COMMAND"
        # BUG 2: exit 1 = error, not block -- tool still runs
        exit 1
    fi
done

exit 0
```

Three bugs in one block:

1. **Input source**: reads `$1` (positional arg) instead of stdin JSON
2. **Output channel**: sends block message to stdout instead of stderr
3. **Exit code**: uses `exit 1` (error) instead of `exit 2` (block)

### Intermediate Fix (Partial)

Commit `d98b01b` fixed the stdin/JSON parsing but kept `exit 1`:

```bash
# Fixed: reads JSON from stdin
INPUT=$(cat /dev/stdin 2>/dev/null) || true
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except (json.JSONDecodeError, KeyError, TypeError):
    print('')
" 2>/dev/null) || true

# ... pattern matching ...

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        # Still broken: stdout + exit 1
        echo "BLOCKED: Command matches dangerous pattern: $pattern"
        echo "Command: $COMMAND"
        exit 1
    fi
done
```

### After (Correct)

Current `validate-bash.sh` -- all three bugs fixed:

```bash
INPUT=$(cat /dev/stdin 2>/dev/null) || true

# ... JSON parsing with python3 ...

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        # Fix: stderr + exit 2
        echo "BLOCKED: Command matches dangerous pattern: $pattern" >&2
        echo "Command: $COMMAND" >&2
        exit 2
    fi
done

exit 0
```

Changes:

- `echo "..."` becomes `echo "..." >&2` (stderr, so Claude sees it)
- `exit 1` becomes `exit 2` (block signal, tool does not execute)

## Output Channel Convention

The output channel determines who sees your message:

| Exit Code | Channel | Who Sees It                                      |
| --------- | ------- | ------------------------------------------------ |
| 0         | stdout  | Claude Code parses as JSON; verbose mode display |
| 0         | stderr  | Ignored                                          |
| 2         | stderr  | Fed to Claude as error context                   |
| 2         | stdout  | Ignored (JSON not parsed)                        |
| Other     | stderr  | Shown in verbose mode (`Ctrl+O`)                 |
| Other     | stdout  | Ignored                                          |

Key rule: **Claude only reads stderr on exit 2, stdout on exit 0.** If you send
your block explanation to stdout and exit 2, Claude never sees why the tool was
blocked.

## JSON Output on Exit 0

Exit 0 hooks can return structured JSON on stdout for fine-grained control.
For `PreToolUse` hooks, this enables three-way decisions (allow, deny, ask)
and tool input modification:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook"
  }
}
```

Valid `permissionDecision` values:

- `"allow"` -- bypasses the permission system entirely
- `"deny"` -- prevents the tool call (equivalent to exit 2)
- `"ask"` -- escalates to the user for confirmation

The JSON approach is more powerful than exit codes alone but requires the hook to
always exit 0 and encode the decision in the output.

## Best Practices for PreToolUse Hooks

### Exit code discipline

```bash
# Allow (default path -- no output needed)
exit 0

# Block (explanation on stderr)
echo "BLOCKED: reason" >&2
exit 2

# Never use exit 1 for blocking
```

### Defensive input parsing

```bash
# Always guard stdin read
INPUT=$(cat /dev/stdin 2>/dev/null) || true

# Guard JSON parsing with || true
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except (json.JSONDecodeError, KeyError, TypeError):
    print('')
" 2>/dev/null) || true

# Allow execution if parsing fails
if [[ -z "$COMMAND" ]]; then
    exit 0
fi
```

### Performance

Hooks run on every tool invocation of the matched type. Keep them fast:

- Avoid network calls in the hot path
- Use simple pattern matching (grep) over heavy parsing
- Exit early when the tool call is clearly safe

### Testing

Test hooks locally by piping JSON to stdin:

```bash
# Test with a safe command (should exit 0)
echo '{"tool_name":"Bash","tool_input":{"command":"npm test"}}' | bash .claude/hooks/validate-bash.sh
echo $?  # Expected: 0

# Test with a dangerous command (should exit 2)
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | bash .claude/hooks/validate-bash.sh
echo $?  # Expected: 2

# Test with empty input (should exit 0, not crash)
echo '' | bash .claude/hooks/validate-bash.sh
echo $?  # Expected: 0

# Test with malformed JSON (should exit 0, not crash)
echo 'not json' | bash .claude/hooks/validate-bash.sh
echo $?  # Expected: 0
```

## Status in ai-resume

Both `PreToolUse` hooks follow the convention. `protect-files.sh` blocks with
`exit 2` and writes the message to stderr at all three block paths:

```bash
# .claude/hooks/protect-files.sh
case "$FILENAME" in
    .env*|*credentials*|*secret*|*password*|id_rsa*|id_ed25519*|*.pem|*.key)
        echo "BLOCKED: This file type is protected and cannot be modified" >&2
        exit 2
        ;;
    *lock*)
        echo "BLOCKED: Lock files should not be manually modified" >&2
        exit 2
        ;;
esac

# ... and the sensitive-directory path
echo "BLOCKED: Files in $dir directory are protected" >&2
exit 2
```

## Upstream Action Items (specforge)

1. **Update hook templates**: specforge hook scaffolding should generate `exit 2`
   with stderr for block paths
2. **Add hook testing guide**: include the stdin-pipe testing pattern in
   specforge documentation
3. **Add a lint check**: CI could verify that no hook script uses `exit 1` in a
   block path (grep for `exit 1` in `.claude/hooks/`)
4. **Document the three-bug pattern**: input source (stdin not `$1`), output
   channel (stderr not stdout), exit code (`2` not `1`) -- these are the three
   things every new hook author gets wrong

## References

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) -- official documentation
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide) -- setup walkthrough and troubleshooting
- [Bash Command Validator Example](https://github.com/anthropics/claude-code/blob/main/examples/hooks/bash_command_validator_example.py) -- official reference implementation
- Commit `dd557cd` -- original broken hook (all three bugs)
- Commit `d98b01b` -- partial fix (stdin parsing fixed, exit code still wrong)
- Current `validate-bash.sh` -- fully corrected (exit 2, stderr, stdin JSON)

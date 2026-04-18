# PostToolUse Auto-Formatting Antipattern in Claude Code Hooks

## Problem Statement

Claude Code's `Edit` tool performs exact string matching on an `old_string` parameter to locate and replace content in files. When a PostToolUse hook runs a formatter (prettier, ruff, rustfmt) after every Edit call, the formatter modifies the file content _between_ consecutive Edit calls. The next Edit call then fails because its `old_string` no longer matches the file -- the formatter changed whitespace, line wrapping, import order, or trailing commas since Claude last read the file.

This produces two failure modes:

1. **"File has been unexpectedly modified" errors** -- Claude detects the file changed since its last read and must re-read the file, recompute the edit, and retry.
2. **Context window erosion** -- Each failed edit generates a system reminder. In multi-edit sequences, the repeated re-reads and retries consume significant context window budget.

The result is a feedback loop: Edit -> format -> mismatch -> re-read -> Edit -> format -> mismatch -> repeat.

## How It Manifests

### Prettier (JSON)

Prettier collapses multi-line arrays to single lines when they fit within the print width:

```json
// Claude writes this:
"skills": [
  "TypeScript",
  "React",
  "Python"
]

// Prettier reformats to:
"skills": ["TypeScript", "React", "Python"]
```

Claude's next Edit targeting the multi-line form fails.

### Prettier (TSX/TS)

Prettier wraps long lines, reorders imports, and adds trailing commas:

```tsx
// Claude writes this:
import { useState, useEffect, useCallback } from 'react';

// Prettier may reformat to:
import { useCallback, useEffect, useState } from 'react';
```

### ruff (Python)

ruff reorders imports per isort conventions and adjusts line length:

```python
# Claude writes this:
from fastapi import FastAPI, HTTPException, Depends
import os

# ruff may reformat to:
import os

from fastapi import Depends, FastAPI, HTTPException
```

### rustfmt (Rust)

rustfmt adjusts brace positioning, trailing commas, and expression formatting:

```rust
// Claude writes this:
let config = Config { host: "localhost".to_string(), port: 8080, debug: true };

// rustfmt reformats to:
let config = Config {
    host: "localhost".to_string(),
    port: 8080,
    debug: true,
};
```

### The Loop

In a typical multi-edit coding task:

1. Claude calls Edit on file A -- PostToolUse reformats file A
2. Claude calls Edit on file A again -- `old_string` no longer matches
3. Claude receives "File has been unexpectedly modified" system reminder
4. Claude re-reads file A, recomputes the edit, retries
5. Edit succeeds -- PostToolUse reformats file A again
6. Claude calls Edit on file A a third time -- another mismatch
7. Repeat until Claude completes all edits on the file

Each iteration wastes context window on the system reminder and the re-read. For a sequence of 5 edits to a single file, this can double or triple the number of tool calls.

## Evidence from GitHub Issues

The Claude Code repository (`anthropics/claude-code`) has multiple open issues documenting this behavior:

| Issue                                                            | Reactions | Summary                                                                                                                                     |
| ---------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| [#3513](https://github.com/anthropics/claude-code/issues/3513)   | 150+      | "File modified since read, either by user or by a linter" -- the canonical report. Users identify PostToolUse formatters as the root cause. |
| [#10882](https://github.com/anthropics/claude-code/issues/10882) | --        | Documents the infinite Edit/format loop specifically in VSCode with prettier-on-save. Same root cause with PostToolUse hooks.               |
| [#10011](https://github.com/anthropics/claude-code/issues/10011) | --        | Reports that PostToolUse hook changes may be silently overwritten by subsequent Edit calls, or cause cascading mismatches.                  |
| [#7443](https://github.com/anthropics/claude-code/issues/7443)   | --        | "File has been unexpectedly modified" during multi-file refactors with formatting hooks active.                                             |
| [#14516](https://github.com/anthropics/claude-code/issues/14516) | --        | Additional "unexpectedly modified" report correlated with auto-formatting tools.                                                            |

The common thread: formatters that run between Edit calls break the exact-match contract that the Edit tool depends on.

## Severity by File Type

| File Type | Impact     | Explanation                                                                                                                             |
| --------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| JSON      | **HIGH**   | Prettier aggressively collapses/expands arrays and objects based on print width. Nearly every multi-line JSON edit triggers a mismatch. |
| TSX/TS    | **HIGH**   | Prettier wraps imports, adds trailing commas, reformats JSX. Most edits to component files trigger reformatting.                        |
| Python    | **MEDIUM** | ruff reorders imports and adjusts line length. Edits to import blocks and long expressions are affected.                                |
| Rust      | **MEDIUM** | rustfmt adjusts brace style and trailing commas. Struct/enum definitions and match arms are affected.                                   |
| Shell     | **LOW**    | shfmt adjusts indentation but rarely changes line structure in ways that break exact matching.                                          |
| YAML      | **LOW**    | Prettier makes minimal changes to YAML. Quoting and flow style changes are rare.                                                        |
| Markdown  | **LOW**    | Prettier adjusts line wrapping in prose but Claude rarely makes consecutive edits to the same markdown paragraph.                       |

## The Official Docs Gap

The [Claude Code hooks documentation](https://docs.anthropic.com/en/docs/claude-code/hooks) promotes PostToolUse formatting as a valid pattern:

> "You can use PostToolUse hooks to automatically format files after they are written or edited."

The documentation provides an example of running prettier in a PostToolUse hook with a `Write|Edit` matcher. This is the pattern that causes the antipattern described above.

However, community guidance in GitHub issue threads contradicts this:

> "Format on commit via Stop hook instead" -- recurring recommendation in #3513 comments.

The official docs do not address:

- The `old_string` mismatch problem caused by mid-sequence formatting
- Context window cost of repeated "file modified" system reminders
- The distinction between formatting individual edits vs. formatting at session boundaries

## The Fix: Format-on-Stop

Move auto-formatting from PostToolUse to a Stop hook. Format only git-changed files, not every individual edit. Run formatting _before_ quality checks so the formatted code passes lint.

### Design Principles

1. **Session boundary, not edit boundary** -- Format when Claude is done editing, not between edits.
2. **Changed files only** -- Use `git diff --name-only HEAD` to identify files that were actually modified. No wasted work on unchanged files.
3. **Format before lint** -- Run the formatter before verify-quality.sh so formatted code passes lint/type checks on the first try.
4. **Infinite loop prevention** -- Check `stop_hook_active` from stdin JSON to prevent re-triggering when the Stop hook itself causes Claude to resume.

### Before/After Settings

**Before (antipattern):**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/post-edit.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/verify-quality.sh"
          }
        ]
      }
    ]
  }
}
```

**After (format-on-stop):**

```json
{
  "hooks": {
    "PostToolUse": [],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format-changed.sh"
          },
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/verify-quality.sh"
          }
        ]
      }
    ]
  }
}
```

Key changes:

- `PostToolUse` array is emptied -- no more per-edit formatting
- `format-changed.sh` is added to the Stop hook chain _before_ `verify-quality.sh`
- The post-edit.sh script remains in the repository but is no longer wired into settings.json

### format-changed.sh Implementation

```bash
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
```

### Key implementation details

- **`stop_hook_active` guard** -- When a Stop hook exits with code 2, Claude resumes work. If format-changed.sh causes verify-quality.sh to fail (exit 2), Claude will fix the issue and stop again, re-triggering Stop hooks. The `stop_hook_active` check prevents infinite recursion.
- **`git diff --name-only HEAD`** -- Only formats files that were actually changed in this session. No wasted formatter invocations on unchanged files.
- **`$((FORMATTED + 1))` instead of `((FORMATTED++))`** -- Avoids the bash arithmetic bug where `((0++))` returns exit code 1, which kills the script under `set -e`. (See project memory for this known issue.)
- **Each formatter is guarded by `command -v`** -- Gracefully skips formatters that aren't installed.
- **Errors are swallowed with `|| true`** -- Formatter failures on individual files don't abort the hook.

## Upstream Action Items

These changes should be applied to the [specforge](https://github.com/schwichtgit/claude-project-foundation) framework:

1. **Update phase 5 template** -- The `settings.json` template generated by `/specforge setup` should use the format-on-stop pattern:

   - `PostToolUse` array should be empty (no `Write|Edit` matcher for formatting)
   - Stop hook chain should include `format-changed.sh` before `verify-quality.sh`

2. **Remove post-edit.sh from the default hook set** -- The `post-edit.sh` script should not be generated by specforge. Projects that already have it can keep it but should unwire it from `settings.json`.

3. **Add format-changed.sh to the default Stop hook chain** -- The script above should be included in the specforge hook templates.

4. **Update specforge documentation** -- The hooks section of the specforge README should:

   - Document the PostToolUse formatting antipattern
   - Explain why format-on-stop is preferred
   - Reference this document or the upstream GitHub issues

5. **Add migration guidance** -- For existing specforge-managed projects, provide a migration checklist:
   - Empty the `PostToolUse` array in `.claude/settings.json`
   - Add `format-changed.sh` to the Stop hook chain before `verify-quality.sh`
   - Verify the format-changed.sh script is present in `.claude/hooks/`

## Key Takeaway

Auto-formatting should happen at session boundaries (Stop hooks), not between individual edits (PostToolUse), because formatters modify file content in ways that break Claude's exact-match Edit tool.

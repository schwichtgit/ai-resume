#!/bin/bash
# Validate-pr hook: Block AI branding in gh pr create commands
# This PreToolUse hook intercepts Bash commands that contain "gh pr create"
# and scans the title and body for AI branding, Co-Authored-By trailers,
# AI-isms, and emoji before the command executes.

set -euo pipefail

# Read JSON from stdin (Claude Code PreToolUse hook protocol)
INPUT=$(cat /dev/stdin 2>/dev/null) || true

if [[ -z "$INPUT" ]]; then
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
    exit 0
fi

# Only check commands that contain "gh pr create" -- pass through everything else
if ! echo "$COMMAND" | grep -q "gh pr create"; then
    exit 0
fi

# Run all validation in python3 for reliable Unicode and regex handling.
# Use a heredoc with single-quoted delimiter to prevent bash from
# interpreting backticks, dollar signs, or other special characters.
python3 - "$COMMAND" <<'PYEOF'
import sys, re

command = sys.argv[1]
violations = []

# --- 1. AI Branding ---
# Strip "Claude Code" (allowed product name) before checking for "Claude"
stripped = re.sub(r'[Cc]laude\s+[Cc]ode', '', command)
# Strip claude in parenthetical scopes like (claude) or (claude_code)
stripped = re.sub(r'\([Cc]laude[^)]*\)', '', stripped)
# Strip file paths containing .claude/ (e.g. .claude/settings.json)
stripped = re.sub(r'\.claude/', './', stripped)
# Strip backtick-quoted references containing claude
stripped = re.sub(r'`[^`]*[Cc]laude[^`]*`', '``', stripped)

if re.search(r'\bClaude\b', stripped, re.IGNORECASE):
    violations.append('AI branding: "Claude" (standalone usage; "Claude Code" is allowed)')

if re.search(r'\bAnthropic\b', command, re.IGNORECASE):
    violations.append('AI branding: "Anthropic"')

if re.search(r'\bGPT\b', command):
    violations.append('AI branding: "GPT"')

if re.search(r'\bOpenAI\b', command, re.IGNORECASE):
    violations.append('AI branding: "OpenAI"')

if re.search(r'\bCopilot\b', command, re.IGNORECASE):
    violations.append('AI branding: "Copilot"')

# --- 2. Co-Authored-By trailers ---
if re.search(r'Co-Authored-By', command, re.IGNORECASE):
    violations.append('Co-Authored-By trailer detected')

# --- 3. AI-isms ---
ai_isms = [
    (r"I'd be happy to", "I'd be happy to"),
    (r'\bCertainly\b', 'Certainly'),
    (r'\bAs an AI\b', 'As an AI'),
    (r'\bAs a language model\b', 'As a language model'),
    (r'\bI have (made|updated|fixed|added|created|implemented|refactored)\b', 'Self-referential language'),
    (r"I've (made|updated|fixed|added|created|implemented|refactored)", 'Self-referential language'),
    (r'\bseamless(ly)?\b', 'seamless'),
    (r'\brobust\b', 'robust'),
    (r'\bpowerful\b', 'powerful'),
    (r'\belegant(ly)?\b', 'elegant'),
    (r'\bstreamlined\b', 'streamlined'),
    (r'\bbeautified\b', 'beautified'),
    (r'\bpolished\b', 'polished'),
    (r'\benhanced\b', 'enhanced'),
]
for pattern, label in ai_isms:
    if re.search(pattern, command, re.IGNORECASE):
        violations.append(f'AI-ism: "{label}"')

# --- 4. Emoji detection ---
emoji_pattern = re.compile(
    '['
    '\U0001F300-\U0001F6FF'
    '\U0001F900-\U0001F9FF'
    '\U0001FA00-\U0001FA6F'
    '\U0001FA70-\U0001FAFF'
    '\U00002600-\U000026FF'
    '\U00002700-\U000027BF'
    '\U0000FE00-\U0000FE0F'
    '\U0001F000-\U0001F02F'
    '\U0000200D'
    '\U00002B50'
    '\U000023E9-\U000023F3'
    '\U0000231A-\U0000231B'
    '\U000025AA-\U000025AB'
    '\U000025FB-\U000025FE'
    '\U00002934-\U00002935'
    '\U00003030'
    '\U0000303D'
    '\U00003297'
    '\U00003299'
    ']+',
    flags=re.UNICODE,
)
if emoji_pattern.search(command):
    violations.append('Emoji detected in PR content')

# --- Report ---
if violations:
    print('BLOCKED: gh pr create contains prohibited content:', file=sys.stderr)
    for v in violations:
        print(f'  - {v}', file=sys.stderr)
    print('', file=sys.stderr)
    print('Please remove AI branding, Co-Authored-By lines, AI-isms, and emoji', file=sys.stderr)
    print('from the PR title and body before creating the pull request.', file=sys.stderr)
    sys.exit(2)

sys.exit(0)
PYEOF

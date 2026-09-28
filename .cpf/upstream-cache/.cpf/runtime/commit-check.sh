#!/bin/bash
# shellcheck shell=bash
# cpf commit and PR rules: the single implementation used by the git
# commit-msg hook, the Claude Code PR hook, and the CI commit-standards
# jobs.
#
#   commit-check.sh --message-file <file>   one commit message (commit-msg)
#   commit-check.sh --range <base>..<head>  every non-merge commit (CI)
#   commit-check.sh --title <title> [--pr <n>]
#                                           PR title, which becomes the
#                                           squash-merge subject
#   commit-check.sh --text-file <file>      PR description (prose rules)
#
# Rules:
#   subject    conventional format (feat|fix|docs|style|refactor|perf|test|
#              build|ci|chore|revert); commit subject over 72 chars warns;
#              PR title must leave room for GitHub's " (#N)" suffix
#   prose      no emoji; no self-references, filler, marketing adjectives,
#              or AI branding; "Claude" only as "Claude Code" (identifiers
#              and paths such as CLAUDE_PROJECT_DIR are not words);
#              no Co-Authored-By trailer
#   message    draft markers (WIP, TODO, ...) and body lines over 100
#              chars warn
#
# Exit 0 when there are no errors (warnings allowed), 1 otherwise.

set -euo pipefail

ERRORS=0
WARNINGS=0

err() {
    echo "ERROR: $*" >&2
    ERRORS=$((ERRORS + 1))
}

warn() {
    echo "WARN: $*" >&2
    WARNINGS=$((WARNINGS + 1))
}

CONVENTIONAL_RE='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+'

_has_emoji() {
    command -v python3 >/dev/null 2>&1 || return 1
    python3 -c '
import re, sys
text = sys.stdin.read()
pattern = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002702-\U000027B0"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "]+",
    re.UNICODE,
)
sys.exit(0 if pattern.search(text) else 1)
' <<<"$1"
}

# Return 0 if "Claude" appears as a standalone word, i.e. not in
# "Claude Code" and not inside an identifier or path such as
# CLAUDE_PROJECT_DIR or .claude/settings.json.
_has_standalone_claude() {
    printf '%s\n' "$1" | sed 's/Claude Code//g' | tr -s '[:space:]' '\n' \
        | sed "s/^[\"'(\[{<,;:!?]*//; s/[\"')\]}>,;:!?.]*\$//" \
        | grep -qix 'claude'
}

check_prose() {
    local text="$1" label="$2"
    if _has_emoji "$text"; then
        err "Emoji in $label."
    fi
    if grep -qiE "\\b(I have|I've|I updated|I fixed|I added|I removed|I refactored)\\b" <<<"$text"; then
        err "Self-referential language in $label."
    fi
    if grep -qiE "\\b(Certainly|I'd be happy to|As an AI|Happy to help)\\b" <<<"$text"; then
        err "AI filler language in $label."
    fi
    if grep -qiE '\b(seamless|robust|powerful|elegant|streamlined|polished|enhanced|refined)\b' <<<"$text"; then
        err "Marketing adjective in $label."
    fi
    if grep -qiE '\b(Anthropic|GPT|OpenAI|Copilot)\b' <<<"$text"; then
        err "AI branding in $label."
    fi
    if _has_standalone_claude "$text"; then
        err "Standalone 'Claude' in $label (use 'Claude Code' if needed)."
    fi
    if grep -qi 'Co-Authored-By:' <<<"$text"; then
        err "Co-Authored-By trailer in $label."
    fi
}

check_subject() {
    local subject="$1" label="$2"
    if ! grep -qE "$CONVENTIONAL_RE" <<<"$subject"; then
        err "$label does not match conventional commit format: type(scope)?: description"
    fi
}

check_message() {
    local msg="$1" label="${2:-commit message}"
    if [[ -z "${msg//[[:space:]]/}" ]]; then
        err "Empty $label."
        return 0
    fi
    local subject
    subject="$(head -n 1 <<<"$msg")"
    check_subject "$subject" "Subject of $label"
    if [[ ${#subject} -gt 72 ]]; then
        warn "Subject of $label exceeds 72 characters (${#subject})."
    fi
    check_prose "$msg" "$label"
    if grep -qE '\b(WIP|FIXME|TODO|XXX|DO NOT MERGE)\b' <<<"$msg"; then
        warn "Draft marker in $label."
    fi
    local long
    long="$(tail -n +3 <<<"$msg" | awk 'length > 100 { n++ } END { print n + 0 }')"
    if [[ "$long" -gt 0 ]]; then
        warn "$long body line(s) of $label exceed 100 characters."
    fi
}

MODE=""
ARG=""
PR_NUMBER=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --message-file | --range | --title | --text-file)
            MODE="$1"
            ARG="${2:-}"
            shift 2
            ;;
        --pr)
            PR_NUMBER="${2:-}"
            shift 2
            ;;
        *)
            echo "commit-check.sh: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

case "$MODE" in
    --message-file)
        # git passes the message file; drop comment lines as git does.
        check_message "$(grep -v '^#' "$ARG" || true)"
        ;;
    --range)
        while IFS= read -r sha; do
            [[ -z "$sha" ]] && continue
            msg="$(git log --format='%B' -n 1 "$sha")"
            # Merge commits (branch updates, dependency bots) are exempt.
            if grep -qE '^Merge ' <<<"$msg"; then
                continue
            fi
            check_message "$msg" "commit ${sha:0:7}"
        done < <(git rev-list --no-merges "$ARG")
        ;;
    --title)
        check_subject "$ARG" "PR title"
        max=72
        if [[ -n "$PR_NUMBER" ]]; then
            suffix=" (#${PR_NUMBER})"
            max=$((72 - ${#suffix}))
        fi
        if [[ ${#ARG} -gt "$max" ]]; then
            err "PR title is ${#ARG} chars; max $max so the squash subject stays within 72."
        fi
        check_prose "$ARG" "PR title"
        ;;
    --text-file)
        check_prose "$(cat "$ARG")" "PR description"
        ;;
    *)
        echo "Usage: commit-check.sh --message-file F | --range A..B | --title T [--pr N] | --text-file F" >&2
        exit 2
        ;;
esac

if [[ "$ERRORS" -gt 0 ]]; then
    echo "Commit standards: $ERRORS error(s), $WARNINGS warning(s)." >&2
    exit 1
fi
if [[ "$WARNINGS" -gt 0 ]]; then
    echo "Commit standards: passed with $WARNINGS warning(s)." >&2
fi
exit 0

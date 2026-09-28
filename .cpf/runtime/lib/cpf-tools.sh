#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034  # CPF_TOOL_* are outputs read by the sourcing script
# cpf-tools.sh -- tool resolution, glob matching, and policy file sets for
# the cpf checks runtime (.cpf/runtime/). Sourced by verify.sh and by the
# boundary shims; never executed directly.
#
# Path rules (the runtime runs in downstream projects, which have no
# plugin source tree):
#   - Project paths come from CPF_PROJECT_ROOT (set by the caller from
#     $CLAUDE_PROJECT_DIR, else `git rev-parse --show-toplevel`, else $PWD).
#     Never derived from this file's location.
#   - Runtime-internal paths come from this file's own directory.
#
# Tool resolution never silently uses a different version than the
# project pins:
#   python tools  <svc>/.venv/bin/<tool>, else `uv run --frozen` when a
#                 uv.lock exists; otherwise unavailable (never $PATH).
#   node tools    <root>/node_modules/.bin/<bin>; else $PATH, reported as
#                 unpinned; otherwise unavailable.
#   ShellCheck    the version in <root>/.tool-versions, installed from the
#                 upstream release and checksum-verified; else $PATH,
#                 reported as unpinned; otherwise unavailable.

CPF_RUNTIME_LIB_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# --- Glob matching ----------------------------------------------------------

# Match a path against one glob with bash `[[ == ]]` (`*` crosses `/`).
# `**/x` also matches top-level `x`; `dir/**` also matches `dir` itself.
cpf_glob_match() {
    local path="$1" glob="$2"
    [[ -z "$glob" ]] && return 1
    # shellcheck disable=SC2053  # intentional unquoted glob pattern
    if [[ $path == $glob ]]; then
        return 0
    fi
    if [[ "$glob" == */\*\* ]]; then
        local trimmed="${glob%/\*\*}"
        # shellcheck disable=SC2053
        if [[ $path == $trimmed/* || $path == "$trimmed" ]]; then
            return 0
        fi
    fi
    if [[ "$glob" == \*\*/* ]]; then
        local rest="${glob#\*\*/}"
        # shellcheck disable=SC2053
        if [[ $path == $rest || $path == */$rest ]]; then
            return 0
        fi
    fi
    return 1
}

# Return 0 if the project-relative path matches any of the given globs.
# Tried as `<rel>` and as `./<rel>` so find-style excludes (`./.git/*`,
# `*/.venv/*`) work too. Never matched as an absolute path: that would
# also match the project's ancestors.
cpf_path_matches_any() {
    local rel="$1"
    shift
    local glob
    for glob in "$@"; do
        if cpf_glob_match "$rel" "$glob" || cpf_glob_match "./$rel" "$glob"; then
            return 0
        fi
    done
    return 1
}

# --- File sets ----------------------------------------------------------------

# Print (NUL-separated) project-relative candidate files.
#   --staged   files staged for commit (added/copied/modified)
#   --tracked  committed files only (ci: build artifacts and installed
#              dependencies such as node_modules/ are never in scope)
#   default    tracked plus untracked-not-ignored files in a git work tree,
#              else every regular file outside .git/
cpf_candidate_files() {
    local mode="${1:-all}"
    (
        cd "$CPF_PROJECT_ROOT" || exit 0
        if [[ "$mode" == "--staged" ]]; then
            git diff --cached --name-only -z --diff-filter=ACM 2>/dev/null
        elif [[ "$mode" == "--tracked" ]] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            git ls-files -z --cached 2>/dev/null
        elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            git ls-files -z --cached --others --exclude-standard 2>/dev/null
        else
            find . -type f -not -path './.git/*' -print0 2>/dev/null \
                | while IFS= read -r -d '' f; do printf '%s\0' "${f#./}"; done
        fi
    )
}

# Print (NUL-separated) the files a tool checks: candidates filtered by the
# tool's include/exclude globs from .cpf/policy.json. When the policy has
# no section for the tool, the given default include globs apply (none =
# the tool is not managed and nothing is printed). For shellcheck without
# a policy, .cpf/shellcheck-excludes.txt supplies the excludes.
#   cpf_tool_files <tool> <mode> [default-include...]
cpf_tool_files() {
    local tool="$1" mode="$2"
    shift 2
    local includes=() excludes=() g
    if [[ "${POLICY_LOADED:-0}" -eq 1 ]] && cpf_policy_has_section "$tool"; then
        while IFS= read -r g; do [[ -n "$g" ]] && includes+=("$g"); done \
            < <(cpf_policy_list "$tool" include)
        while IFS= read -r g; do [[ -n "$g" ]] && excludes+=("$g"); done \
            < <(cpf_policy_list "$tool" exclude)
        [[ "${#includes[@]}" -eq 0 ]] && includes=("$@")
    else
        includes=("$@")
        if [[ "$tool" == "shellcheck" && -f "$CPF_PROJECT_ROOT/.cpf/shellcheck-excludes.txt" ]]; then
            while IFS= read -r g || [[ -n "$g" ]]; do
                g="${g%$'\r'}"
                [[ -z "$g" || "$g" == \#* ]] && continue
                excludes+=("$g")
            done <"$CPF_PROJECT_ROOT/.cpf/shellcheck-excludes.txt"
        fi
    fi
    [[ "${#includes[@]}" -eq 0 ]] && return 0

    local f
    while IFS= read -r -d '' f; do
        [[ -f "$CPF_PROJECT_ROOT/$f" ]] || continue
        # The projected runtime is cpf's code, managed by upgrade; the
        # project cannot fix findings in it, so it is never in scope.
        [[ "$f" == .cpf/runtime/* ]] && continue
        cpf_path_matches_any "$f" "${includes[@]}" || continue
        if [[ "${#excludes[@]}" -gt 0 ]] && cpf_path_matches_any "$f" "${excludes[@]}"; then
            continue
        fi
        printf '%s\0' "$f"
    done < <(cpf_candidate_files "$mode")
}

# Return 0 if .cpf/policy.json declares hooks.<tool>.
cpf_policy_has_section() {
    local file
    file="$(cpf_policy_file)"
    jq -e --arg t "$1" '.hooks | has($t)' "$file" >/dev/null 2>&1
}

# --- Tool resolution ------------------------------------------------------------

# Resolve a pinned Python tool for a service directory. Sets CPF_TOOL_CMD.
cpf_python_tool() {
    local svc_dir="$1" tool="$2"
    CPF_TOOL_CMD=()
    if [[ -x "$svc_dir/.venv/bin/$tool" ]]; then
        CPF_TOOL_CMD=("$svc_dir/.venv/bin/$tool")
        return 0
    fi
    if command -v uv >/dev/null 2>&1 \
        && [[ -f "$svc_dir/uv.lock" || -f "$CPF_PROJECT_ROOT/uv.lock" ]]; then
        CPF_TOOL_CMD=(uv run --frozen --project "$svc_dir" "$tool")
        return 0
    fi
    return 1
}

# Resolve a node CLI. Sets CPF_TOOL_CMD and CPF_TOOL_PINNED (1/0).
cpf_node_tool() {
    local bin="$1"
    CPF_TOOL_CMD=()
    CPF_TOOL_PINNED=0
    if [[ -x "$CPF_PROJECT_ROOT/node_modules/.bin/$bin" ]]; then
        CPF_TOOL_CMD=("$CPF_PROJECT_ROOT/node_modules/.bin/$bin")
        CPF_TOOL_PINNED=1
        return 0
    fi
    if command -v "$bin" >/dev/null 2>&1; then
        CPF_TOOL_CMD=("$bin")
        return 0
    fi
    return 1
}

# Resolve shellcheck. Sets CPF_TOOL_CMD and CPF_TOOL_PINNED (1/0).
cpf_shellcheck_tool() {
    CPF_TOOL_CMD=()
    CPF_TOOL_PINNED=0
    local bin
    if bin="$(CPF_PROJECT_ROOT="$CPF_PROJECT_ROOT" \
        bash "$CPF_RUNTIME_LIB_DIR/cpf-shellcheck.sh" --print-path 2>/dev/null)"; then
        CPF_TOOL_CMD=("$bin")
        CPF_TOOL_PINNED=1
        return 0
    fi
    if command -v shellcheck >/dev/null 2>&1; then
        CPF_TOOL_CMD=(shellcheck)
        return 0
    fi
    return 1
}

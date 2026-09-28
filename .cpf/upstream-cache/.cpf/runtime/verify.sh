#!/bin/bash
# shellcheck shell=bash
# cpf checks runtime: the single implementation of cpf's quality checks.
# Every boundary calls this script; none re-implements a check.
#
#   verify.sh --boundary agent          Claude Code Stop hook (plugin shim)
#   verify.sh --boundary git [--staged] git pre-commit hook
#   verify.sh --boundary ci             CI templates (GitHub, GitLab, Jenkins)
#
# What runs where:
#   static linters   prettier, markdownlint, shellcheck over the file sets
#                    in .cpf/policy.json (all boundaries; staged files only
#                    with --staged)
#   staged files     per-file language lint on staged files (git): eslint,
#                    ruff check + format --check, gofmt/go vet, YAML syntax
#   project checks   verify-quality orchestrator: built-in walk, `task`, or
#                    `custom` (agent)
#
# Exit codes: 0 pass (possibly with warnings), 2 at least one check failed.
# At the agent boundary an internal error exits 0 (fail open, so a broken
# hook never traps a session); at git and ci it fails.
#
# Paths: the project root is $CLAUDE_PROJECT_DIR, else the git top level,
# else $PWD. It is never derived from this script's location, which may be
# a symlink or a copy. Runtime files are found relative to this script.
#
# REMOVE AT v0.2.0 markers tag the legacy fallback (no .cpf/policy.json).

set -euo pipefail

BOUNDARY="agent"
STAGED_MODE="all"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --boundary)
            BOUNDARY="${2:-}"
            shift 2
            ;;
        --boundary=*)
            BOUNDARY="${1#--boundary=}"
            shift
            ;;
        --staged)
            STAGED_MODE="--staged"
            shift
            ;;
        *)
            echo "verify.sh: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done
case "$BOUNDARY" in
    agent | git | ci) ;;
    *)
        echo "verify.sh: --boundary must be agent, git, or ci (got \"$BOUNDARY\")" >&2
        exit 2
        ;;
esac
# Which files the static linters see: staged (git --staged), committed
# only (ci), or tracked plus untracked-not-ignored (agent).
FILE_MODE="$STAGED_MODE"
if [[ "$BOUNDARY" == "ci" && "$STAGED_MODE" == "all" ]]; then
    FILE_MODE="--tracked"
fi
if [[ "$BOUNDARY" == "agent" ]]; then
    trap 'exit 0' ERR
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "cpf: jq not found; checks cannot run (run /cpf:specforge doctor)" >&2
    [[ "$BOUNDARY" == "agent" ]] && exit 0
    exit 2
fi

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export CPF_PROJECT_ROOT="$PROJECT_ROOT"
CPF_RUNTIME_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
POLICY_LIB="$CPF_RUNTIME_DIR/lib/cpf-policy.sh"
# shellcheck source=lib/cpf-tools.sh
# shellcheck disable=SC1091
source "$CPF_RUNTIME_DIR/lib/cpf-tools.sh"

# Per-run state shared between dispatchers and the legacy walker.
FAILED=0
WARNINGS=0
CHECKS_RUN=0

# Lines of tool output shown under a FAIL/WARN/INTERNAL line, and the
# per-line character cap. Overridable for tests and noisy tools.
CPF_OUTPUT_TAIL_LINES="${CPF_OUTPUT_TAIL_LINES:-20}"
CPF_OUTPUT_LINE_CHARS="${CPF_OUTPUT_LINE_CHARS:-240}"

# Run "$@" with stdout+stderr captured. Sets _CPF_RC and _CPF_OUT. The
# `|| _CPF_RC=$?` form keeps a failing tool from tripping the ERR trap
# (which would exit 0 and silently pass the gate).
_cpf_capture() {
    _CPF_RC=0
    _CPF_OUT="$("$@" 2>&1)" || _CPF_RC=$?
}

# Same as _cpf_capture, but runs "$@" from $PROJECT_ROOT. The cd happens
# inside the command substitution's subshell, so it does not leak.
_cpf_capture_in_root() {
    _CPF_RC=0
    _CPF_OUT="$(cd "$PROJECT_ROOT" && "$@" 2>&1)" || _CPF_RC=$?
}

# Print the tail of the last captured output to stderr so the agent can see
# which file/rule/test failed. No-op when the tool printed nothing.
_cpf_emit_tail() {
    [[ -n "${_CPF_OUT:-}" ]] || return 0
    printf '%s\n' "$_CPF_OUT" \
        | tail -n "$CPF_OUTPUT_TAIL_LINES" \
        | cut -c "1-$CPF_OUTPUT_LINE_CHARS" \
        | sed 's/^/      | /' >&2
}

run_check() {
    local name="$1"
    shift
    echo "  [check] $name"
    _cpf_capture "$@"
    if [[ "$_CPF_RC" -eq 0 ]]; then
        echo "    PASS"
    else
        echo "    FAIL: $name" >&2
        _cpf_emit_tail
        FAILED=$((FAILED + 1))
    fi
    CHECKS_RUN=$((CHECKS_RUN + 1))
}

run_optional_check() {
    local name="$1"
    shift
    echo "  [optional] $name"
    _cpf_capture "$@"
    if [[ "$_CPF_RC" -eq 0 ]]; then
        echo "    PASS"
    else
        echo "    WARN: $name" >&2
        _cpf_emit_tail
        WARNINGS=$((WARNINGS + 1))
    fi
    CHECKS_RUN=$((CHECKS_RUN + 1))
}

# ---------------------------------------------------------------------------
# INFRA-025 helpers for the Python branch of the legacy walker.
#
# These two helpers are scoped to this script (single call site) rather than
# promoted to lib/. They do NOT carry
# the `# REMOVE AT v0.2.0` marker because the per-service runner contract is
# permanent; only the surrounding walker scaffolding is slated for removal.
# ---------------------------------------------------------------------------

# Read the per-service opt-out list from `[tool.cpf.hooks] skip = [...]` in
# the given service's pyproject.toml. Pure-bash parsing -- no Python or jq
# dependency. Returns one tool name per line on stdout. Missing file or
# missing section => empty output.
cpf_pyproject_skip_list() {
    local svc_dir="$1"
    local pyproject="$svc_dir/pyproject.toml"
    [[ -f "$pyproject" ]] || return 0

    awk '
        /^\[tool\.cpf\.hooks\]/ { in_section = 1; next }
        /^\[/ { in_section = 0 }
        in_section && /^[[:space:]]*skip[[:space:]]*=/ {
            line = $0
            sub(/^[^=]*=/, "", line)
            # Strip everything outside the bracket pair, then split on commas.
            sub(/^[[:space:]]*\[/, "", line)
            sub(/\][[:space:]]*$/, "", line)
            n = split(line, parts, ",")
            for (i = 1; i <= n; i++) {
                tool = parts[i]
                gsub(/[[:space:]"'"'"']/, "", tool)
                if (length(tool) > 0) {
                    print tool
                }
            }
        }
    ' "$pyproject"
}

# Return 0 if the given pyproject.toml has the `[tool.<name>]` section.
cpf_pyproject_has_section() {
    local svc_dir="$1" section="$2"
    local pyproject="$svc_dir/pyproject.toml"
    [[ -f "$pyproject" ]] || return 1
    grep -qE "^\[tool\.${section}(\..*)?\]" "$pyproject"
}

# Resolve the runner for <tool> in <svc_dir>. Sets the global
# `_CPF_RUNNER_CMD` array to the argv prefix that should be invoked. Returns
# 0 if a runner was resolved, 1 if neither `.venv/bin/<tool>` exists nor
# `uv` plus a lockfile is available. NEVER falls back to bare `<tool>` from
# $PATH -- that is the central contract of INFRA-025.
#
# The uv fallback passes `--frozen` so the hook never re-locks: `uv.lock` is
# read, never written. `--frozen` errors without a lockfile, so the fallback
# is only taken when `uv.lock` exists in the service dir or at the project
# root (uv workspace); otherwise the tool counts as unresolved.
resolve_python_runner() {
    local svc_dir="$1" tool="$2"
    _CPF_RUNNER_CMD=()
    if cpf_python_tool "$svc_dir" "$tool"; then
        _CPF_RUNNER_CMD=("${CPF_TOOL_CMD[@]}")
        return 0
    fi
    return 1
}

# INFRA-026: classify pytest exit codes in the Python branch of the legacy
# walker. Cannot reuse run_check because run_check collapses every nonzero
# exit into a FAIL increment, which collides with exit-code-5 SKIP/WARN
# semantics.
#
#   0         -> PASS        (CHECKS_RUN++)
#   1         -> FAIL        (stderr: "FAIL: Pytest (<rel_dir>)", FAILED++)
#   2|3|4|*   -> INTERNAL    (stderr: "INTERNAL: Pytest (<rel_dir>) rc=<N>",
#                            FAILED++; "any other" exit code also funnels
#                            here)
#   5         -> depends on $on_missing_tests:
#                 skip -> stderr "SKIP: no tests (<rel_dir>)", no counters
#                         other than CHECKS_RUN
#                 warn -> stderr "WARN: no tests (<rel_dir>)", WARNINGS++
#
# Usage:
#   run_pytest_classified <rel_dir> <on_missing_tests> <cmd...>
# where <cmd...> is the full argv (resolver prefix + svc_dir + --tb=no -q).
run_pytest_classified() {
    local rel_dir="$1" on_missing_tests="$2"
    shift 2
    echo "  [check] Pytest ($rel_dir)"
    _cpf_capture "$@"
    local rc="$_CPF_RC"
    CHECKS_RUN=$((CHECKS_RUN + 1))
    case "$rc" in
        0)
            echo "    PASS"
            ;;
        1)
            echo "    FAIL: Pytest ($rel_dir)" >&2
            _cpf_emit_tail
            FAILED=$((FAILED + 1))
            ;;
        5)
            case "$on_missing_tests" in
                warn)
                    echo "    WARN: no tests ($rel_dir)" >&2
                    WARNINGS=$((WARNINGS + 1))
                    ;;
                skip | *)
                    echo "    SKIP: no tests ($rel_dir)" >&2
                    ;;
            esac
            ;;
        *)
            echo "    INTERNAL: Pytest ($rel_dir) rc=$rc" >&2
            _cpf_emit_tail
            FAILED=$((FAILED + 1))
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Legacy walker. Preserved from the alpha.11 hook body verbatim except for
# the Python branch, which INFRA-025 refactored in place to use per-service
# runner resolution. The Node, Rust, and Go branches are unchanged. The
# function is wrapped so the dispatcher can call it for `orchestrator = "none"`
# and the ADR-006 missing-policy fallback can route through the same code
# path.
# REMOVE AT v0.2.0
# ---------------------------------------------------------------------------
run_legacy_walk_and_detect() {
    # ADR-006 fallback path may invoke the walker before policy is loaded.
    # Default `on_missing_runner` to "warn" so both code paths agree.
    local on_missing_runner="${ON_MISSING_RUNNER:-warn}"
    if [[ "$POLICY_LOADED" -eq 1 ]]; then
        local policy_runner
        policy_runner="$(cpf_policy_get verify-quality on_missing_runner)"
        [[ -n "$policy_runner" ]] && on_missing_runner="$policy_runner"
    fi
    case "$on_missing_runner" in
        warn | skip) ;;
        *) on_missing_runner="warn" ;;
    esac

    # INFRA-026: resolve on_missing_tests once for the whole walk. The
    # fallback path (no policy loaded) defaults to skip so exit code 5
    # behaves the same as the documented schema default.
    local on_missing_tests="${ON_MISSING_TESTS:-skip}"
    if [[ "$POLICY_LOADED" -eq 1 ]]; then
        local policy_tests
        policy_tests="$(cpf_policy_get verify-quality on_missing_tests)"
        [[ -n "$policy_tests" ]] && on_missing_tests="$policy_tests"
    fi
    case "$on_missing_tests" in
        warn | skip) ;;
        *) on_missing_tests="skip" ;;
    esac

    local search_dirs=("$PROJECT_ROOT")

    # Also check one level of subdirectories for monorepo support
    for dir in "$PROJECT_ROOT"/*/; do
        [[ -d "$dir" ]] && search_dirs+=("$dir")
    done

    local found_project=false

    for dir in "${search_dirs[@]}"; do
        [[ ! -d "$dir" ]] && continue
        local rel_dir="${dir#"$PROJECT_ROOT"/}"
        [[ "$rel_dir" == "$dir" ]] && rel_dir="."
        [[ "$rel_dir" == */ ]] && rel_dir="${rel_dir%/}"

        # Node.js
        if [[ -f "$dir/package.json" ]]; then
            found_project=true
            echo ""
            echo "Node.js project: $rel_dir"

            if [[ -f "$dir/node_modules/.bin/eslint" ]]; then
                run_optional_check "ESLint ($rel_dir)" bash -c "cd '$dir' && npx eslint . --quiet"
            fi

            if [[ -f "$dir/tsconfig.json" ]]; then
                run_check "TypeScript ($rel_dir)" bash -c "cd '$dir' && npx tsc --noEmit"
            fi

            if grep -q '"test"' "$dir/package.json" 2>/dev/null; then
                run_check "Tests ($rel_dir)" bash -c "cd '$dir' && npm test"
            fi
        fi

        # Python (INFRA-025: per-service runner resolution; never falls back
        # to bare $PATH binaries). Baseline lint+test pair is always
        # attempted; type-check and formatter are attempted only if the
        # corresponding pyproject section is present. Per-service opt-out via
        # [tool.cpf.hooks] skip in the service's pyproject.toml runs BEFORE
        # resolver attempts.
        if [[ -f "$dir/pyproject.toml" ]]; then
            found_project=true
            echo ""
            echo "Python project: $rel_dir"

            local svc_dir="${dir%/}"
            local svc_tools=()
            svc_tools+=("ruff")
            svc_tools+=("pytest")
            if cpf_pyproject_has_section "$svc_dir" "mypy"; then
                svc_tools+=("mypy")
            fi
            if cpf_pyproject_has_section "$svc_dir" "black"; then
                svc_tools+=("black")
            fi

            local svc_skip_list
            svc_skip_list="$(cpf_pyproject_skip_list "$svc_dir")"

            local missing_resolver=0
            local resolved_any=0
            local svc_tool
            for svc_tool in "${svc_tools[@]}"; do
                # Per-service opt-out is applied first.
                if [[ -n "$svc_skip_list" ]] \
                    && printf '%s\n' "$svc_skip_list" \
                        | grep -Fxq "$svc_tool"; then
                    echo "  SKIP: opted out ($svc_tool)" >&2
                    continue
                fi

                if ! resolve_python_runner "$svc_dir" "$svc_tool"; then
                    missing_resolver=1
                    continue
                fi
                resolved_any=1

                case "$svc_tool" in
                    ruff)
                        run_check "Ruff lint ($rel_dir)" \
                            "${_CPF_RUNNER_CMD[@]}" check "$svc_dir"
                        run_optional_check "Ruff format ($rel_dir)" \
                            "${_CPF_RUNNER_CMD[@]}" format --check "$svc_dir"
                        ;;
                    pytest)
                        # INFRA-026: classifier below maps pytest exit codes
                        # explicitly (0 PASS, 1 FAIL, 2-4 INTERNAL FAIL, 5
                        # SKIP/WARN per on_missing_tests). Preserves the
                        # `--tb=no -q` flags INFRA-025 established.
                        run_pytest_classified "$rel_dir" "$on_missing_tests" \
                            "${_CPF_RUNNER_CMD[@]}" "$svc_dir" --tb=no -q
                        ;;
                    mypy)
                        run_check "Mypy ($rel_dir)" \
                            "${_CPF_RUNNER_CMD[@]}" "$svc_dir"
                        ;;
                    black)
                        run_optional_check "Black ($rel_dir)" \
                            "${_CPF_RUNNER_CMD[@]}" --check "$svc_dir"
                        ;;
                esac
            done

            if [[ "$missing_resolver" -eq 1 && "$resolved_any" -eq 0 ]]; then
                case "$on_missing_runner" in
                    skip)
                        echo "  SKIP: no resolver for $rel_dir" >&2
                        ;;
                    warn | *)
                        echo "  WARN: no resolver for $rel_dir" >&2
                        WARNINGS=$((WARNINGS + 1))
                        ;;
                esac
            fi
        elif [[ -f "$dir/requirements.txt" ]]; then
            # Pure requirements.txt projects (no pyproject.toml) cannot be
            # resolved per-service; emit WARN/SKIP per policy and skip.
            found_project=true
            echo ""
            echo "Python project: $rel_dir"
            case "$on_missing_runner" in
                skip)
                    echo "  SKIP: no resolver for $rel_dir" >&2
                    ;;
                warn | *)
                    echo "  WARN: no resolver for $rel_dir" >&2
                    WARNINGS=$((WARNINGS + 1))
                    ;;
            esac
        fi

        # Rust
        if [[ -f "$dir/Cargo.toml" ]]; then
            found_project=true
            echo ""
            echo "Rust project: $rel_dir"

            # Ensure cargo is on PATH (rustup default location)
            if [[ -d "$HOME/.cargo/bin" ]]; then
                export PATH="$HOME/.cargo/bin:$PATH"
            fi

            if command -v cargo >/dev/null 2>&1; then
                run_check "Cargo check ($rel_dir)" cargo check --manifest-path "$dir/Cargo.toml"
                run_check "Clippy ($rel_dir)" cargo clippy --manifest-path "$dir/Cargo.toml" -- -D warnings
                run_optional_check "Cargo test compile ($rel_dir)" cargo test --manifest-path "$dir/Cargo.toml" --no-run
            else
                echo "  Skipping: cargo not found"
            fi
        fi

        # Go
        if [[ -f "$dir/go.mod" ]]; then
            found_project=true
            echo ""
            echo "Go project: $rel_dir"

            (cd "$dir" && run_check "go vet ($rel_dir)" go vet ./...)
            (cd "$dir" && run_optional_check "go test ($rel_dir)" go test ./... -count=1)
        fi
    done

    if [[ "$found_project" == "false" ]]; then
        echo "No recognized project type found. Skipping quality checks."
    fi
}
# END run_legacy_walk_and_detect -- REMOVE AT v0.2.0

# ---------------------------------------------------------------------------
# Task orchestrator. ADR-005 fixed convention: lint failures count as ERROR,
# test failures count as WARNING. Both targets are invoked unconditionally.
# ---------------------------------------------------------------------------
run_task_orchestrator() {
    if ! command -v task >/dev/null 2>&1; then
        echo "  WARN: task binary not on PATH; skipping task orchestrator" >&2
        WARNINGS=$((WARNINGS + 1))
        return 0
    fi

    echo ""
    echo "Task orchestrator (cwd: $PROJECT_ROOT)"

    echo "  [check] task lint"
    _cpf_capture_in_root task lint
    if [[ "$_CPF_RC" -eq 0 ]]; then
        echo "    PASS"
    else
        echo "    FAIL: task lint" >&2
        _cpf_emit_tail
        FAILED=$((FAILED + 1))
    fi
    CHECKS_RUN=$((CHECKS_RUN + 1))

    echo "  [optional] task test"
    _cpf_capture_in_root task test
    if [[ "$_CPF_RC" -eq 0 ]]; then
        echo "    PASS"
    else
        echo "    WARN: task test" >&2
        _cpf_emit_tail
        WARNINGS=$((WARNINGS + 1))
    fi
    CHECKS_RUN=$((CHECKS_RUN + 1))
}

# ---------------------------------------------------------------------------
# Custom orchestrator. Runs the user-supplied command via `sh -c`. Exit code
# is mapped through the hook's severity field per ADR-005:
#   severity=error   -> nonzero exit increments FAILED (blocks stop)
#   severity=warning -> nonzero exit increments WARNINGS
#   severity=info    -> nonzero exit logged but does not affect counters
# ---------------------------------------------------------------------------
run_custom_orchestrator() {
    local custom_command="$1" severity="$2"

    if [[ -z "$custom_command" ]]; then
        echo "ERROR: orchestrator=custom but custom_command is empty" >&2
        FAILED=$((FAILED + 1))
        return 0
    fi

    echo ""
    echo "Custom orchestrator (cwd: $PROJECT_ROOT, severity: $severity)"
    echo "  [check] $custom_command"

    _cpf_capture_in_root sh -c "$custom_command"
    local rc="$_CPF_RC"
    CHECKS_RUN=$((CHECKS_RUN + 1))

    if [[ "$rc" -eq 0 ]]; then
        echo "    PASS"
        return 0
    fi

    case "$severity" in
        error)
            echo "    FAIL: custom_command (rc=$rc)" >&2
            _cpf_emit_tail
            FAILED=$((FAILED + 1))
            ;;
        warning)
            echo "    WARN: custom_command (rc=$rc)" >&2
            _cpf_emit_tail
            WARNINGS=$((WARNINGS + 1))
            ;;
        info)
            echo "    INFO: custom_command (rc=$rc)"
            ;;
        *)
            echo "    FAIL: custom_command (rc=$rc, unknown severity \"$severity\")" >&2
            _cpf_emit_tail
            FAILED=$((FAILED + 1))
            ;;
    esac
}


# ---------------------------------------------------------------------------
# Static linters. File sets come from .cpf/policy.json include/exclude
# (cpf_tool_files). prettier and markdownlint run only when the policy has a
# section for them; shellcheck runs on **/*.sh by default. Each tool's
# policy severity applies (error blocks, warning warns, info reports);
# ShellCheck uses verify-quality.severity. Tools resolve to the project's
# pinned copies (see lib/cpf-tools.sh); an unpinned fallback is noted.
# ---------------------------------------------------------------------------

# A tool the policy needs cannot be resolved. CI must not pass by
# skipping, so the ci boundary fails; agent and git warn (a laptop
# without node must not block every stop or commit).
_cpf_tool_missing() {
    local message="$1"
    if [[ "$BOUNDARY" == "ci" ]]; then
        echo "  FAIL: $message" >&2
        FAILED=$((FAILED + 1))
    else
        echo "  WARN: $message" >&2
        WARNINGS=$((WARNINGS + 1))
    fi
}

# Map a nonzero tool result through a severity. Args: label severity.
_cpf_report_failure() {
    local label="$1" severity="$2"
    case "$severity" in
        warning)
            echo "  WARN: $label" >&2
            _cpf_emit_tail
            WARNINGS=$((WARNINGS + 1))
            ;;
        info)
            echo "  INFO: $label"
            ;;
        error | *)
            echo "  FAIL: $label" >&2
            _cpf_emit_tail
            FAILED=$((FAILED + 1))
            ;;
    esac
}

_cpf_tool_severity() {
    local tool="$1" sev=""
    if [[ "$POLICY_LOADED" -eq 1 ]]; then
        sev="$(cpf_policy_get "$tool" severity)"
    fi
    printf '%s\n' "${sev:-error}"
}

run_shellcheck_pass() {
    if ! cpf_shellcheck_tool; then
        _cpf_tool_missing "shellcheck binary not on PATH; skipping shell lint"
        return 0
    fi
    local sc_cmd=("${CPF_TOOL_CMD[@]}")
    [[ "$CPF_TOOL_PINNED" -eq 1 ]] \
        || echo "  note: shellcheck is not pinned in .tool-versions"

    local files=() f
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(cpf_tool_files shellcheck "$FILE_MODE" '**/*.sh')

    # No shell files staged is normal for a commit; say nothing.
    if [[ "${#files[@]}" -eq 0 && "$STAGED_MODE" == "--staged" ]]; then
        return 0
    fi
    echo ""
    if [[ "${#files[@]}" -eq 0 ]]; then
        # Say so instead of skipping silently: an over-broad exclude
        # would otherwise look exactly like "nothing to check".
        echo "Shellcheck (0 files; check the shellcheck excludes in .cpf/policy.json if unexpected)"
        return 0
    fi

    echo "Shellcheck (${#files[@]} file(s))"
    CHECKS_RUN=$((CHECKS_RUN + 1))
    _cpf_capture_in_root "${sc_cmd[@]}" -x -f gcc "${files[@]}"
    if [[ "$_CPF_RC" -eq 0 ]]; then
        echo "  PASS"
        return 0
    fi
    _cpf_report_failure "shellcheck reported issues" "${SEVERITY:-error}"
}

# Staged content of a file (git boundary) or the working-tree file.
_cpf_file_content() {
    local f="$1"
    if [[ "$STAGED_MODE" == "--staged" ]]; then
        git -C "$PROJECT_ROOT" show ":$f" 2>/dev/null
    else
        cat "$PROJECT_ROOT/$f"
    fi
}

run_prettier_pass() {
    local files=() f
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(cpf_tool_files prettier "$FILE_MODE")
    [[ "${#files[@]}" -eq 0 ]] && return 0
    echo ""
    if ! cpf_node_tool prettier; then
        echo "Prettier (${#files[@]} file(s))"
        _cpf_tool_missing "prettier not installed (npm ci); files not checked"
        return 0
    fi
    local cmd=("${CPF_TOOL_CMD[@]}")
    echo "Prettier (${#files[@]} file(s))"
    [[ "$CPF_TOOL_PINNED" -eq 1 ]] || echo "  note: prettier is not pinned (no node_modules)"
    CHECKS_RUN=$((CHECKS_RUN + 1))
    if [[ "$STAGED_MODE" == "--staged" ]]; then
        # Check the staged content, not the working tree.
        local bad=()
        for f in "${files[@]}"; do
            if ! _cpf_file_content "$f" | (cd "$PROJECT_ROOT" && "${cmd[@]}" --check --stdin-filepath "$f") >/dev/null 2>&1; then
                bad+=("$f")
            fi
        done
        _CPF_OUT="$(printf '%s\n' "${bad[@]}")"
        _CPF_RC="${#bad[@]}"
    else
        _cpf_capture_in_root "${cmd[@]}" --check "${files[@]}"
    fi
    if [[ "$_CPF_RC" -eq 0 ]]; then
        echo "  PASS"
        return 0
    fi
    _cpf_report_failure "prettier: files not formatted" "$(_cpf_tool_severity prettier)"
}

run_markdownlint_pass() {
    local files=() f
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(cpf_tool_files markdownlint "$FILE_MODE")
    [[ "${#files[@]}" -eq 0 ]] && return 0
    echo ""
    if ! cpf_node_tool markdownlint-cli2; then
        echo "Markdownlint (${#files[@]} file(s))"
        _cpf_tool_missing "markdownlint-cli2 not installed (npm ci); files not checked"
        return 0
    fi
    local cmd=("${CPF_TOOL_CMD[@]}")
    echo "Markdownlint (${#files[@]} file(s))"
    [[ "$CPF_TOOL_PINNED" -eq 1 ]] || echo "  note: markdownlint-cli2 is not pinned (no node_modules)"
    CHECKS_RUN=$((CHECKS_RUN + 1))
    if [[ "$STAGED_MODE" == "--staged" ]]; then
        local out="" rc=0 one
        for f in "${files[@]}"; do
            one="$(_cpf_file_content "$f" | (cd "$PROJECT_ROOT" && "${cmd[@]}" -) 2>&1)" \
                || { rc=1; out+="$f:"$'\n'"$one"$'\n'; }
        done
        _CPF_OUT="$out"
        _CPF_RC="$rc"
    else
        # A leading ':' makes markdownlint-cli2 treat each argument as a
        # literal path rather than a glob.
        _cpf_capture_in_root "${cmd[@]}" "${files[@]/#/:}"
    fi
    if [[ "$_CPF_RC" -eq 0 ]]; then
        echo "  PASS"
        return 0
    fi
    _cpf_report_failure "markdownlint reported issues" "$(_cpf_tool_severity markdownlint)"
}

# ---------------------------------------------------------------------------
# Staged-file language lint (git boundary). Per staged file, resolved from
# the nearest project marker directory: eslint (if installed in the
# project), ruff check + format --check (pinned), gofmt/go vet, YAML
# syntax (the project's venv python, else python3, only when PyYAML is
# importable).
# ---------------------------------------------------------------------------

_cpf_find_marker_root() {
    local dir="$1"
    while [[ "$dir" != "." && "$dir" != "/" ]]; do
        if [[ -f "$PROJECT_ROOT/$dir/package.json" || -f "$PROJECT_ROOT/$dir/Cargo.toml" \
            || -f "$PROJECT_ROOT/$dir/pyproject.toml" || -f "$PROJECT_ROOT/$dir/go.mod" ]]; then
            printf '%s\n' "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    local marker
    for marker in package.json Cargo.toml pyproject.toml go.mod; do
        if [[ -f "$PROJECT_ROOT/$marker" ]]; then
            printf '.\n'
            return 0
        fi
    done
    return 1
}

_cpf_yaml_python() {
    local root="$1" py
    for py in "$PROJECT_ROOT/$root/.venv/bin/python" "$PROJECT_ROOT/.venv/bin/python" python3; do
        if command -v "$py" >/dev/null 2>&1 \
            && "$py" -c "import yaml" >/dev/null 2>&1; then
            printf '%s\n' "$py"
            return 0
        fi
    done
    return 1
}

_cpf_lint_one_staged_file() {
    local file="$1" ext="${1##*.}" dir root
    case "$file" in
        *_pb2.py | *_pb2_grpc.py) return 0 ;;
    esac
    dir="$(dirname "$file")"
    root="$(_cpf_find_marker_root "$dir")" || return 0
    local abs_root="$PROJECT_ROOT"
    [[ "$root" != "." ]] && abs_root="$PROJECT_ROOT/$root"

    case "$ext" in
        ts | tsx | js | jsx)
            if [[ -x "$abs_root/node_modules/.bin/eslint" ]]; then
                (cd "$PROJECT_ROOT" && "$abs_root/node_modules/.bin/eslint" "$file" --quiet) || return 1
            fi
            ;;
        py)
            if cpf_python_tool "$abs_root" ruff; then
                (cd "$PROJECT_ROOT" && "${CPF_TOOL_CMD[@]}" check "$file") || return 1
                (cd "$PROJECT_ROOT" && "${CPF_TOOL_CMD[@]}" format --check "$file") || return 1
            fi
            ;;
        go)
            if command -v gofmt >/dev/null 2>&1; then
                if [[ -n "$(cd "$PROJECT_ROOT" && gofmt -l "$file" 2>/dev/null)" ]]; then
                    echo "  gofmt: $file is not formatted (run gofmt -w)" >&2
                    return 1
                fi
            fi
            if command -v golangci-lint >/dev/null 2>&1; then
                (cd "$abs_root" && golangci-lint run "./${dir#"$root"/}/...") || return 1
            elif command -v go >/dev/null 2>&1; then
                (cd "$abs_root" && go vet "./${dir#"$root"/}/...") || return 1
            fi
            ;;
        yml | yaml)
            local py
            if py="$(_cpf_yaml_python "$root")"; then
                _cpf_file_content "$file" | "$py" -c "
import sys, yaml
try:
    yaml.safe_load(sys.stdin.read())
except yaml.YAMLError as e:
    print(f'  YAML error: {e}', file=sys.stderr)
    sys.exit(1)
" || return 1
            fi
            ;;
    esac
    return 0
}

run_staged_file_checks() {
    local files=() f
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(cpf_candidate_files --staged)
    [[ "${#files[@]}" -eq 0 ]] && return 0
    echo ""
    echo "Staged files (${#files[@]})"
    for f in "${files[@]}"; do
        [[ -f "$PROJECT_ROOT/$f" ]] || continue
        CHECKS_RUN=$((CHECKS_RUN + 1))
        _CPF_RC=0
        _CPF_OUT="$(_cpf_lint_one_staged_file "$f" 2>&1)" || _CPF_RC=$?
        if [[ "$_CPF_RC" -ne 0 ]]; then
            echo "  LINT FAIL: $f" >&2
            _cpf_emit_tail
            FAILED=$((FAILED + 1))
        fi
    done
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
echo "=== Quality Gate ($BOUNDARY) ==="

ORCHESTRATOR=""
SEVERITY=""
CUSTOM_COMMAND=""
POLICY_LOADED=0

# ADR-006 fallback: missing or unloadable policy lib -> legacy walk.
# REMOVE AT v0.2.0 (along with the legacy walker above).
if [[ ! -f "$POLICY_LIB" ]]; then
    # REMOVE AT v0.2.0
    echo "cpf: policy loader not found, falling back to legacy walk" \
        "(REMOVE AT v0.2.0)" >&2
elif
    # shellcheck source=lib/cpf-policy.sh
    # shellcheck disable=SC1091
    ! source "$POLICY_LIB" 2>/dev/null
then
    # REMOVE AT v0.2.0
    echo "cpf: failed to source policy loader, falling back to legacy walk" \
        "(REMOVE AT v0.2.0)" >&2
else
    POLICY_FILE="$(cpf_policy_file)"
    if [[ ! -f "$POLICY_FILE" ]]; then
        # REMOVE AT v0.2.0
        echo "cpf: .cpf/policy.json missing, falling back to legacy walk" \
            "(REMOVE AT v0.2.0)" >&2
    else
        POLICY_LOADED=1
        ORCHESTRATOR="$(cpf_policy_get verify-quality orchestrator)"
        SEVERITY="$(cpf_policy_get verify-quality severity)"
        CUSTOM_COMMAND="$(cpf_policy_get verify-quality custom_command)"
        : "${SEVERITY:=error}"
    fi
fi

# Static linters run at every boundary, so a check that passes here passes
# at the next boundary too.
run_shellcheck_pass
run_prettier_pass
run_markdownlint_pass

if [[ "$BOUNDARY" == "git" ]]; then
    run_staged_file_checks
fi

if [[ "$BOUNDARY" == "agent" ]]; then
    if [[ "$POLICY_LOADED" -eq 0 ]]; then
        # REMOVE AT v0.2.0
        run_legacy_walk_and_detect
    else
        case "${ORCHESTRATOR:-none}" in
            none | "")
                run_legacy_walk_and_detect
                ;;
            task)
                run_task_orchestrator
                ;;
            custom)
                run_custom_orchestrator "$CUSTOM_COMMAND" "$SEVERITY"
                ;;
            *)
                echo "ERROR: unknown verify-quality.orchestrator \"$ORCHESTRATOR\"" >&2
                FAILED=$((FAILED + 1))
                ;;
        esac
    fi
fi

echo ""
echo "--- Summary ---"
echo "Checks run: $CHECKS_RUN"
echo "Failed: $FAILED"
echo "Warnings: $WARNINGS"

if [[ "$FAILED" -gt 0 ]]; then
    echo "" >&2
    echo "Quality gate FAILED. Fix issues before stopping." >&2
    exit 2
fi

if [[ "$WARNINGS" -gt 0 ]]; then
    echo ""
    echo "Quality gate passed with warnings."
fi

exit 0

#!/usr/bin/env bash
# shellcheck shell=bash
# cpf-shellcheck-fragment.sh -- emit a `find` exclusion fragment from
# `.cpf/shellcheck-excludes.txt` so the verify-quality hook and CI workflows
# share a single source of truth for shellcheck scope.
#
# The fragment is a sequence of `-not -path '<glob>'` arguments, one per
# non-blank, non-comment line of the excludes file. Empty file (or missing
# file) yields an empty fragment, which means `find` matches every `*.sh`.
#
# Usage (sourced):
#   source .cpf/runtime/lib/cpf-shellcheck-fragment.sh
#   cpf_shellcheck_find_fragment            # writes fragment to stdout
#   cpf_shellcheck_find_fragment <project>  # explicit project dir
#
# Usage (executable CLI):
#   cpf-shellcheck-fragment.sh emit-find-fragment [<project-dir>]
#
# The CLI form is what `eval` calls in workflow YAML embed, e.g.:
#   eval "find . -name '*.sh' \
#     $(bash .cpf/runtime/lib/cpf-shellcheck-fragment.sh emit-find-fragment) \
#     -print0 | xargs -0 shellcheck -x"
#
# Resolution: if a project dir is supplied, read
# `<project>/.cpf/shellcheck-excludes.txt`. Otherwise fall back to
# `$CLAUDE_PROJECT_DIR/.cpf/shellcheck-excludes.txt`, then to git toplevel,
# then to `$PWD`.

cpf_shellcheck_excludes_file() {
    local project_dir="${1:-}"
    if [[ -z "$project_dir" ]]; then
        project_dir="${CLAUDE_PROJECT_DIR:-}"
    fi
    if [[ -z "$project_dir" ]]; then
        project_dir="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
    fi
    printf '%s\n' "$project_dir/.cpf/shellcheck-excludes.txt"
}

cpf_shellcheck_find_fragment() {
    local file
    file="$(cpf_shellcheck_excludes_file "${1:-}")"
    [[ -f "$file" ]] || return 0
    local glob
    while IFS= read -r glob || [[ -n "$glob" ]]; do
        # Skip blank lines and comments. A trailing CR is tolerated.
        glob="${glob%$'\r'}"
        [[ -z "$glob" ]] && continue
        [[ "$glob" == \#* ]] && continue
        # The glob is intentionally single-quoted in the emitted fragment so
        # downstream `eval` keeps it as a single argument to `find`.
        printf "%s" "-not -path '$glob' "
    done <"$file"
    printf '\n'
}

if [[ "${BASH_SOURCE[0]:-}" == "${0}" ]]; then
    case "${1:-}" in
        emit-find-fragment)
            shift
            cpf_shellcheck_find_fragment "${1:-}"
            ;;
        *)
            cat >&2 <<'USAGE'
Usage: cpf-shellcheck-fragment.sh <command> [args]
Commands:
  emit-find-fragment [project-dir]   Emit `-not -path '<glob>'` arguments
                                     for find, one per excludes-file entry.
USAGE
            exit 1
            ;;
    esac
fi

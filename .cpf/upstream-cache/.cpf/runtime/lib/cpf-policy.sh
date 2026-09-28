#!/usr/bin/env bash
# cpf-policy.sh -- loader for .cpf/policy.json
#
# Usage (sourced):
#   source .cpf/runtime/lib/cpf-policy.sh
#   cpf_policy_get <hook> <field>    # scalar (empty string on missing)
#   cpf_policy_list <hook> <field>   # one line per array element
#   cpf_validate_policy [file]       # returns 0 on pass, nonzero on fail
#
# Missing hook, missing field, or missing policy file all yield empty output
# with exit 0 -- the loader is fail-open. Strict checks happen in
# cpf_validate_policy, which init and upgrade call before writing anything.
#
# Usage (executable CLI):
#   cpf-policy.sh get <hook> <field>
#   cpf-policy.sh list <hook> <field>
#   cpf-policy.sh validate [file]

# shellcheck disable=SC2034   # library file; vars are consumed by callers

cpf_policy_file() {
    if [[ -n "${CPF_POLICY_FILE:-}" ]]; then
        printf '%s\n' "$CPF_POLICY_FILE"
        return 0
    fi
    local project_dir
    project_dir="${CLAUDE_PROJECT_DIR:-}"
    if [[ -z "$project_dir" ]]; then
        project_dir="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
    fi
    printf '%s\n' "$project_dir/.cpf/policy.json"
}

cpf_policy_get() {
    local hook="${1:-}" field="${2:-}"
    [[ -z "$hook" || -z "$field" ]] && return 0
    local file
    file="$(cpf_policy_file)"
    [[ -f "$file" ]] || return 0
    jq -r --arg h "$hook" --arg f "$field" '
        .hooks[$h][$f] // "" |
        if type == "array" or type == "object" then "" else tostring end
    ' "$file" 2>/dev/null || true
}

cpf_policy_list() {
    local hook="${1:-}" field="${2:-}"
    [[ -z "$hook" || -z "$field" ]] && return 0
    local file
    file="$(cpf_policy_file)"
    [[ -f "$file" ]] || return 0
    jq -r --arg h "$hook" --arg f "$field" '
        (.hooks[$h][$f] // []) |
        if type == "array" then .[] else empty end
    ' "$file" 2>/dev/null || true
}

cpf_validate_policy() {
    local file="${1:-}"
    if [[ -z "$file" ]]; then
        file="$(cpf_policy_file)"
    fi
    if [[ ! -f "$file" ]]; then
        echo "ERROR: policy file not found: $file" >&2
        return 2
    fi
    if ! jq empty "$file" >/dev/null 2>&1; then
        echo "ERROR: $file is not valid JSON" >&2
        return 3
    fi
    if ! jq -e '(type == "object") and has("hooks") and (.hooks | type == "object")' \
        "$file" >/dev/null 2>&1; then
        echo "ERROR: $file must be an object with a top-level \"hooks\" object" >&2
        return 4
    fi
    local errors
    errors="$(jq -r '
        def allowed_keys: [
            "include","exclude","orchestrator","severity",
            "on_missing_runner","on_missing_tests","custom_command"
        ];
        def orch_values:   ["none","task","custom"];
        def sev_values:    ["error","warning","info"];
        def runner_values: ["warn","skip"];
        def tests_values:  ["warn","skip"];
        .hooks
        | to_entries[]
        | . as $e
        | [
            ( if ($e.value | has("orchestrator"))
                and (orch_values | index($e.value.orchestrator)) == null
                then "\($e.key): invalid orchestrator \"\($e.value.orchestrator)\" (allowed: \(orch_values | join(", ")))"
              else empty end ),
            ( if ($e.value | has("severity")) | not
                then "\($e.key): missing required field \"severity\""
              elif (sev_values | index($e.value.severity)) == null
                then "\($e.key): invalid severity \"\($e.value.severity)\" (allowed: \(sev_values | join(", ")))"
              else empty end ),
            ( if ($e.value | has("on_missing_runner"))
                and (runner_values | index($e.value.on_missing_runner)) == null
                then "\($e.key): invalid on_missing_runner \"\($e.value.on_missing_runner)\" (allowed: \(runner_values | join(", ")))"
              else empty end ),
            ( if ($e.value | has("on_missing_tests"))
                and (tests_values | index($e.value.on_missing_tests)) == null
                then "\($e.key): invalid on_missing_tests \"\($e.value.on_missing_tests)\" (allowed: \(tests_values | join(", ")))"
              else empty end ),
            ( $e.value
              | keys[]
              | . as $k
              | if (allowed_keys | index($k)) == null
                  then "\($e.key): unknown field \"\($k)\""
                else empty end ),
            ( if $e.value.orchestrator == "custom" then
                if ($e.value | has("custom_command")) | not
                  then "\($e.key): orchestrator \"custom\" requires non-empty \"custom_command\""
                elif ($e.value.custom_command | type) != "string"
                  then "\($e.key): \"custom_command\" must be a string"
                elif ($e.value.custom_command | length) == 0
                  then "\($e.key): orchestrator \"custom\" requires non-empty \"custom_command\""
                else empty end
              else empty end )
          ]
        | .[]
    ' "$file" 2>/dev/null)"

    if [[ -n "$errors" ]]; then
        echo "ERROR: policy validation failed in $file:" >&2
        printf '%s\n' "$errors" | sed 's/^/  - /' >&2
        return 5
    fi
    return 0
}

if [[ "${BASH_SOURCE[0]:-}" == "${0}" ]]; then
    case "${1:-}" in
        get)
            shift
            cpf_policy_get "$@"
            ;;
        list)
            shift
            cpf_policy_list "$@"
            ;;
        validate)
            shift
            cpf_validate_policy "$@"
            ;;
        *)
            cat >&2 <<'USAGE'
Usage: cpf-policy.sh <command> [args]
Commands:
  get <hook> <field>       Read scalar field from .cpf/policy.json
  list <hook> <field>      Read array field, one element per line
  validate [path]          Validate policy (default: resolved policy path)
USAGE
            exit 1
            ;;
    esac
fi

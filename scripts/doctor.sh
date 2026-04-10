#!/usr/bin/env bash
set -euo pipefail

# specforge doctor -- validate local dev environment against tool requirements
# Usage: scripts/doctor.sh [--output=text|json] [--registry path] [--project-dir path]

OUTPUT_FORMAT="text"
REGISTRY_PATH=""
PROJECT_DIR=""

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output=*)      OUTPUT_FORMAT="${1#--output=}" ;;
      --registry)      REGISTRY_PATH="$2"; shift ;;
      --registry=*)    REGISTRY_PATH="${1#--registry=}" ;;
      --project-dir)   PROJECT_DIR="$2"; shift ;;
      --project-dir=*) PROJECT_DIR="${1#--project-dir=}" ;;
      *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
    shift
  done
  if [[ "$OUTPUT_FORMAT" != "text" && "$OUTPUT_FORMAT" != "json" ]]; then
    echo "Invalid output format: $OUTPUT_FORMAT (must be text or json)" >&2; exit 1
  fi
  [[ -z "$PROJECT_DIR" ]] && PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
  if [[ -z "$REGISTRY_PATH" ]]; then
    REGISTRY_PATH="$PROJECT_DIR/.specify/doctor-registry.json"
  elif [[ "$REGISTRY_PATH" != /* ]]; then
    REGISTRY_PATH="$PROJECT_DIR/$REGISTRY_PATH"
  fi
}

detect_platform() { uname -s | tr '[:upper:]' '[:lower:]'; }

_has_file() { find "$1" -maxdepth 2 "${@:2}" -print -quit 2>/dev/null | grep -q .; }

detect_project_types() {
  local dir="$1" types=""
  _has_file "$dir" -name "package.json" && types="node"
  _has_file "$dir" \( -name "pyproject.toml" -o -name "setup.py" -o -name "requirements.txt" \) && types="$types python"
  _has_file "$dir" -name "Cargo.toml" && types="$types rust"
  _has_file "$dir" -name "go.mod" && types="$types go"
  _has_file "$dir" -name "Gemfile" && types="$types ruby"
  _has_file "$dir" \( -name "build.gradle" -o -name "build.gradle.kts" -o -name "pom.xml" \) && types="$types java"
  local sh_files
  sh_files="$(find "$dir" -maxdepth 2 -name "*.sh" ! -path "*/scripts/hooks/*" \
    ! -path "*/scripts/install-hooks.sh" -print -quit 2>/dev/null || true)"
  [[ -n "$sh_files" ]] && types="$types shell"
  echo "${types# }"
}

# Sets globals: TOOL_STATUS, TOOL_VERSION, TOOL_INSTALL_HINT
check_tool() {
  local tool_json="$1" platform="$2" project_types_str="$3"
  local name tier version_flag
  name="$(echo "$tool_json" | jq -r '.name')"
  tier="$(echo "$tool_json" | jq -r '.tier')"
  version_flag="$(echo "$tool_json" | jq -r '.version_flag // empty')"
  local tool_ptypes
  tool_ptypes="$(echo "$tool_json" | jq -r '.project_types[]? // empty' 2>/dev/null)"
  # Skip non-required tools that don't match project types
  if [[ "$tier" != "required" && -n "$tool_ptypes" ]]; then
    local matched=false
    for pt in $tool_ptypes; do
      for dt in $project_types_str; do
        [[ "$pt" == "$dt" ]] && { matched=true; break 2; }
      done
    done
    if [[ "$matched" == "false" ]]; then
      TOOL_STATUS="skip"; TOOL_VERSION=""; TOOL_INSTALL_HINT=""; return
    fi
  fi
  # Try primary name, then aliases
  local found_cmd=""
  if command -v "$name" >/dev/null 2>&1; then
    found_cmd="$name"
  else
    local aliases
    aliases="$(echo "$tool_json" | jq -r '.aliases[]? // empty' 2>/dev/null)"
    for alias_cmd in $aliases; do
      command -v "$alias_cmd" >/dev/null 2>&1 && { found_cmd="$alias_cmd"; break; }
    done
  fi
  local install_hint
  install_hint="$(echo "$tool_json" | jq -r --arg p "$platform" '.install[$p] // .install["generic"] // empty')"
  if [[ -n "$found_cmd" ]]; then
    TOOL_VERSION=""
    [[ -n "$version_flag" ]] && TOOL_VERSION="$($found_cmd "$version_flag" 2>&1 | head -1 || true)"
    TOOL_STATUS="pass"; TOOL_INSTALL_HINT=""
  else
    TOOL_INSTALL_HINT="$install_hint"; TOOL_VERSION=""
    case "$tier" in
      required)    TOOL_STATUS="fail" ;;
      recommended) TOOL_STATUS="warn" ;;
      *)           TOOL_STATUS="info" ;;
    esac
  fi
}

output_text() {
  local platform="$1" project_types_str="$2" results="$3"
  local passed="$4" warnings="$5" failures="$6" missing_required="$7"
  echo "specforge doctor"
  echo "================"
  echo ""
  echo "Platform: $platform"
  if [[ -n "$project_types_str" ]]; then
    echo "Project types: $(echo "$project_types_str" | tr ' ' ', ')"
  else
    echo "Project types: (none detected)"
  fi
  for tier_label in required recommended optional; do
    local tier_tools tier_count
    tier_tools="$(echo "$results" | jq -c --arg t "$tier_label" '[.[] | select(.tier == $t)]')"
    tier_count="$(echo "$tier_tools" | jq 'length')"
    [[ $tier_count -eq 0 ]] && continue
    local header
    header="$(echo "${tier_label:0:1}" | tr '[:lower:]' '[:upper:]')${tier_label:1}"
    echo ""
    echo "$header"
    local j=0
    while [[ $j -lt $tier_count ]]; do
      local t t_name t_status t_version t_hint label
      t="$(echo "$tier_tools" | jq -c ".[$j]")"
      t_name="$(echo "$t" | jq -r '.name')"
      t_status="$(echo "$t" | jq -r '.status')"
      t_version="$(echo "$t" | jq -r '.version // empty')"
      t_hint="$(echo "$t" | jq -r '.install_hint // empty')"
      case "$t_status" in
        pass) label="PASS" ;; warn) label="WARN" ;;
        fail) label="FAIL" ;; *)    label="INFO" ;;
      esac
      if [[ "$t_status" == "pass" ]]; then
        echo "  $label  $t_name $t_version"
      else
        echo "  $label  $t_name -- missing"
        [[ -n "$t_hint" ]] && echo "        Install: $t_hint"
      fi
      j=$((j + 1))
    done
  done
  echo ""
  echo "Summary: $passed passed, $warnings warning, $failures failure"
  if [[ $failures -eq 0 ]]; then
    echo "Status: READY"
  else
    echo "Status: NOT READY (missing: $missing_required)"
  fi
}

output_json() {
  local platform="$1" project_types_str="$2" results="$3"
  local passed="$4" warnings="$5" failures="$6"
  local ptypes_json="[]"
  [[ -n "$project_types_str" ]] && ptypes_json="$(echo "$project_types_str" | tr ' ' '\n' | jq -R . | jq -s .)"
  local ready_val="true"
  [[ $failures -gt 0 ]] && ready_val="false"
  jq -n --arg platform "$platform" --argjson ptypes "$ptypes_json" \
    --argjson tools "$results" --argjson passed "$passed" \
    --argjson warnings "$warnings" --argjson failures "$failures" \
    --argjson ready "$ready_val" \
    '{platform:$platform,project_types:$ptypes,tools:$tools,
      summary:{passed:$passed,warnings:$warnings,failures:$failures},ready:$ready}'
}

main() {
  parse_args "$@"
  # Bootstrap jq check -- always plain text to stderr
  if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq is required but not installed." >&2
    echo "  macOS:  brew install jq" >&2
    echo "  Linux:  sudo apt-get install -y jq" >&2
    exit 1
  fi
  local platform project_types_str
  platform="$(detect_platform)"
  project_types_str="$(detect_project_types "$PROJECT_DIR")"
  if [[ ! -f "$REGISTRY_PATH" ]]; then
    echo "Registry not found: $REGISTRY_PATH" >&2; exit 1
  fi
  local registry tool_count
  registry="$(cat "$REGISTRY_PATH")"
  tool_count="$(echo "$registry" | jq '.tools | length')"
  local results="[]" passed=0 warnings=0 failures=0 missing_required=""
  local i=0
  while [[ $i -lt $tool_count ]]; do
    local tool_json name tier
    tool_json="$(echo "$registry" | jq -c ".tools[$i]")"
    name="$(echo "$tool_json" | jq -r '.name')"
    tier="$(echo "$tool_json" | jq -r '.tier')"
    check_tool "$tool_json" "$platform" "$project_types_str"
    if [[ "$TOOL_STATUS" != "skip" ]]; then
      local entry
      entry="$(jq -n --arg name "$name" --arg tier "$tier" --arg status "$TOOL_STATUS" \
        --arg version "$TOOL_VERSION" --arg hint "$TOOL_INSTALL_HINT" \
        '{name:$name,tier:$tier,status:$status,
          version:(if $version=="" then null else $version end),
          install_hint:(if $hint=="" then null else $hint end)}')"
      results="$(echo "$results" | jq --argjson e "$entry" '. + [$e]')"
      case "$TOOL_STATUS" in
        pass) passed=$((passed + 1)) ;;
        warn) warnings=$((warnings + 1)) ;;
        fail) failures=$((failures + 1))
          [[ -n "$missing_required" ]] && missing_required="$missing_required, $name" || missing_required="$name" ;;
        *) ;;
      esac
    fi
    i=$((i + 1))
  done
  if [[ "$OUTPUT_FORMAT" == "json" ]]; then
    output_json "$platform" "$project_types_str" "$results" "$passed" "$warnings" "$failures"
  else
    output_text "$platform" "$project_types_str" "$results" "$passed" "$warnings" "$failures" "$missing_required"
  fi
  [[ $failures -gt 0 ]] && exit 1
  exit 0
}

main "$@"

#!/usr/bin/env bash
# check-deps.sh -- Verify tool dependencies across three tiers.
#
# Usage:
#   scripts/check-deps.sh required   # Tier 1: hard failures, exit 1 on miss
#   scripts/check-deps.sh service    # Tier 2: warnings only, exit 0
#   scripts/check-deps.sh optional   # Tier 3: informational, exit 0
#
# Design notes:
#   - Python is NOT checked globally; uv manages it per-venv.
#   - Uses FAIL=$((FAIL + 1)) instead of ((FAIL++)) to avoid the
#     bash arithmetic bug where ((0++)) returns exit code 1 under set -e.

set -euo pipefail

FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Extract a semver-like version string from arbitrary --version output.
# Returns the first match of MAJOR.MINOR or MAJOR.MINOR.PATCH.
extract_version() {
  grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1
}

# Return 0 if $1 >= $2 using integer semver comparison.
# Missing patch component defaults to 0.
version_gte() {
  local IFS='.'
  # shellcheck disable=SC2206
  local -a a=($1) b=($2)

  local a_major="${a[0]:-0}" a_minor="${a[1]:-0}" a_patch="${a[2]:-0}"
  local b_major="${b[0]:-0}" b_minor="${b[1]:-0}" b_patch="${b[2]:-0}"

  if (( a_major > b_major )); then return 0; fi
  if (( a_major < b_major )); then return 1; fi
  if (( a_minor > b_minor )); then return 0; fi
  if (( a_minor < b_minor )); then return 1; fi
  if (( a_patch >= b_patch )); then return 0; fi
  return 1
}

# check_tool NAME VERSION_CMD MIN_VERSION INSTALL_HINT
#   Prints a PASS / FAIL / MISSING line.
#   Returns 0 on pass, 1 on failure.
check_tool() {
  local name="$1" version_cmd="$2" min_version="$3" hint="$4"
  local actual

  if ! actual=$(eval "$version_cmd" 2>/dev/null | extract_version); then
    printf '  MISSING  %-16s  -- %s\n' "$name" "$hint"
    return 1
  fi

  if [ -z "$actual" ]; then
    printf '  MISSING  %-16s  -- %s\n' "$name" "$hint"
    return 1
  fi

  if version_gte "$actual" "$min_version"; then
    printf '  PASS     %-16s  %s >= %s\n' "$name" "$actual" "$min_version"
    return 0
  else
    printf '  FAIL     %-16s  %s < %s (need >= %s)\n' "$name" "$actual" "$min_version" "$min_version"
    return 1
  fi
}

# check_tool_warn -- same interface as check_tool but prints WARN and never
# increments FAIL.
check_tool_warn() {
  local name="$1" version_cmd="$2" min_version="$3" hint="$4"
  local actual

  if ! actual=$(eval "$version_cmd" 2>/dev/null | extract_version); then
    printf '  WARN     %-16s  not installed -- %s\n' "$name" "$hint"
    return 0
  fi

  if [ -z "$actual" ]; then
    printf '  WARN     %-16s  not installed -- %s\n' "$name" "$hint"
    return 0
  fi

  if version_gte "$actual" "$min_version"; then
    printf '  PASS     %-16s  %s >= %s\n' "$name" "$actual" "$min_version"
  else
    printf '  WARN     %-16s  %s < %s (need >= %s)\n' "$name" "$actual" "$min_version" "$min_version"
  fi
  return 0
}

# check_tool_info NAME VERSION_CMD INSTALL_HINT
#   Reports presence only; never fails.
check_tool_info() {
  local name="$1" version_cmd="$2" hint="$3"
  local actual

  if ! actual=$(eval "$version_cmd" 2>/dev/null | extract_version); then
    printf '  INFO     %-16s  not installed -- %s\n' "$name" "$hint"
    return 0
  fi

  if [ -z "$actual" ]; then
    printf '  INFO     %-16s  not installed -- %s\n' "$name" "$hint"
    return 0
  fi

  printf '  INFO     %-16s  %s\n' "$name" "$actual"
  return 0
}

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

tier_required() {
  echo "Checking required tools..."
  echo ""

  check_tool "Node.js"   "node --version"    "26.2.0" "https://nodejs.org/"              || FAIL=$((FAIL + 1))
  check_tool "npm"       "npm --version"     "11.0.0"  "(bundled with Node.js)"           || FAIL=$((FAIL + 1))
  check_tool "uv"        "uv --version"      "0.9.0"   "curl -LsSf https://astral.sh/uv/install.sh | sh" || FAIL=$((FAIL + 1))
  check_tool "go-task"   "task --version"    "3.48.0"  "https://taskfile.dev/installation/" || FAIL=$((FAIL + 1))

  echo ""
  if (( FAIL > 0 )); then
    echo "$FAIL required tool(s) missing or below minimum version."
    exit 1
  fi
  echo "All required tools present."
}

tier_service() {
  echo "Checking service-level tools..."
  echo ""

  check_tool_warn "rustc"   "rustc --version"   "1.93.0"  "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
  check_tool_warn "cargo"   "cargo --version"   "1.93.0"  "(bundled with Rust)"
  check_tool_warn "protoc"  "protoc --version"  "32.1"    "https://github.com/protocolbuffers/protobuf/releases"

  echo ""
  echo "Service tool check complete (warnings only)."
}

tier_optional() {
  echo "Checking optional tools..."
  echo ""

  check_tool_info "podman"            "podman --version"            "https://podman.io/docs/installation"
  check_tool_info "skopeo"            "skopeo --version"            "https://github.com/containers/skopeo/blob/main/install.md"
  check_tool_info "markdownlint-cli2" "markdownlint-cli2 --help"   "npm install -g markdownlint-cli2"
  check_tool_info "shellcheck"        "shellcheck --version"        "https://github.com/koalaman/shellcheck#installing"
  check_tool_info "cargo-tarpaulin"   "cargo-tarpaulin --version"   "cargo install cargo-tarpaulin"

  echo ""
  echo "Optional tool check complete (informational only)."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

usage() {
  echo "Usage: $0 {required|service|optional}"
  exit 1
}

if (( $# != 1 )); then
  usage
fi

case "$1" in
  required) tier_required ;;
  service)  tier_service  ;;
  optional) tier_optional ;;
  *)        usage         ;;
esac

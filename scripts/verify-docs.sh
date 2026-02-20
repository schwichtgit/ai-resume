#!/usr/bin/env bash
# verify-docs.sh -- Documentation audit script
#
# Checks CLAUDE.md and docs/ against the actual codebase state:
#   1. File paths referenced in CLAUDE.md exist
#   2. Documented API endpoints match actual FastAPI routes
#   3. No undocumented production routes exist
#   4. Container security claims (non-root, read-only) match Dockerfiles/compose
#
# Usage: scripts/verify-docs.sh [--fix]
#
# Exit codes:
#   0 = all checks pass
#   1 = one or more checks failed

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_MD="$REPO_ROOT/CLAUDE.md"
SECURITY_MD="$REPO_ROOT/docs/SECURITY.md"
MAIN_PY="$REPO_ROOT/api-service/ai_resume_api/main.py"
COMPOSE_YAML="$REPO_ROOT/deployment/compose.yaml"

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  TOTAL_COUNT=$((TOTAL_COUNT + 1))
  printf "  PASS  %s\n" "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  TOTAL_COUNT=$((TOTAL_COUNT + 1))
  local file="${2:-}"
  local line="${3:-}"
  if [[ -n "$file" && -n "$line" ]]; then
    printf "  FAIL  %s  (%s:%s)\n" "$1" "$file" "$line"
  elif [[ -n "$file" ]]; then
    printf "  FAIL  %s  (%s)\n" "$1" "$file"
  else
    printf "  FAIL  %s\n" "$1"
  fi
}

separator() {
  printf "\n--- %s ---\n\n" "$1"
}

# =============================================================================
# 1. File path checks (paths referenced in CLAUDE.md)
# =============================================================================
separator "File Path Verification (CLAUDE.md)"

# Paths extracted from CLAUDE.md content.
# Format: "display_path|resolve_path" where resolve_path is the actual
# filesystem path relative to repo root. Paths prefixed with "frontend/"
# scope are resolved under the frontend/ subdirectory when they use
# src/ prefixes. Some paths are git-ignored runtime artifacts (.venv)
# and are marked optional.
declare -a CLAUDE_PATHS=(
  # Specforge artifacts
  ".specify/memory/constitution.md|.specify/memory/constitution.md"
  ".specify/specs/spec.md|.specify/specs/spec.md"
  ".specify/specs/plan.md|.specify/specs/plan.md"
  "feature_list.json|feature_list.json"

  # Frontend source files
  "src/pages/Index.tsx|frontend/src/pages/Index.tsx"
  "src/components/AIChat.tsx|frontend/src/components/AIChat.tsx"
  "src/components/FitAssessment.tsx|frontend/src/components/FitAssessment.tsx"
  "src/components/Experience.tsx|frontend/src/components/Experience.tsx"
  "src/components/ui/|frontend/src/components/ui/"
  "src/index.css|frontend/src/index.css"
  "src/lib/utils.ts|frontend/src/lib/utils.ts"
  "src/App.tsx|frontend/src/App.tsx"
  "src/test/setup.ts|frontend/src/test/setup.ts"

  # Frontend config files
  "tailwind.config.ts|frontend/tailwind.config.ts"
  "vite.config.ts|frontend/vite.config.ts"
  "tsconfig.json|frontend/tsconfig.json"
  "tsconfig.app.json|frontend/tsconfig.app.json"
  "tsconfig.node.json|frontend/tsconfig.node.json"

  # Hook files referenced in Git Hooks Distribution section
  ".githooks/|.githooks/"
  "scripts/install-hooks.sh|scripts/install-hooks.sh"

  # API service
  "api-service/ai_resume_api/main.py|api-service/ai_resume_api/main.py"
  "api-service/ai_resume_api/guardrails.py|api-service/ai_resume_api/guardrails.py"

  # Data files
  "data/example_resume.md|data/example_resume.md"

  # CI gate files
  "ci/principles/commit-gate.md|ci/principles/commit-gate.md"
  "ci/principles/pr-gate.md|ci/principles/pr-gate.md"
  "ci/principles/release-gate.md|ci/principles/release-gate.md"

  # Claude Code hooks settings
  ".claude/settings.json|.claude/settings.json"

  # Code scanning skill files
  ".claude/skills/gh-code-scanning/reference/alert-types.md|.claude/skills/gh-code-scanning/reference/alert-types.md"
  ".claude/skills/gh-code-scanning/examples/fix-example.md|.claude/skills/gh-code-scanning/examples/fix-example.md"
  ".claude/skills/gh-code-scanning/examples/dismiss-example.md|.claude/skills/gh-code-scanning/examples/dismiss-example.md"

  # Dockerfiles
  "frontend/Dockerfile|frontend/Dockerfile"
  "api-service/Dockerfile|api-service/Dockerfile"
  "memvid-service/Dockerfile|memvid-service/Dockerfile"

  # Nginx config
  "nginx.conf|frontend/nginx.conf"

  # Deployment compose
  "deployment/compose.yaml|deployment/compose.yaml"

  # Hooks referenced in useProfile
  "src/hooks/useProfile|frontend/src/hooks/useProfile.ts"

  # Ingest script
  "ingest/ingest.py|ingest/ingest.py"
)

for entry in "${CLAUDE_PATHS[@]}"; do
  display="${entry%%|*}"
  resolve="${entry##*|}"
  full_path="$REPO_ROOT/$resolve"

  if [[ -e "$full_path" ]]; then
    pass "File exists: $display"
  else
    # Find the line in CLAUDE.md that references this path
    line_num=""
    if [[ -f "$CLAUDE_MD" ]]; then
      # Use the display path for grep, escape dots
      escaped=$(printf '%s' "$display" | sed 's/\./\\./g')
      line_num=$(grep -n "$escaped" "$CLAUDE_MD" 2>/dev/null | head -1 | cut -d: -f1 || true)
    fi
    fail "File missing: $display" "CLAUDE.md" "${line_num:-?}"
  fi
done

# =============================================================================
# 2. API endpoint verification (documented vs actual)
# =============================================================================
separator "API Endpoint Verification"

# Extract actual routes from main.py using decorator patterns
# Looks for @app.get, @app.post, @app.put, @app.delete, @app.patch
ACTUAL_ROUTES=()
if [[ -f "$MAIN_PY" ]]; then
  while IFS= read -r line; do
    # Extract route path from decorators like @app.get("/api/v1/profile")
    route=$(echo "$line" | sed -n 's/.*@app\.\(get\|post\|put\|delete\|patch\)("\([^"]*\)".*/\U\1\E \2/p')
    if [[ -n "$route" ]]; then
      ACTUAL_ROUTES+=("$route")
    fi
  done < "$MAIN_PY"
fi

# Also check for Prometheus /metrics endpoint (added via Instrumentator)
if grep -q 'Instrumentator.*expose' "$MAIN_PY" 2>/dev/null; then
  ACTUAL_ROUTES+=("GET /metrics")
fi

printf "  Actual routes found in main.py: %d\n" "${#ACTUAL_ROUTES[@]}"
for route in "${ACTUAL_ROUTES[@]}"; do
  printf "    %s\n" "$route"
done
echo ""

# Documented endpoints in CLAUDE.md (from API Endpoints table)
declare -a DOCUMENTED_ENDPOINTS=(
  "/health"
  "/api/v1/health"
  "/api/v1/chat"
  "/api/v1/profile"
  "/api/v1/suggested-questions"
  "/api/v1/assess-fit"
  "/api/v1/session/{session_id}/clear"
  "/api/v1/sessions/{session_id}"
  "/metrics"
)

for endpoint in "${DOCUMENTED_ENDPOINTS[@]}"; do
  found=false
  for route in "${ACTUAL_ROUTES[@]}"; do
    if [[ "$route" == *"$endpoint"* ]]; then
      found=true
      break
    fi
  done
  if $found; then
    pass "Documented endpoint exists: $endpoint"
  else
    fail "Documented endpoint missing from code: $endpoint" "CLAUDE.md"
  fi
done

# =============================================================================
# 3. Undocumented production route detection
# =============================================================================
separator "Undocumented Route Detection"

# Routes that are expected/internal and don't need CLAUDE.md documentation
declare -a EXEMPT_ROUTES=(
  "/metrics"           # Prometheus metrics (infrastructure)
)

for route in "${ACTUAL_ROUTES[@]}"; do
  route_path="${route#* }"  # Strip HTTP method prefix

  # Check if this route is documented in CLAUDE.md
  is_documented=false
  if grep -q "$route_path" "$CLAUDE_MD" 2>/dev/null; then
    is_documented=true
  fi

  # Check if exempt
  is_exempt=false
  for exempt in "${EXEMPT_ROUTES[@]}"; do
    if [[ "$route_path" == "$exempt" ]]; then
      is_exempt=true
      break
    fi
  done

  if $is_documented; then
    pass "Route documented: $route"
  elif $is_exempt; then
    pass "Route exempt (infrastructure): $route"
  else
    fail "Undocumented production route: $route" "api-service/ai_resume_api/main.py"
  fi
done

# =============================================================================
# 4. Container security claims verification
# =============================================================================
separator "Container Security Claims (docs/SECURITY.md)"

# Check 4a: Non-root user in Dockerfiles
for dockerfile in frontend/Dockerfile api-service/Dockerfile memvid-service/Dockerfile; do
  full="$REPO_ROOT/$dockerfile"
  if [[ ! -f "$full" ]]; then
    fail "Dockerfile not found: $dockerfile" "$dockerfile"
    continue
  fi

  if grep -q '^USER ' "$full"; then
    user_line=$(grep '^USER ' "$full" | tail -1)
    user_name="${user_line#USER }"
    if [[ "$user_name" != "root" ]]; then
      pass "Non-root user in $dockerfile (USER $user_name)"
    else
      fail "Runs as root in $dockerfile" "$dockerfile"
    fi
  else
    fail "No USER directive in $dockerfile (runs as root by default)" "$dockerfile"
  fi
done

# Check 4b: read_only in compose.yaml
if [[ -f "$COMPOSE_YAML" ]]; then
  for service in ai-resume-memvid ai-resume-api ai-resume-frontend; do
    if grep -A 30 "^  $service:" "$COMPOSE_YAML" | grep -q 'read_only: true'; then
      pass "read_only: true for $service in compose.yaml"
    else
      fail "Missing read_only: true for $service" "deployment/compose.yaml"
    fi
  done

  # Check 4c: no-new-privileges in compose.yaml
  for service in ai-resume-memvid ai-resume-api ai-resume-frontend; do
    if grep -A 35 "^  $service:" "$COMPOSE_YAML" | grep -q 'no-new-privileges'; then
      pass "no-new-privileges for $service in compose.yaml"
    else
      fail "Missing no-new-privileges for $service" "deployment/compose.yaml"
    fi
  done
else
  fail "Compose file not found" "deployment/compose.yaml"
fi

# Check 4d: SECURITY.md claims about non-root match reality
if [[ -f "$SECURITY_MD" ]]; then
  if grep -q 'user:.*nonroot.*# or nginx' "$SECURITY_MD" 2>/dev/null || \
     grep -q 'user: nonroot' "$SECURITY_MD" 2>/dev/null; then
    # Verify the api-service Dockerfile actually has a USER directive
    if ! grep -q '^USER ' "$REPO_ROOT/api-service/Dockerfile"; then
      fail "SECURITY.md claims non-root for all containers, but api-service/Dockerfile has no USER directive" "docs/SECURITY.md"
    else
      pass "SECURITY.md non-root claim matches Dockerfiles"
    fi
  fi
fi

# =============================================================================
# 5. CLAUDE.md accuracy checks
# =============================================================================
separator "CLAUDE.md Accuracy Checks"

# Check 5a: Container base image claims
if grep -q 'nginx-unprivileged:1.25-alpine' "$CLAUDE_MD" 2>/dev/null; then
  actual_base=$(grep '^FROM' "$REPO_ROOT/frontend/Dockerfile" | tail -1 | awk '{print $2}')
  if [[ "$actual_base" == *"nginx-unprivileged"* ]]; then
    pass "Frontend base image matches CLAUDE.md claim"
  else
    line_num=$(grep -n 'nginx-unprivileged' "$CLAUDE_MD" | head -1 | cut -d: -f1 || true)
    fail "Frontend base image mismatch: CLAUDE.md says nginx-unprivileged:1.25-alpine, actual is $actual_base" "CLAUDE.md" "${line_num:-?}"
  fi
fi

# Check 5b: Build stage image claim
if grep -q 'node:18-alpine' "$CLAUDE_MD" 2>/dev/null; then
  actual_build=$(grep '^FROM.*builder' "$REPO_ROOT/frontend/Dockerfile" | head -1 | awk '{print $2}')
  if [[ "$actual_build" == *"node:18"* ]]; then
    pass "Frontend build image matches CLAUDE.md claim"
  else
    line_num=$(grep -n 'node:18-alpine' "$CLAUDE_MD" | head -1 | cut -d: -f1 || true)
    fail "Frontend build image mismatch: CLAUDE.md says node:18-alpine, actual is $actual_build" "CLAUDE.md" "${line_num:-?}"
  fi
fi

# Check 5c: data/master_resume.md reference
if grep -q 'data/master_resume.md' "$CLAUDE_MD" 2>/dev/null; then
  if [[ ! -f "$REPO_ROOT/data/master_resume.md" ]]; then
    line_num=$(grep -n 'data/master_resume.md' "$CLAUDE_MD" | head -1 | cut -d: -f1 || true)
    fail "data/master_resume.md referenced in CLAUDE.md but does not exist (may be user-specific, not committed)" "CLAUDE.md" "${line_num:-?}"
  else
    pass "data/master_resume.md exists as referenced"
  fi
fi

# Check 5d: deployment/deploy.py reference
if grep -q 'deployment/deploy.py' "$CLAUDE_MD" 2>/dev/null; then
  if [[ ! -f "$REPO_ROOT/deployment/deploy.py" ]]; then
    line_num=$(grep -n 'deployment/deploy.py' "$CLAUDE_MD" | head -1 | cut -d: -f1 || true)
    fail "deployment/deploy.py referenced in CLAUDE.md but does not exist" "CLAUDE.md" "${line_num:-?}"
  else
    pass "deployment/deploy.py exists as referenced"
  fi
fi

# Check 5e: build-container.sh reference
if grep -q 'build-container.sh' "$CLAUDE_MD" 2>/dev/null; then
  if [[ ! -f "$REPO_ROOT/build-container.sh" ]]; then
    line_num=$(grep -n 'build-container.sh' "$CLAUDE_MD" | head -1 | cut -d: -f1 || true)
    fail "build-container.sh referenced in CLAUDE.md but does not exist" "CLAUDE.md" "${line_num:-?}"
  else
    pass "build-container.sh exists as referenced"
  fi
fi

# Check 5f: claude-progress.txt reference
if grep -q 'claude-progress.txt' "$CLAUDE_MD" 2>/dev/null; then
  if [[ ! -f "$REPO_ROOT/claude-progress.txt" ]]; then
    line_num=$(grep -n 'claude-progress.txt' "$CLAUDE_MD" | head -1 | cut -d: -f1 || true)
    fail "claude-progress.txt referenced in CLAUDE.md but does not exist" "CLAUDE.md" "${line_num:-?}"
  else
    pass "claude-progress.txt exists as referenced"
  fi
fi

# =============================================================================
# Report
# =============================================================================
separator "Documentation Audit Report"

printf "  Total checks:   %d\n" "$TOTAL_COUNT"
printf "  Passing:        %d\n" "$PASS_COUNT"
printf "  Failing:        %d\n" "$FAIL_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  printf "\n  Result: FAIL (%d issue(s) found)\n" "$FAIL_COUNT"
  exit 1
else
  printf "\n  Result: PASS (all checks green)\n"
  exit 0
fi

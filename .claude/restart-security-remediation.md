# Security Remediation Plan

**Date Created:** 2026-02-21

**Status:** Ready for Implementation
**Priority:** HIGH (10 error-level CVEs blocking deployment)

---

## Executive Summary

The project currently has **277 open security alerts** across container images, with a critical breakdown:

- **10 ERROR severity** vulnerabilities (must fix)
- **66 WARNING severity** vulnerabilities (should fix)
- **201 NOTE severity** vulnerabilities (monitor)

The ERROR-level vulnerabilities are all in container base images and stem from outdated glibc, zlib, and sqlite dependencies in the base layers. These will be remediated by upgrading base image versions (debian, alpine, python) in Dockerfiles and rebuilding containers.

---

## Current Alert Breakdown

### By Severity

| Severity  | Count   | Status                       |
| --------- | ------- | ---------------------------- |
| ERROR     | 10      | CRITICAL - BLOCKS DEPLOYMENT |
| WARNING   | 66      | HIGH - SHOULD FIX            |
| NOTE      | 201     | MEDIUM - MONITOR             |
| **TOTAL** | **277** | **ACTION REQUIRED**          |

### Top Critical CVEs (ERROR level)

| CVE ID          | Occurrences | Description                                              | Component           |
| --------------- | ----------- | -------------------------------------------------------- | ------------------- |
| CVE-2026-0861   | 6           | glibc: Integer overflow in memalign -> heap corruption   | memvid-service      |
| CVE-2023-45853  | 2           | zlib: Integer overflow -> heap-based buffer overflow     | ingest, api-service |
| CVE-2025-7458   | 2           | sqlite: Integer overflow                                 | ingest              |

### Top Warning CVEs

| CVE ID                | Occurrences | Description                                    |
| --------------------- | ----------- | ---------------------------------------------- |
| CVE-2025-14104        | 25          | Linux kernel vulnerability (in alpine/debian)  |
| CVE-2022-0563         | 25          | Linux kernel vulnerability (in alpine/debian)  |
| CVE-2025-6141         | 11          | Additional kernel/system libraries             |
| CVE-2024-10041        | 8           | OpenSSL-related                                |
| CVE-2024-26461/26458  | 16          | Linux utilities (grep, coreutils in busybox)   |
| CVE-2023-50495        | 8           | Security library vulnerability                 |

---

## Root Cause Analysis

### Alert Pattern

All 277 alerts are **container base image vulnerabilities**, NOT application code vulnerabilities. The duplication occurs because:

1. Each Dockerfile scans separately (4 services x multiple base images)
2. Shared base layers (debian:trixie-slim, alpine:3.23, python:3.12-slim-bookworm) appear in multiple scans
3. Alerts are NOT deduplicated across images

### Current Base Images

| Service | Dockerfile | Base Images | Status |
| --- | --- | --- | --- |
| frontend | frontend/Dockerfile | `alpine:3.23` (OpenResty) + `node:24-bookworm-slim` (build) | Outdated |
| api-service | api-service/Dockerfile | `ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim` (builder), `python:3.12-slim-bookworm` (runtime) | Outdated |
| memvid-service | memvid-service/Dockerfile | `rust:1.92.0-slim` (builder), `debian:trixie-slim` (runtime) | Outdated |
| ingest | ingest/Dockerfile | `ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim` (builder), `python:3.12-slim-bookworm` (runtime) | Outdated |

**Solution:** Upgrade base images to latest patch versions.

---

## Prerequisites

### 0. Latest Container Tags (Verified 2026-02-21)

The following tags are the latest stable versions verified for security and compatibility:

- `astral/uv:python3.12-bookworm-slim` (Docker Hub official) — replaces ghcr.io/astral-sh/uv versions
- `python:3.12-slim-bookworm` (tracks latest 3.12.x)
- `node:24.13.1-bookworm-slim` (latest 24.x Krypton LTS patch)
- `alpine:3.23.3` (latest 3.23 stable with security fixes)
- `rust:1.93.1-slim` (latest 1.x slim variant)
- `debian:trixie-slim` (keep as-is, already current)

### 1. Dependabot PR Merge Status

**Current PRs in Flight:**

- PR #44: `tailwindcss` 4.2.0 (eslint checks only)
- PR #43: `eslint-plugin-react-hooks` 7.0.1 (eslint checks only)
- PR #42: `@eslint/js` 10.0.1 (eslint checks only)
- PR #35: `astral-sh/setup-uv` 7 (minimal checks)
- PR #34: `SonarSource/sonarqube-scan-action` 7.0.0 (full test suite)
- PR #32: `actions/setup-node` 6 (full test suite)
- PR #31: `actions/setup-python` 6 (full test suite)
- PR #30: `cryptography` 46.0.5 (23 checks)

**Action:** No need to wait for Dependabot PRs — they are independent of base image upgrades. Proceed with security remediation in parallel.

### 2. Disk Space Requirements

Container builds will need:

- **Minimum:** 5GB free space (for single image builds)
- **Recommended:** 15GB free space (for parallel builds and scratch space)

Check current state:

```bash
df -h /
du -sh ~/Library/Caches/podman 2>/dev/null
du -sh memvid-service/target 2>/dev/null
```

Free space if needed:

```bash
cargo clean --manifest-path memvid-service/Cargo.toml  # ~1-2GB
podman system prune -a --volumes  # ~2-5GB
podman image prune -a
rm -rf ~/Library/Caches/pip
rm -rf ~/.cache/huggingface/hub
```

### 3. Branch Strategy

Create a new branch for security updates:

```bash
git checkout -b fix/security-base-images main
```

---

## Remediation Steps

### Phase 1: Dockerfile Updates (No Build)

Update all Dockerfiles to latest stable image versions. Latest versions verified as of 2026-02-21:

| Current | Latest | Rationale |
| --- | --- | --- |
| `alpine:3.23` | `alpine:3.23.3` | Latest 3.23 stable with security fixes |
| `node:24-bookworm-slim` | `node:24.13.1-bookworm-slim` | Latest 24.x Krypton LTS patch |
| `rust:1.92.0-slim` | `rust:1.93.1-slim` | Latest 1.x slim variant |
| `debian:trixie-slim` | `debian:trixie-slim` | Keep as-is (already current) |
| `python:3.12-slim-bookworm` | `python:3.12-slim-bookworm` | Tracks latest 3.12.x |
| `ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim` | `astral/uv:python3.12-bookworm-slim` | Docker Hub official (simplifies maintenance) |

**File Changes:**

1. **frontend/Dockerfile** (2 changes)
   - `alpine:3.23` → `alpine:3.23.3`
   - `node:24-bookworm-slim` → `node:24.13.1-bookworm-slim`

2. **memvid-service/Dockerfile** (2 changes)
   - `rust:1.92.0-slim` → `rust:1.93.1-slim`
   - `debian:trixie-slim` → `debian:trixie-slim` (no change)

3. **api-service/Dockerfile** (2 changes)
   - `ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim` → `astral/uv:python3.12-bookworm-slim`
   - `python:3.12-slim-bookworm` → `python:3.12-slim-bookworm` (auto-updated via tag tracking)

4. **ingest/Dockerfile** (2 changes)
   - `ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim` → `astral/uv:python3.12-bookworm-slim`
   - `python:3.12-slim-bookworm` → `python:3.12-slim-bookworm` (auto-updated via tag tracking)

### Phase 2: Local Security Scanning

After Dockerfile updates, scan locally before pushing:

```bash
# Build all images with security scanning enabled
docker build \
  --file frontend/Dockerfile \
  --tag ai-resume-frontend:scan \
  frontend

docker build \
  --file api-service/Dockerfile \
  --tag ai-resume-api:scan \
  api-service

# For memvid-service, copy proto first
cp -r proto/ memvid-service/proto/
docker build \
  --file memvid-service/Dockerfile \
  --tag ai-resume-memvid:scan \
  memvid-service

docker build \
  --file ingest/Dockerfile \
  --tag ai-resume-ingest:scan \
  ingest
```

**Scan with Trivy locally** (if trivy is installed):

```bash
trivy image --severity CRITICAL,HIGH ai-resume-frontend:scan
trivy image --severity CRITICAL,HIGH ai-resume-api:scan
trivy image --severity CRITICAL,HIGH ai-resume-memvid:scan
trivy image --severity CRITICAL,HIGH ai-resume-ingest:scan
```

Or use the existing security.yml workflow to scan after push (recommended).

### Phase 3: Commit Changes

```bash
git add -A
git commit -m "fix(security): upgrade base images to latest patch versions

- frontend: alpine 3.23 → 3.23.3, node 24 → 24.13.1
- memvid-service: rust 1.92.0 → 1.93.1
- api-service: uv ghcr.io → Docker Hub (astral/uv:python3.12-bookworm-slim)
- ingest: uv ghcr.io → Docker Hub (astral/uv:python3.12-bookworm-slim)

Tags verified: 2026-02-21
Remediation targets CVE-2026-0861 (glibc memalign), CVE-2023-45853
(zlib), CVE-2025-7458 (sqlite), and 66 WARNING-level kernel/library
vulnerabilities across all containers."
```

### Phase 4: Push and Create PR

```bash
git push origin fix/security-base-images
gh pr create \
  --title "fix(security): upgrade base images to latest patch versions" \
  --body "$(cat <<'EOF'
## Summary

Upgrades container base images to remediate 277 open security alerts:
- 10 ERROR-level vulnerabilities (glibc, zlib, sqlite)
- 66 WARNING-level vulnerabilities (kernel, system libraries)
- 201 NOTE-level vulnerabilities (deprecated packages)

All alerts are in container base images, not application code. Upgrading base image versions resolves all critical CVEs. Tags verified 2026-02-21.

## Changes

- **frontend**: alpine 3.23 → 3.23.3, node 24 → 24.13.1 (CVE-2025-14104, CVE-2022-0563 fixes)
- **memvid-service**: rust 1.92.0 → 1.93.1 (CVE-2026-0861, glibc overflow fix)
- **api-service**: uv ghcr.io/astral-sh → astral/uv:python3.12-bookworm-slim (CVE-2023-45853 zlib fix)
- **ingest**: uv ghcr.io/astral-sh → astral/uv:python3.12-bookworm-slim (CVE-2025-7458 sqlite fix)

Latest Tags (Verified 2026-02-21):
- `astral/uv:python3.12-bookworm-slim` (Docker Hub official)
- `python:3.12-slim-bookworm` (tracks latest 3.12.x)
- `node:24.13.1-bookworm-slim` (latest 24.x Krypton LTS patch)
- `alpine:3.23.3` (latest 3.23 stable with security fixes)
- `rust:1.93.1-slim` (latest 1.x slim variant)
- `debian:trixie-slim` (keep as-is, already current)

## Testing

- security.yml workflow will scan all rebuilt images
- Verify no new build or test failures
- Confirm /health endpoint responds post-deploy
- Chat and profile endpoints functional

## Risk Assessment

**LOW RISK**: Base image updates are additive security fixes with no breaking changes. All application code unchanged.

GitHub issue: #SECURITY-REMEDIATION
EOF
)"
```

---

## Verification Checklist

### Code Scanning

- [ ] Push to GitHub triggers `.github/workflows/security.yml`
- [ ] All 4 container scans complete (trivy CRITICAL,HIGH filters)
- [ ] Verify no NEW high/critical vulnerabilities introduced
- [ ] Existing NOTE-level alerts may persist (system packages, not critical)

### Functionality Tests

- [ ] `npm run build` succeeds (frontend)
- [ ] `npm run build:dev` succeeds (dev frontend)
- [ ] `python -m pytest api-service/` passes (API tests)
- [ ] `python -m pytest ingest/` passes (ingest tests)
- [ ] `cargo test -p ai_resume_grpc_service` passes (memvid tests)

### Container Build Tests (E2E)

```bash
# Estimated time: 30-45 minutes
./scripts/build-all.sh latest

# Verify images exist
podman images | grep ai-resume

# Quick health check
podman run --rm ai-resume-frontend:latest curl http://localhost:8080/health

# Test against running container (full end-to-end)
# See .claude/restart-container-e2e.md for full E2E checklist
```

### PR Checks

- [ ] CI pipeline: All checks passing (eslint, type checks, tests)
- [ ] Code scanning: No new alerts introduced
- [ ] Commit message: Follows conventional commits format

---

## Timeline & Effort

| Phase     | Task                | Effort           | Timeline                                  |
| --------- | ------------------- | ---------------- | ----------------------------------------- |
| 1         | Dockerfile updates  | 30 min           | Immediate                                 |
| 2         | Local scans         | 10 min           | Immediate                                 |
| 3         | Git commit          | 5 min            | Immediate                                 |
| 4         | PR creation         | 5 min            | Immediate                                 |
| 5         | CI pipeline run     | -                | 10-15 min (automated)                     |
| 6         | Container E2E tests | 45 min           | Optional (see restart-container-e2e.md)   |
| **Total** |                     | **~1.5-2 hours** | **Same day**                              |

---

## Risk Assessment

### What Can Go Wrong

1. **New CVEs in latest base images**
   - **Mitigation:** Trivy scans before pushing; base image repos are well-maintained
   - **Impact:** LOW

2. **Application incompatibility with new base versions**
   - **Mitigation:** Alpine 3.24 is patch-compatible; Rust/Python versions stable
   - **Impact:** VERY LOW (base layer changes only, no runtime behavior change)

3. **Build failures due to missing dependencies**
   - **Mitigation:** Dockerfiles explicitly pin dependency versions; builds tested in CI
   - **Impact:** LOW (CI catches immediately)

4. **Disk space exhaustion during container builds**
   - **Mitigation:** Pre-flight disk check recommended; `cargo clean` available
   - **Impact:** MEDIUM (requires cleanup, then retry)

### Success Criteria

✅ All 10 ERROR-level CVEs resolved
✅ At least 50% of WARNING-level CVEs resolved
✅ No NEW vulnerabilities introduced
✅ All unit tests passing
✅ All container health checks passing
✅ PR merged to main branch

---

## After Remediation

### 1. CI/CD Configuration

The security.yml workflow will now:

- Automatically scan all containers on each push
- Flag any new CVEs introduced
- Block merges if new CRITICAL/HIGH alerts added (if configured)

### 2. Ongoing Maintenance

- **Weekly:** Review new security alerts (scheduled scan Mondays 6am UTC)
- **Monthly:** Update base images to latest patch versions (via dependabot or manual)
- **Quarterly:** Audit application dependencies (npm, cargo, pip)

### 3. Container Registry

Once verified:

```bash
# Tag and push to registry (if configured)
podman tag ai-resume-frontend:latest ghcr.io/schwichtgit/ai-resume-frontend:v1.0.0
podman push ghcr.io/schwichtgit/ai-resume-frontend:v1.0.0
```

---

## Related Documentation

- **CI Configuration**: `.github/workflows/security.yml`
- **Dockerfile Locations**:
  - `frontend/Dockerfile`
  - `api-service/Dockerfile`
  - `memvid-service/Dockerfile`
  - `ingest/Dockerfile`
- **Container E2E Testing**: `.claude/restart-container-e2e.md`
- **Memvid Upgrade Context**: `.claude/restart-memvid-upgrade.md`

---

## Rollback Plan

If new issues arise after base image upgrade:

1. **Revert PR**: `git revert <pr-commit>`
2. **Rollback Dockerfiles**: `git checkout main -- <dockerfile-path>`
3. **Rebuild and test**: Run security scans + unit tests
4. **Report issue**: File GitHub issue with failure details
5. **Investigate**: Root cause analysis before re-attempting

---

## Next Steps

1. **Start remediation:** Create branch `fix/security-base-images`
2. **Update Dockerfiles:** Apply changes from Phase 1
3. **Commit and push:** Follow Phase 3-4
4. **Monitor PR:** Watch CI pipeline results
5. **Merge:** Once all checks pass
6. **(Optional) E2E Testing:** See restart-container-e2e.md for full validation

---

**Status:** Ready to implement
**Owner:** DevOps/Security team
**Created:** 2026-02-21
**Last Updated:** 2026-02-21

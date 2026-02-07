# Release Quality Gate Plan

## Goal

A comprehensive E2E test pipeline that answers: **"Are we ready to release this version?"**

Runs as a single orchestrator script (`scripts/release-gate.sh`) covering build, ingest, and full API use-case coverage. Serves as the quality gate before merging PRs to main.

---

## Current State Assessment

| File                                | Purpose                               | Tests |
| ----------------------------------- | ------------------------------------- | ----- |
| `api-service/tests/test_e2e_api.py` | In-process pytest (mock mode)         | 10    |
| `scripts/test-e2e-integration.sh`   | Full-stack bash (real gRPC, mock LLM) | 4     |
| `scripts/test-containers.sh`        | Container smoke test (podman)         | 6     |
| `scripts/test-e2e-mock-gates.sh`    | Mock feature gate verification        | 6     |

### Gaps Identified

1. No ingest pipeline test in the E2E flow
2. No container build + tar export verification
3. No negative/edge API test cases (empty message, short JD, 404)
4. No strong-match vs. weak-match fit assessment contrast
5. No frontend serving verification (SPA routing, static assets)
6. No unified orchestrator script with pass/fail summary
7. Bug in `test-containers.sh` line 102 (stray backtick fence)
8. CI only runs pytest E2E, not full-stack integration

---

## Pre-Work: Unblock Main

Before implementing the release gate, three PRs must be resolved to ensure `feature/release-gate` starts from a clean, current `main`.

### Step 0: Fix Flaky Rust Integration Tests

**Problem:** `memvid-service/tests/main_integration_tests.rs` uses `std::env::set_var` / `remove_var` for test configuration, but Rust runs tests in parallel within one process. Environment variables are process-global, so concurrent threads clobber each other's `MOCK_MEMVID` and `MEMVID_FILE_PATH` values. This causes non-deterministic failures in:

- `test_config_requires_memvid_file_without_mock` (PR #22 failure)
- `test_empty_string_memvid_path_with_mock` (PR #21 failure)

**Fix options:**
| Option | Approach | Trade-off |
|--------|----------|-----------|
| (a) `--test-threads=1` in CI | Add to CI workflow cargo test command | Simple but slows all tests |
| (b) Refactor `Config::from_env()` | Accept `HashMap` instead of reading `std::env` directly | Clean but larger refactor |
| (c) `serial_test` crate | Add `#[serial]` attribute to env-mutating tests | Targeted, minimal change |

**Recommendation:** Option (c) -- add `serial_test` crate and `#[serial]` to tests that mutate environment variables. Targeted fix, minimal disruption.

**Where:** Can be done directly on `main` as a small fix PR, or folded into PR #23 during rebase.

### Step 1: Rebase PR #23 onto Main

**PR #23:** `test/e2e-integration` -- adds E2E test infrastructure (10 pytest tests, 4 bash integration tests, gRPC tests, CI e2e job, defensive API fixes, memvid-core 2.0.136 bump)

**Merge conflict:** `memvid-service/Cargo.lock` -- PR #20 (`fix/memvid-container-build`) merged to main after PR #23 branched, both adding `Cargo.lock` independently.

**Resolution:**

1. Rebase `test/e2e-integration` onto current `main`
2. Regenerate `Cargo.lock` with `cargo update` (keeping memvid-core 2.0.136)
3. Include Step 0 fix (serial_test) in the rebase
4. Re-run CI -- all checks must pass

### Step 2: Merge PR #23 to Main

Once CI is green, merge PR #23. This lands:

- `api-service/tests/test_e2e_api.py` (10 tests)
- `api-service/tests/test_e2e_grpc.py` (5 tests)
- `scripts/test-e2e-integration.sh` (4 tests)
- `scripts/publish-containers.sh`
- CI `e2e` job
- Defensive API fixes (health degraded state, empty context handling)
- memvid-core 2.0.136 with ACL fields
- Skills Assessment section in `data/example_resume.md`

### Step 3: Merge Dependabot PRs

With the serial_test fix on main (via PR #23), re-run CI on:

- **PR #22:** `bytes` 1.11.0 -> 1.11.1
- **PR #21:** `time` 0.3.46 -> 0.3.47

Both are safe dependency bumps. Tests should now pass with the race condition fixed.

### Step 4: Create `feature/release-gate` from Updated Main

With all pre-work merged, `main` will have:

- All E2E test infrastructure from PR #23
- Flaky test fix
- Latest cargo dependency bumps
- Clean, conflict-free base

The release gate implementation (Phases 1-7 below) builds on this foundation.

---

## Pipeline Architecture

```
scripts/release-gate.sh [VERSION] [--skip-build] [--skip-ingest]
  |
  +-- Phase 1: Container Build + Tar Export
  |     build-all.sh -> podman save -> deployment/*.tar
  |
  +-- Phase 2: Fresh Ingest
  |     ingest.py --input example_resume.md --output test_resume.mv2 --verify
  |
  +-- Phase 3: Container Smoke Test
  |     test-containers.sh (health, gRPC, frontend)
  |
  +-- Phase 4: API E2E Tests (pytest, mock mode)
  |     test_e2e_api.py (~17 tests)
  |
  +-- Phase 5: Full-Stack Integration (real gRPC, mock LLM)
  |     test-e2e-integration.sh (~10 tests)
  |
  +-- Phase 6: Live Container E2E (optional, requires running compose)
  |     Chat, fit assessment, SSE against real containers
  |
  +-- Phase 7: Release Decision
        All PASS -> "RELEASE READY" + tar files ready for deploy
        Any FAIL -> "RELEASE BLOCKED" + diagnostic summary
```

---

## Phase Details

### Phase 1: Container Build + Tar Export

**What:** Build all 3 container images, export as OCI tar files.

**New file:** `scripts/export-containers.sh`

```
For each image (frontend, api, memvid):
  podman save -> deployment/<image>-<version>.tar
  Verify tar file exists and size > threshold
```

**Validates:**

- Dockerfiles build without errors
- Multi-arch manifests are valid
- Tar files are deployable to edge server

### Phase 2: Fresh Ingest

**New file:** `scripts/test-ingest.sh`

```
source ingest/.venv/bin/activate
python ingest/ingest.py \
  --input data/example_resume.md \
  --output data/.memvid/test_resume.mv2 \
  --verify
```

**Validates:**

- memvid-sdk 2.0.153 can create .mv2 files
- Embedding model loads and produces vectors
- Profile memory card is stored correctly
- Verification queries pass (semantic search, FAQ mirroring)
- Output file format compatible with memvid-core 2.0.136

### Phase 3: Container Smoke Test

**Modified file:** `scripts/test-containers.sh`

**Existing tests (6):** Container running, health, gRPC, chat, Rust logs

**New tests (+4):**

- Frontend container starts and responds
- Frontend health endpoint returns 200
- Frontend serves React SPA (contains `<div id="root">`)
- Frontend SPA routing works (non-existent path returns index.html)

**Fix:** Remove stray backtick at line 102

### Phase 4: API E2E Tests (pytest)

**Modified file:** `api-service/tests/test_e2e_api.py`

**New file:** `api-service/tests/fixtures/job_descriptions.py`

**Existing tests (10):** Health x2, profile, suggested-questions, chat x2, fit, guardrail, session, trace-id

**New tests (+7):**

| #   | Test                                         | Type     | Expected                  |
| --- | -------------------------------------------- | -------- | ------------------------- |
| 11  | Chat with empty message                      | Negative | 422                       |
| 12  | Chat with missing message field              | Negative | 422                       |
| 13  | Fit assessment with short JD (<50 chars)     | Negative | 422                       |
| 14  | Fit assessment with meaningless input        | Edge     | 200 + verdict             |
| 15  | Fit assessment strong-match (VP Engineering) | Positive | verdict + key_matches > 0 |
| 16  | Fit assessment weak-match (Executive Chef)   | Positive | verdict + gaps > 0        |
| 17  | Invalid endpoint GET /api/v1/nonexistent     | Negative | 404                       |

**Job description fixtures:**

- **Strong match:** VP of Platform Engineering at Series B AI startup (Python, Go, K8s, leadership, FedRAMP)
- **Weak match:** Executive Chef at Michelin-starred restaurant (culinary arts, French/Japanese cuisine)

### Phase 5: Full-Stack Integration

**Modified file:** `scripts/test-e2e-integration.sh`

**Existing tests (4):** Health connectivity, chat flow, profile, SSE streaming

**New tests (+6):**

| #   | Test                                        | Type     |
| --- | ------------------------------------------- | -------- |
| 5   | Suggested questions returns non-empty list  | Positive |
| 6   | Fit assessment with strong-match JD         | Positive |
| 7   | Fit assessment with weak-match JD           | Positive |
| 8   | Chat with empty message returns 422         | Negative |
| 9   | Invalid endpoint returns 404                | Negative |
| 10  | Session continuity across multiple messages | Positive |

### Phase 6: Live Container E2E (Optional)

**For local testing against running compose stack.** Not part of CI.

Tests against `localhost:3000` (API) and `localhost:8080` (frontend):

- Real semantic search + LLM chat (non-streaming and SSE)
- Fit assessment with both JD fixtures (real LLM responses)
- Profile structural validation
- Frontend proxy to API

### Phase 7: Release Decision

**Output format:**

```
============================================
  RELEASE GATE SUMMARY (v0.3.0)
============================================
  Phase 1 - Container Build    : PASS
  Phase 2 - Ingest Pipeline    : PASS
  Phase 3 - Container Smoke    : PASS
  Phase 4 - API E2E (17/17)    : PASS
  Phase 5 - Full-Stack (10/10) : PASS
  Phase 6 - Live E2E           : SKIP (--skip-live)
============================================
  RESULT: RELEASE READY
============================================
```

---

## CI Integration Strategy

| Phase               | GitHub Actions                | Local        |
| ------------------- | ----------------------------- | ------------ |
| 1. Container Build  | Skip (separate CD)            | Yes          |
| 2. Ingest           | Skip (requires model)         | Yes          |
| 3. Container Smoke  | Skip (requires podman)        | Yes          |
| 4. API E2E (pytest) | **Yes**                       | Yes          |
| 5. Full-Stack       | **Yes** (build Rust + Python) | Yes          |
| 6. Live E2E         | Skip                          | Yes (opt-in) |
| 7. Release Decision | **Yes** (phases 4-5)          | Yes (all)    |

**CI changes to `.github/workflows/ci.yml`:**

- Expand `e2e` job to also run `test-e2e-integration.sh` (Phase 5)
- Add `release-gate` job (runs on push to main or workflow_dispatch)
- Summary job includes release-gate status

---

## File Change Summary

| Action      | File                                             | Description                   |
| ----------- | ------------------------------------------------ | ----------------------------- |
| **New**     | `scripts/release-gate.sh`                        | Unified orchestrator          |
| **New**     | `scripts/test-ingest.sh`                         | Ingest pipeline test          |
| **New**     | `scripts/export-containers.sh`                   | Tar export + verify           |
| **New**     | `api-service/tests/fixtures/job_descriptions.py` | JD test fixtures              |
| **Modify**  | `api-service/tests/test_e2e_api.py`              | +7 tests (10 -> 17)           |
| **Modify**  | `scripts/test-e2e-integration.sh`                | +6 tests (4 -> 10)            |
| **Modify**  | `scripts/test-containers.sh`                     | Fix bug + 4 frontend tests    |
| **Modify**  | `.github/workflows/ci.yml`                       | Expand e2e + release-gate job |
| **Replace** | `.claude/plan.md`                                | This document                 |

---

## Implementation Order

```
Step 1: Fix test-containers.sh bug (line 102)
Step 2: Create fixtures/job_descriptions.py        \
Step 3: Expand test_e2e_api.py (+7 tests)           > parallel
Step 4: Create test-ingest.sh                       /
Step 5: Expand test-e2e-integration.sh (+6 tests)  \
Step 6: Expand test-containers.sh (+4 tests)        > parallel
Step 7: Create export-containers.sh                 /
Step 8: Create release-gate.sh (depends on 4-7)
Step 9: Update ci.yml (depends on 8)
```

---

## Roadmap Alignment

**Current (edge server deploy):**

- `release-gate.sh` produces tar files in `deployment/`
- Manual `scp` or `scripts/deploy.sh` pushes to edge server

**Next (versioned container registry):**

- `release-gate.sh --publish` calls `scripts/publish-containers.sh`
- Tags containers with version from release-gate
- Updates `deployment/compose.yaml` with pinned version tag

**Future (community consumption):**

- Community users pull pre-built images from registry
- `compose.yaml` in repo always references the latest released version
- Release notes generated from quality gate output

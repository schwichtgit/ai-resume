# Restart: Post-Merge Evaluation

## Context

PR #28 (`chore/specforge-migration`) merged to `main` with 31 commits.
All 124/124 specforge features complete. CI green on all required jobs.

## Branch

Start fresh from `main`.

## Immediate priorities

### 1. Evaluate new memvid release

- Current pins: `memvid-sdk==2.0.153` (Python), `memvid-cli@2.0.153` (CI)
- Bug C workaround active: `memvid doctor --rebuild-time-index` (feature-flagged via `REBUILD_TIME_INDEX`)
- Check if newer memvid release fixes the broken time index in fresh .mv2 files
- If fixed: remove doctor workaround, unpin CLI version, update SDK
- If not: keep workaround, document upstream issue status

### 2. Container E2E on production host

- See `.claude/restart-container-e2e.md` for checklist
- Tarballs in `dist/` (frontend, api, memvid -- rebuild ingest if needed)
- Verify: nginx realip logging with reverse proxy, gRPC connectivity, health endpoints
- Test plan item from PR: "Verify container deployment on production host"

### 3. Taskfile implementation (optional, if time permits)

- Feature plan at `.specify/specs/taskfile-plan.md` (F-125 to F-134)
- go-task build orchestration for the polyglot monorepo
- `task container-build` to replace `scripts/build-all.sh`

## Reference files

- `.specify/memory/constitution.md` -- project constitution + E2E reliability protocol
- `.specify/specs/plan.md` -- specforge plan
- `feature_list.json` -- feature tracking (124 features)
- `memvid-service/tarpaulin-unit.toml` / `tarpaulin-integration.toml` -- coverage profiles

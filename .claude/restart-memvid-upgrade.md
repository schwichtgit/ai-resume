# Restart: Memvid Upgrade + Container E2E

## Context

Session ran out of disk space. Need to free space before container builds.

## Branch

`chore/memvid-upgrade-2.0.157` (based on `main` after PR #28 merge)

## Completed

### 1. Memvid evaluation

- Reproduced all 3 bugs (A, B, C) against latest versions (SDK 2.0.157, core 2.0.137)
- Bug B (#195): **FIXED** -- SDK/core version parity restored
- Bug A (#194): NOT FIXED -- vec_enabled=None, semantic search raises MV011
- Bug C (#196): NOT FIXED -- ask() fails with "frame id out of range" on 12+ frame files
- Upstream report packaged: `memvid_issues/memvid-bug-report-2026-02-20.zip`

### 2. Version upgrade (ALL DONE, NOT YET COMMITTED)

Files changed:

- `ingest/pyproject.toml`: memvid-sdk 2.0.153 -> 2.0.157
- `ingest/uv.lock`: updated
- `memvid-service/Cargo.toml`: memvid-core 2.0.136 -> 2.0.137
- `memvid-service/Cargo.lock`: updated
- `.github/workflows/ci.yml`: memvid-cli@2.0.153 -> @2.0.157
- `scripts/test-e2e-real.sh`: memvid-cli@2.0.153 -> @2.0.157
- `data/.memvid/resume.mv2`: re-ingested with SDK 2.0.157, doctor healed (337KB)
- Local CLI: `volta install memvid-cli@2.0.157` (done)

### 3. Upstream bug report

- `memvid_issues/UPSTREAM_REPORT.md` -- comprehensive report
- `memvid_issues/repro_bug_a.py` -- Bug A reproduction
- `memvid_issues/repro_bug_c.py` -- Bug C reproduction
- `memvid_issues/repro_bug_c_rust/` -- Rust-side Bug C reproduction
- `memvid_issues/package-report.sh` -- packaging script
- `memvid_issues/memvid-bug-report-2026-02-20.zip` -- ready to send

## Remaining

### 1. Commit the version upgrade

- All changes are unstaged on branch `chore/memvid-upgrade-2.0.157`
- Commit message: `chore(deps): upgrade memvid SDK 2.0.157, core 2.0.137`

### 2. Container E2E testing

- See `.claude/restart-container-e2e.md` for full checklist
- DISK SPACE NEEDED: container builds require significant space
- Free space first: `podman system prune -a`, check `~/Library/Caches`, etc.
- Build order: memvid-service, api-service, frontend (no ingest for E2E)
- Then: `cd deployment && podman-compose up -d`
- Test: health endpoints, profile, chat

### 3. Taskfile implementation (optional, if time permits)

- `.specify/specs/taskfile-plan.md` (F-125 to F-134)

## Disk space tips

```bash
# Check disk usage
df -h /
du -sh ~/Library/Caches/podman 2>/dev/null
du -sh ~/Library/Containers/com.docker.docker 2>/dev/null

# Clean podman
podman system prune -a --volumes
podman image prune -a

# Clean other caches
rm -rf ~/Library/Caches/pip
rm -rf ~/.cache/huggingface/hub  # Large ML models
du -sh /tmp/memvid-bug-repro 2>/dev/null  # Temp test artifacts

# Check Rust build artifacts
du -sh memvid-service/target 2>/dev/null
cargo clean --manifest-path memvid-service/Cargo.toml  # Frees ~1-2GB
```

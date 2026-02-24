# Changelog

All notable changes to the **ai-resume** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha.4] - 2026-02-23

### Changed

- API and ingest container runtimes migrated from `python:3.12-slim-bookworm` to UBI 10 micro (3-stage build: `ubi` -> `ubi-minimal` -> `ubi-micro`)
- Container runtime has no shell, no package manager -- only explicitly staged shared libraries
- Release notes now include container image table with pull and cosign verify commands
- Removed `cache-python: true` from all `setup-uv` CI steps (system Python used, cache was a no-op)
- ARM runner label references corrected from `ubuntu-24.04-arm64` to `ubuntu-24.04-arm` across docs

### Fixed

- Release workflow race condition: validate step now iterates all completed CI runs to find the one with container-build jobs (previously selected the wrong run when tag push and main push shared the same SHA)
- CI smoke tests use `podman exec /healthcheck` for api container (no wget in ubi-micro)
- Shebangs in healthcheck and start.py changed to `/app/.venv/bin/python` (no `/usr/bin/env` in ubi-micro)

### Security

- Eliminated 53 Debian CVEs (51 unfixable in stable) from api-service and ingest containers
- Remaining: 2 gnutls CVEs per Python service (awaiting upstream RHEL 10 patch)

## [0.1.0-alpha.3] - 2026-02-23

### Changed

- Container builds run on native ARM runners (`ubuntu-24.04-arm`) instead of QEMU emulation
- Container supply chain security: cosign keyless signing, SBOM attestation via syft, signature verification in release pipeline

### Fixed

- Release workflow authentication: cosign identity matching for tag-triggered CI runs
- Code scanning alert remediation

## [0.1.0-alpha.1] - 2026-02-22

### Added

- Multi-arch container release pipeline to ghcr.io (`release.yml`)
- Trivy container scanning with severity gate and dual-run strategy
- Manual trigger for Trivy security scan workflow
- Go-task build orchestration for polyglot monorepo (72 tasks across 6 Taskfiles)
- TRUSTED_PROXIES configuration and gRPC request correlation for API service
- Git hooks distribution via `.githooks/` with install script
- CI/CD pipeline: CodeQL scanning, SonarQube analysis, release quality gate
- Full-stack E2E integration tests for API, gRPC, and frontend
- Semantic search with cross-encoder re-ranking (Ask mode)
- AI chat interface with SSE streaming and session management
- Fit assessment tool with hybrid pre-analyzed and real-time AI analysis
- Dynamic role classification for fit assessment accuracy
- Data-driven content architecture: single `.mv2` file drives all content
- OCI 1.1 metadata labels and build annotations on all container images
- Rust SBOM embedding via cargo-auditable in memvid-service
- Prometheus metrics endpoint
- Specforge specification-driven development framework (phases 0-7 complete)
- 136 features defined, 125 verified

### Changed

- CI Python management delegated to uv via `.python-version` files (drop `setup-python`)
- Tool versions bumped: Node 22.14.0, uv 0.9.0, go-task 3.48.0, Rust 1.93.0, podman 5.8.0
- Memvid-service runtime switched to distroless base image with `--health` flag
- Memvid-service protobuf compilation uses GitHub releases binary instead of apt
- Container base images upgraded for security (alpine:3.23, python:3.12-slim, debian:trixie-slim)
- Dockerfiles optimized with UV best practices and stable base images
- ESLint upgraded to v10 with aligned peer dependencies
- Vitest and coverage-v8 upgraded from 3.x to 4.x
- Dependabot configured with conventional commit message format
- README rewritten; DEVELOPMENT.md added as canonical dev guide; EOL docs archived
- Memvid SDK upgraded to 2.0.157, core to 2.0.137

### Fixed

- Publish script uses `podman manifest push --all` for macOS manifest list resolution
- CI Python version mismatch: api-service and cross-service tested on 3.11 despite requiring 3.12
- Merge commit and dependabot CI compliance gaps
- Markdown lint pipeline gaps
- Frontend ProfileContext split to resolve fast refresh warning
- CodeQL taint tracking issues in API key handling
- Session ID generation switched to cryptographically secure `crypto.getRandomValues()`
- Unsafe `((VAR++))` bash arithmetic replaced with `$((VAR + 1))` across scripts
- Proto import path for local gRPC connectivity
- Domain mismatch check to prevent contradictory fit ratings
- E2E test reliability with health-gate and 429 handling
- Clippy warnings for Rust 1.93 compatibility
- Coverage gates scoped correctly for memvid integration modules

### Security

- GitHub Code Scanning alerts remediated (API key masking, secure session IDs, bind address documentation)
- `.claude` directory removed from git history
- Container images hardened with distroless runtime and SBOM
- Base image upgrades to address known CVEs

[Unreleased]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.4...HEAD
[0.1.0-alpha.4]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.1...v0.1.0-alpha.3
[0.1.0-alpha.1]: https://github.com/schwichtgit/ai-resume/releases/tag/v0.1.0-alpha.1

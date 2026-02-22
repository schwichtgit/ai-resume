# Changelog

All notable changes to the **ai-resume** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Release pipeline specifications and feature definitions
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
- 124 features implemented and verified

### Changed

- Memvid-service runtime switched to distroless base image with `--health` flag
- Memvid-service protobuf compilation uses GitHub releases binary instead of apt
- Container base images upgraded for security (alpine:3.23, python:3.12-slim, debian:trixie-slim)
- Dockerfiles optimized with UV best practices and stable base images
- ESLint upgraded to v10 with aligned peer dependencies
- Vitest and coverage-v8 upgraded from 3.x to 4.x
- Rust toolchain pinned to 1.92.0 for reproducible builds
- Dependabot configured with conventional commit message format
- README rewritten; DEVELOPMENT.md added as canonical dev guide; EOL docs archived
- Memvid SDK upgraded to 2.0.157, core to 2.0.137

### Fixed

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

[Unreleased]: https://github.com/schwichtgit/ai-resume/commits/HEAD

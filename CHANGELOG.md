# Changelog

All notable changes to the **ai-resume** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Specforge scaffold upgraded from alpha.8 to alpha.9
  - `scripts/hooks/pre-commit`: added markdown and YAML lint checks for staged files
  - `CLAUDE.md.template`: expanded with service environment table, subagent delegation policy, spec-driven workflow table, API/testing/container/MR-PR sections
  - `ci/github/dependabot.yml`: added Go (gomod) commented-out ecosystem entry

## [0.1.0-alpha.12] - 2026-04-10

### Added

- Playwright E2E smoke test suite for frontend (#152)

### Changed

- lucide-react upgraded from 0.577.0 to 1.7.0 (major); brand icons replaced with inline SVGs (#157)
- vite bumped from 8.0.3 to 8.0.5 in frontend (#158)
- fastmcp bumped from 3.0.2 to 3.2.0 in api-service (#151)
- poetry bumped from 2.3.1 to 2.3.3 in api-service (#153)
- SonarSource/sonarqube-scan-action bumped from 7.0.0 to 7.1.0 (#154)
- 7 minor/patch frontend dependency updates (#156)
- 2 minor/patch memvid-service dependency updates (#155)
- Specforge scaffold upgraded from alpha.5 to alpha.8 (#160, #161)

### Fixed

- Release-gate wired into CI summary job; deduplicated security scan steps (#150)

### Security

- cryptography bumped from 46.0.6 to 46.0.7 in api-service (#159)
- CVE-2026-28390 (libssl3 in distroless) suppressed pending upstream rebuild (#157)

## [0.1.0-alpha.11] - 2026-03-29

### Changed

- TypeScript upgraded from 5.x to 6.0.2; removed deprecated `baseUrl` from tsconfig (#145)
- date-fns upgraded from 3.x to 4.1.0 (#145)
- jsdom upgraded from 27.x to 29.0.1 (devDependency, #145)
- globals upgraded from 15.x to 17.4.0 (devDependency, #145)
- npm upgraded from 11.10.1 to 11.12.1 in frontend Dockerfile (#145)
- cryptography bumped from 46.0.5 to 46.0.6 in api-service (#139)
- requests bumped from 2.32.5 to 2.33.0 in api-service (#137)
- picomatch bumped from 4.0.3 to 4.0.4 in frontend (#136)
- OTel JS exporter-trace-otlp-http and instrumentation-fetch bumped to 0.214.0 (#148)
- 22 specforge features verified; stale testing steps updated (#138)
- api-service CI job now reports coverage in GITHUB_STEP_SUMMARY (#138)

### Fixed

- Add `@opentelemetry/sdk-trace-base` as explicit dependency; Rolldown fails on transitive-only imports (#147)
- Remove duplicate PreToolUse hooks from project settings.json (plugin provides these)

### Security

- aws-lc-sys bumped from 0.38.0 to 0.39.1 via aws-lc-rs 1.16.2; fixes Dependabot alerts #25, #26 (X.509 Name Constraints Bypass, CRL Distribution Point Scope Check)
- Pygments bumped from 2.19.2 to 2.20.0 in api-service and ingest; fixes Dependabot alerts #29, #30 (ReDoS in GUID matching)

## [0.1.0-alpha.10] - 2026-03-25

### Changed

- dorny/paths-filter bumped from 3 to 4 in CI workflow (#128)
- sonner bumped from 1.7.4 to 2.0.7 (toast notification library, major) (#131)
- tailwind-merge bumped from 2.6.1 to 3.5.0 (CSS class merging, major) (#132)
- @types/node bumped from 22.19.15 to 25.5.0 (devDependency) (#133)
- 12 minor/patch frontend dependency updates (#134)
- opentelemetry-otlp bumped from 0.31.0 to 0.31.1 in memvid-service (#129)
- rustls-webpki bumped from 0.103.9 to 0.103.10 in memvid-service (#126)
- lz4_flex bumped from 0.12.0 to 0.12.1 in memvid-service (#125)
- flatted bumped from 3.4.1 to 3.4.2 (devDependency) (#127)
- authlib bumped from 1.6.8 to 1.6.9 in api-service (#124)

### Security

- Security review completed: no high-confidence vulnerabilities found in dependency changes
- aws-lc-sys 0.38.0 CVEs (alerts #25, #26) assessed as not exploitable -- no TLS connections made via affected code path; blocked on upstream fix (0.39.0 not yet resolvable)
- Pygments ReDoS alerts (#29, #30) assessed as non-impacting -- test/dev tooling only, not loaded in production

## [0.1.0-alpha.9] - 2026-03-15

### Changed

- Vite upgraded from 7.x to 8.x (Rolldown bundler replaces esbuild/Rollup)
- `@vitejs/plugin-react-swc` replaced with `@vitejs/plugin-react` (Oxc-based)
- Tailwind CSS migrated from v3 to v4 (CSS-first architecture)
- `tailwind.config.ts` and `postcss.config.js` removed (Tailwind v4 uses `@tailwindcss/vite` plugin and `@theme` CSS directives)
- `tailwindcss-animate` replaced with `tw-animate-css` (Tailwind v4 compatible)
- OpenTelemetry Rust crates upgraded from 0.27.x to 0.31.x (opentelemetry, opentelemetry_sdk, opentelemetry-otlp, tracing-opentelemetry)
- 8 Dependabot dependency bumps rolled up into single PR (#122)
- Test isolation for memvid exclusive file locking (#118)
- Frontend TypeScript API fixes for react-day-picker v9, react-resizable-panels v4, OTel SDK v2 (#119)
- Memvid SDK 2.0.159 / Core 2.0.139 (#117)

### Security

- CVE-2026-22184 (zlib buffer overflow) patched via `apk upgrade` in frontend Dockerfile

## [0.1.0-alpha.8] - 2026-03-03

### Changed

- Memvid SDK upgraded from 2.0.157 to 2.0.158 (PyPI)
- Memvid Core upgraded from 2.0.137 to 2.0.138 (crates.io)
- Memvid CLI version pins updated to 2.0.158 in E2E scripts and CI workflow
- `repro_bug_c.py` rewritten to use `find(mode="hybrid")` instead of deprecated `ask()` API (removed `top_k` kwarg)
- Upstream bug report updated: #194 FIXED, #196 partial fix (`find()` works, `ask()` still needs doctor workaround)
- README updated: added MCP server, chat feedback, version, and MCP config endpoints to API table; added MCP Server description

### Fixed

- Rust real-searcher tests fail with "exclusive access unavailable" on memvid-core 2.0.138 due to new file locking; added `#[serial]` to all tests sharing the `.mv2` file

### Security

- Updated `aws-lc-sys` to 0.38.0 fixing 3 high-severity CVEs (PKCS7_verify bypass, AES-CCM timing side-channel)

## [0.1.0-alpha.7] - 2026-03-02

### Added

- gRPC method latency breakdown: `method` label on `memvid_search_latency_ms` histogram (search, ask, get_state)
- Search relevance metrics: `memvid_search_relevance_score` and `memvid_search_chunks_returned` histograms in Rust memvid-service
- Span attributes for retrieval quality: `search.max_relevance`, `search.min_relevance`, `search.avg_relevance`, `search.chunks_returned`
- SSE streaming timing: `chat.time_to_first_token_ms` and `chat.streaming_duration_ms` span attributes in frontend
- `isOtelInitialized()` guard for conditional browser tracing
- Chat feedback endpoint: `POST /api/v1/chat/{session_id}/feedback` with idempotent counter and structured logging
- ThumbsUp/ThumbsDown UI on assistant chat messages with fire-and-forget feedback submission
- Retrieval Quality dashboard: relevance score distribution, chunks/query histogram, configurable low-relevance threshold
- Quality Evals dashboard: feedback rate, positive/negative ratio, Loki log panel with Tempo Data Links
- Success rate % and total error count KPI stat panels on Endpoint Overview dashboard
- gRPC method template variable and per-method p50/p95/p99 panel on Latency Breakdown dashboard
- SSE Streaming row with TTFT and duration panels on Latency Breakdown dashboard

### Changed

- `docs/OBSERVABILITY.md` updated for all Phase 2 features (6 dashboards, new metrics, new runbook)
- Fluent Bit and Loki environment variables added to `deployment/.env.example`

### Fixed

- PreToolUse hook false errors: removed `set -e` from all hook scripts (exit 1 on internal subcommand edge cases reported as "hook error")
- `protect-files.sh` now allows `.env.example` and `.env.sample` edits (priority match before `.env*` block)
- Dashboard metric names and panel types corrected across all Grafana dashboards
- Release gate ingest outcome tests no longer fail on 0% coverage (`--no-cov` for data validation tests)

## [0.1.0-alpha.6] - 2026-03-01

### Added

- End-to-end distributed tracing with OpenTelemetry across all three services (Python, Rust, TypeScript)
- W3C trace context propagation (`traceparent` header) through the full request chain
- Browser tracing via `@opentelemetry/sdk-trace-web` with fetch instrumentation
- OpenTelemetry trace export in memvid-service via `tracing-opentelemetry`
- Observability stack: Grafana, Tempo, Prometheus, Loki, OTEL Collector (`deployment/observability/`)
- Fluent Bit log shipper for production host log forwarding
- Pre-provisioned Grafana dashboards (request waterfall, latency breakdown, endpoint overview, LLM cost)
- Combined dev compose (`compose.dev.yaml`) for single-host observability testing
- Comprehensive observability guide with runbooks (`docs/OBSERVABILITY.md`)

### Changed

- React upgraded from 18.3 to 19.2 (`react`, `react-dom`, `@types/react`, `@types/react-dom`)
- `vaul` upgraded from 0.9.9 to 1.1.2 (React 19 peer dependency compatibility)
- Documentation references updated from React 18 to React 19 across all project files
- Dependency bumps: rollup 4.59.0, minimatch 9.0.9, react-day-picker 9.14.0, chrono (memvid-service minor/patch group), actions/upload-artifact v7, frontend minor/patch batch

### Fixed

- Release validate step waits for successful container builds (#81)
- Missing `lua-resty-http` `http_connect.lua` module in frontend container
- Cargo fmt and mypy type annotation failures in CI
- Removed unused `type: ignore` comments; fixed mypy `arg-type`/`union-attr` errors

## [0.1.0-alpha.5] - 2026-02-25

### Added

- MCP server with Streamable HTTP transport (FastMCP), mounted at `/mcp` with stateless tool invocation
- MCP tools: `ask_question` (semantic resume search + LLM) and `assess_fit` (job fit evaluation)
- MCP resources: `profile://current` and `questions://suggested`
- MCP config endpoint (`/api/v1/mcp/config/{client_id}`) with templates for desktop app, Claude Code CLI, web interface, and Cursor IDE
- WebMCP browser tool registration using Chrome `registerTool()` API with execute handlers
- Header menu with About dialog (version, commit SHA, links) and MCP Config dialog
- Footer redesign with version display and corrected links
- Build-time version injection (`/api/v1/version` endpoint, `VERSION` file in frontend)
- Vite dev proxy for `/mcp` path (matches nginx production routing)

### Changed

- MCP enabled by default (opt-out via `MCP_ENABLED=false`)
- Hero section layout: reduced gap between header and content
- Frontend container: OpenResty lua-resty-http installed via direct download instead of apk (avoids Alpine nginx 1.28 / openresty 1.27 package conflict)

### Fixed

- OpenRouter client crashes on HTTP 200 error responses (missing `choices` key)
- MCP mount 307 redirect: path rewrite middleware replaces complex ASGI forwarding
- MCP lifespan resilient to StreamableHTTPSessionManager reuse across test sessions
- Nginx regex routes `/mcp` (no trailing slash) to API backend
- MCP config dialog loads first tab config on open (no tab switch required)
- MCP config URL uses frontend origin instead of API backend address
- Blog URLs corrected in Footer and About dialog
- Quality hook finds system ruff and uses npx for markdownlint

### Security

- Upgraded cryptography 46.0.4 to 46.0.5 (CVE-2026-26007)

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

[Unreleased]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.12...HEAD
[0.1.0-alpha.12]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.11...v0.1.0-alpha.12
[0.1.0-alpha.11]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.8...v0.1.0-alpha.11
[0.1.0-alpha.8]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.7...v0.1.0-alpha.8
[0.1.0-alpha.7]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.6...v0.1.0-alpha.7
[0.1.0-alpha.6]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.5...v0.1.0-alpha.6
[0.1.0-alpha.5]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.4...v0.1.0-alpha.5
[0.1.0-alpha.4]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.1...v0.1.0-alpha.3
[0.1.0-alpha.1]: https://github.com/schwichtgit/ai-resume/releases/tag/v0.1.0-alpha.1

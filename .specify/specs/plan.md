# Technical Plan: ai-resume

## Overview

**Project:** ai-resume
**Spec Version:** 1.0.0
**Plan Version:** 1.0.0
**Last Updated:** 2026-02-19
**Status:** Approved

---

## Project Structure

```text
ai-resume/
├── frontend/                        # React 18 SPA (Vite + TypeScript + shadcn/ui)
│   ├── src/
│   │   ├── components/              # Section + UI components
│   │   │   ├── AIChat.tsx           # SSE streaming chat interface
│   │   │   ├── Experience.tsx       # Dynamic experience cards
│   │   │   ├── ExperienceCard.tsx   # Individual experience card
│   │   │   ├── FitAssessment.tsx    # Hybrid fit assessment (pre-analyzed + live)
│   │   │   ├── Footer.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Hero.tsx
│   │   │   ├── NavLink.tsx
│   │   │   └── ui/                  # 49 shadcn/ui primitives
│   │   ├── context/
│   │   │   └── ProfileContext.tsx    # React context for profile data
│   │   ├── hooks/
│   │   │   ├── useProfile.ts        # Fetches /api/v1/profile on mount
│   │   │   ├── useStreamingChat.ts  # SSE streaming hook for chat
│   │   │   ├── use-mobile.tsx
│   │   │   ├── use-toast.ts
│   │   │   └── __tests__/           # Hook unit tests
│   │   ├── lib/
│   │   │   ├── api-client.ts        # Typed fetch wrappers
│   │   │   ├── utils.ts             # cn() classname utility
│   │   │   └── __tests__/           # Lib unit tests
│   │   ├── pages/
│   │   │   ├── Index.tsx            # Main page (section composition)
│   │   │   └── NotFound.tsx
│   │   ├── test/
│   │   │   └── setup.ts             # Vitest + RTL test setup
│   │   ├── App.tsx                  # Router + QueryClientProvider
│   │   └── main.tsx                 # Entrypoint
│   ├── Dockerfile                   # Multi-stage: node build -> OpenResty runtime
│   ├── nginx.conf                   # SPA routing, /api/* proxy, security headers
│   ├── package.json
│   ├── vite.config.ts               # Dev proxy /api -> localhost:3000
│   ├── vitest.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── eslint.config.js
│   └── postcss.config.js
│
├── api-service/                     # Python FastAPI orchestration layer
│   ├── ai_resume_api/               # Application package
│   │   ├── main.py                  # FastAPI app, endpoints, SSE streaming
│   │   ├── config.py                # Pydantic Settings (env-driven)
│   │   ├── models.py                # Request/response Pydantic models
│   │   ├── memvid_client.py         # gRPC client to memvid-service
│   │   ├── openrouter_client.py     # httpx client for OpenRouter LLM API
│   │   ├── guardrails.py            # Input sanitization + prompt injection defense
│   │   ├── query_transform.py       # Query rewriting for better retrieval
│   │   ├── role_classifier.py       # Job description classification
│   │   ├── session_store.py         # In-memory session management (TTL cache)
│   │   ├── observability.py         # structlog + OpenTelemetry + Prometheus
│   │   └── proto/                   # Generated gRPC Python stubs
│   ├── tests/                       # pytest suite
│   ├── Dockerfile
│   ├── main.py                      # CLI entrypoint
│   ├── start.py                     # Uvicorn startup wrapper
│   └── pyproject.toml               # Hatchling build, ruff, mypy, pytest config
│
├── memvid-service/                  # Rust gRPC retrieval engine
│   ├── src/
│   │   ├── main.rs                  # Tokio entrypoint, server bootstrap
│   │   ├── lib.rs                   # Library root
│   │   ├── config.rs                # Typed config from env vars
│   │   ├── error.rs                 # ServiceError -> tonic::Status mapping
│   │   ├── metrics.rs               # Prometheus metrics via metrics crate
│   │   ├── grpc/
│   │   │   ├── mod.rs
│   │   │   └── service.rs           # MemvidService gRPC implementation
│   │   └── memvid/
│   │       ├── mod.rs
│   │       ├── searcher.rs          # Trait-based search abstraction
│   │       ├── real.rs              # memvid-core integration
│   │       └── mock.rs              # Mock searcher for testing
│   ├── tests/
│   │   └── main_integration_tests.rs
│   ├── build.rs                     # tonic-build proto compilation
│   ├── Dockerfile
│   ├── Cargo.toml
│   └── rust-toolchain.toml          # Pinned to Rust 1.92.0
│
├── ingest/                          # Python data ingestion pipeline
│   ├── ingest.py                    # Parses master_resume.md -> .mv2 file
│   ├── compare_models.py            # Embedding model comparison tool
│   ├── tests/                       # Parsing, retrieval, edge-case tests
│   └── pyproject.toml               # memvid-sdk, sentence-transformers deps
│
├── proto/                           # Canonical Protobuf definitions
│   └── memvid/v1/
│       └── memvid.proto             # MemvidService + Health RPCs
│
├── data/                            # Resume source content
│   ├── frank_resume.md              # Live resume (YAML frontmatter + markdown)
│   └── example_resume.md            # Template for new users
│
├── deployment/                      # Container orchestration
│   ├── compose.yaml                 # podman compose for 3-service stack
│   └── pyproject.toml               # podman compose dependency
│
├── .githooks/                       # Git hooks (core.hooksPath target)
│   ├── pre-commit                   # ESLint, ruff, clippy, shellcheck
│   └── commit-msg                   # Conventional Commits validation
│
├── scripts/                         # Build, test, and deploy automation
│   ├── build-all.sh                 # Build all containers
│   ├── gen-proto.sh                 # Regenerate gRPC stubs from proto/
│   ├── dev-setup.sh                 # Developer environment bootstrap
│   ├── test-e2e-*.sh               # E2E test runners (mock + real)
│   ├── release-gate.sh              # Release quality gate checks
│   └── verify-quality.sh            # Pre-push quality verification
│
├── ci/                              # CI/CD templates and principles
│   ├── github/workflows/            # Reusable workflow templates
│   └── principles/                  # Commit/PR/release gate docs
│
├── .github/workflows/               # Active GitHub Actions
│   ├── ci.yml                       # Main CI pipeline
│   └── sonarqube.yml                # SonarQube analysis
│
├── docs/                            # Project documentation
│   ├── ARCHITECTURE.md
│   ├── PRD.md
│   ├── DEVELOPMENT.md
│   ├── SETUP.md
│   ├── SECURITY.md
│   ├── TEST_COVERAGE.md
│   └── MASTER_DOCUMENT_SCHEMA.md
│
├── .specify/                        # Specforge artifacts
│   ├── memory/
│   │   └── constitution.md          # Immutable project principles
│   ├── specs/
│   │   ├── spec.md                  # Feature specification
│   │   └── plan.md                  # This file
│   └── templates/                   # Specforge templates + schemas
│
├── .claude/                         # Claude Code configuration
│   ├── settings.json
│   ├── hooks/                       # Claude Code hook scripts
│   └── skills/                      # Custom slash commands
│
├── CLAUDE.md                        # Claude Code project instructions
├── README.md
├── AUTHORS.md
├── LICENSE
├── CODE_OF_CONDUCT.md
├── .gitignore
├── .markdownlintrc
├── .prettierrc.json
└── .prettierignore
```

---

## Tech Stack

### Frontend

| Component         | Choice                | Version            | Rationale                                                     |
| ----------------- | --------------------- | ------------------ | ------------------------------------------------------------- |
| UI Framework      | React                 | ^18.3.1            | Mature ecosystem; component model fits section-based layout   |
| Build Tool        | Vite                  | ^7.3.1             | Sub-second HMR; native ESM; SWC plugin for fast JSX transform |
| Language          | TypeScript            | ^5.8.3             | Type safety across hooks, API client, and component props     |
| CSS Framework     | Tailwind CSS          | ^3.4.17            | Utility-first; design token system via CSS variables          |
| Component Library | shadcn/ui (Radix)     | 49 components      | Accessible, unstyled primitives; copy-paste ownership model   |
| Routing           | React Router DOM      | ^6.30.1            | SPA client-side routing with catch-all for 404                |
| State Management  | TanStack Query        | ^5.83.0            | Server-state caching (configured; profile uses custom hook)   |
| Form Validation   | Zod + react-hook-form | ^3.25.76 / ^7.61.1 | Schema-first validation for fit assessment input              |
| Icons             | Lucide React          | ^0.462.0           | Tree-shakeable icon set, consistent with shadcn defaults      |
| Test Runner       | Vitest                | ^3.2.4             | Vite-native; same transform pipeline as dev server            |
| Test Utilities    | React Testing Library | ^16.0.0            | User-centric DOM assertions                                   |
| DOM Environment   | jsdom                 | ^27.4.0            | Browser-like test environment (requires Node >=20.19)         |
| Linting           | ESLint                | ^9.32.0            | Flat config; react-hooks + react-refresh plugins              |
| Animations        | tailwindcss-animate   | ^1.0.7             | Declarative CSS animations (fade-in, slide-up, pulse-soft)    |

### Backend / API Service

| Component       | Choice                             | Version             | Rationale                                                  |
| --------------- | ---------------------------------- | ------------------- | ---------------------------------------------------------- |
| Runtime         | Python                             | >=3.12, <3.13       | f-string improvements; match/case; typing generics         |
| Web Framework   | FastAPI                            | >=0.115.6           | Async-first; auto OpenAPI docs; Pydantic v2 integration    |
| ASGI Server     | Uvicorn                            | >=0.34.0            | Standard extras for HTTP/1.1 + uvloop                      |
| Data Validation | Pydantic                           | >=2.10.6            | 14 request/response models with Field constraints          |
| Settings        | pydantic-settings                  | >=2.7.1             | Env-driven config with type coercion                       |
| gRPC Client     | grpcio + grpcio-tools              | >=1.69.0            | Communication with Rust memvid-service                     |
| HTTP Client     | httpx                              | >=0.28.1            | Async requests to OpenRouter LLM API                       |
| Rate Limiting   | slowapi                            | >=0.1.9             | Per-IP rate limiting on chat/assess endpoints              |
| Observability   | structlog + OpenTelemetry          | >=24.4.0 / >=1.29.0 | Structured JSON logs; distributed tracing with X-Trace-ID  |
| Metrics         | prometheus-client + instrumentator | >=0.21.1 / >=7.0.0  | Auto HTTP metrics; exposed at /metrics                     |
| Caching         | cachetools                         | >=5.5.0             | TTL cache for profile and memvid health checks             |
| Linting         | ruff + mypy                        | >=0.8.6 / >=1.14.1  | Fast linting; strict type checking (disallow_untyped_defs) |
| Testing         | pytest + pytest-asyncio            | >=8.3.4 / >=0.25.2  | Async test support; coverage via pytest-cov                |
| Build System    | Hatchling                          | (build-backend)     | PEP 517 compliant; minimal config                          |

### Memvid Service (Rust)

| Component             | Choice                                | Version                         | Rationale                                                     |
| --------------------- | ------------------------------------- | ------------------------------- | ------------------------------------------------------------- |
| Language              | Rust                                  | Edition 2021 (toolchain 1.92.0) | Memory safety; sub-millisecond search; zero-cost abstractions |
| Async Runtime         | Tokio                                 | 1 (full features)               | Industry-standard async runtime for gRPC + HTTP servers       |
| gRPC Framework        | Tonic                                 | 0.12                            | Pure-Rust gRPC; tonic-build for codegen from .proto           |
| gRPC Health           | tonic-health                          | 0.12                            | Standard gRPC health checking protocol                        |
| Serialization (Proto) | Prost                                 | 0.13                            | Protobuf code generation paired with tonic                    |
| HTTP Framework        | Axum                                  | 0.7                             | Metrics endpoint; tower middleware compatibility              |
| Middleware            | Tower + tower-http                    | 0.4 / 0.5                       | Layered middleware: tracing, CORS                             |
| Memvid SDK            | memvid-core                           | 2.0.136                         | Native .mv2 file loading; hybrid/semantic/lexical search      |
| Error Handling        | thiserror + anyhow                    | 2.0 / 1.0                       | Typed errors (ServiceError -> tonic::Status)                  |
| Observability         | tracing + tracing-subscriber          | 0.1 / 0.3                       | Structured logging with env-filter and JSON output            |
| Metrics               | metrics + metrics-exporter-prometheus | 0.24 / 0.16                     | Prometheus-compatible metric export                           |
| Serialization (JSON)  | serde + serde_json                    | 1.0                             | Profile metadata deserialization from .mv2 state              |

### Data Ingestion Pipeline

| Component   | Choice                | Version  | Rationale                                          |
| ----------- | --------------------- | -------- | -------------------------------------------------- |
| Runtime     | Python                | >=3.12   | Matches api-service; ecosystem for ML tooling      |
| Memvid SDK  | memvid-sdk            | 2.0.153  | Parses markdown, chunks, embeds, writes .mv2 files |
| Embeddings  | sentence-transformers | >=3.0.0  | HuggingFace models; NPU acceleration on macOS      |
| HTTP Client | httpx                 | >=0.28.1 | Downloads or pushes artifacts                      |

### Data Storage

| Layer           | Format                  | Description                                                                                                                                               |
| --------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source of Truth | `data/master_resume.md` | YAML frontmatter (name, title, tags, suggested_questions, system_prompt) + markdown sections (experience with AI context, skills, fit examples)           |
| Vector Store    | `.mv2` binary file      | Single portable file containing vector embeddings, BM25 lexical index, chunked content, and key-value state (profile metadata). Generated by `ingest.py`. |
| State Retrieval | `GetState` gRPC RPC     | O(1) lookup of profile JSON from .mv2 state store (entity: `__profile__`), avoiding search truncation for structured metadata                             |
| Session Storage | In-memory (Python dict) | Chat sessions with TTL-based eviction; no persistent store                                                                                                |

### API Design

#### External API (REST + SSE)

| Endpoint                      | Method | Purpose                                                    |
| ----------------------------- | ------ | ---------------------------------------------------------- |
| `/api/v1/profile`             | GET    | Full profile (experience, skills, fit examples)            |
| `/api/v1/chat`                | POST   | Chat with streaming (SSE) or non-streaming response        |
| `/api/v1/suggested-questions` | GET    | Pre-configured conversation starters                       |
| `/api/v1/assess-fit`          | POST   | Real-time job description fit analysis                     |
| `/health`, `/api/v1/health`   | GET    | Service health (memvid connection, session count, version) |
| `/metrics`                    | GET    | Prometheus metrics (auto-instrumented)                     |

- **Authentication:** None (public resume site, no user accounts)
- **Streaming Protocol:** Server-Sent Events (SSE) for chat. Events typed as `retrieval | token | metadata | error | done` via `ChatStreamEvent` model.
- **Request Correlation:** `X-Trace-ID` header injected by middleware; propagated through structlog context for log correlation.

#### Internal API (gRPC)

| RPC        | Service       | Purpose                                                 |
| ---------- | ------------- | ------------------------------------------------------- |
| `Search`   | MemvidService | Semantic/lexical/hybrid search over .mv2 index          |
| `Ask`      | MemvidService | Question-answering with retrieval + optional re-ranking |
| `GetState` | MemvidService | O(1) entity/state lookup (profile metadata)             |
| `Check`    | Health        | gRPC health checking protocol                           |

- **Proto Package:** `memvid.v1` (canonical definition in `proto/memvid/v1/memvid.proto`)
- **Search Modes:** `ASK_MODE_HYBRID` (default), `ASK_MODE_SEM`, `ASK_MODE_LEX`

#### Error Format

Errors return JSON with `detail` field (FastAPI `HTTPException` pattern):

```json
{ "detail": "Search service unavailable. Please try again later." }
```

| Exception Class            | HTTP Status | Scenario                             |
| -------------------------- | ----------- | ------------------------------------ |
| `MemvidConnectionError`    | 503         | Memvid gRPC service unreachable      |
| `MemvidSearchError`        | 502         | Search operation failed              |
| `OpenRouterAuthError`      | 503         | LLM API key missing or invalid       |
| `OpenRouterError`          | 502         | LLM API call failed                  |
| `RateLimitExceeded`        | 429         | Per-IP rate limit hit (via slowapi)  |
| Pydantic `ValidationError` | 422         | Request body fails schema validation |

Rust side: `ServiceError` variants map to gRPC status codes (`NotFound`, `Internal`, `InvalidArgument`, `Unavailable`).

---

## Testing Strategy

| Type                | Framework                               | Coverage Target                 | Command                                                                 |
| ------------------- | --------------------------------------- | ------------------------------- | ----------------------------------------------------------------------- |
| Frontend Unit       | Vitest 3.2 + RTL 16 + jsdom 27          | 85% line                        | `cd frontend && npm test`                                               |
| API Service Unit    | pytest 8.3 + pytest-asyncio 0.25        | 85% line                        | `cd api-service && uv run pytest -v --tb=short`                         |
| Ingest Unit         | pytest 8.3 + pytest-asyncio 0.25        | 85% line                        | `cd ingest && uv run pytest -v --tb=short -m "not slow"`                |
| Memvid Service Unit | cargo test + serial_test 3              | 85% line                        | `cd memvid-service && cargo test`                                       |
| API Lint/Type       | ruff 0.8 + mypy 1.14 (strict)           | Zero errors                     | `cd api-service && uv run ruff check . && uv run mypy .`                |
| Ingest Lint/Type    | ruff 0.8 + mypy 1.14 (strict)           | Zero errors                     | `cd ingest && uv run ruff check . && uv run mypy .`                     |
| Memvid Lint         | clippy + rustfmt (1.92)                 | Zero warnings                   | `cd memvid-service && cargo clippy -- -D warnings && cargo fmt --check` |
| Frontend Lint/Type  | ESLint 9 + TypeScript 5.8               | Zero errors                     | `cd frontend && npm run lint && npx tsc --noEmit`                       |
| Integration (Mock)  | Bash + curl + Python assertions         | All assertions pass             | `./scripts/test-e2e-integration.sh`                                     |
| E2E Mock Gates      | Bash + curl (mock permutations)         | All 6 gate scenarios            | `./scripts/test-e2e-mock-gates.sh`                                      |
| E2E Real            | Bash + curl + real ingest + real memvid | 100% coverage, 0% hallucination | `./scripts/test-e2e-real.sh`                                            |
| Commit Standards    | Bash regex (CI-only)                    | Conventional Commits            | CI job `commit-standards`                                               |
| SonarQube           | SonarSource action                      | Quality gate                    | `.github/workflows/sonarqube.yml`                                       |

### Coverage

- **Minimum threshold:** 85% line coverage per service (constitution requirement)
- **Coverage tools:**
  - Frontend: `@vitest/coverage-v8` (V8 engine)
  - API Service: `pytest-cov` (coverage.py) with `--cov=ai_resume_api --cov-report=term-missing`
  - Ingest: `pytest-cov` (dev dependency; coverage addopts not yet wired)
  - Memvid Service: `cargo test` (no `cargo-tarpaulin` or `cargo-llvm-cov` configured yet)
- **Excluded paths:**
  - `frontend/src/components/ui/` (shadcn/ui generated code)
  - `api-service/ai_resume_api/proto/` (generated gRPC stubs)
- **Gap:** Frontend coverage collection and ingest/memvid-service coverage instrumentation are installed but not yet enforced in CI. The 85% gate must be wired into the CI summary job.

### E2E Quality Gate

The true E2E test (`scripts/test-e2e-real.sh`) enforces semantic quality across four phases:

1. **Ingest:** `data/example_resume.md` ingested into a temporary `.mv2` file (real sentence-transformers embeddings)
2. **Service startup:** Real memvid-service loads `.mv2`; real gRPC connection; only LLM is mocked (`MOCK_OPENROUTER=true`)
3. **Semantic quality (7 tests):** Profile identity, health connectivity, chat with real retrieval, suggested questions, fit assessment, SSE streaming
4. **Semantic coverage (13 tests):** One query per resume section category (FAQ, experience, skills, fit, gaps). Each must return `chunks_retrieved > 0`.

**Quality targets:**

- 100% category coverage: every resume section retrievable via semantic search
- 100% factual accuracy: profile identity fields match source markdown exactly
- 0% hallucination: all responses grounded in real memvid chunks (`chunks_retrieved > 0`)

---

## Deployment Architecture

| Component          | Platform                                                                      | Rationale                                                                                |
| ------------------ | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Production Host    | nanopi-r6s (RK3588 ARM64, 4GB RAM, OpenWrt)                                   | Low-power edge server; 180MB total runtime, 3.8GB headroom                               |
| Container Runtime  | Podman (rootless) + podman compose                                            | Daemonless, rootless by default; no Docker dependency                                    |
| Network            | `yellow-net` (192.168.100.0/24, external)                                     | Zone-isolated subnet with static IPs; firewall blocks cross-zone                         |
| Frontend Container | alpine + OpenResty (nginx + Lua)                                              | 35MB image; Lua SEO handler; Pattern B internal routing                                  |
| API Container      | python:3.12-slim-bookworm                                                     | 500MB image, 150-200MB runtime; FastAPI + gRPC client                                    |
| Memvid Container   | distroless/cc-debian12:nonroot (runtime), rust:1.93.1-slim-bookworm (builder) | ~10MB image, 20MB runtime; gRPC on :50051, metrics on :9090; protoc from GitHub releases |
| Host Load Balancer | nginx on host (outside Podman)                                                | TLS termination; domain routing; SSE proxy support                                       |
| Container Security | read_only, no-new-privileges, non-root                                        | All containers unprivileged; volumes mounted ro where possible                           |
| Data Volume        | `/opt/ai-resume/data` mounted ro                                              | .mv2 file + profile config; stateless containers                                         |
| Development        | Local multi-terminal (3 terminals)                                            | Cargo run, uvicorn --reload, npm run dev                                                 |
| CI/CD              | GitHub Actions (`.github/workflows/ci.yml`)                                   | Monorepo path filtering; conditional jobs per service; summary gate                      |
| Release Pipeline   | GitHub Actions (`.github/workflows/release.yml`)                              | Tag-triggered; Podman 5.8 (podman-static) + QEMU; Taskfile orchestration; ghcr.io push   |
| Build Pipeline     | `scripts/build-all.sh` via `task container:build`                             | Multi-arch (amd64 + arm64); Podman manifests; OCI annotations                            |
| Publish Pipeline   | `scripts/publish-containers.sh` via `task container:publish`                  | skopeo manifest copy; semver tag family; server-side re-tagging                          |
| Container Registry | ghcr.io/schwichtgit/ai-resume-{service}                                       | All 4 images; semver tags + latest + sha; monorepo versioning                            |
| Static Analysis    | SonarQube + CodeQL                                                            | Runs on push to main and PRs                                                             |

### Container Topology (Production)

```text
Host nginx (TLS) --> 192.168.100.10:8080 (frontend/OpenResty)
                         |
                         |--> /api/* proxy --> 192.168.100.11:3000 (api-service/FastAPI)
                                                   |
                                                   |--> gRPC --> 192.168.100.12:50051 (memvid-service/Rust)
                                                   |
                                                   |--> HTTPS --> OpenRouter API (external)
```

### Resource Budget (nanopi-r6s)

| Container                  | Memory    | CPU (idle/query)  | Image Size |
| -------------------------- | --------- | ----------------- | ---------- |
| Frontend (OpenResty + SPA) | 10MB      | Minimal           | 35MB       |
| API Service (FastAPI)      | 150MB     | 5-10% (streaming) | 500MB      |
| Memvid Service (Rust gRPC) | 20MB      | <1% / 5%          | 15MB       |
| **Total**                  | **180MB** | **<15%**          | **550MB**  |

---

## Development Environment

### init.sh Requirements

1. **System dependencies:**

   - `protoc` (protobuf compiler) -- required by both api-service (grpcio-tools) and memvid-service (tonic-build)
     - macOS: `brew install protobuf`
     - Ubuntu: `apt-get install -y protobuf-compiler`
   - `uv` (Python package manager by Astral) -- used for venv creation and dependency sync
     - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - `podman` (optional, for container builds) -- 5.0+
     - macOS: `brew install podman`

2. **Language runtimes:**

   - **Node.js 22.x** (CI uses `NODE_VERSION: "22"`; jsdom 27 requires Node 20.19+ minimum)
   - **Python 3.12** (api-service `requires-python = ">=3.12,<3.13"`; constitution specifies Python 3.12)
   - **Rust 1.92.0** (pinned in `memvid-service/rust-toolchain.toml`)

3. **Package installation:**

   ```bash
   # Frontend
   cd frontend && npm ci

   # API Service
   cd api-service && uv venv .venv && uv sync --extra test --extra lint

   # Ingest pipeline
   cd ingest && uv venv .venv && uv sync --extra test --extra lint

   # Memvid Service
   cd memvid-service && cargo fetch

   # Generate Python protobuf stubs
   ./scripts/gen-proto.sh
   ```

4. **Database setup:** N/A (memvid `.mv2` files, no external database)

5. **Verification:**

   ```bash
   # Full monorepo quality check
   ./scripts/verify-quality.sh

   # Per-service verification
   ./scripts/verify-quality.sh --service=frontend
   ./scripts/verify-quality.sh --service=api-service
   ./scripts/verify-quality.sh --service=memvid-service
   ./scripts/verify-quality.sh --service=ingest

   # Cross-service integration (mock backends)
   ./scripts/test-e2e-integration.sh

   # True E2E (real ingest -> real memvid -> real API, mock LLM only)
   ./scripts/test-e2e-real.sh
   ```

---

## Architectural Decisions

### ADR-001: Hybrid Rust + Python Architecture

**Date:** 2026-01-17
**Status:** Accepted

**Context:** The system requires sub-5ms semantic search retrieval from memvid `.mv2` files while also needing rapid iteration on API orchestration, LLM integration, and session management. The memvid core library is written in Rust. The target deployment is an ARM64 edge device with 4GB RAM.

**Decision:** Split the backend into two services: a Rust gRPC service for memvid retrieval (performance-critical path) and a Python FastAPI service for API orchestration, LLM streaming, and session management (iteration-critical path).

**Alternatives Considered:**

1. **Python-only:** Simpler single-language stack, but 10x larger memory footprint for memvid operations (~200MB vs ~20MB), 20x slower cold start (2-3s vs <100ms), GC pauses in the retrieval path, and no native FFI to memvid-core.
2. **Rust-only:** Optimal performance across the board, but 10x slower iteration on API logic (compile vs hot reload), weaker observability (no dynamic log levels, REPL, or live profiling), and immature LLM SDK ecosystem compared to Python.
3. **TypeScript monolith:** Shared language with frontend, but worse memvid integration (Node bindings vs Rust FFI), larger footprint (~80MB vs ~20MB for retrieval), and weaker AI ecosystem than Python.

**Consequences:**

- Positive: <5ms retrieval P95, ~20MB Rust memory, <100ms Rust cold start, Python hot reload for API changes, access to Python AI ecosystem for future complexity
- Negative: Two languages to maintain, inter-process communication overhead (~1-2ms gRPC, negligible vs LLM latency), more complex local dev setup

### ADR-002: Frontend as Router (Pattern B)

**Date:** 2026-01-17
**Status:** Accepted

**Context:** The three-container architecture requires URL routing -- specifically, directing `/api/*` requests to the Python service and all other requests to the React SPA. The deployment target uses a host-level nginx load balancer for TLS termination across multiple applications.

**Decision:** Application-level URL routing lives in the frontend container's nginx config. The host nginx LB handles only TLS termination and domain-to-IP routing, with no knowledge of `/api/*` paths.

**Alternatives Considered:**

1. **Host LB routing (Pattern A):** Host nginx owns all route rules. Simpler single routing layer, but couples infrastructure config to application route changes, requires LB restart for new API routes, breaks self-containment.
2. **Sidecar proxy (Envoy/Traefik):** Dedicated proxy container for routing. More flexible, supports traffic shaping, but adds a fourth container and is over-engineered for single-app deployment on a 4GB device.

**Consequences:**

- Positive: Self-contained deployment unit, host LB config changes only for new domains, no infrastructure dependency for API route additions
- Negative: Frontend container has dual responsibility (serving + proxying), nginx config is part of application codebase

### ADR-003: gRPC for Internal Communication

**Date:** 2026-01-17
**Status:** Accepted

**Context:** The Python API service needs to call the Rust memvid service for semantic search on every chat request. The call is latency-sensitive (target: <5ms). Both services run on the same host within a Podman network.

**Decision:** Use gRPC with Protocol Buffers for Python-to-Rust communication. REST/JSON + SSE is used externally (browser to Python API).

**Alternatives Considered:**

1. **REST/JSON internal:** Simpler to debug with curl, no protobuf compiler dependency, but larger payloads, slower serialization, no built-in streaming, no strongly-typed contract.
2. **Unix domain socket:** Lowest latency (no TCP overhead), but requires custom serialization, no ecosystem tooling, and Podman networking does not easily support cross-container UDS.

**Consequences:**

- Positive: Binary protocol minimizes overhead, strongly-typed `.proto` contract prevents API drift, built-in streaming for future Ask mode, mature tooling (grpcurl, grpcio, tonic)
- Negative: Requires `protoc` in dev/CI, generated code needs import path patching, harder to debug than REST

### ADR-004: OpenRouter for LLM Access

**Date:** 2026-01-17
**Status:** Accepted

**Context:** The chat interface requires LLM inference with streaming token output. The edge deployment target (nanopi-r6s, 4GB RAM) lacks compute capacity for local inference. Monthly cost must stay below $5 at 100 chats/day.

**Decision:** All LLM calls go through the OpenRouter API. No direct model hosting.

**Alternatives Considered:**

1. **Direct model hosting (llama.cpp, vLLM):** Zero per-query cost, full data privacy, but requires GPU or significant CPU exceeding the 4GB edge target, adds model management complexity.
2. **Direct provider APIs (OpenAI, Anthropic):** Slightly lower latency (one fewer hop), but locks into single provider, no model switching without code changes.

**Consequences:**

- Positive: Single API key for multiple providers, easy model switching, no compute requirements on edge, cost-optimized model selection
- Negative: External dependency (outage = no chat), network latency dominates (~500-2000ms), data sent to third-party API

### ADR-005: Single .mv2 File Data Portability

**Date:** 2026-01-17
**Status:** Accepted

**Context:** The system must be portable -- a single deployment artifact should contain all instance-specific resume content. No external database service.

**Decision:** All resume content lives in a single `.mv2` file containing vector embeddings, profile metadata, and chunked text. Generated offline from `data/master_resume.md` via the ingest pipeline. Mounted read-only into containers.

**Alternatives Considered:**

1. **SQLite database:** Proven, SQL-queryable, but no native vector search, larger disk footprint, adds database management layer.
2. **Multiple files (embeddings.bin + profile.json + chunks.jsonl):** Easier to inspect individually, but fragile deployment (missing one file breaks system), version synchronization issues.
3. **PostgreSQL with pgvector:** Full-featured vector search, but requires running database service (violates "no external database" constraint), over-engineered for single-user.

**Consequences:**

- Positive: Single-file deployment, atomic updates, human-readable source (markdown), no database dependency, <20MB runtime memory
- Negative: Full re-ingestion for any content change, no incremental updates, .mv2 format opaque without tooling

### ADR-006: Ephemeral Sessions (No Persistence)

**Date:** 2026-01-17
**Status:** Accepted

**Context:** The chat interface maintains conversation history for LLM context. The constitution mandates "no server-side conversation persistence." No swap on deployment target.

**Decision:** Sessions stored in-memory only using Python `cachetools.TTLCache` with 30-minute TTL. No conversation history written to disk.

**Alternatives Considered:**

1. **SQLite session store:** Persistence across restarts, queryable history, but violates constitution, adds disk I/O, increases attack surface.
2. **Redis/Valkey:** Fast in-memory with optional persistence, but adds a fourth service, consumes memory on 4GB device.
3. **Client-side storage (localStorage):** Zero server resources, but requires sending full history per request (increases LLM token cost), exposes data in browser.

**Consequences:**

- Positive: Zero disk I/O, minimal memory overhead (TTL eviction), no stored data to breach, aligns with privacy posture
- Negative: Sessions lost on restart or TTL expiry, no analytics on conversation patterns

### ADR-007: Yellow Zone Network Isolation

**Date:** 2026-01-17
**Status:** Accepted

**Context:** The edge server hosts multiple applications. Resume containers must not reach other services or adjacent VLANs. Containers need outbound internet for OpenRouter.

**Decision:** All three containers run in dedicated Podman network (`yellow-net`, `192.168.100.0/24`) with static IPs. Firewall rules block cross-zone traffic. No container ports published; host nginx connects directly to yellow-net.

**Alternatives Considered:**

1. **Shared host network:** Simplest setup, but no isolation, port conflicts possible, compromised container has full host network access.
2. **Default Podman bridge (no static IPs):** Less configuration, but dynamic IPs make firewall rules fragile, no CIDR-based zone isolation.

**Consequences:**

- Positive: Defense-in-depth, predictable static IPs for firewall rules, no published ports reduces attack surface, zone isolation matches enterprise patterns
- Negative: More complex initial setup, debugging requires awareness of zone topology, host nginx must have route to 192.168.100.0/24

### ADR-008: Distroless Runtime for Memvid Service (INFRA-024)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** The memvid-service runtime image uses `debian:trixie-slim` which carries 25 LOW/MEDIUM Trivy CVE alerts from unnecessary OS packages (shell, apt, coreutils, ncurses, etc.). The Rust binary only needs glibc, libgcc, and CA certificates at runtime.

**Decision:** Replace the runtime stage with `gcr.io/distroless/cc-debian12:nonroot`. Pin the builder to `rust:1.93.1-slim-bookworm` (glibc 2.36) to match the debian12 distroless runtime (glibc 2.36). The `:nonroot` tag provides UID 65534, eliminating the need for `useradd`. No shell commands in the runtime stage.

**Alternatives Considered:**

1. **`distroless/cc-debian13:nonroot`** -- glibc 2.41 match with trixie builder, but Google labels debian13 images as "not yet stable."
2. **musl static binary + `distroless/static`** -- Smallest possible image (~2MB), zero dynamic dependencies, but `memvid-core` and `aws-lc-sys` may have C dependencies that complicate musl cross-compilation.
3. **Keep `debian:trixie-slim`** -- No migration risk, but 25 unnecessary CVE alerts persist and the attack surface remains larger than necessary.

**Consequences:**

- Positive: Eliminates ~25 OS-level CVE alerts, no shell (reduced attack surface), smaller image, no package manager in runtime
- Negative: No shell for debugging (must use ephemeral debug containers), UID changes from 1000 to 65534 (compose.yaml volume ownership update needed), builder downgrade from trixie to bookworm

### ADR-009: OS-Independent Protoc Binary (INFRA-026)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** The memvid-service Dockerfile pins `protobuf-compiler=3.21.12-11` from Debian's package repository. This couples the protoc version to the OS. Switching from trixie to bookworm requires a different version pin. The `libprotobuf-dev` package is unnecessary -- `tonic-build`/`prost-build` only invoke the `protoc` binary and do not link against `libprotobuf`.

**Decision:** Download protoc v28.x (LTS) directly from GitHub releases (`protocolbuffers/protobuf`) using a pinned `ARG PROTOC_VERSION`. Map Docker `TARGETARCH` to protoc release naming (`amd64` -> `x86_64`, `arm64` -> `aarch_64`). Remove `protobuf-compiler` and `libprotobuf-dev` from apt dependencies.

**Alternatives Considered:**

1. **`protobuf-src` crate** -- Compiles protoc from C++ source via Cargo. Adds significant build time, bundles an old version (v3.19.1), may conflict with newer prost features.
2. **`protoc-bin-vendored` crate** -- Pre-compiled binary as a Cargo dependency. Fast but version is whatever the crate bundles (may lag behind).
3. **Keep apt package** -- Simplest but ties protoc version to OS, breaks on base image migration.

**Consequences:**

- Positive: Protoc version decoupled from OS, trivial to bump via `ARG`, multi-arch support, no unnecessary `libprotobuf-dev`
- Negative: Requires `curl` + `unzip` as transient build dependencies (removed after download)

### ADR-010: cargo-auditable for Rust SBOM (INFRA-025)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** Trivy and Grype have zero visibility into Rust crate dependencies in compiled binaries. Unlike Go (which embeds buildinfo automatically since 1.18), Rust binaries contain no dependency metadata by default. The security workflow scans memvid containers but only finds OS-level CVEs, creating a blind spot for Rust supply chain vulnerabilities.

**Decision:** Install `cargo-auditable` via `cargo install cargo-auditable` in the builder stage. Replace `cargo build --release` with `cargo auditable build --release`. This embeds a `.dep-v0` ELF section (~4KB) containing compressed JSON dependency data. Verification is end-to-end: Trivy scan output must include Rust crate entries. Compatible with `strip = true` release profile.

**Alternatives Considered:**

1. **Copy `Cargo.lock` into runtime image** -- Simpler, Trivy can scan the lockfile, but may not match what was actually compiled (layer caching discrepancies), adds unnecessary file to minimal runtime.
2. **Nightly `-Z sbom` flag** -- RFC 3553 native SBOM support, but behind an unstable flag, not ready for production.
3. **No SBOM** -- Status quo, zero visibility into Rust crate CVEs.

**Consequences:**

- Positive: Full Rust dependency visibility for scanners, ~4KB overhead, survives stripping, drop-in replacement for `cargo build`
- Negative: ~30s added to uncached builds for `cargo install cargo-auditable` (cached in Docker layer after first build)

### ADR-011: Trivy CI Gate with Dual-Run Strategy (FUNC-075)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** The security workflow's `severity: 'CRITICAL,HIGH'` filter is ineffective (aquasecurity/trivy-action#435). All severity levels are reported. The constitution requires critical/high CVEs patched within 7 days, but CI does not enforce this -- the pipeline never fails regardless of findings. Additionally, SARIF must be uploaded even when the pipeline should fail.

**Decision:** Two Trivy runs per container:

1. **Run 1 (SARIF):** `format: sarif`, no exit-code. Always succeeds. Uploads results to GitHub Code Scanning with explicit `category: 'trivy-${{ matrix.image }}'`.
2. **Run 2 (Gate):** `format: table` for readable output, `exit-code: '1'`. Uses `TRIVY_SEVERITY=CRITICAL,HIGH` and `TRIVY_IGNORE_UNFIXED=true` env vars. Fails CI only on fixable CRITICAL/HIGH CVEs.

A `.trivyignore` file (committed empty with comment header) provides documented override for explicitly accepted risks. Sequenced after INFRA-025 (cargo-auditable) to review newly-exposed Rust crate CVEs before the gate activates.

**Alternatives Considered:**

1. **Single run + `continue-on-error`** -- Less clear; the step shows as "passed with warnings" rather than a definitive pass/fail.
2. **Single run + `if: always()`** -- SARIF upload happens but the overall step failure semantics are muddled when multiple steps interact.

**Consequences:**

- Positive: Constitution compliance (CI fails on fixable CRITICAL/HIGH), SARIF always uploaded for visibility, `--ignore-unfixed` prevents blocking on CVEs with no available fix, `.trivyignore` provides escape hatch
- Negative: Two Trivy runs per container (adds ~30s per matrix entry to CI), more complex workflow YAML

### ADR-012: Memvid Health Check via gRPC Port Probe (INFRA-024)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** The current memvid-service healthcheck uses a `/healthcheck` symlink to the main binary. Distroless images have no shell, so `ln -s` is unavailable. The compose.yaml `healthcheck` must verify the service is actually serving, not just that the binary is runnable.

**Decision:** Add a `--health` CLI flag to the memvid-service binary that attempts a TCP connection to `localhost:50051` (the gRPC port). Exits 0 if the connection succeeds (service is listening), exits 1 otherwise. The compose.yaml healthcheck becomes `["/usr/local/bin/memvid-service", "--health"]`. No separate binary or symlink needed.

**Alternatives Considered:**

1. **Minimal exit 0** -- Only proves the binary starts, not that the gRPC server is running.
2. **HTTP /health on metrics port 9090** -- Would work but adds an HTTP handler to the metrics server, mixing concerns.
3. **`grpc_health_probe` binary** -- Standard gRPC health checking, but requires copying an additional binary into the distroless image.

**Consequences:**

- Positive: Verifies actual service availability (not just binary existence), no additional binaries needed, works in distroless without shell
- Negative: Requires a Rust code change (adding CLI argument parsing + TCP connect), binary serves dual purpose (server + health checker)

### ADR-013: Monorepo Versioning -- All Images Same Tag (INFRA-027)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** The repository contains four container images. Two versioning strategies are possible: all images share one version from a single git tag, or each image has independent versions (e.g., `frontend-v1.0.0`, `api-v2.1.0`). The `compose.yaml` uses a single `${VERSION:-latest}` variable for all images. All services are built and deployed together from the same commit.

**Decision:** All four images share the same version derived from a single git tag. A tag `v1.0.0` produces `ghcr.io/schwichtgit/ai-resume-frontend:v1.0.0`, `ai-resume-api:v1.0.0`, `ai-resume-memvid:v1.0.0`, and `ai-resume-ingest:v1.0.0`.

**Alternatives Considered:**

1. **Independent versioning** (`frontend-v1.0.0`, `api-v2.1.0`) -- More granular, but 4x release overhead, breaks compose.yaml's single `VERSION` variable, over-engineered for a single-developer project where all services deploy together.
2. **CalVer** (`2026.02.1`) -- Communicates recency but loses semantic meaning (major/minor/patch). Incompatible with the constitution's explicit SemVer 2.0.0 requirement.

**Consequences:**

- Positive: Simple mental model, one tag per release, compose.yaml works unmodified, single changelog
- Negative: A change to only one service still bumps the version for all images; unchanged images are rebuilt (acceptable for 4 images)

### ADR-014: Podman 5.8 + QEMU in CI via podman-static (INFRA-027)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** GitHub Actions `ubuntu-24.04` runners ship Podman 4.9.3. The project requires Podman 5.8+ for `podman farm build` (native multi-arch distribution). Multi-arch builds in CI require QEMU emulation since runners are amd64-only. The local development workflow uses Podman exclusively.

**Decision:** Install Podman 5.8.0 from `mgoltzsche/podman-static` (statically linked binary archive, ~5s install). Use `docker/setup-qemu-action@v3` for arm64 emulation. Use the pre-installed skopeo 1.13.3 for manifest publishing and server-side re-tagging. Registry-based `--cache-from`/`--cache-to` for layer caching between builds.

**Alternatives Considered:**

1. **Docker Buildx** (`docker/build-push-action` + `docker/setup-buildx-action`) -- Better caching (`type=gha` integrates with GitHub's cache service), dominant action ecosystem, but inconsistent with local Podman workflow and introduces a second container tool in the project.
2. **Native ARM64 runners** (`runs-on: ubuntu-24.04-arm`) -- Faster builds (no QEMU), but 2x runner cost, limited availability, requires matrix strategy + manifest merge step.
3. **Runner's Podman 4.9.3** -- Zero install overhead, but lacks `podman farm build`, older multi-platform `--platform` handling, and diverges from local dev toolchain.

**Consequences:**

- Positive: Consistent toolchain (Podman locally and in CI), `podman farm build` support, pinned version avoids runner update surprises
- Negative: No `type=gha` cache backend (registry-based caching is slower), Rust arm64 QEMU builds are slow (~15-30 min), `podman-static` is a third-party distribution

### ADR-015: Taskfile-Orchestrated Release Workflow (INFRA-027)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** Build logic already lives in Taskfile + scripts (`container:build` wraps `build-all.sh`, `container:publish` wraps `publish-containers.sh`). The release workflow could either call these existing targets or duplicate the logic in CI YAML.

**Decision:** Install `go-task` via `go-task/setup-task@v1` (~2s) in the release workflow. The workflow calls `task container:build` and `task container:publish` with `REGISTRY` and `VERSION` variables. CI owns only: tool installation, authentication, pre-build validation (CI gate, changelog check), Trivy scanning, and GitHub Release creation.

**Alternatives Considered:**

1. **Inline shell in YAML** -- No additional tool dependency, but duplicates Taskfile logic, creating two sources of truth that can drift.
2. **Call scripts directly** (`./scripts/build-all.sh`, `./scripts/publish-containers.sh`) -- Works but bypasses Taskfile's dependency resolution, variable propagation, and precondition checks.

**Consequences:**

- Positive: Single source of truth for build logic, `task container:build` works identically locally and in CI, workflow YAML is concise (~30 lines of steps)
- Negative: Adds `go-task` as a CI dependency, developers must understand Taskfile indirection

### ADR-016: Publish Script Multi-Tag Extension (FUNC-076)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** `publish-containers.sh` currently pushes a single `VERSION` tag and conditionally adds `latest`. FUNC-076 requires a full semver tag family: `v1.2.3`, `1.2.3`, `1.2`, `latest`, `sha-<short>` for stable releases, and only `v1.2.3-beta.1` + `sha-<short>` for pre-releases.

**Decision:** Extend `publish-containers.sh` to auto-detect stable vs pre-release from the version string (`[[ "$VERSION" == *-* ]]`). For stable releases, compute and push the full tag family using `skopeo copy --all docker://...source docker://...target` for server-side re-tagging (no re-upload). For pre-releases, push only the full version and SHA tags.

**Alternatives Considered:**

1. **Tag logic in workflow YAML** -- Works but moves domain logic out of the script, making local testing impossible.
2. **Separate `tag-containers.sh` script** -- Adds a new script for a single concern; better to co-locate with publishing.
3. **`docker/metadata-action`** -- Docker-specific GitHub Action for tag generation. Not Podman-native, adds Docker dependency.

**Consequences:**

- Positive: All tagging logic co-located with publishing, locally testable, server-side re-tagging avoids re-uploading multi-arch images
- Negative: Increased script complexity, semver parsing in bash (simple but not robust against malformed input)

### ADR-017: CI Gate via GitHub API Summary Job Check (FUNC-077)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** The release workflow must verify that CI has passed on the tagged commit before building and pushing images. The CI workflow (`.github/workflows/ci.yml`) has a `summary` aggregation job that depends on all per-service jobs (frontend, api-service, memvid-service, ingest linting, commit standards). If `summary` succeeds, all service checks have passed.

**Decision:** Use `gh api repos/{owner}/{repo}/actions/workflows/ci.yml/runs?head_sha={SHA}` to find the CI run for the tagged commit, then check if the `summary` job concluded with `success`. Fail immediately (no polling or retry) if the `summary` job is not found or did not succeed. Requires `checks: read` permission.

**Alternatives Considered:**

1. **`workflow_run` trigger** -- Release.yml fires automatically after ci.yml completes. Clean separation but unreliable with tag pushes (the tag event and the CI completion event are separate; `workflow_run` may not receive the tag context).
2. **Check all individual job statuses** -- More thorough but fragile (job names change, new jobs added without updating release.yml).
3. **Branch protection required checks** -- Robust but requires specific GitHub repo configuration and doesn't apply to tag pushes (only branch pushes and PRs).

**Consequences:**

- Positive: Simple and direct, checks the single aggregation gate, fails fast with clear error message
- Negative: No polling (if user tags before CI completes, release fails; must re-trigger manually), depends on the `summary` job name not changing

### ADR-018: uv-Managed Python in CI (INFRA-029)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** CI currently uses both `astral-sh/setup-uv@v7` and `actions/setup-python@v6` in every Python job -- redundant since uv can install and manage Python natively. The top-level `PYTHON_VERSION: '3.11'` env var contradicts `requires-python >= 3.12` in `api-service/pyproject.toml`, causing `api-service` and `cross-service` jobs to run on an unsupported Python version. Each Python service already has a `.python-version` file (3.12 for api-service and ingest, 3.13 for deployment).

**Decision:** Remove `actions/setup-python` from all 6 Python jobs in `ci.yml`. Add `enable-cache: true` and `cache-python: true` to each `astral-sh/setup-uv@v7` step. Delete the top-level `PYTHON_VERSION` env var. Let `uv sync` resolve the Python version from each service's `.python-version` file lazily (no explicit `uv python install` step).

**Alternatives Considered:**

1. **Keep setup-python, fix version to 3.12** -- Fixes the mismatch but retains the redundant action and the duplicated version pin (env var + .python-version file). Two sources of truth can drift again.
2. **Use setup-uv `python-version` input** -- Sets `UV_PYTHON` env var but does not install Python. Works for single-service jobs but requires per-job overrides for multi-service jobs. Adds complexity without benefit over `.python-version` files.
3. **Pin uv to specific minor (`@v7.2`)** -- Tighter reproducibility but breaks Dependabot auto-updates for the GitHub Actions ecosystem. The `@v7` major tag is the convention used by the action's maintainers.

**Consequences:**

- Positive: Single source of truth for Python versions (`.python-version` per service), fixes 3.11 vs 3.12 mismatch, removes redundant action, simpler YAML (~18 lines removed)
- Negative: First CI run after migration has no Python cache (~15s download), uv becomes the sole Python provider in CI (acceptable given it already manages venvs and dependencies)

### ADR-019: Native ARM Runner Multi-Arch Container Pipeline (INFRA-030)

**Date:** 2026-02-22
**Status:** Accepted

**Context:** The release pipeline (`release.yml`) uses a static podman binary (`mgoltzsche/podman-static`) for container builds, which fails on GitHub Actions runners with `failed to reexec: Permission denied`. The existing approach also uses QEMU emulation for cross-platform builds (amd64 + arm64), which is slow. GitHub now provides free native ARM64 runners (`ubuntu-24.04-arm64`) for public repositories, enabling native compilation on both architectures.

**Decision:** Split the container pipeline across `ci.yml` (build + test) and `release.yml` (merge manifests + publish + release). Use a matrix strategy of 4 images x 2 platforms (8 parallel jobs) on native runners. CI pushes arch-specific images to ghcr.io on main branch pushes only (PRs verify build but don't push). Release workflow pulls tested arch-specific images and creates OCI manifest lists.

**Key Technical Decisions:**

1. **Job architecture:** `container-build` (8 matrix, ci.yml) -> `container-test` (8 matrix, ci.yml) -> `container-merge` (1 job, release.yml) -> `release` (1 job, release.yml)
2. **Push policy:** Build-only on PRs. Push arch-specific images to ghcr.io only on main branch pushes.
3. **Paths filter:** New `containers` filter triggers on Dockerfiles, service source, deployment configs, proto files.
4. **Registry auth:** `redhat-actions/podman-login@v1` for native podman credential handling.
5. **Smoke tests:** Per-arch health check, port verification, non-root user check, OCI annotation verification.
6. **publish-ci.sh:** Subcommand design (`push-arch`, `merge`, `tag-family`) for composability and local testability.
7. **release.yml jobs:** `validate` -> `merge-manifests` -> `publish-tags` -> `create-release`. Separates concerns for partial re-runs.

**Arch-specific tag format:** Dot-separated: `<version>.<arch>` (e.g., `v0.1.0-alpha.1.amd64`). Version tag applied only to merged manifest list.

**Trivy SARIF categories:** Arch-qualified: `trivy-release-<image>-<arch>` for unique GitHub Code Scanning entries.

**Proto sync:** Conditional on `matrix.image`, only for `memvid-service` and `api-service`.

**Alternatives Considered:**

1. **Fix static podman binary (add rootless setup)** -- Fragile, non-standard for GitHub Actions, still requires QEMU for cross-arch. Does not solve the performance problem.
2. **Switch to Docker/Buildx** -- Pre-installed on runners and well-supported, but diverges from the project's podman-based toolchain. Would require maintaining two container runtimes (podman local, Docker CI).
3. **Single runner with QEMU + runner's native podman** -- Quick fix that unblocks the immediate failure but ARM builds remain ~10x slower than native. Acceptable as a temporary workaround but not a long-term solution.
4. **Push arch images from PRs** -- Enables testing PR container images but creates ghcr.io tag pollution with orphaned PR-specific tags. Storage cost and cleanup overhead not justified.

**Consequences:**

- Positive: Native ARM compilation (~10x faster than QEMU), containers tested as CI quality gate, clean separation between build (CI) and publish (release), no static binary hacks, composable publish script
- Negative: CI pushes arch-specific images to ghcr.io on every main push (storage cost, mitigated by retention policies), more complex YAML (~100 lines in ci.yml, release.yml refactored), `redhat-actions/podman-login@v1` adds a third-party action dependency

### ADR-020: Container Supply Chain Security via Sigstore (INFRA-031)

**Date:** 2026-02-23
**Status:** Accepted

**Context:** The INFRA-030 container pipeline uses tag-based handoff between CI and release workflows. Arch-specific images are referenced by mutable tags rather than immutable digests. No cryptographic signing, SBOM generation, or transparency logging exists. This leaves a supply chain integrity gap: there is no proof that released images are the exact bytes that passed CI security scanning. A comparable Jenkins pipeline (previously built for a different project) solved this with native arch nodes, build timestamps, per-arch cosign signing, SBOM attestation, digest-based manifest merging, and a verification gate before tag promotion.

**Decision:** Implement a Sigstore-based supply chain using cosign keyless signing (Fulcio OIDC + Rekor transparency log), syft SBOM generation, and OCI 1.1 referrers for attestation storage. The signing chain is:

1. CI builds and pushes arch images, capturing digests via `--digestfile`
2. CI generates CycloneDX SBOM against the pushed image by digest
3. CI attaches SBOM as OCI 1.1 referrer via `cosign attest --type cyclonedx`
4. CI signs the image by digest with `cosign sign` (keyless, Fulcio cert + Rekor inclusion proof)
5. CI uploads digest JSON artifact per matrix cell
6. Release downloads digests and creates manifest lists using `podman manifest add <image>@<digest>`
7. Release signs each manifest list with `cosign sign`
8. `verify-signatures` job gates tag promotion: `cosign verify` with workflow-scoped identity
9. Only after verification: semver tag family applied via `skopeo copy --all`

**Key Technical Decisions:**

1. **Cosign keyless (Sigstore Fulcio + Rekor)** -- No manual key management. GitHub Actions OIDC token as identity claim. Signatures countersigned by Rekor transparency log with trusted timestamp. Certificate expiry (10 min) does not affect verification because Rekor entry is immutable.
2. **Workflow-scoped identity** -- `--certificate-identity` matching exact workflow path + ref (e.g., `ci.yml@refs/heads/main`). Tighter than repo-scoped: only the designated CI/release workflows can produce valid signatures.
3. **Digest-based handoff** -- `podman push --digestfile` captures exact digest at push time. Stored as JSON artifact per matrix cell. Release uses `podman manifest add <image>@<digest>` instead of tag refs. Eliminates TOCTOU window.
4. **SBOM: CycloneDX JSON against pushed digest** -- `syft <registry>/<image>@<digest>` ensures SBOM describes exactly what is in registry (not the local build cache). CycloneDX chosen over SPDX for broader container ecosystem tooling support.
5. **Dual SBOM storage** -- Actions artifact (for CI/audit access) + OCI 1.1 referrer via `cosign attest` (travels with image, discoverable by scanners).
6. **Step ordering (Sigstore convention)** -- After push: (1) SBOM generation, (2) SBOM attestation, (3) image signing. Attestation before signing follows the Sigstore reference workflow.
7. **`COSIGN_YES: "true"` env var** -- Single declaration at job level instead of `--yes` per invocation.
8. **Tool installation via GitHub Actions** -- `sigstore/cosign-installer@v3` (v2.4.0+ for OCI 1.1), `anchore/sbom-action/download-syft@v0`. Pinned actions, not ad-hoc curl downloads.
9. **Build timestamp dev tags** -- `dev-<sha>-B<YYYYMMDDHHMMSS>` guarantees uniqueness across re-runs. Version tags unaffected.
10. **Always-blocking failures** -- cosign sign, cosign attest, and syft all fail the CI job if they error. The verify-signatures gate in release is the final check, not a compensating control.
11. **Verify checks both identities** -- `publish-ci.sh verify` tries ci.yml identity then release.yml identity. Covers arch images (signed by CI) and manifest lists (signed by release) without requiring a flag.

**Alternatives Considered:**

1. **Manual key management (cosign generate-key-pair)** -- More control but requires secret key storage, rotation, and distribution. Keyless via Fulcio is zero-management for GitHub Actions.
2. **Notation (CNCF)** -- Alternative signing tool. Less mature GitHub Actions integration, smaller ecosystem. Cosign + Sigstore has wider adoption and first-class OIDC support.
3. **SPDX-JSON SBOMs** -- ISO standard (ISO/IEC 5962:2021). CycloneDX chosen for broader tooling support in container/DevSecOps ecosystems.
4. **SBOM from local image (pre-push)** -- Faster (no network pull). Rejected because the SBOM would describe the local build cache, not necessarily what was pushed to registry. Digest-referenced SBOM is provably accurate.
5. **Repository-scoped cosign identity** -- Simpler, survives workflow renames. Rejected in favor of workflow-scoped for tighter security: only the designated workflow can sign.
6. **Non-blocking signing on dev pushes** -- Would allow dev iteration if Sigstore has outages. Rejected for simplicity: one policy (always block) is easier to reason about. Sigstore has high availability (Fulcio + Rekor are production Google services).

**Consequences:**

- Positive: Cryptographic proof of image provenance via Sigstore, digest-pinned releases eliminate TOCTOU, SBOM for compliance (EO 14028, NIST SSDF), OCI 1.1 referrers for scanner discoverability, Rekor transparency log prevents backdating, verification gate prevents unsigned tag promotion, build timestamps prevent dev tag collisions
- Negative: Adds ~30-45s per matrix cell (syft + cosign attest + cosign sign), requires `id-token: write` permission (OIDC), artifact upload/download between workflows adds complexity, external dependency on Sigstore infrastructure (Fulcio, Rekor), workflow rename requires updating verification commands

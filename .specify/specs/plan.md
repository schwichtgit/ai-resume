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

| Component          | Platform                                    | Rationale                                                           |
| ------------------ | ------------------------------------------- | ------------------------------------------------------------------- |
| Production Host    | nanopi-r6s (RK3588 ARM64, 4GB RAM, OpenWrt) | Low-power edge server; 180MB total runtime, 3.8GB headroom          |
| Container Runtime  | Podman (rootless) + podman compose          | Daemonless, rootless by default; no Docker dependency               |
| Network            | `yellow-net` (192.168.100.0/24, external)   | Zone-isolated subnet with static IPs; firewall blocks cross-zone    |
| Frontend Container | alpine + OpenResty (nginx + Lua)            | 35MB image; Lua SEO handler; Pattern B internal routing             |
| API Container      | python:3.12-slim-bookworm                   | 500MB image, 150-200MB runtime; FastAPI + gRPC client               |
| Memvid Container   | debian:trixie-slim (runtime)                | 15MB image, 20MB runtime; gRPC on :50051, metrics on :9090          |
| Host Load Balancer | nginx on host (outside Podman)              | TLS termination; domain routing; SSE proxy support                  |
| Container Security | read_only, no-new-privileges, non-root      | All containers unprivileged; volumes mounted ro where possible      |
| Data Volume        | `/opt/ai-resume/data` mounted ro            | .mv2 file + profile config; stateless containers                    |
| Development        | Local multi-terminal (3 terminals)          | Cargo run, uvicorn --reload, npm run dev                            |
| CI/CD              | GitHub Actions (`.github/workflows/ci.yml`) | Monorepo path filtering; conditional jobs per service; summary gate |
| Build Pipeline     | `scripts/build-all.sh`                      | Multi-arch (amd64 + arm64); scp transfer; podman compose deploy     |
| Static Analysis    | SonarQube + CodeQL                          | Runs on push to main and PRs                                        |

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

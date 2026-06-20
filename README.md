![AI Resume Screenshot](frontend/public/ai-resume.png)

# AI Resume Agent

**Turn a static resume into an AI-powered conversation.**

TypeScript (React 19) | Python 3.12 (FastAPI) | Rust (memvid gRPC)

AI-Resume is a containerized web application that acts as your digital professional proxy. It provides a "30-second scan" layout for speed, backed by a semantic AI agent that recruiters can "interview" in real-time. Using natural language, they can query specific experience (e.g., "How has she handled MLOps at scale?") and receive a synthesized, evidence-based summary derived from your personal semantic knowledge base.

<https://github.com/user-attachments/assets/0b183e42-db28-4ac0-ad22-8cd66d68308c>

> _A recruiter asks about AI experience, tests job fit with a real job description, and explores leadership style -- all without scheduling a call._

## Live Demo

Try it with a fictional candidate: **[jane-doe-ai-resume.schwichtenberg.us](https://jane-doe-ai-resume.schwichtenberg.us/)**

Suggested things to try:

- Ask about specific skills or experience
- Paste a real job description into the Fit Assessment tab
- Ask a question the resume can't answer (watch the honest response)

## Who Is This For?

| You are a...                   | What you get                                                                                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Resume Owner**               | Deploy your resume as an always-available AI agent. Visitors get thoughtful answers about your experience without you being in the room.                                       |
| **Recruiter / Hiring Manager** | Instant, detailed answers about a candidate. Ask about specific skills, experience depth, or job fit. No more scanning PDFs or scheduling screening calls.                     |
| **Engineer / Architect**       | A reference implementation of a production RAG system: Rust gRPC service, Python FastAPI, React frontend, semantic search with cross-encoder re-ranking, container deployment. |

## Architecture Overview

```text
master_resume.md        Python ingest         .mv2 file          Rust gRPC        Python API       React SPA
(your resume)     --->  (chunk + embed)  ---> (vector DB)   ---> (search)    --->  (LLM + SSE) ---> (chat UI)
                                                                  <5ms              streaming        responsive
```

All content comes from a single Markdown file with YAML frontmatter. No hardcoded data in the frontend -- everything flows through the API from the `.mv2` vector database.

Four services behind a reverse proxy:

| Service            | Stack                                                | Role                                                    |
| ------------------ | ---------------------------------------------------- | ------------------------------------------------------- |
| **frontend**       | React 19, TypeScript, Vite 8, Tailwind v4, shadcn/ui | Chat UI, experience cards, fit assessment               |
| **api-service**    | Python, FastAPI, OpenRouter                          | LLM orchestration, fit assessment, SSE streaming        |
| **memvid-service** | Rust, Tonic gRPC, memvid-core                        | Semantic search, state lookup, Ask mode with re-ranking |
| **ingest**         | Python, memvid-sdk                                   | One-shot pipeline: parse resume markdown into .mv2      |

Key technical decisions:

- **Hybrid search**: BM25 lexical + vector semantic + cross-encoder re-ranking (Reciprocal Rank Fusion)
- **Honest by design**: System prompts enforce factual grounding; guardrails block prompt injection
- **Single-file portability**: One `.mv2` file contains all embeddings, metadata, and profile data
- **Read-only containers**: All services run rootless with read-only filesystems

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design, data flow, and network topology. The system includes end-to-end distributed tracing with OpenTelemetry across all three languages, a Grafana/Tempo/Prometheus/Loki observability stack, and pre-built dashboards for request waterfalls, latency breakdowns, and LLM cost tracking -- see [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md).

## What It Does

**AI Chat** -- Ask anything about the candidate's background. The agent retrieves relevant resume context via hybrid search (BM25 + vector embeddings + cross-encoder re-ranking) and generates grounded, citation-backed answers. It will not hallucinate or make things up. Users can rate responses with thumbs up/down feedback.

**Fit Assessment** -- Paste a real job description and get an honest analysis: key matches, gaps, and a recommendation. Pre-analyzed examples show strong and weak fit scenarios so you know what calibrated output looks like.

**Experience Cards** -- Structured view of roles, projects, and skills loaded dynamically from a single portable data file.

**MCP Server** -- Exposes the resume agent as an MCP-compatible tool server. Connect from Claude Desktop, Cursor, or any MCP client to query the candidate's experience programmatically.

## Prerequisites

| Tool    | Minimum | Required For                         |
| ------- | ------- | ------------------------------------ |
| Node.js | 26.2.0  | Frontend build and dev server        |
| npm     | 11.0.0  | Frontend deps (bundled with Node.js) |
| uv      | 0.9.0   | Python package management            |
| go-task | 3.48.0  | Build orchestration (`task` CLI)     |
| Rust    | 1.96.0  | memvid-service only                  |
| podman  | 5.8.0   | Container builds and deployment only |

Python is not a global prerequisite. `uv` manages per-service virtual environments and pins the Python version in each service's `pyproject.toml`.

Verify all tools are installed and meet minimum versions:

```bash
task deps
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the full tiered prerequisite list.

## Quick Start

```bash
# 0. Bootstrap dev environment (npm deps, Python venvs, Rust crates, git hooks)
task setup

# 1. Create your resume
cp data/example_resume.md data/master_resume.md
# Edit with your information (see data/example_resume.md for the schema)

# 2. Ingest into vector database
cd ingest && uv run python ingest.py --verify

# 3. Run the full stack (three terminals)
task dev:memvid      # Terminal 1 -- Rust gRPC service (port 50051)
task dev:api         # Terminal 2 -- Python FastAPI (port 3000)
task dev:frontend    # Terminal 3 -- Vite dev server (port 8080)
```

Print these dev instructions any time with `task dev`.

## Build System

The project uses [go-task](https://taskfile.dev) as the build orchestrator for the entire monorepo. A root `Taskfile.yml` includes per-service taskfiles. Run `task --list` for every available target.

Key commands:

```bash
task setup           # Bootstrap full dev environment
task deps            # Check tool dependencies
task lint            # Lint all services (ESLint, ruff, clippy, markdownlint)
task test            # Test all services
task audit           # Whole-SBOM vuln sweep (npm, pip-audit, cargo audit)
task build           # Build all services (production)
task check           # Full quality sweep: lint + typecheck + test + build
task ci              # Reproduce CI pipeline locally
task container:build # Build all container images
task clean           # Remove build artifacts
```

Per-service targets are namespaced: `task frontend:test`, `task api:lint`, `task memvid:build:release`, `task ingest:test:coverage`.

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the complete build system reference, per-service commands, testing, and coverage thresholds.

## API Endpoints

| Method | Path                                 | Description                                           |
| ------ | ------------------------------------ | ----------------------------------------------------- |
| GET    | `/health`                            | Health check (root-level alias)                       |
| GET    | `/api/v1/health`                     | Health check with dependency status                   |
| POST   | `/api/v1/chat`                       | AI chat with semantic search (supports SSE streaming) |
| GET    | `/api/v1/profile`                    | Profile metadata from memvid                          |
| GET    | `/api/v1/suggested-questions`        | Suggested chat questions from profile                 |
| POST   | `/api/v1/assess-fit`                 | Real-time job fit assessment via AI                   |
| POST   | `/api/v1/chat/{session_id}/feedback` | Submit thumbs up/down feedback on responses           |
| POST   | `/api/v1/session/{session_id}/clear` | Clear conversation history for a session              |
| DELETE | `/api/v1/sessions/{session_id}`      | Delete a chat session                                 |
| GET    | `/api/v1/version`                    | Build version and commit SHA                          |
| GET    | `/api/v1/mcp/config/{client_id}`     | MCP client configuration template                     |
| --     | `/mcp`                               | MCP Streamable HTTP server (opt-out via env)          |
| GET    | `/metrics`                           | Prometheus metrics (infrastructure)                   |

## Deployment

Configure secrets and deploy with containers:

```bash
# Configure
cp deployment/.env.example deployment/.env
# Set OPENROUTER_API_KEY in deployment/.env

# Build container images
task container:build

# Deploy
cd deployment && podman compose up -d
```

The stack runs on both amd64 and arm64, including ARM64 edge devices (Raspberry Pi 4/5, NanoPi) with 4GB+ RAM. Each service enforces a 200MB memory limit.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for multi-arch builds, ARM64 edge deployment, compose configuration, and troubleshooting.

## Project Structure

```text
ai-resume/
  frontend/           # React 19 + TypeScript + Vite + Tailwind + shadcn/ui
  api-service/        # Python 3.12 FastAPI -- LLM orchestration, SSE streaming
  memvid-service/     # Rust -- gRPC semantic search (<5ms retrieval)
  ingest/             # Python -- resume markdown -> .mv2 vector database
  deployment/         # Compose files, .env.example, deployment utilities
  data/               # Resume source files and .mv2 output
  proto/              # gRPC .proto definitions (shared)
  scripts/            # Build, hook install, and utility scripts
  ci/                 # CI gate principles (commit, PR, release)
  docs/               # Architecture, deployment, security, development guides
  Taskfile.yml        # Root build orchestrator (go-task)
```

## Documentation

| Document                                                         | Description                                  |
| ---------------------------------------------------------------- | -------------------------------------------- |
| [Architecture](docs/ARCHITECTURE.md)                             | System design, data flow, network topology   |
| [Deployment](docs/DEPLOYMENT.md)                                 | Container builds, ARM64 edge, compose config |
| [Development](docs/DEVELOPMENT.md)                               | Build system, per-service commands, testing  |
| [Observability](docs/OBSERVABILITY.md)                           | Distributed tracing, dashboards, runbooks    |
| [Security](docs/SECURITY.md)                                     | Threat model, prompt injection, hardening    |
| [Hook Exit Codes](docs/hook-exit-code-conventions.md)            | Claude Code hook exit code conventions       |
| [Post-Edit Hook Antipattern](docs/post-edit-hook-antipattern.md) | Hook design guidance                         |

## About This Project

A reference project by [Frank Schwichtenberg](https://github.com/schwichtgit) -- built to solve a real problem (making resumes interactive) while demonstrating production engineering practices across the stack:

- **Systems design**: Rust + Python hybrid architecture with gRPC boundaries
- **Search and retrieval**: Semantic search, BM25, cross-encoder re-ranking, metadata filtering
- **LLM engineering**: RAG pipeline, prompt design, guardrails, streaming responses
- **Infrastructure**: Multi-arch containers, rootless deployment, read-only filesystems
- **Security**: Prompt injection defense, rate limiting, input validation, container hardening

## License

PolyForm Noncommercial License 1.0.0 -- See [LICENSE](LICENSE) file.

# Development Guide

Development reference for the ai-resume polyglot monorepo. For architecture,
API endpoints, and content authoring, see [CLAUDE.md](../CLAUDE.md).

## Prerequisites

All dependencies are checked by `task deps`. Three tiers:

### Required (Tier 1 -- hard fail)

| Tool    | Minimum | Install                                            |
| ------- | ------- | -------------------------------------------------- |
| Node.js | 26.2.0  | <https://nodejs.org/>                              |
| npm     | 11.0.0  | Bundled with Node.js                               |
| uv      | 0.9.0   | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| go-task | 3.48.0  | <https://taskfile.dev/installation/>               |

[go-task](https://taskfile.dev) is the build orchestrator for the entire
monorepo. All build, lint, test, and deploy commands go through it.

Python is **not** a global prerequisite. `uv` manages per-service virtual
environments and pins the Python version in each service's `pyproject.toml`.

### Service-level (Tier 2 -- warn only)

| Tool   | Minimum | Notes                                |
| ------ | ------- | ------------------------------------ |
| rustc  | 1.93.0  | Required for memvid-service          |
| cargo  | 1.93.0  | Bundled with Rust                    |
| protoc | 32.1    | Required for gRPC proto regeneration |

### Optional (Tier 3 -- informational)

| Tool              | Purpose                         |
| ----------------- | ------------------------------- |
| podman            | Container builds and deployment |
| skopeo            | Container image publishing      |
| markdownlint-cli2 | Markdown linting                |
| shellcheck        | Shell script linting            |
| cargo-tarpaulin   | Rust code coverage              |

Verify everything at once:

```bash
task deps
```

## Quick Start

Bootstrap the full dev environment (installs npm deps, creates Python venvs,
fetches Rust crates, installs git hooks):

```bash
task setup
```

Run the full stack in three terminals:

```bash
# Terminal 1 -- memvid gRPC service (Rust, port 50051)
task dev:memvid

# Terminal 2 -- API service (Python/FastAPI, port 3000)
task dev:api

# Terminal 3 -- Frontend dev server (Vite, port 8080)
task dev:frontend
```

Or print these instructions any time with `task dev`.

## Build System (Taskfile)

The project uses [go-task](https://taskfile.dev) with a root `Taskfile.yml`
that includes per-service taskfiles. Run `task --list` to see every available
target.

### Key Aggregate Tasks

| Task                 | What it does                                        |
| -------------------- | --------------------------------------------------- |
| `task setup`         | Bootstrap all services + git hooks                  |
| `task lint`          | Lint all services + docs (ESLint, ruff, clippy, md) |
| `task lint:fix`      | Lint with auto-fix across all services              |
| `task test`          | Unit test all services                              |
| `task test:coverage` | Unit test all services with coverage reporting      |
| `task build`         | Build frontend (production) + memvid (release)      |
| `task check`         | Full quality sweep: lint, typecheck, test, build    |
| `task ci`            | Reproduce CI pipeline locally (check + coverage)    |
| `task clean`         | Remove build artifacts (preserves Python venvs)     |
| `task clean:all`     | Remove build artifacts AND Python venvs             |

### Per-Service Task Prefixes

Each service is namespaced under its include alias:

| Prefix      | Service        | Directory         |
| ----------- | -------------- | ----------------- |
| `frontend:` | Frontend       | `frontend/`       |
| `api:`      | API Service    | `api-service/`    |
| `memvid:`   | Memvid Service | `memvid-service/` |
| `ingest:`   | Ingest         | `ingest/`         |
| `deploy:`   | Deployment     | `deployment/`     |

Common per-service targets: `setup`, `lint`, `lint:fix`, `test`,
`test:coverage`, `dev`. Example: `task api:test:coverage`.

### Other Tasks

| Task                | What it does                                    |
| ------------------- | ----------------------------------------------- |
| `task proto`        | Regenerate gRPC Python stubs from `.proto` file |
| `task e2e`          | Cross-service integration tests (mock backends) |
| `task e2e:real`     | True E2E tests (real ingest + real memvid)      |
| `task docs:lint`    | Lint all Markdown files (markdownlint-cli2)     |
| `task release-gate` | Full release quality gate                       |

## Per-Service Development

### Frontend (`frontend/`)

TypeScript, React 19, Vite 8 (Rolldown), Tailwind CSS v4, shadcn/ui.

```bash
task frontend:dev             # Vite dev server on port 8080
task frontend:build           # Production build -> frontend/dist/
task frontend:lint            # ESLint
task frontend:typecheck       # tsc --noEmit
task frontend:test            # Vitest (single run)
task frontend:test:coverage   # Vitest with coverage
task frontend:test:watch      # Vitest in watch mode
```

Raw commands (from `frontend/` directory):

```bash
npm run dev
npm run build
npm run lint
npx tsc --noEmit
npm test -- --run
npm test -- --run --coverage
```

**E2E tests** (Playwright, requires all services running):

```bash
npx playwright install chromium  # first time only
E2E_BASE_URL=http://localhost:8080 npx playwright test
```

The E2E suite is data-driven (tests structure and behavior, not specific resume
content) and works against any deployed instance.

### API Service (`api-service/`)

Python 3.12, FastAPI, uvicorn. The Python package name is `ai_resume_api`
(not `app`).

```bash
task api:dev              # uvicorn with hot reload on port 3000
task api:lint             # ruff check + format check
task api:lint:fix         # ruff check --fix + format
task api:typecheck        # mypy
task api:test             # pytest
task api:test:coverage    # pytest with --cov=ai_resume_api
```

Raw commands (from `api-service/` directory):

```bash
source .venv/bin/activate
uv run uvicorn ai_resume_api.main:app --reload --port 3000
uv run ruff check .
uv run mypy .
uv run pytest -v --tb=short
uv run pytest -v --tb=short --cov=ai_resume_api --cov-report=term-missing
```

Each Python service has its own `.venv` managed by `uv`. Task commands handle
venv activation automatically via `uv run`.

### Memvid Service (`memvid-service/`)

Rust 1.93+, gRPC (tonic), port 50051.

```bash
task memvid:dev             # cargo run
task memvid:build           # cargo build (debug)
task memvid:build:release   # cargo build --release
task memvid:lint            # cargo clippy -- -D warnings
task memvid:fmt             # cargo fmt
task memvid:test            # cargo test
task memvid:test:coverage   # cargo tarpaulin (requires cargo-tarpaulin)
```

Raw commands (from `memvid-service/` directory):

```bash
cargo run
cargo build --release
cargo clippy -- -D warnings
cargo test
cargo tarpaulin --config tarpaulin-unit.toml
```

### Ingest (`ingest/`)

Python pipeline for parsing resume markdown into `.mv2` files.

```bash
task ingest:lint            # ruff check + format check
task ingest:lint:fix        # ruff check --fix + format
task ingest:typecheck       # mypy
task ingest:test            # pytest (excludes slow tests)
task ingest:test:coverage   # pytest with --cov=ingest --cov-fail-under=85
```

Raw commands (from `ingest/` directory):

```bash
source .venv/bin/activate
uv run pytest -v --tb=short -m "not slow"
uv run ruff check .
uv run mypy .
```

## Testing

Run all unit tests across the monorepo:

```bash
task test
```

With coverage reporting:

```bash
task test:coverage
```

Integration and end-to-end:

```bash
task e2e          # Cross-service integration (mock backends)
task e2e:real     # True E2E (real ingest + real memvid, mock LLM)
```

### Coverage Thresholds

Target: 85% line coverage per service.

| Service  | Threshold | Notes                                        |
| -------- | --------- | -------------------------------------------- |
| frontend | 10%       | Ramping up; target is 85% as tests are added |
| api      | 85%       |                                              |
| ingest   | 85%       | Enforced via `--cov-fail-under=85`           |
| memvid   | 85%       | Requires `cargo-tarpaulin`                   |

### Test Frameworks

| Service  | Framework                      |
| -------- | ------------------------------ |
| frontend | Vitest + React Testing Library |
| api      | pytest                         |
| ingest   | pytest                         |
| memvid   | cargo test                     |

## Code Quality

### Linters by Language

| Language   | Tool              | Command              |
| ---------- | ----------------- | -------------------- |
| TypeScript | ESLint            | `task frontend:lint` |
| Python     | ruff              | `task api:lint`      |
| Rust       | clippy            | `task memvid:lint`   |
| Markdown   | markdownlint-cli2 | `task docs:lint`     |

### Aggregate Commands

```bash
task lint        # Lint everything (all services + docs)
task lint:fix    # Lint with auto-fix where possible
task check       # lint + typecheck + test + build
task ci          # Full CI reproduction: lint + typecheck + coverage + build + docs
```

### Type Checking

```bash
task frontend:typecheck   # tsc --noEmit
task api:typecheck        # mypy
task ingest:typecheck     # mypy
```

## Container Development

Container tooling uses **podman** (not docker). Compose commands use
`podman compose` (the compose plugin, not the standalone `podman-compose`).

### Build

```bash
task container:build      # Build all service images (frontend, api, memvid)
```

This runs `scripts/build-all.sh` which builds each Dockerfile:

- `frontend/Dockerfile` -- alpine + OpenResty, port 8080
- `api-service/Dockerfile` -- python:3.12-slim, port 3000
- `memvid-service/Dockerfile` -- debian:trixie-slim, port 50051

### Deploy Locally

```bash
task deploy:compose:up      # podman compose up -d
task deploy:compose:down    # podman compose down
task deploy:compose:logs    # podman compose logs -f
```

### Other Container Tasks

```bash
task container:test         # Container smoke tests
task container:export       # Export images as tar files
task container:publish      # Publish to remote registry (requires skopeo)
```

## Git Workflow

### Commit Format

[Conventional Commits](https://www.conventionalcommits.org/):

```text
type(scope): description
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
`ci`, `chore`, `revert`.

Subject line: 72 characters max, imperative mood, no emoji.

### Git Hooks

Project hooks live in `.githooks/` (tracked in git). Install them:

```bash
task setup:hooks
# or directly:
./scripts/install-hooks.sh
```

This sets `git config core.hooksPath .githooks`. Hooks include:

- `pre-commit` -- runs ESLint on staged frontend files
- `commit-msg` -- validates Conventional Commits format

Skip temporarily with `git commit --no-verify`. Uninstall with
`git config --unset core.hooksPath`.

### Branch Strategy

- Work on feature branches
- Push individual, atomic commits (no squashing before push)
- Squash happens at PR merge time (configured in GitHub)

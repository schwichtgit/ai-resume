# Feature Plan: Taskfile Build Orchestration

## Metadata

| Field        | Value                |
| ------------ | -------------------- |
| Plan Version | 1.0.0                |
| Created      | 2026-02-20           |
| Status       | Draft                |
| Depends On   | plan.md v1.0.0       |
| Branch       | feat/taskfile-build  |

---

## Motivation

The ai-resume monorepo has 22 shell scripts in `scripts/` that handle building, testing,
deploying, protobuf generation, quality verification, and release gating. These scripts:

1. **Duplicate boilerplate** -- 8 scripts independently implement `wait_for_health`,
   `curl_with_429_retry`, `wait_for_port`, color output helpers, and cleanup traps.
2. **Lack change detection** -- `build-all.sh` rebuilds all 4 container images unconditionally,
   even if only one service changed. `verify-quality.sh` re-checks every service on every run.
3. **Have implicit ordering** -- `release-gate.sh` hard-codes a 6-phase pipeline
   (`build` -> `export` -> `ingest` -> `smoke` -> `pytest` -> `e2e`), but the dependencies
   between phases are implicit in the script flow, not declared.
4. **Are not discoverable** -- New contributors must read each script to understand what
   commands are available. There is no `--help` or task listing equivalent.
5. **Are platform-fragile** -- Several scripts use GNU-specific `stat`, `numfmt`, `sed` flags
   that behave differently on macOS (BSD) vs Linux (GNU).

Taskfile (go-task) solves these problems with:

- **YAML-based task declarations** with `desc:` fields for discoverability (`task --list`)
- **`sources`/`generates` change detection** via content checksums, skipping up-to-date tasks
- **Declared `deps:`** for parallel dependency execution
- **`includes:`** for monorepo service-scoped Taskfiles with namespacing
- **Cross-platform** behavior without GNU vs BSD workarounds
- **Single binary** (`brew install go-task`, no runtime dependencies)

---

## Scope

### In Scope

- Root `Taskfile.yml` with monorepo orchestration
- Per-service `Taskfile.yml` in `frontend/`, `api-service/`, `memvid-service/`, `ingest/`
- Change detection via `sources`/`generates` for build, lint, test targets
- Container build orchestration with service-level granularity
- CI workflow integration (replace inline commands with `task` calls)
- Release gate pipeline as dependent task chain
- Developer ergonomics: `task setup`, `task dev`, `task test`, `task build`

### Deferred (Out of Scope)

- Remote Taskfiles or shared task libraries
- Replacing the E2E test scripts entirely (they contain complex test logic; Taskfile wraps them)
- Replacing `deployment/compose.yaml` (Taskfile orchestrates compose, does not replace it)
- Windows support (project targets Linux/macOS only per constitution)
- Taskfile-based CI caching (GitHub Actions cache continues to use its native mechanism)

---

## Proposed Task Hierarchy

### Root Taskfile (`Taskfile.yml`)

```text
task                          # default: list all tasks
task setup                    # One-time dev environment bootstrap
task dev                      # Start all services for local dev
task build                    # Build all containers (with change detection)
task test                     # Run all unit tests
task lint                     # Run all linters
task quality                  # lint + typecheck + test (replaces verify-quality.sh)
task proto                    # Regenerate gRPC stubs from proto/
task hooks                    # Install git hooks
task e2e                      # Cross-service integration tests
task e2e:real                 # True E2E (real ingest, real search, mock LLM)
task release-gate             # Full release quality gate pipeline
task deploy                   # Build, export, transfer, deploy to edge
task clean                    # Remove build artifacts and .task/ cache
```

### Frontend Taskfile (`frontend/Taskfile.yml`)

```text
task frontend:install         # npm ci
task frontend:dev             # npm run dev
task frontend:build           # npm run build (with sources/generates)
task frontend:lint            # npm run lint
task frontend:typecheck       # npx tsc --noEmit
task frontend:test            # npm test -- --run
task frontend:test:watch      # npm run test:watch
task frontend:test:coverage   # npm test -- --run --coverage
task frontend:format          # npx prettier --write
task frontend:format:check    # npx prettier --check
task frontend:container       # podman build frontend container
```

### API Service Taskfile (`api-service/Taskfile.yml`)

```text
task api:install              # uv sync --extra test --extra lint
task api:dev                  # uvicorn with --reload
task api:lint                 # ruff check + ruff format --check
task api:lint:fix             # ruff check --fix + ruff format
task api:typecheck            # mypy .
task api:test                 # pytest -v --tb=short
task api:test:coverage        # pytest --cov --cov-fail-under=85
task api:test:e2e             # pytest tests/test_e2e_api.py
task api:test:outcome         # pytest outcome tests (factual, honesty, security, etc.)
task api:container            # podman build api container
```

### Memvid Service Taskfile (`memvid-service/Taskfile.yml`)

```text
task memvid:build             # cargo build --release (with sources/generates)
task memvid:build:debug       # cargo build
task memvid:dev               # cargo run --release
task memvid:lint              # cargo clippy -- -D warnings
task memvid:format            # cargo fmt
task memvid:format:check      # cargo fmt --check
task memvid:test              # cargo test
task memvid:test:coverage     # cargo tarpaulin --fail-under 85
task memvid:container         # podman build memvid container
```

### Ingest Taskfile (`ingest/Taskfile.yml`)

```text
task ingest:install           # uv sync --extra test --extra lint
task ingest:run               # python ingest.py --input ... --output ...
task ingest:lint              # ruff check + ruff format --check
task ingest:lint:fix          # ruff check --fix + ruff format
task ingest:typecheck         # mypy .
task ingest:test              # pytest -v --tb=short -m "not slow"
task ingest:test:coverage     # pytest --cov-fail-under=85
task ingest:test:slow         # pytest -v -m slow (includes embedding tests)
task ingest:container         # podman build ingest container
```

### Aggregate Tasks (Root)

```text
task containers               # Build all 4 containers (deps: frontend:container, api:container, ...)
task containers:export        # Save containers as OCI tarballs (replaces export-containers.sh)
task containers:publish       # Push to remote registry (replaces publish-containers.sh)
task containers:smoke         # Quick smoke test (replaces test-containers.sh)
```

---

## Change Detection Strategy

### Frontend

```yaml
# frontend/Taskfile.yml
tasks:
  build:
    desc: Production build
    deps: [install]
    cmds:
      - npm run build
    sources:
      - src/**/*.{ts,tsx,css}
      - index.html
      - vite.config.ts
      - tailwind.config.ts
      - tsconfig.json
      - tsconfig.app.json
      - package.json
      - package-lock.json
    generates:
      - dist/**/*

  lint:
    desc: Run ESLint
    cmds:
      - npm run lint
    sources:
      - src/**/*.{ts,tsx}
      - eslint.config.js

  test:
    desc: Run tests
    cmds:
      - npm test -- --run
    sources:
      - src/**/*.{ts,tsx}
      - src/test/setup.ts
      - vitest.config.ts

  container:
    desc: Build frontend container image
    deps: [build]
    cmds:
      - podman build ...
    sources:
      - dist/**/*
      - Dockerfile
      - nginx.conf
      - nginx-default.conf
```

### API Service

```yaml
# api-service/Taskfile.yml
tasks:
  test:
    desc: Run pytest
    cmds:
      - uv run pytest -v --tb=short
    sources:
      - ai_resume_api/**/*.py
      - tests/**/*.py
      - pyproject.toml

  lint:
    desc: Lint with ruff
    cmds:
      - uv run ruff check .
      - uv run ruff format --check .
    sources:
      - ai_resume_api/**/*.py
      - tests/**/*.py
      - pyproject.toml

  container:
    desc: Build API container image
    cmds:
      - podman build ...
    sources:
      - ai_resume_api/**/*.py
      - Dockerfile
      - pyproject.toml
      - uv.lock
```

### Memvid Service

```yaml
# memvid-service/Taskfile.yml
tasks:
  build:
    desc: Build release binary
    cmds:
      - cargo build --release
    sources:
      - src/**/*.rs
      - build.rs
      - Cargo.toml
      - Cargo.lock
    generates:
      - target/release/memvid-service

  container:
    desc: Build memvid container image
    deps: [build]
    cmds:
      - podman build ...
    sources:
      - Dockerfile
      - target/release/memvid-service
```

### Proto Generation

```yaml
# Root Taskfile.yml
tasks:
  proto:
    desc: Regenerate gRPC stubs from proto definitions
    cmds:
      - ./scripts/gen-proto.sh
    sources:
      - proto/memvid/v1/memvid.proto
    generates:
      - api-service/ai_resume_api/proto/memvid/v1/memvid_pb2.py
      - api-service/ai_resume_api/proto/memvid/v1/memvid_pb2_grpc.py
```

### Method

Use `checksum` (the default) for all tasks. Checksums are more reliable than timestamps
across git operations (clone, checkout, rebase all reset timestamps). The `.task/` directory
storing checksums will be added to `.gitignore`.

---

## Migration Plan

### Scripts That Become Taskfile Tasks (Replace)

| Script | Replacement Task | Notes |
| --- | --- | --- |
| `scripts/build-all.sh` | `task containers` | Per-service change detection via `sources` |
| `scripts/export-containers.sh` | `task containers:export` | Rewrite as Taskfile commands |
| `scripts/verify-quality.sh` | `task quality` | Aggregate `lint` + `typecheck` + `test` per svc |
| `scripts/install-hooks.sh` | `task hooks` | Simple enough to inline |
| `scripts/gen-proto.sh` | `task proto` | Add `sources`/`generates` for change detection |
| `scripts/dev-setup.sh` | `task setup` | Prerequisites check + install per service |

### Scripts That Become Taskfile Wrappers (Keep Script, Task Calls It)

| Script                            | Wrapper Task              | Rationale                                   |
| --------------------------------- | ------------------------- | ------------------------------------------- |
| `scripts/test-containers.sh`      | `task containers:smoke`   | Complex test logic; Taskfile adds deps      |
| `scripts/test-e2e-integration.sh` | `task e2e`                | Complex multi-service orchestration         |
| `scripts/test-e2e-real.sh`        | `task e2e:real`           | Complex 4-phase test with service lifecycle |
| `scripts/test-e2e-mock-gates.sh`  | `task e2e:mock-gates`     | Complex test permutations                   |
| `scripts/release-gate.sh`         | `task release-gate`       | Taskfile declares phase deps; script runs   |
| `scripts/deploy.sh`               | `task deploy`             | SSH/SCP operations best in shell            |
| `scripts/publish-containers.sh`   | `task containers:publish` | skopeo commands best in shell               |

### Scripts That Remain Unchanged (No Task Wrapper Needed)

| Script | Reason |
| --- | --- |
| `scripts/profile-latency.sh` | Ad-hoc profiling tool, not a build target |
| `scripts/load-test.py` | Ad-hoc load testing tool |
| `scripts/release-gate-matrix.sh` | Companion to release-gate.sh |
| `scripts/test-outcome-portability.sh` | Called by CI directly |
| `scripts/test-outcome-containers.sh` | Called by CI directly |
| `scripts/verify-docs.sh` | Called by CI directly |

### Migration Order

1. **Phase 1**: Root Taskfile + per-service Taskfiles with `install`, `lint`, `test`, `build`
2. **Phase 2**: Add `sources`/`generates` change detection to all tasks
3. **Phase 3**: Container build tasks (`container`, `containers`, `containers:export`)
4. **Phase 4**: E2E and integration test wrappers
5. **Phase 5**: CI workflow migration (replace inline commands with `task` calls)
6. **Phase 6**: Release gate pipeline as task dependency chain
7. **Phase 7**: Remove replaced scripts, update CLAUDE.md and documentation

---

## CI Integration

### Current CI Structure

The CI workflow (`.github/workflows/ci.yml`) uses `dorny/paths-filter` for monorepo change
detection and conditional job execution. Each job inlines its own commands.

### Proposed CI Structure

Install `task` in CI via the official GitHub Action, then call task targets:

```yaml
# Example: frontend job
frontend:
  needs: changes
  if: ${{ needs.changes.outputs.frontend == 'true' }}
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '22'
        cache: npm
        cache-dependency-path: frontend/package-lock.json
    - uses: arduino/setup-task@v2
      with:
        version: '3.x'
    - run: task frontend:install
    - run: task frontend:lint
    - run: task frontend:typecheck
    - run: task frontend:test:coverage
    - run: task frontend:build
```

### What CI Continues to Own

- **Path-based change detection** (`dorny/paths-filter`) -- Taskfile's `sources/generates` is
  for local incremental builds, not CI job gating. CI still needs paths-filter to skip entire
  jobs when a service has no changes.
- **Caching** (node_modules, cargo, uv, HuggingFace) -- GitHub Actions cache is more
  effective than Taskfile's checksum-based skip for CI cold starts.
- **Matrix strategies** -- The security.yml Trivy scan uses a matrix; this stays in CI.
- **Summary job** -- Aggregation logic stays in CI YAML.

### What Migrates to Taskfile

- **Inline command sequences** in each job step (lint, typecheck, test, build)
- **Working directory management** (`defaults.run.working-directory` replaced by Taskfile `dir:`)
- **Quality gate checks** (coverage thresholds, lint zero-error enforcement)

---

## Feature List Entries

The following features should be added to `feature_list.json` when implementation begins.
IDs use the existing kebab-case naming convention matching the other 124 features.

```json
{
  "id": "taskfile-root",
  "category": "build",
  "title": "Root Taskfile with Monorepo Task Orchestration",
  "description": "Root Taskfile.yml providing aggregate tasks (setup, dev, build, test, lint, quality, clean) that delegate to per-service Taskfiles via includes. Supports task --list for discoverability.",
  "testing_steps": [
    "Run 'task --list' from the repo root and verify it lists at least 15 tasks across all services",
    "Run 'task --version' and verify go-task is installed",
    "Run 'cat Taskfile.yml' and verify it declares 'version: 3' and 'includes:' for frontend, api-service, memvid-service, and ingest",
    "Run 'task quality --dry' and verify it would invoke lint, typecheck, and test for all services"
  ],
  "passes": false,
  "verified": false,
  "dependencies": []
}
```

```json
{
  "id": "taskfile-frontend",
  "category": "build",
  "title": "Frontend Taskfile with Change Detection",
  "description": "frontend/Taskfile.yml providing install, dev, build, lint, typecheck, test, format, and container tasks with sources/generates change detection for build and test targets.",
  "testing_steps": [
    "Run 'task frontend:build' twice in succession; verify second run prints 'Task \"frontend:build\" is up to date'",
    "Modify frontend/src/App.tsx and run 'task frontend:build' again; verify it rebuilds",
    "Run 'task frontend:lint' and verify ESLint executes against frontend/src",
    "Run 'task frontend:test' and verify Vitest runs",
    "Run 'task frontend:container' and verify podman builds the frontend image"
  ],
  "passes": false,
  "verified": false,
  "dependencies": ["taskfile-root"]
}
```

```json
{
  "id": "taskfile-api-service",
  "category": "build",
  "title": "API Service Taskfile with Change Detection",
  "description": "api-service/Taskfile.yml providing install, dev, lint, typecheck, test, and container tasks with sources/generates change detection. Activates the correct Python venv.",
  "testing_steps": [
    "Run 'task api:test' and verify pytest runs against api-service tests",
    "Run 'task api:lint' and verify ruff check and ruff format --check execute",
    "Run 'task api:typecheck' and verify mypy runs",
    "Run 'task api:test' twice without changes; verify second run prints up to date",
    "Run 'task api:container' and verify podman builds the API image"
  ],
  "passes": false,
  "verified": false,
  "dependencies": ["taskfile-root"]
}
```

```json
{
  "id": "taskfile-memvid-service",
  "category": "build",
  "title": "Memvid Service Taskfile with Change Detection",
  "description": "memvid-service/Taskfile.yml providing build, dev, lint, format, test, and container tasks with sources/generates for the Rust binary. Change detection skips cargo build when sources unchanged.",
  "testing_steps": [
    "Run 'task memvid:build' and verify cargo build --release completes",
    "Run 'task memvid:build' again without changes; verify it prints up to date",
    "Run 'task memvid:lint' and verify clippy runs with -D warnings",
    "Run 'task memvid:test' and verify cargo test runs",
    "Run 'task memvid:container' and verify podman builds the memvid image"
  ],
  "passes": false,
  "verified": false,
  "dependencies": ["taskfile-root"]
}
```

```json
{
  "id": "taskfile-ingest",
  "category": "build",
  "title": "Ingest Taskfile with Change Detection",
  "description": "ingest/Taskfile.yml providing install, run, lint, typecheck, test, and container tasks with sources/generates change detection for Python test results.",
  "testing_steps": [
    "Run 'task ingest:test' and verify pytest runs ingest tests",
    "Run 'task ingest:lint' and verify ruff check and ruff format --check execute",
    "Run 'task ingest:typecheck' and verify mypy runs",
    "Run 'task ingest:container' and verify podman builds the ingest image"
  ],
  "passes": false,
  "verified": false,
  "dependencies": ["taskfile-root"]
}
```

```json
{
  "id": "taskfile-proto-generation",
  "category": "build",
  "title": "Proto Stub Generation with Change Detection",
  "description": "Root-level proto task that regenerates Python gRPC stubs from proto/memvid/v1/memvid.proto only when the .proto file changes. Uses sources/generates to skip when stubs are current.",
  "testing_steps": [
    "Run 'task proto' and verify Python stubs are generated in api-service/ai_resume_api/proto/",
    "Run 'task proto' again without changing the .proto file; verify it prints up to date",
    "Modify proto/memvid/v1/memvid.proto (add a comment) and run 'task proto'; verify stubs regenerate"
  ],
  "passes": false,
  "verified": false,
  "dependencies": ["taskfile-root"]
}
```

```json
{
  "id": "taskfile-container-orchestration",
  "category": "build",
  "title": "Container Build Orchestration via Taskfile",
  "description": "Root-level container tasks (containers, containers:export, containers:publish, containers:smoke) that orchestrate multi-service container builds with per-service change detection. Replaces scripts/build-all.sh and scripts/export-containers.sh.",
  "testing_steps": [
    "Run 'task containers' and verify all 4 container images are built",
    "Run 'task containers' again without source changes; verify skipped services print up to date",
    "Run 'task containers:export' and verify OCI tar files are created in deployment/",
    "Run 'task containers:smoke' and verify the container smoke test suite passes"
  ],
  "passes": false,
  "verified": false,
  "dependencies": [
    "taskfile-frontend",
    "taskfile-api-service",
    "taskfile-memvid-service",
    "taskfile-ingest"
  ]
}
```

```json
{
  "id": "taskfile-quality-gate",
  "category": "build",
  "title": "Unified Quality Gate via Taskfile",
  "description": "Root-level quality task that runs lint, typecheck, and test for all 4 services in parallel via Taskfile deps. Replaces scripts/verify-quality.sh with declarative dependency graph.",
  "testing_steps": [
    "Run 'task quality' and verify it runs lint, typecheck, and test for frontend, api-service, memvid-service, and ingest",
    "Introduce a lint error in one service and run 'task quality'; verify it reports the failure",
    "Run 'task quality' with all services clean; verify all checks pass"
  ],
  "passes": false,
  "verified": false,
  "dependencies": [
    "taskfile-frontend",
    "taskfile-api-service",
    "taskfile-memvid-service",
    "taskfile-ingest"
  ]
}
```

```json
{
  "id": "taskfile-ci-integration",
  "category": "build",
  "title": "CI Workflow Integration with Taskfile",
  "description": "Update .github/workflows/ci.yml to install go-task and invoke task targets instead of inline commands. Preserves dorny/paths-filter for job gating and GitHub Actions caching.",
  "testing_steps": [
    "Verify .github/workflows/ci.yml installs go-task via arduino/setup-task action",
    "Verify frontend CI job uses 'task frontend:lint', 'task frontend:typecheck', 'task frontend:test:coverage', 'task frontend:build'",
    "Verify api-service CI job uses 'task api:lint', 'task api:typecheck', 'task api:test'",
    "Verify memvid-service CI job uses 'task memvid:format:check', 'task memvid:lint', 'task memvid:build', 'task memvid:test'",
    "Verify ingest CI job uses 'task ingest:lint', 'task ingest:typecheck', 'task ingest:test:coverage'",
    "Verify dorny/paths-filter is preserved for monorepo change detection"
  ],
  "passes": false,
  "verified": false,
  "dependencies": [
    "taskfile-root",
    "taskfile-frontend",
    "taskfile-api-service",
    "taskfile-memvid-service",
    "taskfile-ingest"
  ]
}
```

```json
{
  "id": "taskfile-release-pipeline",
  "category": "build",
  "title": "Release Gate Pipeline via Taskfile Dependencies",
  "description": "Root-level release-gate task that chains the full release pipeline (build -> export -> ingest -> smoke -> pytest -> e2e) as declared Taskfile dependencies. Wraps existing scripts where needed.",
  "testing_steps": [
    "Run 'task release-gate --dry' and verify it shows the correct task execution order",
    "Verify the release-gate task declares deps on containers, containers:export, containers:smoke, e2e",
    "Run 'task release-gate' and verify all phases execute in dependency order"
  ],
  "passes": false,
  "verified": false,
  "dependencies": [
    "taskfile-container-orchestration",
    "taskfile-quality-gate"
  ]
}
```

---

## Dependencies

### go-task Binary

- **Version**: 3.x (latest stable, currently 3.43+)
- **Install methods**:
  - macOS: `brew install go-task`
  - Linux: `sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin`
  - CI: `arduino/setup-task@v2` GitHub Action
- **No runtime dependencies**: Single static binary, no Go runtime needed
- **Already available**: `go-task` is in Homebrew and major Linux package managers

### Taskfile Schema

- VSCode/IDE support: `schemaVersion: 3` provides JSON Schema validation
- Add `.task/` to `.gitignore` (checksum storage directory)

### Compatibility

- `task` command must not conflict with existing system commands. On macOS, there is a
  BSD `task` utility but it is rarely installed. go-task installs as both `task` and
  `go-task` to avoid conflicts.

---

## Risks and Trade-offs

### Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Developers unfamiliar with Taskfile | Medium | Low | YAML syntax is simple; `task --list` provides discoverability; CLAUDE.md updated with examples |
| go-task version incompatibility in CI | Low | Medium | Pin version in `arduino/setup-task@v2` with `version: '3.x'` |
| Change detection false positives (task runs when not needed) | Low | Low | Acceptable; worst case is a redundant build. Use `--force` to override |
| Change detection false negatives (task skips when source changed) | Very Low | High | Checksums are content-based, not timestamp-based; very reliable. `.task/` can be deleted to force rebuild |
| Existing scripts break during migration | Medium | Medium | Phased migration; keep scripts alongside Taskfile tasks during transition. Only remove scripts after CI validates task equivalents |
| Shell scripts with complex logic cannot be fully expressed in Taskfile | N/A | N/A | By design: complex scripts are wrapped, not replaced. Taskfile provides orchestration, not reimplementation |

### Trade-offs

| Decision | Pro | Con |
| --- | --- | --- |
| Wrap complex scripts instead of rewriting | Preserves tested logic; lower risk | Two layers (Taskfile + script) to maintain |
| Use checksum method (default) over timestamp | Reliable across git operations | Slightly slower than timestamp for large source trees |
| Keep dorny/paths-filter in CI alongside Taskfile sources | CI job gating is coarser-grained (skip entire jobs); Taskfile is finer-grained (skip individual tasks) | Two layers of change detection |
| Single `task` binary dependency | No runtime, no plugins, cross-platform | Another tool to install; go-task is less universal than make |

### Alternatives Considered

| Alternative | Reason Not Chosen |
| --- | --- |
| **GNU Make** | Tab-sensitivity, no native YAML, poor Windows support, no built-in checksum-based change detection |
| **just** | No `sources`/`generates` change detection; no task dependencies; positioned as a command runner not a build tool |
| **mise** | More opinionated (replaces nvm/pyenv/asdf); Taskfile integration exists but adds unnecessary complexity for this project |
| **Turborepo/Nx** | JavaScript-ecosystem focused; overkill for a 4-service polyglot monorepo; adds node_modules dependency to non-JS services |
| **Bazel** | Enterprise-grade but massive learning curve; overkill for this project size |

---

## Implementation Notes

### Taskfile.yml Skeleton (Root)

```yaml
version: '3'

vars:
  VERSION: '{{.VERSION | default "latest"}}'
  REGISTRY: '{{.REGISTRY | default "localhost"}}'
  GIT_REVISION:
    sh: git rev-parse --short HEAD 2>/dev/null || echo "unknown"
  BUILD_DATE:
    sh: date -u +"%Y-%m-%dT%H:%M:%SZ"

includes:
  frontend:
    taskfile: ./frontend/Taskfile.yml
    dir: ./frontend
  api:
    taskfile: ./api-service/Taskfile.yml
    dir: ./api-service
  memvid:
    taskfile: ./memvid-service/Taskfile.yml
    dir: ./memvid-service
  ingest:
    taskfile: ./ingest/Taskfile.yml
    dir: ./ingest

tasks:
  default:
    desc: List all available tasks
    cmds:
      - task --list

  setup:
    desc: Bootstrap development environment
    deps:
      - frontend:install
      - api:install
      - ingest:install
      - hooks
    cmds:
      - echo "Development environment ready"

  hooks:
    desc: Install git hooks
    cmds:
      - git config core.hooksPath .githooks
      - chmod +x .githooks/*
    status:
      - test "$(git config core.hooksPath)" = ".githooks"

  proto:
    desc: Regenerate gRPC stubs from proto definitions
    cmds:
      - ./scripts/gen-proto.sh
    sources:
      - proto/memvid/v1/memvid.proto
    generates:
      - api-service/ai_resume_api/proto/memvid/v1/memvid_pb2.py
      - api-service/ai_resume_api/proto/memvid/v1/memvid_pb2_grpc.py

  lint:
    desc: Run all linters
    deps:
      - frontend:lint
      - api:lint
      - memvid:lint
      - ingest:lint

  test:
    desc: Run all unit tests
    deps:
      - frontend:test
      - api:test
      - memvid:test
      - ingest:test

  quality:
    desc: Full quality check (lint + typecheck + test)
    deps:
      - lint
      - frontend:typecheck
      - api:typecheck
      - ingest:typecheck
      - test

  build:
    desc: Build all containers
    aliases: [containers]
    deps:
      - frontend:container
      - api:container
      - memvid:container
      - ingest:container

  clean:
    desc: Remove build artifacts and task cache
    cmds:
      - rm -rf .task/
      - rm -rf frontend/dist/
      - rm -rf memvid-service/target/
```

### Python Venv Handling

Taskfile tasks for Python services must activate the correct venv. Use `sh` to source
the venv before running commands:

```yaml
# api-service/Taskfile.yml
tasks:
  test:
    desc: Run pytest
    cmds:
      - |
        source .venv/bin/activate
        pytest -v --tb=short
    sources:
      - ai_resume_api/**/*.py
      - tests/**/*.py
      - pyproject.toml
```

Alternatively, reference the venv Python directly:

```yaml
tasks:
  test:
    desc: Run pytest
    cmds:
      - .venv/bin/python -m pytest -v --tb=short
```

The second approach is preferred because it avoids shell sourcing complexity and works
consistently across `sh` and `bash`.

### Container Build Task Pattern

Each service's `container` task follows the same pattern:

```yaml
tasks:
  container:
    desc: Build container image
    vars:
      IMAGE_NAME: ai-resume-frontend
    cmds:
      - podman manifest rm "{{.REGISTRY}}/{{.IMAGE_NAME}}:{{.VERSION}}" 2>/dev/null || true
      - >-
        podman build
        --platform linux/amd64,linux/arm64
        --manifest "{{.REGISTRY}}/{{.IMAGE_NAME}}:{{.VERSION}}"
        --annotation "org.opencontainers.image.version={{.VERSION}}"
        --annotation "org.opencontainers.image.created={{.BUILD_DATE}}"
        --annotation "org.opencontainers.image.revision={{.GIT_REVISION}}"
        -f Dockerfile .
    sources:
      - Dockerfile
      - dist/**/*
      - nginx.conf
      - nginx-default.conf
```

Root variables (`VERSION`, `REGISTRY`, `GIT_REVISION`, `BUILD_DATE`) propagate to included
Taskfiles automatically.

---

## CLAUDE.md Updates Required

When implementation is complete, update the following CLAUDE.md sections:

1. **Development > Commands**: Add `task` commands alongside existing `npm`/`uv` commands
2. **Container Deployment > Building**: Reference `task containers` instead of `scripts/build-all.sh`
3. **Development > Testing**: Add `task test`, `task e2e`, `task e2e:real`
4. **Quality Standards**: Reference `task quality` as the primary quality gate command
5. Add a new section **Build Orchestration** explaining the Taskfile structure

---

## Success Criteria

1. `task --list` from repo root shows all available tasks with descriptions
2. `task quality` passes (lint + typecheck + test for all 4 services)
3. `task containers` builds all 4 container images with per-service change detection
4. Running `task containers` twice without source changes skips all builds
5. CI workflows use `task` targets and all CI jobs pass
6. No existing scripts are removed until their Taskfile replacements are validated in CI
7. `task release-gate` executes the full release pipeline

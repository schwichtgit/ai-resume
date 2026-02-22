# Taskfile Build System -- Implementation Plan

## Metadata

| Field        | Value                        |
| ------------ | ---------------------------- |
| Plan Version | 2.0.0                        |
| Created      | 2026-02-21                   |
| Status       | Pending Approval             |
| Depends On   | plan.md v1.0.0               |
| Branch       | `feat/taskfile-build-system` |

---

## Overview

This plan introduces [go-task](https://taskfile.dev/) as the primary build orchestration
tool for the ai-resume polyglot monorepo. The Taskfile replaces ad-hoc shell scripts with
a declarative, discoverable, consistent interface for humans and AI agents.

**Principle:** Existing scripts are **wrapped, not deleted** -- the Taskfile calls them
where they already do the right thing and inlines logic only where scripts are thin wrappers.

### Prerequisites

- go-task 3.48.0 already installed at `/usr/local/bin/task`
- CI: `arduino/setup-task@v2` GitHub Action

---

## File Layout

```text
ai-resume/
  Taskfile.yml                    # Root orchestrator (includes per-service)
  frontend/Taskfile.yml           # Frontend tasks
  api-service/Taskfile.yml        # API service tasks
  memvid-service/Taskfile.yml     # Memvid service tasks
  ingest/Taskfile.yml             # Ingest pipeline tasks
  deployment/Taskfile.yml         # Container + compose tasks
```

Add `.task/` to `.gitignore` (checksum storage directory).

---

## Naming Convention

Task names follow a `namespace:verb` pattern. The root Taskfile re-exports high-level
aggregate tasks (no namespace prefix) and includes service-specific tasks under their
namespace.

### High-Level Aggregate Tasks (Primary Interface)

| Task                     | Description                                         |
| ------------------------ | --------------------------------------------------- |
| `task setup`             | Install all deps, create venvs, install hooks       |
| `task lint`              | Lint all services (parallel)                        |
| `task lint:fix`          | Lint all services with auto-fix                     |
| `task test`              | Unit test all services (parallel)                   |
| `task test:coverage`     | Unit test all services with coverage enforcement    |
| `task build`             | Build all services (frontend prod, cargo release)   |
| `task check`             | Full quality sweep: lint + typecheck + test + build |
| `task ci`                | Mirror GitHub Actions CI locally                    |
| `task dev`               | Print instructions for starting dev servers         |
| `task dev:frontend`      | Start frontend dev server                           |
| `task dev:api`           | Start API service with hot reload                   |
| `task dev:memvid`        | Start memvid gRPC service                           |
| `task container:build`   | Build all container images                          |
| `task container:export`  | Export containers as tar files                      |
| `task container:publish` | Push containers to remote registry                  |
| `task container:test`    | Run container smoke tests                           |
| `task e2e`               | Run cross-service integration tests (mock)          |
| `task e2e:real`          | Run true E2E tests (real ingest + real memvid)      |
| `task release-gate`      | Full release quality gate                           |
| `task proto`             | Regenerate gRPC stubs                               |
| `task clean`             | Remove build artifacts                              |
| `task deps`              | Check required tool dependencies                    |

### Service-Namespaced Tasks (Secondary)

| Namespace   | Tasks                                                                                              |
| ----------- | -------------------------------------------------------------------------------------------------- |
| `frontend:` | `lint`, `lint:fix`, `typecheck`, `test`, `test:coverage`, `test:watch`, `build`, `dev`, `setup`    |
| `api:`      | `lint`, `lint:fix`, `typecheck`, `test`, `test:coverage`, `format`, `format:check`, `dev`, `setup` |
| `memvid:`   | `lint`, `fmt`, `fmt:check`, `build`, `build:release`, `test`, `test:coverage`, `dev`, `setup`      |
| `ingest:`   | `lint`, `lint:fix`, `typecheck`, `test`, `test:coverage`, `format`, `format:check`, `setup`        |
| `deploy:`   | `build`, `export`, `publish`, `test`, `compose:up`, `compose:down`, `compose:logs`                 |
| `docs:`     | `lint`, `lint:fix`                                                                                 |

---

## Dependency Detection

Tools are checked in three tiers. Each tier uses semantic version comparison
(major.minor.patch) with a reusable `check_tool` function that extracts versions
from varied `--version` output formats.

**Python strategy:** The system `python3` (macOS 3.9.6) is irrelevant. Python is
managed per-venv by `uv`. The global check only verifies `uv` is installed. Each
service's `setup` task uses `uv venv` + `uv sync`, which downloads and pins the
correct Python version from `.python-version`.

### Tier 1 -- Required (fail if missing or below minimum)

| Tool    | Minimum | Source                                   | Install Hint                                       |
| ------- | ------- | ---------------------------------------- | -------------------------------------------------- |
| Node.js | 22.12.0 | jsdom 27 peer dep; CI `NODE_VERSION: 22` | `https://nodejs.org/`                              |
| npm     | 10.0.0  | Ships with Node 22+                      | (bundled with Node.js)                             |
| uv      | 0.4.0   | Manages Python + venvs for all services  | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| go-task | 3.0.0   | Build orchestration                      | `https://taskfile.dev/installation/`               |

### Tier 2 -- Service-specific (warn if missing; required for that service)

| Tool       | Minimum | Required For   | Install Hint                                                      |
| ---------- | ------- | -------------- | ----------------------------------------------------------------- |
| Rust/rustc | 1.92.0  | memvid-service | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Cargo      | 1.92.0  | memvid-service | (bundled with Rust)                                               |
| protoc     | 3.0.0   | gRPC codegen   | `https://github.com/protocolbuffers/protobuf/releases`            |

### Tier 3 -- Optional (info only, never fail)

| Tool              | Install Hint                                                |
| ----------------- | ----------------------------------------------------------- |
| podman            | `https://podman.io/docs/installation`                       |
| skopeo            | `https://github.com/containers/skopeo/blob/main/install.md` |
| markdownlint-cli2 | `npm install -g markdownlint-cli2`                          |
| shellcheck        | `https://github.com/koalaman/shellcheck#installing`         |
| cargo-tarpaulin   | `cargo install cargo-tarpaulin`                             |

### Version Comparison Implementation

The `deps` task uses a shared script (`scripts/check-deps.sh`) for reuse across
Taskfile and CI. Core functions:

```bash
# Extract first semver-like pattern (X.Y.Z or X.Y) from any --version output
extract_version() {
  echo "$1" | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1
}

# Compare two semver strings: returns 0 if $1 >= $2, 1 otherwise
version_gte() {
  local have="$1" need="$2"
  local have_major have_minor have_patch
  local need_major need_minor need_patch
  IFS='.' read -r have_major have_minor have_patch <<< "$have"
  IFS='.' read -r need_major need_minor need_patch <<< "$need"
  have_patch="${have_patch:-0}"
  need_patch="${need_patch:-0}"
  if (( have_major > need_major )); then return 0; fi
  if (( have_major < need_major )); then return 1; fi
  if (( have_minor > need_minor )); then return 0; fi
  if (( have_minor < need_minor )); then return 1; fi
  if (( have_patch >= need_patch )); then return 0; fi
  return 1
}

# Check a single tool: name, version-command, minimum, install-hint
check_tool() {
  local name="$1" cmd="$2" min_version="$3" hint="$4"
  if ! command -v "${cmd%% *}" &>/dev/null; then
    printf "  MISSING  %-16s  -- %s\n" "$name" "$hint"
    return 1
  fi
  local raw actual
  raw=$(eval "$cmd" 2>&1) || true
  actual=$(extract_version "$raw")
  if [ -z "$actual" ]; then
    printf "  UNKNOWN  %-16s  (could not parse version)\n" "$name"
    return 1
  fi
  if version_gte "$actual" "$min_version"; then
    printf "  PASS     %-16s  %s >= %s\n" "$name" "$actual" "$min_version"
    return 0
  else
    printf "  FAIL     %-16s  %s < %s (need >= %s)\n" "$name" "$actual" "$min_version" "$min_version"
    return 1
  fi
}
```

Note: Uses `FAIL=$((FAIL + 1))` not `((FAIL++))` to avoid the bash arithmetic
exit-code bug with `set -e`.

### Taskfile `deps` Tasks

```yaml
deps:
  desc: Check all tool dependencies
  cmds:
    - task: deps:required
    - task: deps:service
    - task: deps:optional

deps:required:
  desc: Verify required tools (fail if missing or below minimum)
  silent: true
  cmds:
    - bash scripts/check-deps.sh required

deps:service:
  desc: Check service-specific tools (warn only)
  silent: true
  cmds:
    - bash scripts/check-deps.sh service

deps:optional:
  desc: Check optional tools (info only)
  silent: true
  cmds:
    - bash scripts/check-deps.sh optional
```

---

## Service Taskfile Designs

### frontend/Taskfile.yml

Key decisions:

- `setup` uses `sources`/`generates`/`status` for idempotent `npm ci`
- `deps: [setup]` on every lint/test/build ensures dependencies are present
- Change detection via checksums skips up-to-date builds

```yaml
version: '3'

tasks:
  setup:
    desc: Install frontend npm dependencies
    cmds:
      - npm ci
    sources:
      - package.json
      - package-lock.json
    generates:
      - node_modules/.package-lock.json
    status:
      - test -d node_modules

  lint:
    desc: Run ESLint
    deps: [setup]
    cmds:
      - npm run lint
    sources:
      - src/**/*.{ts,tsx}
      - eslint.config.js

  lint:fix:
    desc: Run ESLint with auto-fix
    deps: [setup]
    cmds:
      - npm run lint -- --fix

  typecheck:
    desc: Run TypeScript type checking
    deps: [setup]
    cmds:
      - npx tsc --noEmit

  test:
    desc: Run Vitest
    deps: [setup]
    cmds:
      - npm test -- --run
    sources:
      - src/**/*.{ts,tsx}
      - src/test/setup.ts
      - vitest.config.ts

  test:coverage:
    desc: Run Vitest with coverage
    deps: [setup]
    cmds:
      - npm test -- --run --coverage

  test:watch:
    desc: Run Vitest in watch mode
    deps: [setup]
    cmds:
      - npm run test:watch

  build:
    desc: Production build
    deps: [setup]
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
    generates:
      - dist/**/*

  dev:
    desc: Start Vite dev server
    deps: [setup]
    cmds:
      - npm run dev
```

### api-service/Taskfile.yml

Key decisions:

- Uses `uv run` consistently (matches CI behavior)
- No venv activation needed -- `uv run` detects and uses existing venvs

```yaml
version: '3'

vars:
  VENV: .venv
  UV_RUN: uv run

tasks:
  setup:
    desc: Create venv and install dependencies
    cmds:
      - uv venv {{.VENV}}
      - uv sync --extra test --extra lint
    status:
      - test -d {{.VENV}}
      - test -f {{.VENV}}/bin/python

  lint:
    desc: Run ruff lint + format check
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff check .'
      - '{{.UV_RUN}} ruff format --check .'
    sources:
      - ai_resume_api/**/*.py
      - tests/**/*.py
      - pyproject.toml

  lint:fix:
    desc: Run ruff lint and format with auto-fix
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff check --fix .'
      - '{{.UV_RUN}} ruff format .'

  typecheck:
    desc: Run mypy type checking
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} mypy .'

  format:
    desc: Format with ruff
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff format .'

  format:check:
    desc: Check formatting with ruff
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff format --check .'

  test:
    desc: Run pytest
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} pytest -v --tb=short'
    sources:
      - ai_resume_api/**/*.py
      - tests/**/*.py
      - pyproject.toml

  test:coverage:
    desc: Run pytest with coverage
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} pytest -v --tb=short --cov=ai_resume_api --cov-report=term-missing'

  dev:
    desc: Start FastAPI with hot reload
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} uvicorn ai_resume_api.main:app --reload --port 3000'
```

### memvid-service/Taskfile.yml

Key decisions:

- No `deps: [setup]` -- `cargo build/test` automatically fetches dependencies
- `test:coverage` uses existing `tarpaulin-unit.toml` config

```yaml
version: '3'

tasks:
  setup:
    desc: Fetch Rust dependencies
    cmds:
      - cargo fetch
    status:
      - test -f Cargo.lock

  lint:
    desc: Run clippy with deny warnings
    cmds:
      - cargo clippy -- -D warnings

  fmt:
    desc: Format Rust code
    cmds:
      - cargo fmt

  fmt:check:
    desc: Check Rust formatting
    cmds:
      - cargo fmt --check

  build:
    desc: Build debug
    cmds:
      - cargo build

  build:release:
    desc: Build release
    cmds:
      - cargo build --release
    sources:
      - src/**/*.rs
      - build.rs
      - Cargo.toml
      - Cargo.lock
    generates:
      - target/release/memvid-service

  test:
    desc: Run cargo test
    cmds:
      - cargo test

  test:coverage:
    desc: Run cargo tarpaulin (unit)
    preconditions:
      - sh: command -v cargo-tarpaulin
        msg: 'cargo-tarpaulin not found. Install: cargo install cargo-tarpaulin'
    cmds:
      - cargo tarpaulin --config tarpaulin-unit.toml

  dev:
    desc: Run memvid service
    cmds:
      - cargo run
```

### ingest/Taskfile.yml

```yaml
version: '3'

vars:
  VENV: .venv
  UV_RUN: uv run

tasks:
  setup:
    desc: Create venv and install dependencies
    cmds:
      - uv venv {{.VENV}}
      - uv sync --extra test --extra lint
    status:
      - test -d {{.VENV}}

  lint:
    desc: Run ruff lint + format check
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff check .'
      - '{{.UV_RUN}} ruff format --check .'

  lint:fix:
    desc: Run ruff lint and format with auto-fix
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff check --fix .'
      - '{{.UV_RUN}} ruff format .'

  typecheck:
    desc: Run mypy type checking
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} mypy .'

  format:
    desc: Format with ruff
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff format .'

  format:check:
    desc: Check formatting with ruff
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} ruff format --check .'

  test:
    desc: Run pytest (exclude slow)
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} pytest -v --tb=short -m "not slow"'

  test:coverage:
    desc: Run pytest with coverage
    deps: [setup]
    cmds:
      - '{{.UV_RUN}} pytest -v --tb=short -m "not slow" --cov=ingest --cov-report=term-missing --cov-fail-under=85'
```

### deployment/Taskfile.yml

Key decisions:

- Wraps existing shell scripts -- they handle multi-arch builds, OCI annotations, error handling
- `preconditions` check for podman/skopeo with install hints
- Uses `podman compose` (not podman-compose)

```yaml
version: '3'

vars:
  REGISTRY: '{{.REGISTRY | default "localhost"}}'
  VERSION: '{{.VERSION | default "latest"}}'

tasks:
  build:
    desc: Build all container images
    preconditions:
      - sh: command -v podman
        msg: 'podman not found. See: https://podman.io/docs/installation'
    cmds:
      - ../scripts/build-all.sh {{.VERSION}}

  export:
    desc: Export container images as tar files
    preconditions:
      - sh: command -v podman
        msg: 'podman not found.'
    cmds:
      - ../scripts/export-containers.sh {{.VERSION}}

  publish:
    desc: Publish containers to remote registry
    preconditions:
      - sh: command -v skopeo
        msg: 'skopeo not found. See: https://github.com/containers/skopeo/blob/main/install.md'
      - sh: command -v podman
        msg: 'podman not found.'
    cmds:
      - ../scripts/publish-containers.sh {{.CLI_ARGS}}

  test:
    desc: Run container smoke tests
    cmds:
      - ../scripts/test-containers.sh {{.VERSION}}

  compose:up:
    desc: Start services with podman compose
    cmds:
      - podman compose up -d

  compose:down:
    desc: Stop services
    cmds:
      - podman compose down

  compose:logs:
    desc: Show service logs
    cmds:
      - podman compose logs -f {{.CLI_ARGS}}
```

---

## Root Taskfile.yml

```yaml
version: '3'

vars:
  REGISTRY: '{{.REGISTRY | default "localhost"}}'
  VERSION: '{{.VERSION | default "latest"}}'
  PROJECT_ROOT:
    sh: pwd
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
  deploy:
    taskfile: ./deployment/Taskfile.yml
    dir: ./deployment
    vars:
      REGISTRY: '{{.REGISTRY}}'
      VERSION: '{{.VERSION}}'

tasks:
  default:
    desc: List all available tasks
    cmds:
      - task --list

  deps:
    desc: Check all required tool dependencies
    cmds:
      - task: deps:required
      - task: deps:optional

  deps:required:
    # (see Dependency Detection section above)

  deps:optional:
    # (see Dependency Detection section above)

  setup:
    desc: Bootstrap full dev environment
    deps: [deps:required]
    cmds:
      - task: frontend:setup
      - task: api:setup
      - task: memvid:setup
      - task: ingest:setup
      - task: setup:hooks

  setup:hooks:
    desc: Install git hooks
    cmds:
      - ./scripts/install-hooks.sh
    status:
      - test "$(git config core.hooksPath)" = ".githooks"

  lint:
    desc: Lint all services
    deps: [frontend:lint, api:lint, memvid:lint, ingest:lint, docs:lint]

  lint:fix:
    desc: Lint all services with auto-fix
    deps:
      [
        frontend:lint:fix,
        api:lint:fix,
        memvid:fmt,
        ingest:lint:fix,
        docs:lint:fix,
      ]

  test:
    desc: Unit test all services
    deps: [frontend:test, api:test, memvid:test, ingest:test]

  test:coverage:
    desc: Unit test all services with coverage
    deps:
      [
        frontend:test:coverage,
        api:test:coverage,
        memvid:test:coverage,
        ingest:test:coverage,
      ]

  build:
    desc: Build all services
    deps: [frontend:build, memvid:build:release]

  check:
    desc: Full local quality sweep (lint + typecheck + test + build)
    cmds:
      - task: lint
      - task: frontend:typecheck
      - task: api:typecheck
      - task: ingest:typecheck
      - task: test
      - task: build

  ci:
    desc: Reproduce CI pipeline locally
    cmds:
      - task: deps:required
      - task: lint
      - task: frontend:typecheck
      - task: api:typecheck
      - task: ingest:typecheck
      - task: test:coverage
      - task: build
      - task: docs:lint

  proto:
    desc: Regenerate gRPC Python stubs
    cmds:
      - ./scripts/gen-proto.sh
    sources:
      - proto/memvid/v1/memvid.proto
    generates:
      - api-service/ai_resume_api/proto/memvid/v1/memvid_pb2.py
      - api-service/ai_resume_api/proto/memvid/v1/memvid_pb2_grpc.py

  e2e:
    desc: Cross-service integration tests (mock backends)
    cmds:
      - ./scripts/test-e2e-integration.sh

  e2e:real:
    desc: True E2E tests (real ingest + real memvid, mock LLM)
    cmds:
      - ./scripts/test-e2e-real.sh

  release-gate:
    desc: Full release quality gate
    cmds:
      - ./scripts/release-gate.sh {{.VERSION}}

  container:build:
    desc: Build all container images
    cmds:
      - task: deploy:build

  container:export:
    desc: Export containers as tar files
    cmds:
      - task: deploy:export

  container:publish:
    desc: Publish containers to remote registry
    cmds:
      - task: deploy:publish

  container:test:
    desc: Run container smoke tests
    cmds:
      - task: deploy:test

  dev:
    desc: Print dev server startup instructions
    cmds:
      - |
        echo "Start each service in a separate terminal:"
        echo ""
        echo "  Terminal 1 (memvid):   task dev:memvid"
        echo "  Terminal 2 (api):      task dev:api"
        echo "  Terminal 3 (frontend): task dev:frontend"

  dev:frontend:
    desc: Start frontend dev server
    cmds:
      - task: frontend:dev

  dev:api:
    desc: Start API service with hot reload
    cmds:
      - task: api:dev

  dev:memvid:
    desc: Start memvid gRPC service
    cmds:
      - task: memvid:dev

  docs:lint:
    desc: Lint Markdown files
    cmds:
      - npx --prefix frontend markdownlint-cli2 '**/*.md'

  docs:lint:fix:
    desc: Lint and fix Markdown files
    cmds:
      - npx --prefix frontend markdownlint-cli2 --fix '**/*.md'

  clean:
    desc: Remove build artifacts
    cmds:
      - rm -rf .task/
      - rm -rf frontend/dist
      - rm -rf memvid-service/target
      - echo "Clean complete. Python .venvs preserved (use 'task clean:all' to remove)."

  clean:all:
    desc: Remove build artifacts AND virtual environments
    cmds:
      - task: clean
      - rm -rf api-service/.venv
      - rm -rf ingest/.venv
      - rm -rf deployment/.venv
```

---

## Script Absorption Strategy

| Existing Script                   | Taskfile Action                  | Rationale                        |
| --------------------------------- | -------------------------------- | -------------------------------- |
| `scripts/build-all.sh`            | Wrapped by `deploy:build`        | Complex multi-arch logic -- keep |
| `scripts/install-hooks.sh`        | Wrapped by `setup:hooks`         | Simple, correct -- keep          |
| `scripts/gen-proto.sh`            | Wrapped by `task proto`          | Small, correct -- keep           |
| `scripts/test-e2e-integration.sh` | Wrapped by `task e2e`            | Complex -- keep                  |
| `scripts/test-e2e-real.sh`        | Wrapped by `task e2e:real`       | Complex -- keep                  |
| `scripts/test-e2e-mock-gates.sh`  | Wrapped by `task e2e:mock-gates` | Complex -- keep                  |
| `scripts/publish-containers.sh`   | Wrapped by `deploy:publish`      | Complex -- keep                  |
| `scripts/export-containers.sh`    | Wrapped by `deploy:export`       | Correct -- keep                  |
| `scripts/test-containers.sh`      | Wrapped by `deploy:test`         | Correct -- keep                  |
| `scripts/release-gate.sh`         | Wrapped by `task release-gate`   | Complex -- keep                  |
| `scripts/dev-setup.sh`            | **Replaced** by `task setup`     | Outdated paths                   |
| `scripts/verify-quality.sh`       | **Replaced** by `task check`     | Reimplements what Taskfile does  |

Standalone tools (no wrapper needed): `profile-latency.sh`, `load-test.py`,
`release-gate-matrix.sh`, `test-outcome-portability.sh`, `test-outcome-containers.sh`,
`verify-docs.sh`.

---

## How `task ci` Mirrors GitHub Actions

```text
task ci
  --> deps:required          (verify tools)
  --> frontend:lint           (ESLint)
  --> api:lint                (ruff check + format check)
  --> memvid:lint             (cargo clippy)
  --> ingest:lint             (ruff check + format check)
  --> docs:lint               (markdownlint-cli2)
  --> frontend:typecheck      (tsc --noEmit)
  --> api:typecheck           (mypy)
  --> ingest:typecheck        (mypy)
  --> frontend:test:coverage  (vitest --coverage)
  --> api:test:coverage       (pytest --cov)
  --> memvid:test:coverage    (cargo tarpaulin)
  --> ingest:test:coverage    (pytest --cov --cov-fail-under=85)
  --> frontend:build          (vite build)
  --> memvid:build:release    (cargo build --release)
```

Cross-service and E2E tests require running services, so they are excluded
from `task ci` but available as `task e2e` and `task e2e:real`.

---

## Change Detection Strategy

Uses `checksum` method (the default). Checksums are more reliable than timestamps across
git operations (clone, checkout, rebase all reset timestamps). The `.task/` directory
stores checksums and is added to `.gitignore`.

Key `sources`/`generates` mappings:

| Task                   | Sources                                                    | Generates                       |
| ---------------------- | ---------------------------------------------------------- | ------------------------------- |
| `frontend:build`       | `src/**/*.{ts,tsx,css}`, config files                      | `dist/**/*`                     |
| `memvid:build:release` | `src/**/*.rs`, `build.rs`, `Cargo.toml`, `Cargo.lock`      | `target/release/memvid-service` |
| `proto`                | `proto/memvid/v1/memvid.proto`                             | `*_pb2.py`, `*_pb2_grpc.py`     |
| `frontend:lint`        | `src/**/*.{ts,tsx}`, `eslint.config.js`                    | --                              |
| `api:lint`             | `ai_resume_api/**/*.py`, `tests/**/*.py`, `pyproject.toml` | --                              |

---

## CI Integration

### Current

CI workflow (`.github/workflows/ci.yml`) uses `dorny/paths-filter` for monorepo change
detection and conditional job execution. Each job inlines its own commands.

### Proposed (Phase 3)

Install `task` in CI via `arduino/setup-task@v2`, then call task targets:

```yaml
frontend:
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v6
    - uses: arduino/setup-task@v2
      with:
        version: '3.x'
    - run: task frontend:lint
    - run: task frontend:typecheck
    - run: task frontend:test:coverage
    - run: task frontend:build
```

**CI continues to own**: path-based change detection, caching, matrix strategies,
summary job. **Migrates to Taskfile**: inline command sequences, working directory
management, quality gate checks.

---

## Implementation Sequence

### Phase 1 -- Foundation (1 commit)

1. Add `.task/` to `.gitignore`
2. Create root `Taskfile.yml` with `deps`, `setup`, `clean`, `default` tasks
3. Create `frontend/Taskfile.yml` with full task set + change detection
4. Create `api-service/Taskfile.yml` with full task set
5. Create `memvid-service/Taskfile.yml` with full task set + change detection
6. Create `ingest/Taskfile.yml` with full task set
7. Create `deployment/Taskfile.yml` wrapping existing scripts
8. Verify: `task --list` shows all tasks with descriptions

### Phase 2 -- Aggregate tasks (1 commit)

1. Wire up `lint`, `test`, `build`, `check`, `ci` aggregate tasks
2. Wire up `container:*`, `e2e`, `e2e:real`, `release-gate`
3. Wire up `dev:*` and `docs:*` tasks
4. Verify: `task ci` runs full quality suite locally

### Phase 3 -- Documentation + feature tracking (1 commit)

1. Update CLAUDE.md to document Taskfile commands alongside existing commands
2. Add features F-125 through F-134 to `feature_list.json`

---

## Feature IDs (for feature_list.json)

| ID    | Title                      | Category       |
| ----- | -------------------------- | -------------- |
| F-125 | Root Taskfile orchestrator | infrastructure |
| F-126 | Dependency detection task  | infrastructure |
| F-127 | Frontend Taskfile          | infrastructure |
| F-128 | API service Taskfile       | infrastructure |
| F-129 | Memvid service Taskfile    | infrastructure |
| F-130 | Ingest Taskfile            | infrastructure |
| F-131 | Deployment Taskfile        | infrastructure |
| F-132 | CI reproduction task       | infrastructure |
| F-133 | Setup task                 | infrastructure |
| F-134 | Documentation update       | infrastructure |

---

## Risks and Trade-offs

| Risk                                                        | Likelihood | Impact | Mitigation                                                 |
| ----------------------------------------------------------- | ---------- | ------ | ---------------------------------------------------------- |
| Developers unfamiliar with Taskfile                         | Medium     | Low    | `task --list` for discoverability; CLAUDE.md updated       |
| Change detection false negatives                            | Very Low   | High   | Checksums are content-based; delete `.task/` to force      |
| Existing scripts break during migration                     | Medium     | Medium | Phased migration; keep scripts alongside until validated   |
| Two layers of change detection (CI paths-filter + Taskfile) | N/A        | Low    | Different granularity: CI gates jobs, Taskfile gates tasks |

### Alternatives Considered

| Alternative  | Reason Not Chosen                                                   |
| ------------ | ------------------------------------------------------------------- |
| GNU Make     | Tab-sensitivity, no native YAML, no checksum-based change detection |
| just         | No `sources`/`generates` change detection; no task dependencies     |
| Turborepo/Nx | JS-ecosystem focused; overkill for polyglot monorepo                |
| Bazel        | Massive learning curve; overkill for this project size              |

---

## Design Principles

- **Wrap, do not rewrite**: Complex scripts are wrapped, not reimplemented
- **Fail fast with clear messages**: `preconditions` check tool availability with install hints
- **Idempotent setup**: `status` checks prevent redundant installs
- **Parallel by default**: Independent service tasks run concurrently via `deps:` blocks
- **No hidden state**: No global environment modifications
- **CI parity**: `task ci` reproduces exactly what GitHub Actions runs

---

## Success Criteria

1. `task --list` from repo root shows all available tasks with descriptions
2. `task check` passes (lint + typecheck + test + build for all services)
3. `task container:build` builds all container images
4. Running `task build` twice without source changes skips all builds
5. `task ci` reproduces CI locally and passes
6. No existing scripts removed until Taskfile replacements validated

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Description:** Polyglot web application enabling recruiters to query a candidate's experience via AI chat with semantic search retrieval
**Tech Stack:** TypeScript (React 19), Python 3.12 (FastAPI), Rust 1.96 (memvid gRPC)
**Repository:** <https://github.com/schwichtgit/ai-resume>

This is an interactive AI-powered resume site built with Vite, React, TypeScript, shadcn/ui, and Tailwind CSS. The site showcases a candidate's experience with an AI chat interface that answers questions about their background, an honest fit assessment tool, and detailed experience cards.

## Feature Development Workflow

This project uses the [specforge](https://github.com/schwichtgit/claude-project-foundation) framework for specification-driven development.

### Specforge Phases

| Phase | Command                   | Artifact                          |
| ----- | ------------------------- | --------------------------------- |
| 0     | `/specforge constitution` | `.specify/memory/constitution.md` |
| 1     | `/specforge spec`         | `.specify/specs/spec.md`          |
| 2     | `/specforge plan`         | `.specify/specs/plan.md`          |
| 3     | `/specforge features`     | `feature_list.json`               |
| 4     | `/specforge analyze`      | Score report                      |
| 5     | `/specforge setup`        | Setup checklist                   |

Phase status is deliberately not a column here. It was one, and it rotted the
same way the feature counts did -- every row read "Complete", two of them
carrying detail (`Approved`, `87.4/100`) that nothing updates when the phase is
re-run. A phase's real status is whether its artifact exists and is current, so
check the artifact.

### Implementation Rules

- **Implementation gate:** Do not implement features until `/specforge analyze` scores >= 80
- **Skip-if-current:** If an artifact already exists and is current, skip its phase
- **Session bootstrap:** At the start of each coding session, read: constitution, plan, `feature_list.json`
- **Feature tracking:** `feature_list.json` is the single source of truth for feature status
- **Feature verification gate:** A feature may only be marked `"passes": true` and `"verified": true` AFTER every entry in its `testing_steps` array has been executed and confirmed passing in the current session. Never set these flags speculatively.
- **Feature counts are not restated here.** `feature_list.json` is the single
  source of truth and changes with every feature pass, so a count copied into
  this file goes stale silently -- it previously claimed 124 features with 90
  unverified, long after the real numbers had moved. Query the file instead:

```bash
jq '.features | length' feature_list.json                      # total
jq '[.features[] | select(.verified)] | length' feature_list.json  # verified
```

## Subagent Policy

### Mandatory Delegation (MUST use subagents)

- Code changes and feature implementations
- Security fixes and vulnerability remediation
- Multi-file documentation updates
- Testing and test coverage improvements
- Schema validation and data migration
- Codebase exploration spanning 3+ files

### Parallelization

- Launch independent analyses as parallel subagents
- Spawn multiple subagents simultaneously when tasks have no data dependencies
- Use Explore agent for broad codebase research

### Main Conversation Only

- Orchestration and task sequencing
- Aggregating subagent results
- User clarification and decision-making
- Single-file reads and quick git commands
- Skill invocations (already isolated)

## Development

### Commands

#### Taskfile (recommended -- orchestrates all services)

```bash
task setup           # Bootstrap full dev environment
task deps            # Check tool dependencies
task lint            # Lint all services
task test            # Test all services
task audit           # Whole-SBOM vuln sweep (npm, pip-audit, cargo audit)
task build           # Build all services
task check           # Full quality sweep (lint + typecheck + test + build)
task ci              # Reproduce CI pipeline locally
task dev             # Show dev server instructions
task container:build # Build all container images
task clean           # Remove build artifacts
```

#### Frontend (npm)

```bash
npm run dev          # Start dev server (http://localhost:8080)
npm run build        # Production build
npm run build:dev    # Development mode build
npm run preview      # Preview production build
```

```bash
npm run lint         # Run ESLint
npm test             # Run tests once
npm run test:watch   # Run tests in watch mode
```

### Testing

#### Unit Tests (Vitest + React Testing Library)

- Test files: `src/**/*.{test,spec}.{ts,tsx}`
- Test setup: `src/test/setup.ts`
- Run all: `npm test`
- Run a single test file: `npm test -- src/path/to/file.test.ts`

#### E2E Tests (Playwright)

- Test files: `e2e/*.spec.ts`
- Config: `playwright.config.ts`
- Requires all three services running (frontend, api-service, memvid-service)
- Tests are data-driven (resume-agnostic) -- work with any `.mv2` file
- Components use `data-testid` attributes for stable Playwright selectors
- Runs in CI via `.github/workflows/e2e-production.yml` -- against the deployed
  site every 6 hours and on `workflow_dispatch`. This is the only check that
  calls the real LLM; CI holds no `OPENROUTER_API_KEY`, so nothing pre-merge
  can detect that the configured model has been retired upstream.

```bash
# Install browser (first time only)
npx playwright install chromium

# Run against local dev server (requires services running)
E2E_BASE_URL=http://localhost:8080 npx playwright test

# Run against production
E2E_BASE_URL=https://frank-ai-resume.schwichtenberg.us npx playwright test

# Run a locally built frontend against the deployed backend -- the only way to
# exercise a UI change against the real LLM before it ships
VITE_API_PROXY_TARGET=https://frank-ai-resume.schwichtenberg.us npm run dev
E2E_BASE_URL=http://localhost:8080 npx playwright test

# View HTML report after run
npx playwright show-report
```

### Virtual Environments

**CRITICAL**: This project uses separate Python virtual environments for each service:

- `api-service/.venv` - FastAPI backend for profile API and gRPC client
- `ingest/.venv` - Data ingestion pipeline (memvid-sdk for .mv2 file creation)
- `deployment/.venv` - Deployment utilities

**When running Python commands, ALWAYS activate the correct venv first:**

```bash
# For data ingestion or memvid operations
source ingest/.venv/bin/activate
python ingest/ingest.py

# For API service development
source api-service/.venv/bin/activate
python api-service/main.py

# For deployment tasks
source deployment/.venv/bin/activate
```

Each venv is **isolated** with its own dependencies. Do not run Python scripts without activating the appropriate environment.

## Architecture

### Observability & Distributed Tracing

Full OpenTelemetry instrumentation across all three services (Python, Rust, TypeScript) with W3C trace context propagation. Grafana/Tempo/Prometheus/Loki stack on a separate observer host. See [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) for architecture, dashboards, runbooks, and configuration.

### Data-Driven Content Architecture (Phase 4 Complete ✅)

**Single-File Portability:** ALL content comes from a single `.mv2` file generated from markdown:

```text
data/<your_resume>.md (YAML + Markdown)
    ↓ python ingest.py
data/.memvid/resume.mv2 (Vector DB + Profile JSON)
    ↓ gRPC + REST API
Frontend Components (Dynamic Rendering)
```

**Data Flow:**

1. **Source**: A resume markdown file (e.g., `data/example_resume.md`) - YAML frontmatter + markdown sections
2. **Ingest**: `python ingest.py` - Parses, chunks, embeds, stores in .mv2
3. **Storage**: `.mv2` file contains:
   - Vector embeddings for semantic search
   - Profile metadata (name, title, email, experience, skills, fit examples)
   - Chunked resume content
4. **API**: Python FastAPI (`api-service/`) loads profile from memvid
5. **Frontend**: React hooks (`useProfile`) fetch from API

**No Hardcoded Data:** All components are fully data-driven from the API.

### Component Structure

- **Page-level**: `src/pages/Index.tsx` - Main page with section composition
- **Section components**: `Hero`, `Experience`, `FitAssessment`, `AIChat`, `Header`, `Footer`
- **Data hooks**: `useProfile()` - Loads profile from `/api/v1/profile`
- **Shared components**: `src/components/ui/` - shadcn/ui primitives
- **Layout**: Single-page app with smooth scroll sections

### Key Features

**AI Chat Interface** (`src/components/AIChat.tsx`):

- Real LLM-powered chat via OpenRouter API
- Semantic search retrieval from memvid (<5ms)
- Streaming responses via Server-Sent Events (SSE)
- Session management with conversation history
- Suggested questions loaded from profile API

**Fit Assessment** (`src/components/FitAssessment.tsx`):

- **Hybrid Approach:**
  - Tab 1: Pre-analyzed strong fit example (from profile)
  - Tab 2: Pre-analyzed weak fit example (from profile)
  - Tab 3: Real-time AI analysis (paste custom job description)
- POST `/api/v1/assess-fit` endpoint for live assessments
- Structured output: verdict, key matches, gaps, recommendation

**Experience Cards** (`src/components/Experience.tsx`):

- Dynamic loading from profile API
- Experience entries with ai_context (situation, approach, technical work, lessons learned)
- Skills categorization (strong/moderate/gaps)
- All data from resume markdown → API

### API Endpoints

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

### Styling System

- Tailwind CSS v4 with CSS-first configuration (no `tailwind.config.ts`)
- Design tokens defined via `@theme {}` directives in `src/index.css`
- `@tailwindcss/vite` plugin (replaces PostCSS integration, no `postcss.config.js`)
- `tw-animate-css` for component animations (replaces deprecated `tailwindcss-animate`)
- shadcn/ui component library for UI primitives
- Custom animations: `fade-in`, `slide-up`, `pulse-soft`
- Utility function: `cn()` from `src/lib/utils.ts` for conditional classnames

### Path Aliases

- `@/` maps to `src/` directory (configured in vite.config.ts and tsconfig.json)
- Import example: `import { useProfile } from "@/hooks/useProfile"`

## TypeScript Configuration

- Relaxed type checking: `noImplicitAny: false`, `strictNullChecks: false`
- Split configs: `tsconfig.json` (project), `tsconfig.app.json` (app), `tsconfig.node.json` (build tools)

## State Management

- React Query (TanStack Query) configured in App.tsx but not actively used
- Profile data loaded via `useProfile()` hook (fetches from API on mount)
- Component-level state with useState (no global state management)

## Browser Router

- Routes defined in `src/App.tsx`
- Current routes: `/` (Index), `*` (NotFound)
- Add custom routes ABOVE the catch-all `*` route

## Extending Content

To add new experience, skills, or fit assessment examples:

1. Edit your resume markdown file (see `data/example_resume.md` for the template)
2. Update the relevant section:
   - **Professional Experience**: Add `### Company Name` sections with role, period, highlights, AI Context
   - **Skills Assessment**: Update skills lists under `### Strong Skills`, `### Moderate Skills`, `### Gaps`
   - **Fit Assessment Examples**: Add example job descriptions with assessments
3. Run `python ingest.py --input data/your_resume.md --output data/.memvid/resume.mv2`
4. Restart the API service (it will load the new .mv2 file)
5. Components automatically render the new data from the API

**Key Schema Elements:**

- **YAML Frontmatter**: name, title, email, linkedin, suggested_questions, system_prompt, tags
- **AI Context**: situation, approach, technical_work, lessons_learned (for each experience)
- **Fit Examples**: title, fit_level, role, job_description, verdict, key_matches, gaps, recommendation

See `data/example_resume.md` for a complete template.

## Quality Standards

Quality is enforced by Claude Code hooks configured in `.claude/settings.json`:

| Hook                | Trigger               | Purpose                                                                      |
| ------------------- | --------------------- | ---------------------------------------------------------------------------- |
| `protect-files.sh`  | Pre-edit (Write/Edit) | Blocks modification of sensitive files (.env, keys, credentials, lock files) |
| `validate-bash.sh`  | Pre-bash              | Blocks destructive commands (rm -rf /, force push, hard reset)               |
| `validate-pr.sh`    | Pre-bash              | Validates PR descriptions and targets                                        |
| `format-changed.sh` | On stop               | Auto-formats changed files by detected language (runs before quality checks) |
| `verify-quality.sh` | On stop               | Runs lint, type check, and test suite before session end                     |

### Coverage Threshold

85% line coverage per service (defined in `.specify/memory/constitution.md`).

### CI Gates

- `ci/principles/commit-gate.md` -- enforced on every commit
- `ci/principles/pr-gate.md` -- enforced on every pull request
- `ci/principles/release-gate.md` -- enforced on every release

## Container Deployment

### Building Multi-Architecture Containers

Each service has its own Dockerfile (`frontend/Dockerfile`, `api-service/Dockerfile`, `memvid-service/Dockerfile`). The build script creates all container images:

**Build all containers:**

```bash
scripts/build-all.sh [tag]
```

**Deploy with compose:**

```bash
cd deployment && podman compose up -d
```

### Running the Container

**Run locally:**

```bash
podman run -d -p 8080:8080 --name frank-resume localhost/frank-resume:latest
```

**With custom domain (behind reverse proxy):**

```bash
podman run -d \
  -p 8080:8080 \
  --name frank-resume \
  localhost/frank-resume:latest
```

The application expects to be served at `frank-resume.schwichtenberg.us` when deployed.

### Container Architecture

- **Frontend base**: alpine with OpenResty (runs as nginx user)
- **Frontend build stage**: node trixie-slim for npm build
- **API base**: ubi10/ubi-micro runtime, rockylinux:10-minimal builder (3-stage build)
- **Ingest base**: ubi10/ubi-micro runtime, rockylinux:10-minimal builder (3-stage build)
- **Memvid base**: gcr.io/distroless/static-debian13:nonroot (runs as nonroot
  user). `static`, not `cc`: the binary is statically linked against musl, so
  the runtime ships no libc, no OpenSSL and no zlib.
- **Frontend port**: 8080 (unprivileged)
- **API port**: 3000
- **Memvid port**: 50051 (gRPC)

Base image versions are deliberately absent here and from the Dockerfile
comments: every base is digest-pinned and bumped by Dependabot, which updates
the `FROM` line and nothing else, so any restated version rots silently. Read
the `FROM` lines for versions; `git log` for when a pin last moved.

- **Health check**: GET /health endpoint

### Nginx Configuration

The included `nginx.conf` provides:

- Security headers (X-Frame-Options, CSP, etc.)
- Gzip compression for assets
- SPA routing (all routes return index.html)
- Static asset caching (1 year for immutable files)
- Health check endpoint at /health

### Deployment Notes

The container is designed to run behind a reverse proxy (Traefik, Caddy, nginx) that handles:

- TLS termination
- Domain routing to frank-resume.schwichtenberg.us
- Port mapping from 80/443 to container port 8080

## Security Workflows

### GitHub Code Scanning Alerts

This project uses GitHub Code Scanning with CodeQL to detect security vulnerabilities. Use the `/gh-code-scanning` skill to manage alerts.

**Common Commands:**

```bash
# List all open code scanning alerts
/gh-code-scanning list

# Get detailed information about an alert
/gh-code-scanning detail <alert-number>

# Fix a security vulnerability
/gh-code-scanning fix <alert-number>

# Dismiss a false positive or won't-fix alert
/gh-code-scanning dismiss <alert-number> <reason>

# Verify an alert has been fixed
/gh-code-scanning verify <alert-number>
```

**Dismissal Reasons:**

- `false-positive` - Alert is not a real issue
- `wont-fix` - Valid issue but won't be fixed (requires rationale)
- `used-in-tests` - Only used in test code

**Best Practices:**

1. Prioritize fixing `error` severity alerts before `warning` or `note`
2. Always use the `detail` command to understand the vulnerability before fixing
3. Document all dismissals in `docs/SECURITY.md` with clear rationale
4. Test fixes to ensure functionality isn't broken
5. Use `verify` command after fixes to confirm resolution

**Manual Fallback:**

If the skill is unavailable, use GitHub CLI directly:

```bash
# List alerts
gh api repos/schwichtgit/ai-resume/code-scanning/alerts \
  --jq '.[] | select(.state == "open") | {number, rule: .rule.id, severity: .rule.severity}'

# Get alert detail
gh api repos/schwichtgit/ai-resume/code-scanning/alerts/1

# Dismiss alert
gh api --method PATCH repos/schwichtgit/ai-resume/code-scanning/alerts/1 \
  -f state='dismissed' \
  -f dismissed_reason='false-positive' \
  -f dismissed_comment='Explanation here'
```

**Reference:**

- Alert types and remediation: `.claude/skills/gh-code-scanning/reference/alert-types.md`
- Fix example: `.claude/skills/gh-code-scanning/examples/fix-example.md`
- Dismiss example: `.claude/skills/gh-code-scanning/examples/dismiss-example.md`

## Git Hooks Distribution

- `.githooks/` is tracked in git and contains all project git hooks (`pre-commit`, `commit-msg`)
- `scripts/install-hooks.sh` sets `git config core.hooksPath .githooks` (no manual file copying needed)
- To install hooks after cloning: `./scripts/install-hooks.sh`
- To skip hooks temporarily: `git commit --no-verify`
- To uninstall: `git config --unset core.hooksPath`
- Pre-commit ESLint: don't use `--max-warnings 0` (shadcn/ui warnings are expected)
- Pre-commit path fix: strip `frontend/` prefix before passing to ESLint when cd'd into frontend/

## Git Commit Guidelines

### Format

- Conventional Commits: `type(scope): description`
- Types: `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`
- Subject line: <= 72 characters, imperative mood
- No emoji, no AI-isms, no Co-Authored-By trailers

### Commit Strategy

- Create focused, atomic commits with clear messages as you work
- Each commit should be a meaningful, standalone change (not WIP or fixup)
- Push individual commits to the feature branch -- do NOT squash before push
- Squash happens at PR merge time (configured in GitHub), not by the developer

## Communication Style

- **Tone:** Technical, direct, and terse
- **No AI-isms:** No self-references, filler phrases, or marketing adjectives
- **No emoji** in code, comments, commit messages, or PR descriptions unless explicitly requested
- **Conventional Commits** for all commit messages (see Git Commit Guidelines)

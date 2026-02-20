# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Description:** Polyglot web application enabling recruiters to query a candidate's experience via AI chat with semantic search retrieval
**Tech Stack:** TypeScript (React 18), Python 3.12 (FastAPI), Rust 1.84 (memvid gRPC)
**Repository:** https://github.com/schwichtgit/ai-resume

This is an interactive AI-powered resume site built with Vite, React, TypeScript, shadcn/ui, and Tailwind CSS. The site showcases a candidate's experience with an AI chat interface that answers questions about their background, an honest fit assessment tool, and detailed experience cards.

## Feature Development Workflow

This project uses the [specforge](https://github.com/schwichtgit/claude-project-foundation) framework for specification-driven development.

### Specforge Phases

| Phase | Command                   | Artifact                          | Status                  |
| ----- | ------------------------- | --------------------------------- | ----------------------- |
| 0     | `/specforge constitution` | `.specify/memory/constitution.md` | Complete                |
| 1     | `/specforge spec`         | `.specify/specs/spec.md`          | Complete                |
| 2     | `/specforge plan`         | `.specify/specs/plan.md`          | Complete (Approved)     |
| 3     | `/specforge features`     | `feature_list.json`               | Complete (124 features) |
| 4     | `/specforge analyze`      | Score report                      | Complete (87.4/100)     |
| 5     | `/specforge setup`        | Setup checklist                   | Pending                 |

### Implementation Rules

- **Implementation gate:** Do not implement features until `/specforge analyze` scores >= 80
- **Skip-if-current:** If an artifact already exists and is current, skip its phase
- **Session bootstrap:** At the start of each coding session, read: constitution, plan, `claude-progress.txt`, `feature_list.json`
- **Feature tracking:** `feature_list.json` is the single source of truth for feature status
- **Brownfield awareness:** 90 features have `verified: false` (existing code, not yet validated). 34 features are greenfield (no `verified` field)

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

- Tests are configured with Vitest + React Testing Library
- Test files: `src/**/*.{test,spec}.{ts,tsx}`
- Test setup: `src/test/setup.ts`
- Run a single test file: `npm test -- src/path/to/file.test.ts`

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
python deployment/deploy.py
```

Each venv is **isolated** with its own dependencies. Do not run Python scripts without activating the appropriate environment.

## Architecture

### Data-Driven Content Architecture (Phase 4 Complete ✅)

**Single-File Portability:** ALL content comes from a single `.mv2` file generated from markdown:

```
data/master_resume.md (YAML + Markdown)
    ↓ python ingest.py
data/.memvid/resume.mv2 (Vector DB + Profile JSON)
    ↓ gRPC + REST API
Frontend Components (Dynamic Rendering)
```

**Data Flow:**

1. **Source**: `data/master_resume.md` - YAML frontmatter + markdown sections
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
- All data from `data/master_resume.md` → API

### Styling System

- Tailwind CSS with custom design tokens defined in `tailwind.config.ts`
- CSS variables for theming in `src/index.css`
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

1. Edit `data/master_resume.md` (or create your own resume markdown file)
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

| Hook                | Trigger                | Purpose                                                                      |
| ------------------- | ---------------------- | ---------------------------------------------------------------------------- |
| `protect-files.sh`  | Pre-edit (Write/Edit)  | Blocks modification of sensitive files (.env, keys, credentials, lock files) |
| `validate-bash.sh`  | Pre-bash               | Blocks destructive commands (rm -rf /, force push, hard reset)               |
| `validate-pr.sh`    | Pre-bash               | Validates PR descriptions and targets                                        |
| `post-edit.sh`      | Post-edit (Write/Edit) | Auto-formats files by detected language                                      |
| `verify-quality.sh` | On stop                | Runs lint, type check, and test suite before session end                     |

### Coverage Threshold

85% line coverage per service (defined in `.specify/memory/constitution.md`).

### CI Gates

- `ci/principles/commit-gate.md` -- enforced on every commit
- `ci/principles/pr-gate.md` -- enforced on every pull request
- `ci/principles/release-gate.md` -- enforced on every release

## Container Deployment

### Building Multi-Architecture Containers

The project includes a Dockerfile and build script for creating OCI containers that work on both amd64 and arm64 (aarch64) architectures.

**Build multi-arch image:**

```bash
./build-container.sh [tag]
```

This creates a manifest with both amd64 and arm64 images. The script uses Podman's multi-architecture build support.

**Manual build commands:**

```bash
# Create manifest
podman manifest create localhost/frank-resume:latest

# Build for amd64
podman build --platform linux/amd64 --manifest localhost/frank-resume:latest .

# Build for arm64
podman build --platform linux/arm64 --manifest localhost/frank-resume:latest .

# Inspect manifest
podman manifest inspect localhost/frank-resume:latest
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

- **Base image**: nginx-unprivileged:1.25-alpine (runs as non-root user)
- **Build stage**: node:18-alpine for npm build
- **Runtime**: Minimal nginx serving static files
- **Port**: 8080 (unprivileged)
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

## Git Commit Guidelines

### Format

- Conventional Commits: `type(scope): description`
- Types: `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`
- Subject line: <= 72 characters, imperative mood
- No emoji, no AI-isms, no Co-Authored-By trailers

### Commit Strategy

When working on development tasks that result in multiple commits:

1. Create focused, atomic commits with clear messages
2. When features are complete and all tests pass:
   - Squash/rebase commits using the original task commit message
   - Push a single, clean commit to the public repository

## Communication Style

- **Tone:** Technical, direct, and terse
- **No AI-isms:** No self-references, filler phrases, or marketing adjectives
- **No emoji** in code, comments, commit messages, or PR descriptions unless explicitly requested
- **Conventional Commits** for all commit messages (see Git Commit Guidelines)

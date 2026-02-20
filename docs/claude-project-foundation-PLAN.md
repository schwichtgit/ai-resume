# PLAN.md -- Claude Project Foundation

## What This Document Is

This is the implementation plan for the Claude Project Foundation repository: a reusable harness for spec-driven, autonomous Claude Code projects. It is self-contained. Someone reading this in a fresh repo with no prior context should have everything needed to implement the foundation from scratch.

## Problem Statement

Building production-quality software with Claude Code in long-running autonomous sessions currently requires assembling patterns from multiple sources, each with significant gaps:

**Anthropic's autonomous-coding quickstart** ([source](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)) provides a two-agent pattern (initializer + coding agent), `feature_list.json` for cross-session progress tracking, `init.sh` for environment setup, git-as-checkpoint, and a 10-step coding loop. It lacks an interactive spec phase (the `app_spec.txt` is pre-written), has no spec quality validation, no commit standards enforcement, no CI integration, no constitution/principles layer, and is web-app-specific.

**AutoForge** ([source](https://github.com/AutoForgeAI/autoforge)) provides a spec creation workflow, SQLite-based feature management, MCP server tools, dependency tracking, and a monitoring UI. It lacks interactive requirements gathering with humans in the loop, foundational SDLC enforcement (TDD, coverage thresholds, linting, static analysis), CI integration, git commit/PR quality standards, and GitHub repo setup best practices.

**Battle-tested production practices** (extracted from the ai-resume project) provide multi-layer Claude Code hooks (validate-bash, protect-files, validate-pr, post-edit, verify-quality), git hooks (pre-commit, commit-msg), CI workflows (path-filtered monorepo, per-language jobs, commit standards, summary aggregation), and communication standards. These are hardcoded to one specific project.

This foundation generalizes and synthesizes all three into a portable scaffold.

### References

- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) -- Anthropic engineering blog describing the two-agent pattern
- [Anthropic autonomous-coding quickstart](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding) -- Reference implementation of the harness
- [AutoForge](https://github.com/AutoForgeAI/autoforge) -- OSS framework implementing the harness pattern with spec workflow
- [Spec-Driven Development with Claude Code](https://alexop.dev/posts/spec-driven-development-claude-code-in-action/) -- Practical SDD implementation guide
- [Claude Code Checkpointing](https://code.claude.com/docs/en/checkpointing) -- Built-in session state management
- [GitHub Spec Kit](https://github.com/github/spec-kit) -- GitHub's spec-driven development toolkit

## Architecture: Three Layers

### Layer 1: Abstract SDLC Principles (platform-agnostic)

Universal quality gates stated as principles, not CI YAML. These apply regardless of whether the CI platform is GitHub Actions, GitLab CI, Jenkins, or something else.

- **Commit gate:** Linting passes for changed files, no secrets in diffs, conventional commit format, no forbidden patterns (WIP, TODO, DEBUG), no AI-isms, no emoji.
- **PR gate:** All commit gates + full type checking + test suite passes + code coverage >= configurable threshold (default 85%) + static analysis clean.
- **Release gate:** All PR gates + dependency audit (no known vulnerabilities) + license compliance + changelog entry + version bump.

### Layer 2: Interactive Planning Phase

The `/specforge` Claude Code skill that guides humans and Claude Code through collaborative specification authoring. Seven sub-commands, each producing a concrete artifact that feeds into the next:

1. `/specforge constitution` -- Define immutable project principles
2. `/specforge spec` -- Document features and acceptance criteria
3. `/specforge clarify` -- Surface ambiguities for human resolution
4. `/specforge plan` -- Make technical architecture decisions
5. `/specforge features` -- Generate feature_list.json with testing steps
6. `/specforge analyze` -- Score spec for autonomous-readiness
7. `/specforge setup` -- Generate platform-specific project setup checklist

### Layer 3: Platform Implementations (pluggable)

GitHub is first-class (fully implemented CI workflows, recommended repo settings, templates). GitLab and Jenkins are documented as abstract-to-platform mapping guides.

## Repo Structure

```
claude-project-foundation/
├── .specify/
│   ├── memory/
│   │   └── constitution.md              # Template: immutable project principles
│   ├── specs/                           # Feature specs land here (initially empty)
│   ├── templates/
│   │   ├── constitution-template.md     # Guided constitution authoring
│   │   ├── spec-template.md             # Feature spec format
│   │   ├── plan-template.md             # Technical plan format
│   │   ├── tasks-template.md            # Task breakdown format
│   │   └── feature-list-schema.json     # feature_list.json JSON Schema
│   └── WORKFLOW.md                      # Tool-agnostic process documentation
├── .claude/
│   ├── settings.json                    # Hook definitions
│   ├── hooks/
│   │   ├── validate-bash.sh             # Block destructive bash patterns
│   │   ├── protect-files.sh             # Block sensitive file modification
│   │   ├── validate-pr.sh              # Enforce PR standards
│   │   ├── post-edit.sh                # Auto-format on file save
│   │   └── verify-quality.sh           # Quality gate on stop
│   └── skills/
│       └── specforge/
│           └── SKILL.md                 # Interactive spec workflow skill
├── prompts/
│   ├── initializer-prompt.md            # First context window prompt
│   └── coding-prompt.md                 # Subsequent context window prompt
├── scripts/
│   ├── hooks/
│   │   ├── pre-commit                   # Git pre-commit hook
│   │   └── commit-msg                   # Git commit-msg hook
│   ├── install-hooks.sh                 # Copy hooks to .git/hooks/
│   └── bootstrap.sh                     # Drop foundation into a new repo
├── ci/
│   ├── principles/
│   │   ├── commit-gate.md               # Abstract: what commits must pass
│   │   ├── pr-gate.md                   # Abstract: what PRs must pass
│   │   └── release-gate.md              # Abstract: what releases must pass
│   ├── github/
│   │   ├── workflows/
│   │   │   ├── ci.yml                   # Parameterized CI template
│   │   │   └── commit-standards.yml     # PR commit validation
│   │   ├── CODEOWNERS.template          # CODEOWNERS template
│   │   ├── dependabot.yml               # Dependabot config
│   │   ├── PULL_REQUEST_TEMPLATE.md     # PR template
│   │   └── repo-settings.md             # Recommended GitHub settings checklist
│   ├── gitlab/
│   │   └── gitlab-ci-guide.md           # GitLab CI mapping guide
│   └── jenkins/
│       └── jenkinsfile-guide.md         # Jenkins mapping guide
├── CLAUDE.md.template                   # CLAUDE.md starter with placeholders
├── FOUNDATION.md                        # What this is and how to use it
├── PLAN.md                              # This document
└── LICENSE
```

---

## Phase 1: Repository Setup and Abstract Principles

### Task 1.1: Create the repo structure

Create all directories listed above. Every directory that starts empty should contain a `.gitkeep` file. Initialize a git repo with `main` as the default branch.

Initial commit message: `chore: initialize claude-project-foundation repository structure`

### Task 1.2: Write FOUNDATION.md

This is the primary README-equivalent. Sections:

**What This Is:** 3-paragraph explanation: reusable scaffold providing (1) interactive spec-crafting phase, (2) autonomous execution phase, (3) quality gates enforcing SDLC best practices. Synthesizes Anthropic's autonomous-coding quickstart, AutoForge spec workflow, and production project experience.

**Quick Start:** Step-by-step: clone repo (or run bootstrap.sh), install hooks, copy .claude/settings.json, run /specforge constitution through /specforge analyze, use initializer prompt for first session, use coding prompt for subsequent sessions.

**Architecture Overview:** Describe the three layers with a diagram showing data flow from constitution through spec through feature_list.json through autonomous implementation.

**Directory Structure:** Tree listing with one-line descriptions.

**Customization:** How to adjust coverage thresholds, add/remove hook checks, add language support, modify spec workflow.

**Design Principles:** No hardcoded project details. All hooks auto-detect or accept configuration. GitHub first-class, other platforms documented. Communication standards: technical, direct, no AI-isms, no emoji, conventional commits.

### Task 1.3: Write ci/principles/commit-gate.md

Abstract requirements every commit must satisfy:

1. **Lint Changed Files:** Run appropriate linter per language (TypeScript: ESLint, Python: Ruff, Rust: clippy, Shell: shellcheck, Go: go vet). Only lint files in the changeset.

2. **No Secrets in Diff:** Scan staged changes for: AWS keys (`AKIA[0-9A-Z]{16}`), OpenAI keys (`sk-[a-zA-Z0-9]{48}`), GitHub tokens (`ghp_`, `gho_`), GitLab tokens (`glpat-`), Slack tokens (`xoxb-`), generic high-entropy strings near keywords (password, secret, token, api_key).

3. **No Forbidden Files:** Block: `.env*`, `*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `credentials.json`, `service-account*.json`, `*.keystore`.

4. **Conventional Commit Format:** Subject matches `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+`. Subject line <= 72 chars. Body lines <= 100 chars (warning).

5. **No AI-isms:** Block (case-insensitive): self-references ("I have", "I've", "I updated", "I fixed"), filler ("Certainly", "I'd be happy to", "As an AI"), marketing adjectives ("seamless", "robust", "powerful", "elegant", "streamlined", "polished", "enhanced", "refined"), AI branding ("Anthropic", "GPT", "OpenAI", "Copilot"), standalone "Claude" (allow "Claude Code" as product name), Co-Authored-By trailers.

6. **No Emoji:** Block Unicode emoji (U+1F300-U+1F9FF, U+2600-U+27BF, related ranges).

7. **No Draft Markers:** Warn (not block): WIP, FIXME, TODO, XXX, DO NOT MERGE, temp, temporary, debug.

### Task 1.4: Write ci/principles/pr-gate.md

All commit gate checks apply to every commit in the PR, plus:

1. **Type Checking:** Full type checker per language (TypeScript: tsc --noEmit, Python: mypy/pyright, Rust: cargo check).
2. **Test Suite:** Full test suite passes with zero failures.
3. **Code Coverage:** Coverage >= configurable threshold (default 85%). Report coverage delta from base branch.
4. **Static Analysis:** ESLint, Ruff lint + format check, cargo clippy -D warnings, cargo fmt --check, shellcheck.
5. **Format Check:** Prettier, Ruff format, cargo fmt, shfmt, gofmt.
6. **Build Verification:** Project builds in clean environment.
7. **No Merge Conflicts.**
8. **Commit Standards:** Every commit in the PR passes all commit gate checks.

### Task 1.5: Write ci/principles/release-gate.md

All PR gate checks apply, plus:

1. **Dependency Audit:** npm audit, pip-audit/safety, cargo audit. No high/critical vulnerabilities.
2. **License Compliance:** All dependencies use approved licenses (MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, 0BSD, Unlicense). Flag GPL, AGPL, unknown for manual review.
3. **Changelog Entry:** CHANGELOG.md entry exists for the version. Keep a Changelog format.
4. **Version Bump:** Version incremented from previous release. SemVer format.
5. **Clean Dependency Tree:** No unused dependencies. No circular chains.

### Task 1.6: Write .specify/templates/constitution-template.md

Guided template with placeholders:

```markdown
# Project Constitution

This document defines immutable principles for the project. These principles
govern all development activity, including autonomous Claude Code sessions.
Once established, these principles do not change without explicit human approval.

## Project Identity

**Project Name:** [PROJECT_NAME]
**One-Line Description:** [DESCRIPTION]
**Primary Language(s):** [LANGUAGES]
**Target Platform(s):** [PLATFORMS]

## Non-Negotiable Principles

List 3-7 principles that must never be violated:

1. [PRINCIPLE_1]
2. [PRINCIPLE_2]
3. [PRINCIPLE_3]

## Quality Standards

### Testing

- Minimum code coverage: [COVERAGE_THRESHOLD]% (default: 85%)
- Test framework: [TEST_FRAMEWORK]
- Test categories required: unit, integration, [ADDITIONAL]

### Code Style

- Linter: [LINTER]
- Formatter: [FORMATTER]
- Type checking: [TYPE_CHECKER] (strict mode: [yes/no])

### Commit Standards

- Format: Conventional Commits (feat, fix, docs, etc.)
- No emoji in commit messages or PR titles
- No AI-isms or self-referential language
- No Co-Authored-By trailers
- Subject line maximum: 72 characters

### Communication Style

- Tone: [TONE]
- Forbidden patterns: [PATTERNS]

## Architectural Constraints

1. [CONSTRAINT_1]
2. [CONSTRAINT_2]
3. [CONSTRAINT_3]

## Security Requirements

1. [SECURITY_1]
2. [SECURITY_2]
3. [SECURITY_3]

## Out of Scope

1. [OUT_OF_SCOPE_1]
2. [OUT_OF_SCOPE_2]
```

---

## Phase 2: Quality Gate Scripts

All scripts generalized from the ai-resume project. Project-specific references removed. Scripts auto-detect project type from configuration files (package.json, Cargo.toml, pyproject.toml, go.mod, etc.).

### Task 2.1: Write .claude/hooks/validate-bash.sh

PreToolUse hook for Bash commands. Reads JSON from stdin, parses the command field. Blocks:

- Destructive: `rm -rf /`, `rm -rf /*`, `rm -rf ~`, `rm -rf $HOME`
- Force push: `git push --force`, `git push -f`, `git push origin.*--force`
- Hard reset: `git reset --hard`, `git clean -fd`, `git checkout .`, `git restore .`
- Permissions: `chmod -R 777`, `chmod 777`
- Disk: `> /dev/sd`, `mkfs.`, `dd if=/dev/zero`, `dd if=/dev/random`
- Fork bomb: `:(){ :|:& };:`
- Environment: `unset PATH`, `PATH=`
- Pipe-to-shell: `curl.*| sh`, `curl.*| bash`, `wget.*| sh`, `wget.*| bash`

Exit 0 if clean, exit 1 if blocked. All patterns are already universal -- no project-specific changes needed.

### Task 2.2: Write .claude/hooks/protect-files.sh

PreToolUse hook for Write/Edit. Reads JSON from stdin, parses file_path. Blocks modification of:

- Environment files: `.env`, `.env.*`
- SSH keys: `id_rsa*`, `id_ed25519*`, `id_ecdsa*`, `authorized_keys`, `known_hosts`
- Certificates: `*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`
- Credentials: `*credentials*`, `*secret*`, `*password*`, `*token*`, `*.keystore`
- Cloud configs: `gcloud-*.json`, `service-account*.json`, `aws-credentials`
- Lock files: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.lock`, `poetry.lock`
- Sensitive directories: `.ssh`, `.gnupg`, `.aws`, `.gcloud`

Exit 0 if allowed, exit 1 if blocked.

### Task 2.3: Write .claude/hooks/validate-pr.sh

PreToolUse hook for `gh pr create` commands. Uses embedded python3 for Unicode handling. Checks PR title/body for:

1. AI branding (with "Claude Code" exemption, parenthetical scope exemption, file path exemption)
2. Co-Authored-By trailers
3. AI-isms (self-references, filler, marketing adjectives)
4. Emoji (full Unicode ranges)

Reports all violations. Exit 2 on violation (Claude Code blocking convention), exit 0 if clean.

### Task 2.4: Write .claude/hooks/post-edit.sh

PostToolUse hook for Write/Edit. Auto-formats based on file extension:

- `*.ts`, `*.tsx`, `*.js`, `*.jsx`, `*.json`, `*.css`, `*.html`, `*.md`: Prettier (discover package.json in project root or common subdirectories: `frontend/`, `web/`, `client/`, `app/`)
- `*.py`: Ruff format + check fix, fallback to Black, fallback to autopep8
- `*.rs`: rustfmt
- `*.sh`: shfmt
- `*.yaml`, `*.yml`: Prettier
- `*.go`: gofmt
- `*.rb`: rubocop -a
- `*.java`, `*.kt`: google-java-format

All formatters wrapped in `|| true` (best-effort, never blocking). All formatters optional (skip silently if not installed). Exit 0 always.

Changes from ai-resume: Remove hardcoded frontend/package.json path. Add generic package.json discovery. Add Go, Ruby, Java/Kotlin support.

### Task 2.5: Write .claude/hooks/verify-quality.sh

Stop hook. Reads JSON from stdin. Checks `stop_hook_active` -- if true, exit 0 immediately (prevents infinite loop).

Auto-detects project structure by scanning project root and one level of subdirectories for:

- `package.json` -> Node.js: ESLint + tsc --noEmit + npm test
- `pyproject.toml` or `requirements.txt` -> Python: Ruff lint + format check + pytest
- `Cargo.toml` -> Rust: cargo check + cargo clippy -D warnings + cargo test --no-run
- `go.mod` -> Go: go vet + go test

Uses `run_check` / `run_optional_check` pattern:

- `run_check` failures increment FAILED counter
- `run_optional_check` failures increment WARNINGS counter
- FAILED > 0: stderr message + exit 2 (blocks stopping)
- WARNINGS only: advisory + exit 0

Changes from ai-resume: Remove all hardcoded service names. Replace with auto-discovery. Support monorepo and single-project repos. Add Go detection. Dynamic venv path discovery.

**Critical:** Use `FAILED=$((FAILED + 1))` not `((FAILED++))` -- the latter fails with `set -e` when FAILED=0.

### Task 2.6: Write scripts/hooks/pre-commit

Git pre-commit hook. Discovers staged files via `git diff --cached --name-only --diff-filter=ACM`.

1. **check_forbidden_files():** Same patterns as protect-files.sh.
2. **check_for_secrets():** Scan staged content (`git show ":$file"`) for secret patterns (AWS, OpenAI, GitHub, GitLab, Slack tokens, generic password/secret/api_key/token assignments).
3. **lint_staged_files():** Auto-detect file types, find nearest project root (directory with package.json/Cargo.toml/pyproject.toml/go.mod), run appropriate linter scoped to that root. Exclude protobuf generated files (`*_pb2.py`, `*_pb2_grpc.py`).

Exit 1 on failure, exit 0 otherwise.

Changes from ai-resume: Remove hardcoded service path prefixes. Add dynamic project root discovery. Add shellcheck and Go support.

### Task 2.7: Write scripts/hooks/commit-msg

Git commit-msg hook. Reads message from `$1`.

1. Empty check (block)
2. Subject length > 72 (warn)
3. Emoji detection via python3 Unicode ranges (block)
4. AI-ism detection: self-references, filler, marketing adjectives, AI branding (block)
5. Standalone "Claude" check: strip "Claude Code", parenthetical scopes, then check for remaining "Claude" (block)
6. Conventional commits format validation (block)
7. Draft markers: WIP, FIXME, TODO, XXX (warn)
8. Co-Authored-By: note (not block)
9. Body line length > 100 (warn)

This is already universal -- carry forward from ai-resume with no structural changes.

### Task 2.8: Write .claude/settings.json

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/post-edit.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/validate-bash.sh"
          },
          {
            "type": "command",
            "command": ".claude/hooks/validate-pr.sh"
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/protect-files.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/verify-quality.sh"
          }
        ]
      }
    ]
  }
}
```

### Task 2.9: Write scripts/install-hooks.sh

Determines project root via `git rev-parse --show-toplevel`. Copies `scripts/hooks/pre-commit` and `scripts/hooks/commit-msg` to `.git/hooks/`. Makes all `.claude/hooks/*.sh` executable. Prints summary.

---

## Phase 3: Spec Workflow and Templates

### Task 3.1: Write .claude/skills/specforge/SKILL.md

The interactive spec workflow skill. User-invocable with seven sub-commands.

**`/specforge constitution`:** Read constitution-template.md, present sections one at a time, ask focused questions for each (Project Identity, Non-Negotiable Principles, Quality Standards, Architectural Constraints, Security Requirements, Out of Scope). Assemble into `.specify/memory/constitution.md`. Present for review.

**`/specforge spec`:** Read constitution. Ask human to describe features in plain language. For each feature area, ask: "What can a user do?", "What happens when it goes wrong?", "What are the edge cases?", "What does success look like?" Group into categories (infrastructure, functional, style, testing). Document with title, description, acceptance criteria, dependencies. Write to `.specify/specs/spec.md`.

**`/specforge clarify`:** Read constitution and spec. Analyze for: ambiguous requirements, missing error handling, undefined edge cases, contradictions, missing non-functional requirements, unstated assumptions. Present each as numbered question with quoted text, why it matters for autonomous implementation, and 2-3 suggested resolutions. Record decisions. Update spec. Repeat until resolved.

**`/specforge plan`:** Read all previous artifacts. Propose technical decisions: project structure, tech stack, data storage, API design, deployment, testing strategy, CI/CD platform. For each: recommendation with rationale, alternatives, trade-offs. Get human approval. Write to `.specify/specs/plan.md`.

**`/specforge features`:** Read all artifacts. For each spec feature, create feature_list.json entry: id (kebab-case), category, title, description, testing_steps (3-15 concrete verifiable steps), passes (false), dependencies. Order by priority (infrastructure first, style last). Validate: acyclic dependency graph, every feature has 3+ steps, 20%+ have 10+ steps, all dependency references resolve. Write to `feature_list.json`.

**`/specforge analyze`:** Score spec for autonomous-readiness on 0-100 scale across five dimensions (weighted):

- Completeness (25%): constitution filled, acceptance criteria for every feature, plan complete, feature_list.json valid
- Testability (25%): concrete testing steps, specific values, sufficient step depth, no vague criteria
- Dependency Quality (15%): no circular deps, wide graph, infrastructure has no deps
- Ambiguity (20%): no unresolved questions, error handling specified, edge cases documented, NFRs quantified
- Autonomous Feasibility (15%): no human-judgment features, no unavailable credentials, programmatic testing

Print score with breakdown. Remediation steps for dimensions < 70. Recommend "ready" if >= 80.

**`/specforge setup`:** Read plan for CI platform. For GitHub (default), generate checklist:

- Branch protection (require PR, status checks, reviews)
- Required status checks (lint, typecheck, test, coverage, commit-standards, summary)
- CODEOWNERS for critical paths
- Dependabot configuration per ecosystem
- CodeQL and secret scanning with push protection
- Squash merge default, auto-delete head branches
- PR and issue templates

Print as actionable steps with `gh` CLI commands where possible.

### Task 3.2: Write .specify/templates/spec-template.md

Feature spec format with sections: Overview, Infrastructure features (no dependencies), Functional features (with Given/When/Then acceptance criteria, error handling, dependencies), Style features (visual, responsive, accessibility criteria), Testing features (coverage criteria).

### Task 3.3: Write .specify/templates/plan-template.md

Technical plan format with sections: Project Structure (directory tree), Tech Stack (frontend, backend, storage, API with rationales), Testing Strategy (unit, integration, e2e with frameworks), Deployment Architecture, Development Environment (init.sh requirements), Architectural Decisions (decision records with context, alternatives, consequences).

### Task 3.4: Write .specify/templates/tasks-template.md

Task breakdown format with: implementation groups ordered by dependency, table per group (task, feature ID, effort S/M/L), effort key definitions, session planning guidance.

### Task 3.5: Write .specify/templates/feature-list-schema.json

JSON Schema for feature_list.json:

- features: array of objects
- Each object: id (kebab-case pattern), category (enum: infrastructure/functional/style/testing), title (5-100 chars), description (10+ chars), testing_steps (array, 3+ items, 10+ chars each), passes (boolean), dependencies (array of kebab-case IDs)
- additionalProperties: false

### Task 3.6: Write .specify/WORKFLOW.md

Tool-agnostic process documentation. Describes:

- Overview: two-phase workflow (interactive planning + autonomous execution)
- Phase 1 (Planning): seven steps with inputs, outputs, participant roles
- Phase 2 (Execution): two-agent pattern (initializer creates infrastructure, coding agent implements features in 10-step loop)
- Artifacts: every file produced, location, format, creator
- Rules: feature_list.json immutability, one feature at a time, regression verification, commit per feature, progress documentation
- Quality Gates: reference to ci/principles/ documents

---

## Phase 4: Execution Harness

### Task 4.1: Write prompts/initializer-prompt.md

First context window prompt. Adapted from Anthropic quickstart, made generic.

**Role:** "You are the initializer agent in a multi-session autonomous development pipeline. Your job is to read the project specification and create foundational artifacts. You do NOT implement features."

**Inputs:** Read in order: constitution, spec, plan, feature_list.json (if exists).

**Task 1 -- Validate Feature List:** If feature_list.json exists, validate against schema, verify dependencies resolve, verify no circular deps. If missing, create from spec.

**Task 2 -- Create init.sh:** Generate idempotent environment setup script: install dependencies, run migrations, start servers, print URLs. Tech stack from plan. Works on macOS and Linux.

**Task 3 -- Initialize Git:** git init (if needed), create .gitignore for tech stack, commit setup files.

**Task 4 -- Create Project Structure:** Directories, placeholder files, config files, README per plan.

**Critical Rules:** Features IMMUTABLE except passes. Do NOT implement features. Leave project buildable. Update claude-progress.txt.

**Completion Checklist:** Constitution/spec/plan read, feature_list.json valid, init.sh exists, git initialized, structure matches plan, claude-progress.txt updated, no uncommitted changes.

### Task 4.2: Write prompts/coding-prompt.md

Subsequent context window prompt. The 10-step loop:

1. **Orient:** pwd, ls, read constitution, read plan, read claude-progress.txt, git log --oneline -20, read feature_list.json
2. **Start Servers:** Run init.sh if needed, verify accessible
3. **Verify Existing:** Test 1-2 previously passing features. Fix regressions FIRST.
4. **Select Feature:** Highest-priority (earliest) where passes=false and all dependencies pass
5. **Implement:** Follow constitution quality standards and plan architecture. Build missing functionality.
6. **Test:** Execute each testing_step. Web: UI testing. Libraries: test runner. CLI: command output.
7. **Update Tracking:** Set passes:true ONLY if ALL steps pass. ONLY modify passes field.
8. **Commit:** git add specific files. Conventional commit message. No AI-isms/emoji/Co-Authored-By.
9. **Document:** Update claude-progress.txt with accomplishments, passing features, issues, next focus, stats.
10. **Clean Shutdown:** All committed, no dangling processes, builds and runs, progress file current.

**Critical Rules:** One feature thoroughly > many started. Fix regressions first. Never modify feature_list.json except passes. Conventional commits. Document blockers and move on if externally blocked. Build missing functionality rather than treating it as a blocker.

### Task 4.3: Write CLAUDE.md.template

Starter CLAUDE.md for new projects with placeholders for:

- Project Overview (description, tech stack)
- Development Workflow (subagent guidance, commands, testing)
- Architecture (project-specific)
- Quality Standards (references foundation hooks and gates)
- Git Commit Guidelines (conventional commits, no AI-isms, no emoji, no Co-Authored-By)
- Communication Style (technical, direct, terse, no AI-isms)

---

## Phase 5: GitHub First-Class Implementation

### Task 5.1: Write ci/github/workflows/ci.yml

Parameterized CI workflow template.

**Trigger:** push to main, pull_request to main, workflow_dispatch.
**Permissions:** `contents: read`, `pull-requests: read`.

**Job: changes** -- `dorny/paths-filter@v3` with commented examples for common structures. Configurable path filters.

**Job: nodejs** (conditional) -- checkout, setup-node (v22), npm ci, lint, typecheck, test, build.

**Job: python** (conditional, commented by default) -- checkout, setup-uv, setup-python (3.12), uv sync, ruff check + format, mypy, pytest with coverage.

**Job: rust** (conditional, commented by default) -- checkout, setup-rust-toolchain, cargo cache, fmt --check, clippy -D warnings, build, test.

**Job: commit-standards** (pull_request only) -- iterate commits between base..head, validate conventional format, emoji, AI-isms, subject length.

**Job: summary** (always runs) -- aggregates all job results. Fails if any required job failed. ONLY job required in branch protection.

Include comments explaining how to enable/disable language jobs and customize paths.

### Task 5.2: Write ci/github/workflows/commit-standards.yml

Standalone commit message validation workflow. Same logic as commit-standards job in ci.yml but as separate file for projects wanting only commit enforcement. Trigger: pull_request only.

### Task 5.3: Write ci/github/CODEOWNERS.template

```
# Quality gate infrastructure
.claude/                    @OWNER
.github/                    @OWNER
scripts/hooks/              @OWNER
ci/                         @OWNER
.specify/memory/            @OWNER

# Security-critical files
*.pem                       @OWNER
*.key                       @OWNER
.env*                       @OWNER
**/security*                @OWNER
```

### Task 5.4: Write ci/github/dependabot.yml

Dependabot config with npm enabled, python/rust/cargo commented, github-actions enabled. Weekly schedule, group minor/patch updates.

### Task 5.5: Write ci/github/PULL_REQUEST_TEMPLATE.md

Sections: Summary (1-3 bullets), Changes (checklist), Test Plan (checklist + "all existing tests pass" + "new tests added"), Checklist (conventional commits, no secrets, docs updated, no AI-isms).

### Task 5.6: Write ci/github/repo-settings.md

GitHub settings checklist with `gh` CLI commands:

- Branch protection on main (require PR, status checks, reviews)
- Required status checks: summary job only
- Squash merge default, auto-delete head branches
- CodeQL for detected languages
- Secret scanning with push protection
- Dependabot: copy dependabot.yml to .github/
- CODEOWNERS: copy template to .github/, replace @OWNER
- PR template: copy to .github/

### Task 5.7: Write ci/gitlab/gitlab-ci-guide.md

Mapping guide: commit gate -> stages/rules, PR gate -> merge request pipelines, release gate -> tagged pipelines, path filtering -> `rules: changes`, required checks -> merge request approvals, CODEOWNERS -> GitLab CODEOWNERS format. Include skeleton .gitlab-ci.yml.

### Task 5.8: Write ci/jenkins/jenkinsfile-guide.md

Mapping guide: commit gate -> pipeline stages, PR gate -> multibranch pipeline, release gate -> release pipeline, path filtering -> changeset condition, required checks -> quality gate plugin. Include skeleton Jenkinsfile.

---

## Phase 6: Bootstrap and Testing

### Task 6.1: Write scripts/bootstrap.sh

Accepts target directory (default: current). Checks for existing git repo. Copies: .specify/, .claude/, scripts/hooks/, scripts/install-hooks.sh, ci/, prompts/, CLAUDE.md.template (rename to CLAUDE.md if none exists). Runs install-hooks.sh. Makes hooks executable. Prints summary and next steps.

Must not overwrite existing files without --force flag. Works on macOS and Linux. Handles spaces in paths. Idempotent.

### Task 6.2: Test bootstrap

Manual verification: create empty directory, run bootstrap.sh, verify all files, verify git init, verify hooks installed, make test commit, verify commit-msg hook fires.

### Task 6.3: Test spec-crafting workflow

Manual verification: invoke /specforge constitution through /specforge analyze, verify all artifacts created in correct locations, verify feature_list.json validates against schema.

### Task 6.4: Test autonomous execution workflow

Manual verification: use initializer prompt for first session, verify it creates feature_list.json/init.sh/project structure. Use coding prompt for second session, verify it orients, selects feature, implements, tests, commits, updates progress.

---

## Implementation Notes

### Hook Behavioral Details (from production experience)

1. **Hook input is JSON via stdin**, not positional arguments. Read with `cat /dev/stdin`.
2. **Stop hooks: exit 2 blocks stopping** (not exit 1). Exit 1 is a hook error.
3. **Stop hooks must check `stop_hook_active` field.** If true, exit 0 immediately (prevents infinite loop).
4. **Stop hooks do NOT support matchers.** They apply globally.
5. **PreToolUse/PostToolUse hooks use matchers.** The `matcher` field accepts patterns like `"Bash"`, `"Write|Edit"`.
6. **Bash arithmetic with `set -e`:** `((VAR++))` when VAR=0 returns exit code 1. Use `VAR=$((VAR + 1))` instead.
7. **`$CLAUDE_PROJECT_DIR` environment variable** is available in hooks, points to project root.

### Git Hook Behavioral Details

1. `.git/hooks/` is not tracked by git. Source copies live in `scripts/hooks/`, installed by `install-hooks.sh`.
2. Pre-commit hook receives no arguments. Discover staged files via `git diff --cached`.
3. Commit-msg hook receives message file path as `$1`.
4. ESLint in pre-commit: avoid `--max-warnings 0` if project uses generated UI components with expected warnings.
5. Monorepo: when cd'ing into subdirectory for linting, adjust file paths to be relative to that subdirectory.

### CI Behavioral Details

1. **Only require the `summary` job in branch protection.** Conditional jobs show as "skipped" when no relevant files changed, blocking PRs if required.
2. **Always add top-level `permissions` block.** CodeQL flags workflows without it.
3. **Node 18 is EOL.** Use Node 20+ or 22+. jsdom 27+ requires Node 20.19+ or 22.12+.
4. **`dorny/paths-filter@v3` requires `pull-requests: read` permission.**
5. **Python CI:** Prefer `uv` over `pip` for speed. Use `astral-sh/setup-uv@v4`.

---

## Dependency Graph

```
Phase 1 (Repo Setup + Principles)
  |
  +--> Phase 2 (Quality Gate Scripts)
  |      |
  |      +--> Phase 3 (Spec Workflow + Templates)
  |             |
  |             +--> Phase 4 (Execution Harness)
  |
  +--> Phase 5 (GitHub Implementation)  [parallel with Phase 3+4]
         |
         +--> Phase 6 (Bootstrap + Testing)  [after Phase 4 + 5]
```

Phase 5 can proceed in parallel with Phases 3 and 4.
Phase 6 requires all other phases.

---

## File Summary

| File                                          | Phase | Description                         |
| --------------------------------------------- | ----- | ----------------------------------- |
| `FOUNDATION.md`                               | 1.2   | Project README                      |
| `PLAN.md`                                     | --    | This document                       |
| `ci/principles/commit-gate.md`                | 1.3   | Abstract commit requirements        |
| `ci/principles/pr-gate.md`                    | 1.4   | Abstract PR requirements            |
| `ci/principles/release-gate.md`               | 1.5   | Abstract release requirements       |
| `.specify/templates/constitution-template.md` | 1.6   | Constitution authoring template     |
| `.specify/templates/spec-template.md`         | 3.2   | Feature spec format                 |
| `.specify/templates/plan-template.md`         | 3.3   | Technical plan format               |
| `.specify/templates/tasks-template.md`        | 3.4   | Task breakdown format               |
| `.specify/templates/feature-list-schema.json` | 3.5   | JSON Schema for feature_list.json   |
| `.specify/WORKFLOW.md`                        | 3.6   | Tool-agnostic process documentation |
| `.claude/settings.json`                       | 2.8   | Hook wiring configuration           |
| `.claude/hooks/validate-bash.sh`              | 2.1   | Block destructive bash patterns     |
| `.claude/hooks/protect-files.sh`              | 2.2   | Block sensitive file modification   |
| `.claude/hooks/validate-pr.sh`                | 2.3   | Enforce PR standards                |
| `.claude/hooks/post-edit.sh`                  | 2.4   | Auto-format on save                 |
| `.claude/hooks/verify-quality.sh`             | 2.5   | Quality gate on stop                |
| `.claude/skills/specforge/SKILL.md`           | 3.1   | Interactive spec workflow skill     |
| `prompts/initializer-prompt.md`               | 4.1   | First context window prompt         |
| `prompts/coding-prompt.md`                    | 4.2   | Subsequent context window prompt    |
| `CLAUDE.md.template`                          | 4.3   | Starter CLAUDE.md                   |
| `scripts/hooks/pre-commit`                    | 2.6   | Git pre-commit hook                 |
| `scripts/hooks/commit-msg`                    | 2.7   | Git commit-msg hook                 |
| `scripts/install-hooks.sh`                    | 2.9   | Hook installation                   |
| `scripts/bootstrap.sh`                        | 6.1   | Foundation installation             |
| `ci/github/workflows/ci.yml`                  | 5.1   | Parameterized CI workflow           |
| `ci/github/workflows/commit-standards.yml`    | 5.2   | Standalone commit validation        |
| `ci/github/CODEOWNERS.template`               | 5.3   | Code ownership template             |
| `ci/github/dependabot.yml`                    | 5.4   | Dependency update config            |
| `ci/github/PULL_REQUEST_TEMPLATE.md`          | 5.5   | PR template                         |
| `ci/github/repo-settings.md`                  | 5.6   | GitHub settings checklist           |
| `ci/gitlab/gitlab-ci-guide.md`                | 5.7   | GitLab CI mapping guide             |
| `ci/jenkins/jenkinsfile-guide.md`             | 5.8   | Jenkins mapping guide               |
| `LICENSE`                                     | 1.1   | License file                        |

**Total: 33 files across 6 phases.**

---

## Source Material for Implementation

When implementing Phase 2 (quality gate scripts), use these files from the ai-resume project as the starting point for generalization:

- `.claude/hooks/verify-quality.sh` -- Most complex hook; replace hardcoded service names with auto-discovery
- `.claude/hooks/validate-pr.sh` -- Python-embedded Unicode/regex validation; carry forward nearly verbatim
- `.claude/hooks/validate-bash.sh` -- Already universal; carry forward as-is
- `.claude/hooks/protect-files.sh` -- Already universal; carry forward as-is
- `.claude/hooks/post-edit.sh` -- Remove hardcoded frontend/ path; add generic discovery + more languages
- `.claude/settings.json` -- Hook wiring pattern; carry forward structure
- `scripts/hooks/pre-commit` -- Remove hardcoded service paths; add dynamic root discovery
- `scripts/hooks/commit-msg` -- Already universal; carry forward as-is
- `.github/workflows/ci.yml` -- Path-filtered monorepo pattern; parameterize for template

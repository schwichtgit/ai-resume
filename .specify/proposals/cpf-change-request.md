# CPF Change Request: Upstream Improvements from ai-resume

**Source project:** schwichtgit/ai-resume (0.1.0-alpha.5 -> 0.1.0-alpha.6)
**Date:** 2026-04-09
**Author:** Frank Schwichtenberg

## Context

During the specforge upgrade from alpha.5 to alpha.6, several
review-tier files were rejected because the downstream project
had more capable versions. This CR proposes upstreaming the
universally applicable patterns so future cpf projects benefit.

---

## 1. CI Workflow Improvements

### 1a. Conditional job execution via paths-filter

**Current scaffold:** All CI jobs run on every push/PR.

**Proposal:** Add `dorny/paths-filter` (or equivalent) to the
CI template so jobs only run when relevant files change. This
is especially valuable for polyglot monorepos but benefits any
project with distinct test/lint scopes.

```yaml
- uses: dorny/paths-filter@v4
  id: changes
  with:
    filters: |
      frontend:
        - 'src/**'
        - 'package.json'
      backend:
        - 'api/**'
        - 'pyproject.toml'
```

**Impact:** Reduces CI minutes, faster feedback on focused PRs.

### 1b. Action version bump: checkout@v4 -> v6

**Current scaffold:** `actions/checkout@v4` in
`commit-standards.yml`.

**Proposal:** Bump to `actions/checkout@v6` across all
workflow templates. The project already uses v6 everywhere.

---

## 2. Dependabot Configuration

### 2a. Conventional commit prefixes

**Current scaffold:** No `commit-message` configuration.

**Proposal:** Add conventional commit formatting to the
dependabot template:

```yaml
commit-message:
  prefix: 'build'
  include: 'scope'
```

**Rationale:** All cpf projects enforce conventional commits
via commit-msg hooks. Without this config, dependabot PRs
fail commit validation or require manual fixup.

### 2b. Grouped minor/patch updates

**Current scaffold:** Has groups but no commit-message config.

**Proposal:** Combine groups with commit-message config so
grouped PRs produce valid conventional commits automatically.

### 2c. Multi-ecosystem template pattern

**Current scaffold:** Only github-actions + npm ecosystems.

**Proposal:** Add commented-out blocks for common ecosystems
(pip, cargo, go) so downstream projects can uncomment what
they need rather than writing from scratch.

---

## 3. Security Workflow Separation

### 3a. Recommend separate workflows per scanner

**Current scaffold:** Ships a standalone `codeql.yml`.

**Proposal:** Document the pattern of keeping scanners in
separate workflows. Benefits:

- **Independent failure modes** -- a Trivy failure does not
  mask a CodeQL result or vice versa
- **Independent triggers** -- CodeQL on every push, container
  scanning only when Dockerfiles/dependencies change
- **Clearer ownership** -- code analysis vs image scanning

Not a structural scaffold change (codeql.yml is already
separate), but worth a best-practices note in
`ci/github/repo-settings.md` for projects that add container
scanning later.

---

## 4. CLAUDE.md Template Enhancements

### 4a. Specforge workflow tracking table

**Current template:** Brief mention of specforge with
workflow order.

**Proposal:** Replace with a structured table showing phases,
commands, artifacts, and status. Downstream projects fill in
status as they progress:

```markdown
| Phase | Command            | Artifact        | Status   |
| ----- | ------------------ | --------------- | -------- |
| 0     | `/specforge const` | constitution.md | [STATUS] |
| 1     | `/specforge spec`  | spec.md         | [STATUS] |
| ...   | ...                | ...             | ...      |
```

### 4b. Subagent delegation policy section

**Current template:** Brief "Subagent Guidance" with a short
list.

**Proposal:** Expand into a structured delegation policy with
three categories:

- **Mandatory delegation** -- tasks that MUST use subagents
  (multi-file changes, security fixes, test suites)
- **Parallelization** -- when to launch parallel subagents
  (independent analyses, no data dependencies)
- **Main conversation only** -- what stays in the main
  context (orchestration, user decisions, quick reads)

This is universally applicable -- all cpf projects benefit
from explicit agent coordination rules.

### 4c. Structured testing documentation

**Current template:** Single `[TEST_COMMAND]` placeholder.

**Proposal:** Expand into subsections:

```markdown
### Unit Tests

- Framework: [UNIT_TEST_FRAMEWORK]
- Test files: [TEST_FILE_PATTERN]
- Run all: [UNIT_TEST_COMMAND]

### E2E Tests (optional)

- Framework: [E2E_FRAMEWORK]
- Prerequisites: [E2E_PREREQUISITES]
- Run: [E2E_COMMAND]
```

### 4d. Quality hooks as a table

**Current template:** Bullet list of hook descriptions.

**Proposal:** Use a table for scannability:

```markdown
| Hook          | Trigger  | Purpose               |
| ------------- | -------- | --------------------- |
| protect-files | Pre-edit | Block sensitive edits |
| validate-bash | Pre-bash | Block destructive rm  |
| ...           | ...      | ...                   |
```

### 4e. Git commit strategy (procedural)

**Current template:** Covers commit message format only.

**Proposal:** Add a "Commit Strategy" subsection covering
the workflow, not just the format:

- Atomic commits with clear messages as you work
- Push individual commits (no squash before push)
- Squash at PR merge time (configured in GitHub)

### 4f. API endpoint reference table (optional)

**Proposal:** Add an optional section for projects with APIs:

```markdown
## API Endpoints

| Method | Path    | Description  |
| ------ | ------- | ------------ |
| GET    | /health | Health check |
| ...    | ...     | ...          |
```

### 4g. Container deployment section (optional)

**Proposal:** Add an optional section for containerized
projects covering build commands, ports, health checks,
and reverse proxy notes. Mark as optional so non-container
projects can delete it.

### 4h. Service-specific environment setup (optional)

**Proposal:** Add an optional section for polyglot projects
documenting per-service environment activation (venvs, nvm,
rustup). Prevents the common mistake of running commands in
the wrong environment.

---

## 5. Markdownlint Configuration

### 5a. Default ignores for common directories

**Current scaffold:** `.markdownlint-cli2.yaml` has minimal
ignores.

**Proposal:** Add default ignores for directories that
commonly contain third-party markdown:

```yaml
ignores:
  - 'node_modules/**'
  - '**/node_modules/**'
  - '.venv/**'
  - '**/.venv/**'
  - '**/target/**'
```

These are universally safe to exclude and prevent lint
failures from vendored/generated content.

---

## 6. Directory Semantics Best Practice

### 6a. Define `.claude/` vs `.specify/` boundaries

**Current state:** Downstream projects accumulate ad-hoc
documents in `.claude/` (plans, cheat sheets, change
requests, security docs) alongside Claude Code tooling
(hooks, settings, skills). The `.specify/` directory is
well-structured but only covers specforge artifacts.

**Proposal:** Document and enforce these conventions:

| Directory             | Purpose                  | Examples                                          |
| --------------------- | ------------------------ | ------------------------------------------------- |
| `.claude/`            | Claude Code tooling only | hooks, settings, skills, PLAN.md (active session) |
| `.specify/memory/`    | Specforge governance     | constitution, versioning strategy                 |
| `.specify/specs/`     | Specforge spec artifacts | spec.md, plan.md                                  |
| `.specify/proposals/` | Pre-spec planning docs   | change requests, ADR drafts, feature proposals    |
| `.specify/templates/` | Specforge templates      | constitution-template, spec-template              |

**Key rules:**

- `.claude/` is for **tooling configuration**, not project
  planning documents
- Session-scoped working docs (restart prompts, cheat sheets)
  should be ephemeral and cleaned up, not committed
- Change requests and proposals that outlive a session belong
  in `.specify/proposals/`
- `.specify/proposals/` feeds the specforge workflow:
  proposals mature into specs via `/cpf:specforge spec`

**Scaffold change:** Add `.specify/proposals/.gitkeep` to the
common scaffold. Add a note in `.specify/WORKFLOW.md`
describing the directory semantics.

---

## Priority Assessment

| Item                           | Impact | Effort | Priority |
| ------------------------------ | ------ | ------ | -------- |
| 2a. Dependabot commit prefixes | High   | Low    | P0       |
| 1b. Checkout v6 bump           | High   | Low    | P0       |
| 5a. Markdownlint ignores       | High   | Low    | P0       |
| 4b. Delegation policy          | High   | Med    | P1       |
| 4c. Testing subsections        | High   | Med    | P1       |
| 4e. Commit strategy            | Med    | Low    | P1       |
| 4d. Hooks table format         | Med    | Low    | P1       |
| 1a. Paths-filter pattern       | High   | Med    | P2       |
| 2c. Multi-ecosystem template   | Med    | Low    | P2       |
| 4a. Specforge tracking table   | Med    | Low    | P2       |
| 3a. Scanner separation docs    | Low    | Low    | P2       |
| 4f. API endpoints section      | Med    | Low    | P3       |
| 4g. Container deployment       | Med    | Med    | P3       |
| 4h. Environment setup          | Med    | Low    | P3       |
| 2b. Grouped updates + commits  | Low    | Low    | P3       |
| 6a. Directory semantics        | High   | Low    | P1       |

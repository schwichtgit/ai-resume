# Workflow Documentation

This document describes the two-phase workflow for spec-driven
autonomous development.

## Overview

**Phase 1 (Interactive Planning):** Human and Claude Code
collaboratively author project specifications through the
`/cpf:specforge` skill. Seven steps, each producing a concrete
artifact.

**Phase 2 (Autonomous Execution):** Two-agent pattern
implements features across multiple Claude Code sessions using
the artifacts from Phase 1.

## Phase 1: Interactive Planning

| Step | Command                       | Input                    | Output                            | Participant    |
| ---- | ----------------------------- | ------------------------ | --------------------------------- | -------------- |
| 1    | `/cpf:specforge constitution` | constitution-template.md | `.specify/memory/constitution.md` | Human + Claude |
| 2    | `/cpf:specforge spec`         | constitution.md          | `.specify/specs/spec.md`          | Human + Claude |
| 3    | `/cpf:specforge clarify`      | constitution.md, spec.md | spec.md (updated)                 | Human + Claude |
| 4    | `/cpf:specforge plan`         | constitution.md, spec.md | `.specify/specs/plan.md`          | Human + Claude |
| 5    | `/cpf:specforge features`     | All artifacts            | `feature_list.json`               | Human + Claude |
| 6    | `/cpf:specforge analyze`      | All artifacts            | Score report (conversation)       | Claude         |
| 7    | `/cpf:specforge setup`        | plan.md                  | Setup checklist (conversation)    | Claude         |

## Phase 2: Autonomous Execution

### Initializer Agent (First Session)

Uses `prompts/initializer-prompt.md`. Creates foundational artifacts:

- Validates feature_list.json against schema
- Creates init.sh (idempotent environment setup)
- Initializes git with .gitignore
- Creates project structure per plan
- Does NOT implement features

### Coding Agent (Subsequent Sessions)

Uses `prompts/coding-prompt.md`. Follows a 10-step loop per session:

1. Orient (read artifacts, check progress)
2. Start servers (run init.sh)
3. Verify existing (test passing features, fix regressions)
4. Select feature (highest priority, deps met, not yet passing)
5. Implement (follow constitution + plan)
6. Test (execute all testing_steps)
7. Update tracking (set passes:true only if ALL steps pass)
8. Commit (conventional format, no AI-isms)
9. Document (update claude-progress.txt)
10. Clean shutdown

## Artifacts

| Artifact     | Location                          | Format     | Created By                  |
| ------------ | --------------------------------- | ---------- | --------------------------- |
| Constitution | `.specify/memory/constitution.md` | Markdown   | /cpf:specforge constitution |
| Spec         | `.specify/specs/spec.md`          | Markdown   | /cpf:specforge spec         |
| Plan         | `.specify/specs/plan.md`          | Markdown   | /cpf:specforge plan         |
| Feature List | `feature_list.json`               | JSON       | /cpf:specforge features     |
| Progress     | `claude-progress.txt`             | Plain text | Coding agent                |

## Branch Workflow

All work must happen on feature branches, not directly on
`main`. The pre-commit hook blocks commits to `main` by
default.

- Create branches from up-to-date main:
  `git fetch origin main && git checkout -b feat/my-feature origin/main`
- The opt-out `CPF_ALLOW_MAIN_COMMIT=1` is for release
  automation and initial project setup only.

## Rules

- **feature_list.json is immutable** except for the `passes`
  field, which only the coding agent may change.
- **One feature at a time.** Complete one thoroughly before starting the next.
- **Regression verification.** Test previously passing features
  before implementing new ones.
- **Commit per feature.** Each completed feature gets its own
  conventional commit.
- **Progress documentation.** Update claude-progress.txt at
  the end of every session.
- **Fix regressions first.** If a previously passing feature
  breaks, fix it before new work.

## MR/PR Workflow

Before any new commit on a branch:

1. `git fetch origin`
2. Check MR/PR state:
   - GitLab: `glab mr view`
   - GitHub: `gh pr view`
3. If the MR/PR is already merged, stop. Create a new
   branch from `origin/main` for the next piece of work.

Do not commit to a branch whose MR/PR has been merged.

Before opening a merge request or pull request:

1. `git fetch origin`
2. `git rebase origin/main` -- resolve any conflicts
3. Verify CI passes on the rebased branch
4. Open the MR/PR

The MR/PR diff must contain only the work introduced by
the branch. If commits already merged into main appear in
the diff, rebase is needed.

## Directory Semantics

These conventions define what belongs in each directory.

| Directory             | Purpose                     | Examples                                       |
| --------------------- | --------------------------- | ---------------------------------------------- |
| `.claude/`            | Claude Code tooling only    | hooks, settings, PLAN.md (session-scoped)      |
| `.specify/memory/`    | Specforge governance        | constitution.md, versioning strategy           |
| `.specify/specs/`     | Specforge spec artifacts    | spec.md, plan.md                               |
| `.specify/proposals/` | Pre-spec planning documents | change requests, ADR drafts, feature proposals |
| `.specify/templates/` | Specforge templates         | constitution-template.md, spec-template.md     |

**Key rules:**

- `.claude/` is for tooling configuration, not project
  planning documents
- Session-scoped working docs (restart prompts, cheat sheets)
  are ephemeral -- do not commit them
- Change requests and proposals that outlive a session belong
  in `.specify/proposals/`
- `.specify/proposals/` feeds the specforge workflow: proposals
  mature into specs via `/cpf:specforge spec`
- `.claude/PLAN.md` is session-scoped, not a persistent
  planning artifact

## Quality Gates

All code changes are subject to quality gates defined in:

- `ci/principles/commit-gate.md` -- Every commit
- `ci/principles/pr-gate.md` -- Every pull request
- `ci/principles/release-gate.md` -- Every release

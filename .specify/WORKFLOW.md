# Workflow Documentation

This document describes the two-phase workflow for spec-driven autonomous development.

## Overview

**Phase 1 (Interactive Planning):** Human and Claude Code collaboratively author project specifications through the `/specforge` skill. Seven steps, each producing a concrete artifact.

**Phase 2 (Autonomous Execution):** Two-agent pattern implements features across multiple Claude Code sessions using the artifacts from Phase 1.

## Phase 1: Interactive Planning

| Step | Command                   | Input                    | Output                            | Participant    |
| ---- | ------------------------- | ------------------------ | --------------------------------- | -------------- |
| 1    | `/specforge constitution` | constitution-template.md | `.specify/memory/constitution.md` | Human + Claude |
| 2    | `/specforge spec`         | constitution.md          | `.specify/specs/spec.md`          | Human + Claude |
| 3    | `/specforge clarify`      | constitution.md, spec.md | spec.md (updated)                 | Human + Claude |
| 4    | `/specforge plan`         | constitution.md, spec.md | `.specify/specs/plan.md`          | Human + Claude |
| 5    | `/specforge features`     | All artifacts            | `feature_list.json`               | Human + Claude |
| 6    | `/specforge analyze`      | All artifacts            | Score report (conversation)       | Claude         |
| 7    | `/specforge setup`        | plan.md                  | Setup checklist (conversation)    | Claude         |

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

| Artifact     | Location                          | Format     | Created By              |
| ------------ | --------------------------------- | ---------- | ----------------------- |
| Constitution | `.specify/memory/constitution.md` | Markdown   | /specforge constitution |
| Spec         | `.specify/specs/spec.md`          | Markdown   | /specforge spec         |
| Plan         | `.specify/specs/plan.md`          | Markdown   | /specforge plan         |
| Feature List | `feature_list.json`               | JSON       | /specforge features     |
| Progress     | `claude-progress.txt`             | Plain text | Coding agent            |

## Rules

- **feature_list.json is immutable** except for the `passes` field, which only the coding agent may change.
- **One feature at a time.** Complete one thoroughly before starting the next.
- **Regression verification.** Test previously passing features before implementing new ones.
- **Commit per feature.** Each completed feature gets its own conventional commit.
- **Progress documentation.** Update claude-progress.txt at the end of every session.
- **Fix regressions first.** If a previously passing feature breaks, fix it before new work.

## Quality Gates

All code changes are subject to quality gates defined in:

- `ci/principles/commit-gate.md` -- Every commit
- `ci/principles/pr-gate.md` -- Every pull request
- `ci/principles/release-gate.md` -- Every release

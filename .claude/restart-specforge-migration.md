# Restart: Specforge Migration -- Phase 4+

Paste everything below the line into a fresh Claude Code session.

---

/mind /specforge /gh-code-scanning

We are migrating ai-resume from its docs-based workflow (PRD.md, ARCHITECTURE.md, TODO.md) to the specforge feature management framework.

**Branch:** `chore/specforge-migration`
**Checkpoint commit:** `7300d4f` -- phases 0-3 complete, clean working tree.
**Pass 2 changes:** uncommitted edits to `feature_list.json` and `data/.gitignore`.

**Master reference:** `docs/SPECFORGE-MIGRATION-PLAN.md` -- read this first. It contains the full migration plan, feature inventory, schema extensions, and CLAUDE.md merge strategy.

## Completed Phases

### Phase 0: Constitution (`/specforge constitution`)

- Written to `.specify/memory/constitution.md`
- All 8 human decisions resolved (TypeScript relaxed, three-container hard constraint, graceful degradation, content/ -> chore/ prefix, future phases out of scope, 10 req/min rate limit, ephemeral-only sessions, multi-language out of scope)

### Phase 1: Spec (`/specforge spec`)

- Written to `.specify/specs/spec.md`
- 118 features: INFRA-001 to INFRA-023, FUNC-001 to FUNC-074, STYLE-001 to STYLE-004, TEST-001 to TEST-017

### Phase 2: Plan (`/specforge plan`)

- Written to `.specify/specs/plan.md`
- Status: **Approved** (all 6 sections reviewed and approved by human)
- 7 ADRs defined

### Phase 3: Features (`/specforge features`) -- Pass 1 + Pass 2 complete

- Written to `feature_list.json` (project root)
- Schema extended: `verified` boolean added to `.specify/templates/feature-list-schema.json`
- **124 features: 28 infrastructure, 74 functional, 5 style, 17 testing**
- 90 brownfield (`verified: false`), 34 greenfield (no `verified` field)
- Validated: schema valid, no circular deps, all dependency refs resolve

**Pass 2 audit completed.** Automated audit + interactive review applied these fixes:

1. `dark-mode` recategorized: functional -> style (74 func, 5 style)
2. Container features given logical dependencies: `frontend-container` (3 deps), `api-service-container` (2 deps), `memvid-service-container` (2 deps)
3. `dark-mode` given `tailwind-design-tokens` dependency
4. `ask-mode-reranking` title updated to "(Partial)" to match description
5. `fit-assessment-ui-tabs` description clarified vs `fit-assessment-component`
6. `outcome-portability` description prefixed "PRD outcome validation:" to distinguish from `data-portability`
7. `data/.gitignore` updated: wildcard `*_resume.md` + `!example_resume.md` (covers master_resume.md, frank_resume.md, any future personal resume)

**Audit false positives** (initially flagged, confirmed correct):

- `proto/memvid/v1/memvid.proto` path exists (audit agent wrong)
- `githooks-core-hookspath` was already greenfield (no `verified` field)
- Feature count was already 124 (audit agent miscounted as 137)

**Resume file convention clarified:**

- `data/master_resume.md` -- expected runtime default (not in git)
- `data/example_resume.md` -- reference template (in git)
- `data/frank_resume.md` -- personal data (local only, gitignored)

## Current Phase: Phase 4

Run `/specforge analyze` to score the spec for autonomous-readiness (target >= 80).

## Remaining Phases

### Phase 5: CLAUDE.md Merge + Coding Prompt Update

- Section 7 of the migration plan contains the full merge plan
- 16 sections mapped with KEEP/MERGE/ADOPT verdicts and a proposed final section order
- Also update coding-prompt.md with brownfield awareness

### Phase 6: Verification Sprint

- Validate brownfield features (90 features with `verified: false`)
- Run testing_steps against existing implementations
- Flip `verified: false` to `verified: true` or mark as needing rework

### Phase 7: Legacy Archive

- Move superseded docs to `docs/archive/`

### Phase 8: Greenfield Implementation

- Implement the 34 greenfield features using feature_list.json as the work queue

## Key File Locations

| File                                          | Purpose                                        |
| --------------------------------------------- | ---------------------------------------------- |
| `docs/SPECFORGE-MIGRATION-PLAN.md`            | Master reference for all phases                |
| `.specify/memory/constitution.md`             | Immutable project principles                   |
| `.specify/specs/spec.md`                      | Full specification (118 features)              |
| `.specify/specs/plan.md`                      | Technical plan (approved)                      |
| `.specify/templates/feature-list-schema.json` | JSON schema with `verified` extension          |
| `feature_list.json`                           | 124 features, validated, Pass 1+2 complete     |
| `data/.gitignore`                             | Wildcard resume ignore pattern                 |
| `docs/ARCHITECTURE.md`                        | Three-container architecture reference         |
| `CLAUDE.md`                                   | Current dev instructions (to merge in Phase 5) |

Start with Phase 4: `/specforge analyze`.

# Phase 7: Greenfield Feature Implementation

We have completed the specforge migration phases 1-6 for ai-resume. All 90 brownfield features are verified. **34 greenfield features remain to be implemented.**

**Branch:** `chore/specforge-migration`

**Master reference:** `docs/SPECFORGE-MIGRATION-PLAN.md`

## Completed Phases

| Phase | Status | Details |
| ----- | ------ | ------- |
| 0-5 | Complete | Constitution, spec, plan, features, analyze, setup |
| 6 | Complete | All 90/90 brownfield features verified |

## Phase 6 Verification Summary (Sessions 1-2)

### Session 1 (78 features verified)

| Batch | Features | Details |
| ----- | -------- | ------- |
| 1 | 9 Tier 1 | testing_step fixes for secrets, CI, parsing features |
| 2 | 4 test infra | frontend (24/24), api-service (91%), memvid (77/77), ingest (70/71) |
| 3 | 3 frontend | footer, loading-states, backend-health-indicator |
| 4 | 3 API | clear-conversation, assess-fit-endpoint, profile-api |
| 6A | 3 ingest | semantic-embedding, mv2-file-creation, ingest-edge-cases |

### Session 2 (12 features verified)

| Batch | Features | Details |
| ----- | -------- | ------- |
| 5 | 7 API core | rate-limiting, mock-streaming, session-management, chat-endpoint, openrouter-client, input-guardrails, output-guardrails |
| 6B | 3 portability | data-portability, container-smoke-tests, portability-test |
| 7 | 2 complex | ai-chat-component, ask-mode-reranking |

### Key Fixes in Session 2

- **Python symlink module aliasing**: `app` symlink to `ai_resume_api` creates separate Python modules with separate global state. Fixed conftest to reset both module aliases for session store and rate limiter.
- **Rate limiter dynamic limit**: Changed `@limiter.limit()` from static f-string to lambda for testability. Added rate limit headers middleware.
- **Unskipped tests**: 5 previously skipped tests (3 rate-limiting + 2 mock-streaming) now pass.

## Test Results (End of Phase 6)

| Service | Tests | Passed | Coverage |
| ------- | ----- | ------ | -------- |
| Frontend | 24 | 24 | -- |
| API Service | 281 | 281 | 91% |
| Memvid Service | 77 | 77 | -- (needs --test-threads=1) |
| Ingest | 73 | 72 | -- (1 hangs: test_full_rag_pipeline, external API) |

All quality checks pass: ESLint, TypeScript, Ruff lint, Ruff format, Cargo check, Cargo clippy.

## Key File Locations

| File | Purpose |
| ---- | ------- |
| `feature_list.json` | 124 features: 90 verified brownfield, 34 greenfield |
| `docs/SPECFORGE-MIGRATION-PLAN.md` | Master reference for all phases |
| `.claude/settings.json` | Hooks: format-changed (Stop), verify-quality (Stop) |
| `CLAUDE.md` | Project instructions |

## Next Steps: Greenfield Implementation

34 greenfield features need implementation. These features have no `verified` field in `feature_list.json` (they are new code, not existing code validation).

### Instructions

1. Read `feature_list.json` and identify the 34 greenfield features (those without a `verified` field)
2. Read `docs/SPECFORGE-MIGRATION-PLAN.md` for phase 7 guidance
3. Prioritize by dependencies and category
4. Implement features, write tests, verify testing_steps pass
5. Update `feature_list.json` as features are completed

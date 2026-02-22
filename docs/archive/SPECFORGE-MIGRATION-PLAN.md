# Specforge Migration Plan

Migration of ai-resume from docs-based workflow (PRD.md, ARCHITECTURE.md, TODO.md) to the specforge feature management and guardrails framework.

**Status:** Planning complete, awaiting Phase 0 execution
**Date:** 2026-02-19
**Branch:** content/frank-resume
**Source framework:** [claude-project-foundation](https://github.com/schwichtgit/claude-project-foundation)
**Reference greenfield:** [Kahi](https://github.com/kahiteam/kahi)

---

## Table of Contents

1. [Background](#1-background)
2. [Brownfield Challenges](#2-brownfield-challenges)
3. [Schema Extension: `verified` Property](#3-schema-extension-verified-property)
4. [Feature Inventory](#4-feature-inventory)
5. [PRD Outcome Codification](#5-prd-outcome-codification)
6. [Constitution Pre-Fill](#6-constitution-pre-fill)
7. [CLAUDE.md Merge Plan](#7-claudemd-merge-plan)
8. [Migration Phases](#8-migration-phases)
9. [Legacy Archive Strategy](#9-legacy-archive-strategy)
10. [Risk Assessment](#10-risk-assessment)

---

## 1. Background

### Current Methodology

ai-resume uses a docs-based development methodology with three core documents:

| Document               | Lines | Role                                                                           |
| ---------------------- | ----- | ------------------------------------------------------------------------------ |
| `docs/PRD.md`          | ~147  | Problem statement, functional/non-functional requirements, acceptance criteria |
| `docs/ARCHITECTURE.md` | ~721  | Three-container architecture, data flow, security design, network topology     |
| `docs/TODO.md`         | ~1471 | Phased roadmap (Phases 1-12), task tracker, changelog                          |

This methodology served well through the initial build (Phases 1-4 complete, Phase 5 partially complete). The project has reached a significant milestone with a working end-to-end system.

### Target Methodology

The specforge workflow produces structured artifacts that enable autonomous implementation:

| Artifact     | Location                          | Purpose                                               |
| ------------ | --------------------------------- | ----------------------------------------------------- |
| Constitution | `.specify/memory/constitution.md` | Immutable project principles                          |
| Spec         | `.specify/specs/spec.md`          | Features with acceptance criteria (Given/When/Then)   |
| Plan         | `.specify/specs/plan.md`          | Technical architecture decisions                      |
| Feature List | `feature_list.json`               | Testable features with dependencies and testing steps |
| Progress     | `claude-progress.txt`             | Per-session progress tracking                         |

### Why Migrate

1. **Structured feature tracking** -- `feature_list.json` replaces markdown checkboxes with typed JSON, dependency graphs, and testing steps
2. **Autonomous execution** -- the coding agent loop (orient, verify, select, implement, test, commit) requires specforge artifacts
3. **Verification gaps** -- many completed features lack adequate test coverage; the specforge testing_steps framework forces explicit verification criteria
4. **PRD acceptance criteria are unmeasured** -- 12 of 42 PRD criteria have zero test coverage, including all three blocking release gates

### What Bootstrap Installed

Running `claude-project-foundation/scripts/bootstrap.sh` on 2026-02-19 created:

| Path                                          | Contents                                                                        |
| --------------------------------------------- | ------------------------------------------------------------------------------- |
| `.specify/WORKFLOW.md`                        | Specforge workflow documentation                                                |
| `.specify/templates/constitution-template.md` | Constitution template                                                           |
| `.specify/templates/spec-template.md`         | Spec template                                                                   |
| `.specify/templates/plan-template.md`         | Plan template                                                                   |
| `.specify/templates/feature-list-schema.json` | JSON Schema for feature_list.json                                               |
| `.specify/templates/tasks-template.md`        | Task breakdown template                                                         |
| `.specify/memory/.gitkeep`                    | Placeholder for constitution                                                    |
| `.specify/specs/.gitkeep`                     | Placeholder for specs                                                           |
| `.specify/specs/spec.md`                      | **Wrong content** (foundation's own spec, not ai-resume's)                      |
| `.claude/skills/specforge/SKILL.md`           | `/specforge` skill definition                                                   |
| `ci/`                                         | CI principles: commit-gate.md, pr-gate.md, release-gate.md + workflow templates |
| `prompts/initializer-prompt.md`               | Initializer agent prompt                                                        |
| `prompts/coding-prompt.md`                    | Coding agent prompt                                                             |
| `CLAUDE.md.template`                          | Generic CLAUDE.md template                                                      |
| `.prettierrc.json`                            | Prettier config                                                                 |
| `.prettierignore`                             | Prettier ignore patterns                                                        |

Existing files were preserved (non-force mode): `.claude/settings.json`, `.claude/hooks/*`, `scripts/hooks/*`, `CLAUDE.md`.

---

## 2. Brownfield Challenges

### Challenge 1: Constitution Must Extract, Not Invent

The constitution template expects fresh definition of principles. For ai-resume, principles already exist scattered across PRD.md, ARCHITECTURE.md, CLAUDE.md, and `.claude/settings.json`. The `/specforge constitution` session must extract from these sources, not start from blank.

### Challenge 2: Hooks Diverge from Foundation

ai-resume's hooks are polyglot-aware with service-specific venv paths. The foundation's hooks are generic with auto-discovery. ai-resume's versions are correct for this project and must be preserved.

| Hook                | ai-resume Version                                      | Foundation Version                 | Resolution     |
| ------------------- | ------------------------------------------------------ | ---------------------------------- | -------------- |
| `protect-files.sh`  | 122 lines, detailed pattern matching                   | 66 lines, different JSON parsing   | Keep ai-resume |
| `verify-quality.sh` | 143 lines, hardcoded service paths with venv awareness | ~150 lines, generic auto-discovery | Keep ai-resume |
| `validate-bash.sh`  | 93 lines                                               | Similar                            | Keep ai-resume |
| `post-edit.sh`      | 81 lines                                               | Similar                            | Keep ai-resume |
| `validate-pr.sh`    | 133 lines                                              | Similar                            | Keep ai-resume |

### Challenge 3: Wrong spec.md Content

Bootstrap copied the foundation's own spec (specforge-plugin project) into `.specify/specs/spec.md`. Must be deleted and replaced with ai-resume content.

### Challenge 4: TODO.md Dual Role

The 1471-line TODO.md serves as both feature tracker (checkbox items) and historical changelog (timestamps, commit SHAs, implementation notes). Specforge replaces function (1) with `feature_list.json`. Function (2) needs preservation via archive.

### Challenge 5: Document Mapping

| Specforge Artifact  | Existing ai-resume Doc         | Overlap                                                        |
| ------------------- | ------------------------------ | -------------------------------------------------------------- |
| `constitution.md`   | CLAUDE.md + PRD.md constraints | Partial                                                        |
| `spec.md`           | PRD.md functional requirements | Partial -- PRD lacks Given/When/Then format                    |
| `plan.md`           | ARCHITECTURE.md                | High overlap -- ARCHITECTURE.md is more detailed               |
| `feature_list.json` | TODO.md                        | Partial -- TODO has phases, not feature IDs with testing steps |

### Challenge 6: Initializer/Coding Prompts Assume Greenfield

`prompts/initializer-prompt.md` expects to create project structure from scratch. For ai-resume, the initializer step is moot. The coding agent loop starts mid-stream.

---

## 3. Schema Extension: `verified` Property

### Problem

In greenfield specforge, `passes` means "has this feature been implemented and tested?" In brownfield, many features ARE implemented but haven't been verified against specforge-level acceptance criteria. We need to distinguish:

- Feature not implemented at all
- Feature implemented but not verified (brownfield migration)
- Feature implemented AND verified against acceptance criteria

### Solution

Add an optional `verified` boolean property to `feature-list-schema.json`:

```json
"verified": {
  "type": "boolean",
  "description": "Brownfield migration status. When present and false, indicates an existing implementation that has not been validated against specforge testing_steps. When true, the implementation has been explicitly verified. Absent for greenfield features."
}
```

### State Matrix

| `passes` | `verified` | Meaning                                         |
| -------- | ---------- | ----------------------------------------------- |
| `false`  | _(absent)_ | Greenfield -- not implemented                   |
| `false`  | `false`    | Brownfield -- implemented but not yet validated |
| `true`   | `true`     | Brownfield -- validated and confirmed working   |
| `true`   | _(absent)_ | Greenfield -- implemented and passing           |
| `false`  | `true`     | INVALID -- verified implies passes              |
| `true`   | `false`    | INVALID -- passes without verification          |

**Invariant:** `verified: true` implies `passes: true`. Both flip simultaneously on successful verification.

### Brownfield Feature Lifecycle

```text
CATALOGED ───[run testing_steps]───> VERIFIED/PASSING
  (passes:false, verified:false)       (passes:true, verified:true)
       |                                      |
       └──[steps fail]──> NEEDS FIX ──[fix]──┘
```

### Coding Agent Modifications

Changes required to `prompts/coding-prompt.md`:

**Step 4 (Select Feature):** Prioritize `verified: false` features (verification tasks) over greenfield features (implementation tasks). Verification is faster and unlocks dependency chains.

**Step 5 (Implement):** Conditional behavior:

- If `verified: false`: READ existing implementation first. Do NOT rebuild from scratch. Run testing_steps against existing code. Fix gaps only if tests reveal actual failures.
- If no `verified` field: Build from scratch per constitution and plan.

**Step 7 (Update Tracking):** Extend field modification rule from "only modify `passes`" to "only modify `passes` and `verified`".

---

## 4. Feature Inventory

### Summary

| Category       | Total   | Passes (est.) | Needs Tests | Not Implemented |
| -------------- | ------- | ------------- | ----------- | --------------- |
| Infrastructure | 23      | ~14           | ~6          | ~3              |
| Functional     | 57      | ~25           | ~20         | ~12             |
| Style          | 4       | ~2            | ~2          | 0               |
| Testing        | 7       | ~4            | ~1          | ~2              |
| **Total**      | **~91** | **~45**       | **~29**     | **~17**         |

Plus 10 PRD outcome features (category: testing), bringing the total to ~101 features.

### Infrastructure Features (23)

| ID                         | Title                                               | Status   | Tests                                 |
| -------------------------- | --------------------------------------------------- | -------- | ------------------------------------- |
| `project-structure`        | Project Directory Structure and Monorepo Layout     | Complete | None (structural)                     |
| `prd-and-design-docs`      | PRD, Architecture, and Design Documentation         | Complete | None (docs)                           |
| `toml-config-schema`       | TOML Configuration Schema                           | Complete | `test_config.py` (20 tests)           |
| `podman-network-design`    | Podman Yellow Zone Network Architecture             | Complete | None (infra)                          |
| `secrets-management`       | Environment Variable Secrets Management             | Complete | `test_config.py` covers env loading   |
| `deployment-scripts`       | Deployment Scripts (deploy.sh, dev-setup.sh)        | Complete | `test-containers.sh` (6 smoke tests)  |
| `build-automation`         | Multi-Arch Container Build Scripts                  | Complete | Smoke tested                          |
| `python-venv-isolation`    | Isolated Python Virtual Environments per Service    | Complete | None (manual)                         |
| `function-based-naming`    | Function-Based Service Directory Naming             | Complete | None (structural)                     |
| `python-package-naming`    | Fully-Qualified Python Package Name (ai_resume_api) | Complete | All api-service tests use new imports |
| `proto-definition`         | gRPC Protobuf Definition (memvid.v1)                | Complete | memvid: 16 tests, api: 24 tests       |
| `frontend-container`       | Frontend nginx + React Container (53 MB)            | Complete | Smoke tested                          |
| `api-service-container`    | Python API Service Container (192 MB)               | Complete | Smoke tested                          |
| `memvid-service-container` | Rust Memvid gRPC Container (97 MB)                  | Complete | Smoke tested                          |
| `readonly-containers`      | Read-Only Filesystem with tmpfs Mounts              | Complete | None (runtime)                        |
| `stdout-logging`           | All Services Log to stdout/stderr                   | Complete | None (runtime)                        |
| `health-check-endpoints`   | Health Check Endpoints (all services)               | Complete | `test_main.py`, memvid integration    |
| `vite-dev-proxy`           | Vite Development Proxy for /api Routes              | Complete | None                                  |
| `nginx-spa-routing`        | Nginx SPA Routing and Asset Caching                 | Complete | None                                  |
| `git-hooks`                | Pre-commit and Commit-msg Git Hooks                 | Complete | None                                  |
| `ci-workflows`             | GitHub CI Workflows (lint, test, build)             | Complete | None                                  |
| `ingest-venv-setup`        | Ingest Pipeline UV Environment Setup                | Complete | None                                  |
| `compose-yaml`             | Podman Compose Deployment Configuration             | Complete | `test-containers.sh`                  |

### Functional Features (57)

| ID                              | Title                                           | Status   | Tests                                                           |
| ------------------------------- | ----------------------------------------------- | -------- | --------------------------------------------------------------- |
| `markdown-frontmatter-parsing`  | YAML Frontmatter Parsing from Resume Markdown   | Complete | `test_parsing.py` (6 tests)                                     |
| `section-extraction`            | Markdown Section Extraction (## headings)       | Complete | `test_parsing.py` (5 tests)                                     |
| `experience-chunk-parsing`      | Experience Entry Parsing with AI Context        | Complete | `test_parsing.py` (6 tests)                                     |
| `skills-parsing`                | Skills Section Parsing (strong/moderate/gaps)   | Complete | `test_parsing.py` (4 tests)                                     |
| `faq-parsing`                   | FAQ Chunk Extraction with Keywords              | Complete | `test_parsing.py` (4 tests)                                     |
| `failure-story-parsing`         | Failure Story Extraction                        | Complete | `test_parsing.py` (3 tests)                                     |
| `fit-assessment-parsing`        | Fit Assessment Example Parsing                  | Complete | `test_parsing.py` (5 tests)                                     |
| `semantic-embedding`            | all-mpnet-base-v2 Embedding Generation          | Complete | `test_embeddings.py` (1 test)                                   |
| `mv2-file-creation`             | .mv2 File Generation with Hybrid Search         | Complete | `test_memvid.py` (3), `test_e2e.py` (3)                         |
| `ingest-retrieval-verification` | Ingestion Retrieval Quality Verification        | Complete | `test_ingest_retrieval.py` (3 tests)                            |
| `ingest-edge-cases`             | Ingest Pipeline Edge Case Handling              | Complete | `test_ingest_edge_cases.py` (21 tests)                          |
| `profile-in-memvid`             | Profile Metadata Stored Inside .mv2 File        | Complete | `test_config.py` profile loading                                |
| `profile-api`                   | GET /api/v1/profile Endpoint                    | Complete | `test_main.py` (partial)                                        |
| `suggested-questions-api`       | GET /api/v1/suggested-questions Endpoint        | Complete | `test_main.py` (partial)                                        |
| `chat-endpoint`                 | POST /api/v1/chat Endpoint                      | Complete | `test_main.py` (46 tests), `test_integration.py` (4)            |
| `streaming-sse`                 | Server-Sent Events Streaming Responses          | Complete | `test_main.py`, `test_integration.py`                           |
| `mock-streaming`                | Mock Streaming for Local Development            | Complete | `test_main.py`                                                  |
| `openrouter-client`             | OpenRouter LLM Client with Streaming            | Complete | `test_openrouter_client.py` (35 tests)                          |
| `session-management`            | In-Memory Session Store with TTL                | Complete | `test_session_store.py` (14 tests)                              |
| `rate-limiting`                 | Per-IP Rate Limiting with slowapi               | Complete | `test_main.py` covers rate limits                               |
| `grpc-memvid-client`            | gRPC Client to Rust Memvid Service              | Complete | `test_memvid_client.py` (16), `test_memvid_client_grpc.py` (24) |
| `grpc-memvid-server`            | Rust gRPC Server with Search RPC                | Complete | `grpc/service.rs` (16), `main_integration_tests.rs` (27)        |
| `mock-searcher`                 | Mock Memvid Searcher for Testing                | Complete | `memvid/mock.rs` (7 tests)                                      |
| `real-memvid-searcher`          | Real memvid-core .mv2 File Loading              | Complete | `memvid/real.rs` (13 tests)                                     |
| `prometheus-metrics-api`        | Prometheus Metrics Endpoint (API Service)       | Complete | `test_main.py` (partial)                                        |
| `prometheus-metrics-memvid`     | Prometheus Metrics Endpoint (Memvid :9090)      | Complete | `metrics.rs` (7 tests)                                          |
| `structured-logging-api`        | Structured Logging with structlog (API Service) | Complete | None (operational)                                              |
| `structured-logging-memvid`     | Structured JSON Logging with tracing (Memvid)   | Complete | None (operational)                                              |
| `trace-id-propagation`          | X-Trace-ID Header Propagation                   | Complete | None                                                            |
| `llm-specific-metrics`          | LLM-Specific Prometheus Metrics                 | Complete | None                                                            |
| `input-guardrails`              | Prompt Injection Input Detection                | Complete | `test_guardrails.py` (25 tests)                                 |
| `output-guardrails`             | Internal Structure Leakage Output Filtering     | Complete | `test_guardrails.py` (included)                                 |
| `system-prompt-hardening`       | Defensive System Prompt in Resume Data          | Complete | None (content-level)                                            |
| `api-client-frontend`           | Frontend API Client (api-client.ts)             | Complete | `api-client.test.ts` (23 assertions)                            |
| `streaming-chat-hook`           | useStreamingChat Custom React Hook              | Complete | None                                                            |
| `profile-hook`                  | useProfile Custom React Hook                    | Complete | `useProfile.test.ts` (11 assertions)                            |
| `ai-chat-component`             | AIChat Component with Real API Integration      | Complete | None                                                            |
| `hero-component`                | Hero Section Component (Data-Driven)            | Complete | None                                                            |
| `experience-component`          | Experience Section Component (Data-Driven)      | Complete | None                                                            |
| `fit-assessment-component`      | Hybrid Fit Assessment Component                 | Complete | None                                                            |
| `header-component`              | Header Component (Data-Driven)                  | Complete | None                                                            |
| `footer-component`              | Footer Component (Data-Driven)                  | Complete | None                                                            |
| `dynamic-meta-tags`             | Dynamic HTML Meta Tags from Profile API         | Complete | `useProfile.test.ts` (5 meta-tag tests)                         |
| `seo-lua-handler`               | Lua-Based SEO Handler for Bot Rendering         | Complete | None                                                            |
| `assess-fit-endpoint`           | POST /api/v1/assess-fit Real-Time AI Analysis   | Complete | `test_main.py` covers endpoint                                  |
| `role-classifier`               | Multi-Domain Role Classifier for Fit Assessment | Complete | `test_role_classifier_e2e.py` (35 tests, 96%)                   |
| `query-transform`               | Query Transformation for Memvid Search          | Complete | `test_query_transform.py` (12 tests)                            |
| `pydantic-models`               | Pydantic Request/Response Models                | Complete | `test_models.py` (24 tests)                                     |
| `data-portability`              | Single-File Portability (.mv2 Only)             | Complete | `scripts/test_portability.py`                                   |
| `fit-assessment-ui-tabs`        | Three-Tab Fit Assessment UI                     | Complete | None                                                            |
| `error-display-retry`           | Error Display with Retry in Chat UI             | Complete | None                                                            |
| `loading-states`                | Loading States Throughout UI                    | Complete | None                                                            |
| `cancel-streaming`              | Cancel Streaming Button in Chat                 | Complete | None                                                            |
| `clear-conversation`            | Clear Conversation Button in Chat               | Complete | None                                                            |
| `suggested-questions-ui`        | Dynamic Suggested Questions from Backend        | Complete | None                                                            |
| `backend-health-indicator`      | Backend Health Indicator in Chat UI             | Complete | None                                                            |
| `ask-mode-reranking`            | Ask Mode with Cross-Encoder Re-Ranking          | Partial  | Limited                                                         |

### Not-Implemented Features (17)

| ID                         | Title                                          | Source      |
| -------------------------- | ---------------------------------------------- | ----------- |
| `edge-deployment`          | Edge Server Deployment (ARM64)                 | Phase 5     |
| `error-boundaries`         | Component-Level Error Boundaries               | Phase 3     |
| `a11y-improvements`        | Accessibility Improvements                     | Phase 3     |
| `fit-assessment-dynamic`   | Dynamic Fit Assessment from Config             | Phase 3     |
| `config-driven-ui`         | Theme and Section Visibility from Config       | Phase 3     |
| `vulnerability-scanning`   | Container Vulnerability Scanning (grype/trivy) | Phase 6     |
| `load-testing`             | Load Testing (<100 Concurrent Chats)           | Phase 6     |
| `performance-profiling`    | Performance Profiling (P95 <2s, memvid <5ms)   | Phase 6     |
| `injection-test-scenarios` | Automated Prompt Injection Testing             | Phase 5.5   |
| `post-stream-leakage`      | Post-Stream Output Leakage Detection           | Phase 5.5   |
| `documentation-audit`      | Complete Documentation Verification            | Phase 6     |
| `dark-mode`                | Dark Mode UI                                   | Phase 9     |
| `conversation-persistence` | Conversation History Persistence               | Phase 9     |
| `mobile-responsive`        | Mobile-Responsive Design Improvements          | Phase 9     |
| `ontology-knowledge-graph` | Ontology-Based Knowledge Graph RAG             | Phase 10/12 |

### Style Features (4)

| ID                       | Title                                                 | Status   |
| ------------------------ | ----------------------------------------------------- | -------- |
| `tailwind-design-tokens` | Tailwind CSS Design Tokens and Custom Theme           | Complete |
| `custom-animations`      | Custom CSS Animations (fade-in, slide-up, pulse-soft) | Complete |
| `shadcn-ui-components`   | shadcn/ui Component Library Integration               | Complete |
| `single-page-scroll`     | Single-Page App with Smooth Scroll Sections           | Complete |

### Testing Infrastructure Features (7)

| ID                          | Title                                        | Status      | Details                                    |
| --------------------------- | -------------------------------------------- | ----------- | ------------------------------------------ |
| `frontend-test-infra`       | Frontend Vitest + jsdom Test Infrastructure  | Complete    | 3 test files, ~36 assertions               |
| `api-service-test-infra`    | API Service pytest + Coverage Infrastructure | Complete    | 11 test files, 255 functions, 80% coverage |
| `memvid-service-test-infra` | Memvid Service Rust Test Infrastructure      | Complete    | 77 tests, 7 files, 88.77% coverage         |
| `ingest-test-infra`         | Ingest Pipeline pytest Test Infrastructure   | Complete    | 8 test files, 71 functions                 |
| `container-smoke-tests`     | Container Smoke Tests (test-containers.sh)   | Complete    | 6 smoke tests                              |
| `portability-test`          | Portability Validation Script                | Complete    | 1 script                                   |
| `e2e-quality-acceptance`    | End-to-End Data Exposure Quality Acceptance  | Not Started | None                                       |

### Test Coverage Gaps

**Frontend (critical gap):** Zero component tests for AIChat (282 lines), FitAssessment (408 lines), Experience/ExperienceCard (234 lines), Hero, Header, Footer (266 lines), useStreamingChat hook, Index page.

**API Service:** `observability.py` has no dedicated tests. Potential stale imports in `test_guardrails.py` (`from app.guardrails` vs `from ai_resume_api.guardrails`).

**Cross-service/E2E:** Zero end-to-end tests exercising Browser -> Frontend -> API -> Memvid -> API -> Browser. PRD "End-to-End Quality Acceptance Criteria" entirely untested.

---

## 5. PRD Outcome Codification

### PRD Compliance Assessment

Of 42 discrete acceptance criteria in the PRD:

| Status              | Count | Details                                                                |
| ------------------- | ----- | ---------------------------------------------------------------------- |
| Met                 | 13    | All data requirements, most MVP functional, constraints                |
| Partially Met       | 4     | Mobile responsive, honesty, E2E data coverage, memory                  |
| Not Measured        | 12    | All NFRs, all success metrics, all E2E quality gates, negative testing |
| Not Met             | 2     | Conversation persistence, analytics                                    |
| Implicit (untested) | 11    | Within E2E block, zero test coverage                                   |

### Blocking Release Gates (Zero Test Coverage Today)

| Gate               | Target                  | Current Status             |
| ------------------ | ----------------------- | -------------------------- |
| Category coverage  | 100% (10/10 categories) | `test_e2e.py` covers 5/10  |
| Factual accuracy   | 100%                    | No automated fact-checking |
| Hallucination rate | 0%                      | No hallucination detection |

### Proposed PRD Outcome Features (10)

These are category: `testing` features that validate PRD acceptance criteria:

#### `outcome-data-coverage`

All 10 resume fact categories retrievable through natural language queries.

Testing steps:

1. Load `.mv2` and verify >= 10 frames of chunked content
2. For each of 10 PRD categories (Profile, Experience Timeline, Technical Skills, Accomplishments, Security, AI/ML, Leadership, Failures, Honest Limitations, Fit Scenarios), send validation query and verify top-3 results contain expected terms
3. Assert 100% category coverage (10/10)
4. Generate coverage report

#### `outcome-factual-accuracy`

LLM responses contain only facts present in the source resume.

Testing steps:

1. Parse `data/example_resume.md` into structured ground truth JSON
2. Send 5+ recruiter-style questions to `POST /api/v1/chat`
3. Extract factual claims from responses (companies, dates, metrics, skills)
4. Assert every claim appears in ground truth (0 hallucinated facts)
5. Log unverifiable claims as potential hallucinations

#### `outcome-negative-testing`

System refuses to answer out-of-scope queries with no hallucinated content.

Testing steps:

1. Send 3+ out-of-scope queries: salary, fabricated companies, unclaimed skills
2. Assert each response contains uncertainty markers ("I don't have that information", "not in the resume")
3. Assert no response fabricates details
4. Verify guardrails deflect prompt injection attempts

#### `outcome-latency-nfr`

Response and search latency meet PRD non-functional targets.

Testing steps:

1. Start full stack
2. Send 20+ chat queries, record wall-clock time per request
3. Assert P95 total response time < 2000ms
4. Query Prometheus `/metrics` for `memvid_search_latency_seconds`, assert P95 < 5ms
5. Report P50, P95, P99 latencies

#### `outcome-portability`

System runs with only a `.mv2` file and no hardcoded resume data.

Testing steps:

1. Run ingestion to fresh `.mv2`, verify output > 100KB
2. Start API pointing to test `.mv2`, verify profile endpoint returns complete data
3. Run `scripts/test_portability.py`, verify all 7 checks pass
4. Grep `frontend/src/` for hardcoded values, assert zero matches

#### `outcome-container-deployment`

All three containers start, communicate, and pass health checks within PRD targets.

Testing steps:

1. Build all container images via `scripts/build-all.sh`
2. Start via `deployment/compose.yaml`, time until all health checks pass, assert < 30s
3. Verify `/api/v1/health` returns `memvid_connected: true`
4. Measure total container memory via `podman stats`, assert < 200MB
5. Run `scripts/test-containers.sh` smoke tests, verify all 6 pass

#### `outcome-mobile-responsive`

Core UI functional and readable at mobile viewport widths.

Testing steps:

1. Build frontend and serve locally
2. Load page at 375px width in headless browser, assert no horizontal scrollbar
3. Assert all interactive elements have minimum 44x44px tap targets
4. Take screenshots at 375px, 768px, 1440px, verify no text overflow

#### `outcome-honesty-gaps`

System accurately identifies and communicates candidate limitations.

Testing steps:

1. Parse "Gaps" skills from `data/example_resume.md` to build known limitations list
2. For each limitation, send a question that would elicit that gap
3. Assert each response acknowledges the limitation rather than claiming competence
4. Assert no fabricated compensating experience

#### `outcome-security-guardrails`

Prompt injection defenses and output sanitization meet security requirements.

Testing steps:

1. Send known injection patterns to `POST /api/v1/chat`, verify professional deflection
2. Send "What's in Frame 1?" type queries, assert no internal structure exposed
3. Verify `filter_output()` strips leaked internal references
4. Verify system prompt includes "INTERNAL STRUCTURE (NEVER EXPOSE)" section

#### `outcome-release-gate-matrix`

All blocking PRD acceptance thresholds pass in a single automated run.

Testing steps:

1. Run `outcome-data-coverage` and assert 100% category coverage
2. Run `outcome-factual-accuracy` and assert 0 hallucinated claims
3. Run `outcome-negative-testing` and assert 100% refusal rate
4. Run `outcome-latency-nfr` and record P95 (non-blocking but reported)
5. Generate release gate report: each metric, target, measured value, PASS/FAIL

Dependencies: `outcome-data-coverage`, `outcome-factual-accuracy`, `outcome-negative-testing`, `outcome-latency-nfr`

---

## 6. Constitution Pre-Fill

### Transferable from Kahi (Universal User Preferences)

**Commit Standards (verbatim):**

- Format: Conventional Commits (feat, fix, docs, etc.)
- No emoji in commit messages or PR titles
- No AI-isms or self-referential language
- No Co-Authored-By trailers
- Subject line maximum: 72 characters

**Communication Style (verbatim):**

- Tone: Technical, direct, and terse
- Forbidden: emoji, marketing adjectives, filler words, self-referential language

**Branching Workflow (verbatim):**

- All changes via PR only, no direct commits to `main`
- Conventional prefixes: feat/, fix/, docs/, ci/, refactor/, test/, chore/
- Branch protection on `main` as deployment prerequisite

**Versioning (adapted -- FIPS removed):**

- Semantic Versioning 2.0.0
- Pre-release tags: -alpha.N, -beta.N, -rc.N

**Testing threshold (transferred):**

- Minimum code coverage: 85% per service

**Graceful degradation (pattern transferred, specifics adapted):**

- If memvid or LLM unavailable, core profile display continues

### Project-Specific Items (from ai-resume docs)

**Project Identity:**

- Project Name: ai-resume -- AI-powered interactive resume agent
- One-Line Description: Polyglot web application enabling recruiters to query a candidate's experience via AI chat with semantic search retrieval
- Primary Languages: TypeScript (React 18), Python 3.12 (FastAPI), Rust 1.84 (memvid gRPC)
- Target Platforms: Linux (amd64, arm64), macOS (amd64, arm64 -- development only)

**Non-Negotiable Principles:**

1. Single-file data portability -- ALL instance content from a single `.mv2` file generated from markdown. No hardcoded data in application code.
2. Zero hallucination tolerance -- never fabricate companies, dates, metrics, or skills not in the source resume. 100% factual accuracy is a blocking release gate.
3. Honest gap identification -- accurately report what the candidate cannot do. No overselling.
4. Edge-deployable -- runs on ARM64 with 4GB RAM, <200MB memory, no external database.
5. API keys via environment variables only -- no secrets in images, git, or config files.
6. Graceful degradation -- if memvid or LLM unavailable, core profile display continues.

**Quality Standards:**

- Test frameworks: Vitest + RTL (frontend), pytest (Python), cargo test (Rust)
- Test categories: unit, integration, end-to-end
- E2E quality gate: 100% category coverage, 100% factual accuracy, 0% hallucination
- Code style per language:

| Language   | Linter               | Formatter   | Type Checker       |
| ---------- | -------------------- | ----------- | ------------------ |
| TypeScript | ESLint               | Prettier    | tsc (relaxed mode) |
| Python     | Ruff                 | Ruff format | mypy/pyright       |
| Rust       | Clippy `-D warnings` | cargo fmt   | cargo check        |
| Shell      | ShellCheck           | shfmt       | N/A                |

**Architectural Constraints:**

1. Three-container architecture -- Frontend (nginx + React), API (Python FastAPI), Memvid (Rust gRPC). Single responsibility per container.
2. Frontend as router -- application-level URL routing in frontend nginx. Host nginx handles TLS termination and domain routing only.
3. gRPC internal, REST/SSE external -- Rust memvid exposes gRPC. Python API exposes REST/JSON + SSE streaming to browsers.
4. Stateless containers -- no instance data in images. `.mv2` files and config mounted as read-only volumes.
5. LLM via OpenRouter -- all LLM calls through OpenRouter API. No direct model hosting.
6. Isolated Python venvs -- each Python service has its own `.venv` with independent dependencies.

**Security Requirements:**

1. Multi-layer prompt injection defense -- input validation, structural separation, defensive system prompt, output filtering. All four layers required.
2. No secrets in containers or git -- API keys via env vars, `.env` in `.gitignore`, validated at startup, never logged.
3. Rootless read-only containers -- non-root users, read-only filesystems, `no-new-privileges`.
4. Network zone isolation -- containers in dedicated subnet, firewall prevents cross-zone traffic.
5. Rate limiting on all API endpoints -- per-IP throttling, 429 responses.
6. Dependency vulnerability scanning -- Grype scans, critical/high CVEs patched within 7 days.
7. Commit-gate secret scanning -- block commits containing API keys, tokens, high-entropy strings.

**Out of Scope:**

1. User authentication -- public resume, no login
2. Multi-user / multi-resume support -- single candidate per instance
3. Real-time resume editing -- content changes require re-ingestion
4. ATS integration -- no applicant tracking system connectors
5. Windows deployment -- Linux containers only
6. Direct model hosting -- no on-device LLM inference

### Questions for Human (During `/specforge constitution`)

1. TypeScript strictness: codify current relaxed mode or aspire to strict?
2. Container count: hard "three" or flexible "well-defined service boundaries"?
3. Graceful degradation specifics: what fallback when memvid is down?
4. Branch prefix `content/`: keep as-is, or map to `docs/` or `chore/`?
5. Future phases (voice, multi-agent, auth): constitutionally out of scope or open?
6. Rate limit: specific number (10 req/min) or "configurable threshold required"?
7. Conversation persistence: constitutional prohibition or future-phase allowance?
8. Multi-language content: out of scope?

---

## 7. CLAUDE.md Merge Plan

### Section Comparison

| #   | Section                        | Source         | Verdict                                                           |
| --- | ------------------------------ | -------------- | ----------------------------------------------------------------- |
| 1   | Project Overview               | Both           | MERGE -- adopt Kahi's structured format, keep ai-resume content   |
| 2   | Feature Development Workflow   | Kahi only      | ADOPT -- core specforge integration, entirely missing             |
| 3   | Subagent Policy                | Both           | MERGE -- Kahi's 3-tier structure, ai-resume's specific categories |
| 4   | Commands                       | ai-resume only | KEEP                                                              |
| 5   | Testing                        | ai-resume only | KEEP                                                              |
| 6   | Virtual Environments           | ai-resume only | KEEP                                                              |
| 7   | Architecture (all subsections) | ai-resume only | KEEP                                                              |
| 8   | TypeScript Configuration       | ai-resume only | KEEP                                                              |
| 9   | State Management               | ai-resume only | KEEP                                                              |
| 10  | Browser Router                 | ai-resume only | KEEP                                                              |
| 11  | Extending Content              | ai-resume only | KEEP                                                              |
| 12  | Quality Standards              | Kahi only      | ADOPT -- documents hooks already in settings.json                 |
| 13  | Container Deployment           | ai-resume only | KEEP                                                              |
| 14  | Security Workflows             | ai-resume only | KEEP                                                              |
| 15  | Git Commit Guidelines          | Both           | MERGE -- consolidate duplication, adopt compact format            |
| 16  | Communication Style            | Both           | MERGE -- consolidate, remove commit rules (moved to Git section)  |

### Proposed Final Section Order

1. Project Overview (restructured)
2. Feature Development Workflow (new, from Kahi)
3. Subagent Policy (restructured, merged)
4. Development (Commands, Testing, Virtual Environments -- reorganized)
5. Architecture (all existing subsections)
6. TypeScript Configuration
7. State Management
8. Browser Router
9. Extending Content
10. Quality Standards (new, from Kahi)
11. Container Deployment
12. Security Workflows
13. Git Commit Guidelines (consolidated)
14. Communication Style (consolidated)

### Key Additions

**Feature Development Workflow (from Kahi):**

- Full specforge phase listing (constitution through setup)
- Skip-if-current rule for existing artifacts
- Implementation gate: do not code until analyze >= 80
- Session bootstrap: read constitution, plan, progress, feature_list on startup

**Quality Standards (new section):**

- Documents the 6 hook types already wired in `.claude/settings.json`
- References constitution for coverage threshold
- Links to `ci/principles/` gate files

**Three-Tier Subagent Policy:**

- Mandatory delegation: code changes, security fixes, multi-file docs, testing, schema validation, 3+ file exploration
- Parallelization: independent analyses as parallel subagents
- Main conversation: orchestrate, aggregate, clarify, single-file edits

---

## 8. Migration Phases

### Phase 0: Constitution Extraction

|              |                                          |
| ------------ | ---------------------------------------- |
| **Mode**     | Interactive (human + Claude Code)        |
| **Command**  | `/specforge constitution`                |
| **Input**    | Pre-fill from Section 6 of this document |
| **Output**   | `.specify/memory/constitution.md`        |
| **Duration** | ~1 hour                                  |

Extract project principles from CLAUDE.md, PRD.md, ARCHITECTURE.md. Use Kahi transferable items as starting point. Human confirms each section.

### Phase 1: Specification Extraction

|              |                                                                 |
| ------------ | --------------------------------------------------------------- |
| **Mode**     | Interactive (human + Claude Code)                               |
| **Commands** | `/specforge spec`, then `/specforge clarify`                    |
| **Input**    | Constitution + PRD.md + TODO.md                                 |
| **Output**   | `.specify/specs/spec.md` (replaces incorrect bootstrap content) |
| **Duration** | ~2-3 hours                                                      |

**Prerequisite:** Delete `.specify/specs/spec.md` (contains wrong content from bootstrap).

Synthesize spec from existing docs. Cover ALL features (completed and pending). Use Given/When/Then format for functional features.

### Phase 2: Plan Confirmation

|              |                                       |
| ------------ | ------------------------------------- |
| **Mode**     | Interactive (human + Claude Code)     |
| **Command**  | `/specforge plan`                     |
| **Input**    | Constitution + spec + ARCHITECTURE.md |
| **Output**   | `.specify/specs/plan.md`              |
| **Duration** | ~30 minutes                           |

Confirm existing architecture decisions in specforge format. Resolve any gaps.

### Phase 3: Feature List Generation (Primary Deliverable)

|              |                                                          |
| ------------ | -------------------------------------------------------- |
| **Mode**     | Two-pass: autonomous generation, then interactive review |
| **Command**  | `/specforge features` (with brownfield extensions)       |
| **Input**    | All specforge artifacts + this inventory document        |
| **Output**   | `feature_list.json`                                      |
| **Duration** | ~3-4 hours                                               |

**Pass 1 (autonomous):** Subagent reads TODO.md, PRD.md, ARCHITECTURE.md and generates draft `feature_list.json`. Maps each TODO phase/section to features, writes testing_steps, applies `verified: false` for brownfield features.

**Pass 2 (interactive):** Human + Claude review. Validate categories, refine testing_steps, confirm dependencies, add PRD outcome features.

**Brownfield classification:**

- Phases 1-4 (all checked): `verified: false` -- code exists, needs validation
- Phases 5-8 (mixed): inspect each -- some `verified: false`, some greenfield
- Phases 9-12 (all unchecked): no `verified` field -- pure greenfield
- PRD outcome features: no `verified` field -- must be run fresh

**Batching strategy for testing_steps:**

1. Infrastructure (Phase 1, 1.5) -- ~10 features
2. Backend (Phase 2, 2.5, 2.6) -- ~20 features
3. Frontend (Phase 3, 3.5) -- ~15 features
4. Data pipeline (Phase 4) -- ~15 features
5. Deployment and Security (Phase 5, 5.5) -- ~10 features
6. QA and Observability (Phase 6, 7) -- ~10 features
7. Production and Extended (Phase 8-12) -- ~15 features
8. PRD outcomes -- 10 features

### Phase 4: Readiness Analysis

|              |                             |
| ------------ | --------------------------- |
| **Mode**     | Autonomous                  |
| **Command**  | `/specforge analyze`        |
| **Input**    | All specforge artifacts     |
| **Output**   | Score report (target >= 80) |
| **Duration** | ~15 minutes                 |

May trigger fixes to spec or feature_list if score is low.

### Phase 5: CLAUDE.md Merge and Schema Update

|              |                                                                                     |
| ------------ | ----------------------------------------------------------------------------------- |
| **Mode**     | Autonomous (subagent)                                                               |
| **Input**    | Section 7 of this document                                                          |
| **Output**   | Updated `CLAUDE.md`, updated `feature-list-schema.json`, updated `coding-prompt.md` |
| **Duration** | ~1 hour                                                                             |

Three changes:

1. Merge CLAUDE.md per Section 7
2. Add `verified` property to `feature-list-schema.json`
3. Update `prompts/coding-prompt.md` Steps 4, 5, 7 for brownfield awareness

### Phase 6: Verification Sprint

|              |                                                     |
| ------------ | --------------------------------------------------- |
| **Mode**     | Autonomous (coding agent, multi-session)            |
| **Input**    | `feature_list.json` with `verified: false` features |
| **Output**   | Features flip to `passes: true, verified: true`     |
| **Duration** | 4-6 coding sessions                                 |

Coding agent runs through brownfield features, executing testing_steps against existing codebase. NOT implementation work -- validation work. Features that fail verification get gaps noted and fixed.

**Priority:** Verification tasks (5-10 min each) before greenfield implementation (30-120 min each).

### Phase 7: Legacy Archive

|             |                                                    |
| ----------- | -------------------------------------------------- |
| **Mode**    | Single commit                                      |
| **Trigger** | All specforge artifacts complete AND analyze >= 80 |
| **Output**  | `docs/archive/` containing legacy process docs     |

See Section 9 for details.

### Phase 8: Greenfield Implementation

|            |                                                                   |
| ---------- | ----------------------------------------------------------------- |
| **Mode**   | Autonomous (coding agent, multi-session)                          |
| **Input**  | `feature_list.json` with `passes: false` (no `verified`) features |
| **Output** | Ongoing development                                               |

Normal specforge coding loop for genuinely new features.

---

## 9. Legacy Archive Strategy

### Trigger Condition

Archive ONLY when ALL of the following are true:

1. `.specify/memory/constitution.md` exists and is human-approved
2. `.specify/specs/spec.md` exists (ai-resume content, not bootstrap placeholder)
3. `.specify/specs/plan.md` exists
4. `feature_list.json` exists and validates against schema
5. `/specforge analyze` score >= 80

### Files to Archive

| File                   | Destination                    | Rationale                                                                  |
| ---------------------- | ------------------------------ | -------------------------------------------------------------------------- |
| `docs/PRD.md`          | `docs/archive/PRD.md`          | Superseded by `.specify/specs/spec.md` + `.specify/memory/constitution.md` |
| `docs/ARCHITECTURE.md` | `docs/archive/ARCHITECTURE.md` | Superseded by `.specify/specs/plan.md`                                     |
| `docs/TODO.md`         | `docs/archive/TODO.md`         | Superseded by `feature_list.json`                                          |

### Files to Keep

| File                               | Rationale                    |
| ---------------------------------- | ---------------------------- |
| `docs/SECURITY.md`                 | Not replaced by specforge    |
| `docs/SPECFORGE-MIGRATION-PLAN.md` | This document -- audit trail |
| `docs/SETUP.md`                    | Operational, not process     |
| `docs/DEVELOPMENT.md`              | Operational, not process     |
| `docs/TEST_COVERAGE.md`            | Reference, not process       |
| All other `docs/` content          | Not process documents        |

### Transition Period

During the period when specforge artifacts exist alongside legacy docs:

- Add comment at top of each legacy doc: `<!-- Superseded by [specforge artifact] as of YYYY-MM-DD -->`
- CLAUDE.md references specforge artifacts as authoritative
- Legacy docs remain readable but not authoritative

### Archive Commit

Single commit: `chore: archive legacy process docs superseded by specforge`

Contents of `docs/archive/README.md`:

```text
Pre-specforge process documents. Retained for historical reference.
Superseded by .specify/ artifacts as of YYYY-MM-DD.
```

Archive is committed (not gitignored). Historical context has value.

### Post-Archive Verification

- Grep CLAUDE.md for paths `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/TODO.md` -- assert zero references
- Grep `ci/` and `.github/workflows/` for same -- update any references
- Verify no feature in `feature_list.json` has testing_steps referencing archived paths

---

## 10. Risk Assessment

### Risk 1: Transition Period Dual Source of Truth (Medium)

**Issue:** During Phases 0-4, both legacy docs and specforge artifacts exist. Requirements could diverge.

**Mitigation:** Add dated supersession comments to legacy docs immediately upon creating their specforge replacement. CLAUDE.md points to specforge artifacts as authoritative. Archive only after all replacements exist and analyze >= 80.

### Risk 2: Analyze >= 80 Gate for Existing Project (Low)

**Issue:** Running `/specforge analyze` on newly created artifacts for existing features may score low because testing_steps are retroactive.

**Mitigation:** Brownfield features can start with `passes: false` and reasonable testing_steps derived from existing tests. The >= 80 gate measures spec quality, not implementation completeness.

### Risk 3: Hooks Documentation Disconnect (Low)

**Issue:** Adding a Quality Standards section describing hooks could confuse users unaware that hooks exist in `.claude/settings.json`.

**Mitigation:** Explicitly reference the settings file in the Quality Standards section.

### Risk 4: Subagent Policy Strictness Change (Low)

**Issue:** Kahi's "MUST be delegated" is stricter than ai-resume's current "IMPORTANT: Use subagents."

**Mitigation:** Keep strong language but preserve the "Direct execution acceptable for" escape hatch.

### Risk 5: Feature Volume (Medium)

**Issue:** ~101 features with 3+ testing_steps each = 300+ testing steps to write. This is significant authoring effort.

**Mitigation:** Two-pass strategy: autonomous generation of draft, then interactive review. Batch by phase for manageable review sessions.

### Risk 6: Coding Agent Greenfield Assumptions (Medium)

**Issue:** `prompts/coding-prompt.md` assumes `init.sh` exists and project was initialized by the initializer agent.

**Mitigation:** Skip initializer entirely. Modify coding-prompt.md Steps 4, 5, 7 for brownfield awareness. Create `init.sh` as a lightweight dev-setup script (not project scaffolding).

### Risk 7: Lost Historical Context (Low)

**Issue:** Archiving TODO.md loses the development timeline, timestamps, and commit SHAs embedded in it.

**Mitigation:** Archive (do not delete). `docs/archive/TODO.md` preserves the full history. `feature_list.json` and `claude-progress.txt` track forward progress.

### Risk 8: Stale References Post-Archive (Low)

**Issue:** After archiving, some file could still reference `docs/PRD.md` or similar paths.

**Mitigation:** Post-archive verification step: grep entire repo for archived paths, update any references found.

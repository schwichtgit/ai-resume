# Development Roadmap (TODO)

Prioritized list of tasks to complete the hybrid Rust + Python AI Resume agent.

---

## Phase 1: Core Infrastructure ✅

- [x] Create comprehensive PRD.md
- [x] Design hybrid architecture (Rust + Python)
- [x] Create TOML configuration schema
- [x] Design podman network & storage (Pattern B: yellow zone)
- [x] Plan secrets management
- [x] Create deployment scripts
- [x] Create development setup scripts
- [x] Consolidate documentation to docs/
- [x] Implement Pattern B networking (frontend as router)
- [x] Document host nginx LB integration
- [x] Document OpenWrt firewall rules

---

## Phase 1.5: Memvid Ingest Pipeline ✅

**Approach:** Python SDK (`memvid-sdk`) with `sentence-transformers` for local embeddings.

**Note:** This is data ingestion/indexing, not ML training. No model parameters are updated.

### Installation & Environment ✅

- [x] Set up dedicated UV environment in `ingest/`
- [x] Install memvid-sdk v2.0.151 via pip
- [x] Install sentence-transformers for local embeddings
- [x] Verify SDK functionality with test script
- [x] Document setup in `ingest/README.md`

### Ingest Script Implementation ✅

- [x] Create `ingest/ingest.py`:
  - [x] Parse YAML frontmatter from `master_resume.md`
  - [x] Chunk markdown by ## headings (section-based)
  - [x] Experience chunks by company/role
  - [x] Failure stories as individual chunks
  - [x] Create semantic tags for each chunk
  - [x] Use `all-mpnet-base-v2` embeddings (768 dimensions)
  - [x] Batch insert with `put_many()` for efficiency
  - [x] Validate output with verification queries
- [x] Create `ingest/test_memvid.py`:
  - [x] SDK validation tests
  - [x] Create/query/close workflow test

### Data Preparation ✅

- [x] `data/master_resume.md` properly formatted:
  - [x] YAML frontmatter (name, title, tags, system_prompt, suggested_questions)
  - [x] Markdown sections (##) for chunking
  - [x] AI Context sections with situation/approach/technical/lessons
  - [x] Chunking guidance at end of document
- [x] Verified markdown structure parses correctly

### Ingest Results ✅

- [x] Ingestion produces `data/.memvid/resume.mv2`:
  - [x] 13 frames (chunked content)
  - [x] 280KB file size (with 768-dim embeddings)
  - [x] Hybrid search enabled (lexical + vector)
- [x] Verification queries pass:
  - [x] "Python experience" → Skills Assessment
  - [x] "M&A integration" → Siemens experience
  - [x] "leadership philosophy" → Leadership & Management
  - [x] "failure lessons" → Failure stories
  - [x] "security compliance" → Relevant sections

### Embedding Model ✅

- [x] Using `all-mpnet-base-v2` from sentence-transformers:
  - [x] 768-dimensional embeddings
  - [x] Optimized for semantic search on professional documents
  - [x] Runs locally on CPU (no API keys required)
  - [x] Model downloaded on first run (~420MB)

### Documentation ✅

- [x] `ingest/README.md` complete:
  - [x] Setup instructions
  - [x] Usage guide
  - [x] Embedding model documentation
  - [x] Chunking strategy table
  - [x] Integration notes (runtime mounting, not embedded)

### Remaining (Optional Enhancements)

- [ ] NPU/Metal acceleration investigation (sentence-transformers uses CPU by default)
- [ ] Benchmark script for performance comparison
- [ ] Content validation tool (`scripts/validate-resume.sh`)

---

## Phase 2: Backend Implementation (API Server)

### Python FastAPI Service ✅

- [x] Implement FastAPI entrypoint (`app/main.py`)
- [x] Implement environment configuration (`app/config.py`)
- [x] Create Pydantic request/response models (`app/models.py`)
- [x] Implement OpenRouter LLM client:
  - [x] Streaming response handling (SSE)
  - [x] Token counting
  - [x] Error handling (auth, rate limit, generic)
- [x] Implement gRPC client to Rust memvid service
  - [x] Protobuf definition (`proto/memvid/v1/memvid.proto`)
  - [x] Client implementation with mock fallback
  - [x] Error handling
- [x] Implement session management:
  - [x] In-memory session store with TTL (cachetools.TTLCache)
  - [x] Session cleanup (automatic via TTL)
  - [x] Concurrent session limits (max_sessions config)
- [x] Implement rate limiting:
  - [x] Per-IP rate limiting (slowapi)
  - [x] Graceful degradation
  - [x] Rate limit headers in responses
- [x] Add observability:
  - [x] Structured logging with structlog
  - [x] Prometheus metrics endpoint (`/metrics`)
  - [x] Request tracing (correlation IDs)
- [x] Write tests:
  - [x] Unit tests for each module
  - [x] Integration tests with mock memvid service
  - [x] **Coverage: 80%** (102 tests passing)

### Rust Memvid Service (Phase 2a Complete)

- [x] Implement gRPC server with Axum & Tonic
- [x] Create proto definition (`proto/memvid/v1/memvid.proto`)
- [x] Implement mock searcher for testing
- [x] Implement memvid file loading:
  - [x] Integrate memvid-core Rust crate (v2.0.134)
  - [x] Load .mv2 file on startup
  - [x] Handle missing/corrupted files (falls back to mock)
  - [x] Frame count verification
- [x] Implement semantic search interface:
  - [x] Searcher trait with Search method
  - [x] Return top N results with metadata (title, score, snippet, tags)
  - [x] Mock implementation returns sample resume data
  - [x] Real memvid-core integration (v2.0.134 with hybrid search)
- [x] Add health checks:
  - [x] gRPC health service (memvid.v1.Health/Check)
  - [x] Frame count and memvid file path in response
- [x] Add observability:
  - [x] Structured JSON logging with tracing
  - [x] Prometheus metrics endpoint (:9090)
  - [x] Search latency histogram
  - [x] Search count and error counters
- [x] Write tests:
  - [x] Unit tests for all modules
  - [x] gRPC service tests
  - [x] Metrics endpoint tests
  - [x] **Coverage: 88.77%** (exceeds 80% target)

### Container Builds ✅

- [x] Build and test Python API container:
  - [x] Fix Dockerfile for UV package installation (`.venv` path, README.md)
  - [x] Add proto compilation stage to Dockerfile
  - [x] Multi-arch build (amd64 + arm64)
  - [x] Test container runs locally (health check passes)
- [x] Build and test Rust memvid container:
  - [x] Fix Dockerfile (add `build.rs`, use debian-slim for glibc)
  - [x] Multi-arch build (amd64 + arm64)
  - [x] Test container runs locally (gRPC + metrics servers start)
- [x] Test containers communicate via gRPC:
  - [x] Both containers run with podman network
  - [x] Health check passes with `memvid_connected: true`
  - [x] Chat endpoint works (mock mode responding)
  - [x] Verify Rust receives gRPC search requests from Python
  - [x] Streaming SSE responses working

**Build Scripts:**
- [x] Updated `scripts/build-all.sh`:
  - [x] Multi-arch manifest builds (amd64 + arm64)
  - [x] `--no-cache` flag for clean rebuilds
  - [x] `--skip-frontend` flag (frontend not yet implemented)
  - [x] Shows architecture info post-build
- [x] Created `scripts/test-containers.sh`:
  - [x] Automated smoke tests
  - [x] Verifies both containers, health, gRPC, chat
  - [x] All 6 tests passing

---

## Phase 2.5: Streaming Chat Implementation ✅

**Goal:** Implement production-ready streaming chat endpoint with proper RAG, error handling, and observability.

Based on analysis from `docs/streamchat.pdf` (Perplexity AI recommendations).

### Core Improvements ✅

- [x] Refactor `/api/v1/chat` endpoint (api-service/ai_resume_api/main.py):
  - [x] Apply improved exception handling structure
  - [x] Add granular try/except for Memvid and OpenRouter with structured logging
  - [x] Use consistent HTTPException responses
  - [x] Consolidate session persistence logic (avoid duplicate `session_store.set()` calls)
  - [x] Add structured logging with consistent fields (session_id, model, chunks_retrieved, latency)

### Streaming Implementation ✅

- [x] Implement `_stream_chat_response()` helper:
  - [x] Async generator for real OpenRouter streaming
  - [x] SSE-compatible output format (`data:`, `event:` fields)
  - [x] Token counting and timing metrics (start_time, elapsed_seconds)
  - [x] Graceful cancellation handling (CancelledError for client disconnects)
  - [x] Accumulate full response content for session persistence
  - [x] Final stats event: `{"chunks_retrieved": n, "tokens_used": n, "elapsed_seconds": x}`
  - [x] Completion event: `event: end\ndata: [DONE]\n\n`
  - [x] Error event: `event: error\ndata: {message}\n\n`
  - [x] Session persistence after stream completes

- [x] Implement `_mock_stream_response()` helper:
  - [x] Simulate token-by-token streaming for local development
  - [x] Random delays (50-150ms) for realistic behavior
  - [x] Same SSE format as real streaming
  - [x] Stats and completion events matching real implementation
  - [x] Enable development without OpenRouter API key

### Helper Functions ✅

- [x] Add `_format_context()` - Standardize Memvid context formatting
- [x] Add `_persist_session()` - Encapsulate session store updates
- [x] Add `_format_sse_event()` - SSE event formatting utility (optional)

### OpenRouter Client Enhancement ✅

- [x] Update `ai_resume_api/openrouter_client.py`:
  - [x] Add `stream_chat()` async generator method
  - [x] Parse streaming response chunks (OpenAI format: `choices[0].delta.content`)
  - [x] Return dict with `{"content": "...", "tokens_used": n}`
  - [x] Handle streaming errors gracefully

### Testing & Observability ✅

- [x] Add integration tests:
  - [x] Test streaming endpoint with mock
  - [x] Test non-streaming endpoint
  - [x] Test client disconnect handling (CancelledError)
  - [x] Test OpenRouter error scenarios
  - [x] Verify session persistence after streaming
  - [x] Target >80% coverage

- [x] Add observability:
  - [x] Structured logs for each request phase (memvid, session, llm)
  - [x] Metrics: request rate, latency (P50/P95/P99), error rate, token usage
  - [x] Verify Prometheus metrics exposition at `/metrics`

### SSE Format Specification ✅

```
data: {token}\n\n                          # Token chunks
event: stats\ndata: {json}\n\n            # Final stats
event: end\ndata: [DONE]\n\n              # Stream completion
event: error\ndata: {message}\n\n         # Errors
```

### Acceptance Criteria ✅

- [x] Streaming chat works with real OpenRouter LLM
- [x] Mock streaming works without OpenRouter API key
- [x] Client disconnects don't leave orphaned sessions
- [x] All responses include stats event (chunks_retrieved, tokens_used, elapsed)
- [x] Session history persists correctly after streaming
- [x] Structured logs contain session_id, model, chunks_retrieved
- [x] Integration tests pass with >80% coverage
- [x] No regression in existing health/chat endpoints

**Status:** Complete - Implemented January 20, 2026

---

## Phase 2.6: Architectural Refactoring ✅

**Goal:** Align naming convention - services by function (what they do), not by language implementation.

### Service Directory Refactoring ✅

- [x] Rename directories to function-based naming:
  - [x] `api-server-python/` → `api-service/` (FastAPI orchestration)
  - [x] `api-server-rust/` → `memvid-service/` (memvid semantic search)
  - [x] `frontend/` confirmed (React SPA - kept as-is)
- [x] Update all file references:
  - [x] `scripts/build-all.sh` - directory paths in build commands
  - [x] `scripts/test-containers.sh` - output paths and references
  - [x] `deployment/compose.yaml` - service names and image references
  - [x] All Dockerfiles - COPY paths and module references

### Python Package Naming ✅

- [x] Rename Python package for wheel distribution clarity:
  - [x] `app/` → `ai_resume_api/` (fully-qualified package name)
  - [x] Update `pyproject.toml`:
    - [x] `packages = ["ai_resume_api"]`
    - [x] Pytest coverage scope to `ai_resume_api`
  - [x] Update all Python imports across 4 files:
    - [x] `ai_resume_api/main.py` - 6 imports updated
    - [x] `ai_resume_api/memvid_client.py` - 3 imports updated
    - [x] `ai_resume_api/openrouter_client.py` - 1 import updated
    - [x] `ai_resume_api/session_store.py` - 2 imports updated
  - [x] Update Dockerfile:
    - [x] Proto compilation stage paths
    - [x] COPY instructions for application code
    - [x] Uvicorn module reference in CMD

### Documentation Updates ✅

- [x] Update README.md with new paths:
  - [x] Container versions section
  - [x] Development setup section
  - [x] Project structure diagram
- [x] Update service README files:
  - [x] `api-service/README.md` - project structure
  - [x] `memvid-service/README.md` - project structure
- [x] Update DESIGN.md:
  - [x] Development terminal setup commands
  - [x] Module references (app → ai_resume_api)

### Testing & Validation ✅

- [x] Verify Python venv integrity:
  - [x] `uv sync --check` passes (lock file up-to-date)
  - [x] New `.venv` directory functional
- [x] Rebuild containers with new paths:
  - [x] Both containers build successfully (amd64)
  - [x] Images created: `ai-resume-api` and `ai-resume-memvid`
- [x] Run integration tests:
  - [x] All 6 smoke tests passing
  - [x] gRPC communication functional
  - [x] Chat endpoint responding correctly

### Naming Convention (Final)

**Directories:** Function-based
- `frontend/` - React SPA
- `api-service/` - FastAPI REST/gRPC orchestration
- `memvid-service/` - Rust gRPC semantic search

**Containers:** Descriptive
- `ai-resume-api` - Python FastAPI service
- `ai-resume-memvid` - Rust memvid gRPC service
- `ai-resume-frontend` - nginx + React SPA

**Python Package:** Fully-qualified
- `ai_resume_api` - Distributable package (not generic "app")

**Status:** Complete - Refactored January 20, 2026
**Commits:** `8b977aa` (main refactor) + `5532bef` (post-refactor optimizations)

---

## Phase 3: Frontend Integration ✅

- [x] Create API client service (`src/lib/api-client.ts`):
  - [x] Chat endpoint integration (streaming SSE)
  - [x] Health check endpoint
  - [x] Suggested questions endpoint
  - [x] Error handling with ApiError class
  - [x] Request cancellation via AbortController
- [x] Create custom hook for streaming (`src/hooks/useStreamingChat.ts`):
  - [x] Server-Sent Events (SSE) parsing
  - [x] Message streaming display
  - [x] Token accumulation
  - [x] Graceful disconnection
  - [x] Session management with auto-generated UUIDs
  - [x] Retry logic
- [x] Update AIChat component:
  - [x] Replace pattern matching with API calls
  - [x] Display streaming responses with cursor animation
  - [x] Handle API errors with retry button
  - [x] Show loading states ("Connecting...", "Thinking...")
  - [x] Backend health indicator
  - [x] Clear conversation button
  - [x] Cancel streaming button
- [x] Configure Vite proxy for development:
  - [x] `/api` proxied to `http://localhost:3000`
  - [x] Removed unused lovable-tagger dependency
- [ ] Update FitAssessment component:
  - [ ] Load data from config (if applicable)
  - [ ] Dynamic job matching
- [ ] Add configuration-driven UI:
  - [ ] Load `profile.toml` from API
  - [ ] Apply theme from config
  - [ ] Show/hide sections based on config
  - [x] Dynamic suggested questions (from backend API)
- [x] Improve user experience:
  - [x] Error display with retry option
  - [x] Loading states throughout
  - [x] Empty states with suggested questions
  - [ ] Error boundaries (component-level)
  - [ ] Accessibility improvements (a11y)

---

## Phase 3.5: Read-Only Containers & tmpfs Hardening ✅

**Goal:** Implement production-grade container security with read-only filesystems and proper tmpfs mounts.

### Container Security Hardening ✅

- [x] Add read-only filesystem to all services:
  - [x] `ai-resume-memvid`: `read_only: true`
  - [x] `ai-resume-api`: `read_only: true`
  - [x] `ai-resume-frontend`: `read_only: true`

- [x] Configure tmpfs mounts for writable directories:
  - [x] **memvid-service**: `/tmp` (128M), `/run` (64M)
  - [x] **api-service**: `/tmp` (256M), `/var/tmp` (128M), `/run` (64M)
  - [x] **frontend**: `/var/cache/nginx` (128M), `/var/run` (64M), `/tmp` (64M)

- [x] Disable unnecessary bind mount log volumes:
  - [x] Removed `/opt/ai-resume/logs/rust:/var/log/app:rw` from memvid-service
  - [x] Removed `/opt/ai-resume/logs/python:/var/log/app:rw` from api-service

### Logging to stdout ✅

- [x] Verified all services log to stdout (container best practice):
  - [x] **memvid-service**: Uses `tracing_subscriber` with JSON output to stdout
  - [x] **api-service**: Uses `structlog` to stdout
  - [x] **frontend (nginx)**: Added explicit `access_log /dev/stdout` and `error_log /dev/stderr`

### Health Checks Update ✅

- [x] Changed memvid-service health check:
  - [x] From: `grpc-health-probe -addr=:50051` (missing binary)
  - [x] To: `wget -q --spider http://localhost:9090/metrics` (HTTP endpoint, proves Rust service is healthy)

- [x] Added `wget` to memvid-service Dockerfile:
  - [x] Installed in runtime image for health checks
  - [x] Lightweight addition to debian-slim base

### Rationale ✅

- **Read-only filesystem**: Prevents accidental writes, container tampering, limits blast radius
- **tmpfs mounts**:
  - Rust/Python runtimes need temp space (stdlib operations, LLM streaming buffers)
  - memvid library needs temp files for processing
  - nginx needs writable cache directory (even with `proxy_buffering off`, needs temp space)
  - Sized appropriately: memvid/python need more than nginx
  - Cleared on container exit (no persistent state leaks)
- **No bind mount logs**: All logs to stdout/stderr (captured by container runtime, accessible via `podman logs`)
- **HTTP health check**: Simpler than gRPC, avoids binary dependency, metrics endpoint proves service is working

### Files Modified ✅

- [x] `deployment/compose.yaml`:
  - [x] Added `tmpfs:` sections to all three services
  - [x] Updated memvid health check to use metrics endpoint
  - [x] Removed unnecessary log volume mounts

- [x] `memvid-service/Dockerfile`:
  - [x] Added `wget` to runtime image

- [x] `frontend/nginx.conf`:
  - [x] Added explicit stdout/stderr logging configuration

### Verification ✅

- [x] Services can write to tmpfs without filling up (memvid, Python, nginx)
- [x] All services log to stdout (observable via `podman logs`)
- [x] Health checks pass with new HTTP metrics endpoint
- [x] Read-only filesystem prevents accidental writes

**Status:** Complete - January 21, 2026

---

## Phase 4: Data-Driven Architecture ✅

**Goal:** Transform from hardcoded, Frank-specific implementation to portable, configuration-driven architecture where any candidate can deploy by replacing `data/*.md` and re-running ingest.

**Status:** ✅ COMPLETE - Achieved true single-file portability (only .mv2 needed)

### 4.1: Backend Profile API (Foundation) ✅

**Priority:** 🔴 CRITICAL | **Effort:** 2-3 hours | **Status:** ✅ COMPLETE

- [x] Extend ingest pipeline to export profile:
  - [x] Extract YAML frontmatter during ingest
  - [x] **IMPROVED:** Store profile as JSON frame INSIDE .mv2 (eliminated profile.json side-car)
  - [x] Include: name, title, email, linkedin, location, status, suggested_questions, system_prompt, tags
  - [x] **EXTENDED:** Added experience[], skills{}, fit_assessment_examples[]
- [x] Add `GET /api/v1/profile` endpoint:
  - [x] Load from memvid (with profile.json fallback for backward compatibility)
  - [x] Return extended profile metadata (includes experience and skills)
  - [x] Parse structured experience entries with ai_context
- [x] Update `GET /api/v1/suggested-questions`:
  - [x] Read from memvid profile (not hardcoded list)
  - [x] Return 404 if profile not found (no hardcoded fallbacks)
- [x] Update `config.py`:
  - [x] Add `load_profile_from_memvid()` async method
  - [x] Load `system_prompt` from profile at startup
  - [x] Remove hardcoded system prompt

### 4.2-4.12: Complete Implementation ✅

**Status:** ✅ ALL COMPLETE

The implementation exceeded the original plan. Key achievements:

- [x] **4.2: Frontend Profile Hook** - Created useProfile with experience/skills support
- [x] **4.3: Component Refactoring** - All components data-driven (Footer, Header, Hero, Experience, FitAssessment)
- [x] **4.4: HTML Metadata** - Lua-based SEO endpoint + dynamic React meta tag updates
- [x] **4.5-4.6: Extended API** - Experience entries, skills data, fit assessment examples
- [x] **4.7: Profile in Memvid** - Stored profile IN .mv2 file (eliminated profile.json side-car)
- [x] **4.8: Hybrid Fit Assessment** - Pre-analyzed examples + real-time AI analysis via POST /api/v1/assess-fit
- [x] **4.9: Legacy Cleanup** - Removed frank-profile.ts, eliminated all hardcoded mock data
- [x] **4.10: Testing** - Created scripts/test_portability.py for validation
- [x] **4.11: Documentation** - Updated README.md, CLAUDE.md for data-driven architecture

**Major Improvements Beyond Original Plan:**

1. **True Single-File Portability:** Profile stored AS memvid frame (not side-car file)
2. **Hybrid Fit Assessment:** Both pre-analyzed examples AND real-time AI analysis
3. **Extended Data Model:** Experience with ai_context, skills categorization, fit examples
4. **Server-Side SEO:** Lua handler for bot-specific rendering (not just build-time)
5. **Dynamic Frontend Metadata:** React updates document.title and meta tags at runtime

### Phase 4 Summary

| Task | Effort | Priority | Status |
|------|--------|----------|--------|
| 4.1 Backend Profile API | 2-3h | 🔴 CRITICAL | ✅ COMPLETE |
| 4.2 Frontend Profile Hook | 3-4h | 🔴 CRITICAL | ✅ COMPLETE |
| 4.3 Component Refactoring | 2-3h | 🔴 CRITICAL | ✅ COMPLETE |
| 4.4 HTML Metadata | 1-2h | 🟡 HIGH | ✅ COMPLETE |
| 4.5-4.6 Extended API & Cleanup | 2-3h | 🟡 HIGH | ✅ COMPLETE |
| 4.7 Profile in Memvid | 2h | 🔴 CRITICAL | ✅ COMPLETE |
| 4.8 Hybrid Fit Assessment | 4-5h | 🟡 HIGH | ✅ COMPLETE |
| 4.9-4.10 Legacy Cleanup | 1-2h | 🟡 MEDIUM | ✅ COMPLETE |
| 4.11 Testing & Validation | 2h | 🟡 HIGH | ✅ COMPLETE |
| 4.12 Documentation | 1h | 🟢 MEDIUM | ✅ COMPLETE |
| **Total** | **~20h** | | **✅ COMPLETE** |

### Success Criteria ✅

- [x] **Portability:** Can deploy for `example_resume.md` without code changes
- [x] **Single-File:** Only .mv2 file needed (no profile.json or config files)
- [x] **No Hardcoded Data:** All personal data from markdown → .mv2 → API → Frontend
- [x] **Hybrid Fit Assessment:** Pre-analyzed examples + real-time AI
- [x] **Dynamic SEO:** Server-side rendering for bots, dynamic meta tags for browsers
- [x] **Fully Data-Driven:** Experience, skills, fit examples all from data source

**Achieved:** January 24, 2026

### Key Commits (18 total)

1. `c33cdeb` - Fix: Remove hardcoded data from index.html, add dynamic meta tag updates
2. `ddebd7c` - Refactor: Consolidate type definitions in api-client.ts
3. `02825ac` - Implement Phase 4.8.1: Add fit assessment examples to example_resume.md
4. `3ad4f45` - Implement Phase 4.8.2: Parse fit assessment examples in ingest.py
5. `6b020b5` - Implement Phase 4.8.3: Add fit assessment examples to profile API
6. `b1d4475` - Implement Phase 4.8.4: Create POST /api/v1/assess-fit endpoint for real-time AI
7. `7a4928b` - Implement Phase 4.8.5: Refactor FitAssessment component for hybrid approach
8. `97695f1` - Implement Phase 4.9: Remove frank-profile.ts legacy file
9. `57a55bb` - Implement Phase 4.10: Backend Mock Cleanup - Remove hardcoded mock data
10. `a07ad3c` - Implement Phase 4.11: Create portability test script
11. `79c84c3` - Implement Phase 4.12: Update README for data-driven architecture

### Key Files Modified

- `ingest.py` - Parse fit examples, store profile in .mv2
- `api-service/ai_resume_api/` - Extended models, assess-fit endpoint, profile from memvid
- `frontend/src/components/` - FitAssessment refactored, all components data-driven
- `frontend/src/hooks/useProfile.ts` - Extended with fit examples, dynamic meta tags
- `frontend/index.html` - Generic placeholders, dynamic updates
- `frontend/lua/seo-handler.lua` - Server-side SEO rendering
- `scripts/test_portability.py` - Validation test
- `README.md` - Updated for data-driven architecture
- Removed: `frontend/src/data/frank-profile.ts` (legacy)

---

## Phase 5: Container & Deployment

### Container Building ✅

- [x] Verify multi-arch Dockerfiles:
  - [x] Frontend (nginx + React) - 53 MB, multi-arch (amd64 + arm64)
  - [x] API server (Python) - 192 MB, multi-arch
  - [x] Memvid service (Rust) - 97 MB, multi-arch
- [x] Test container builds locally
- [x] Verify container sizes & startup times
- [x] Test cross-architecture loading

### Local Testing ✅

- [x] Test all three services together
- [x] Verify all three services start
- [x] Test inter-container communication (nginx → api-service → memvid-service)
- [x] Verify health checks work (frontend /health, api /api/v1/health)
- [x] Test API endpoints manually (health, suggested-questions, chat)
- [x] Test streaming SSE through nginx proxy

### Edge Deployment

- [ ] Test `scripts/deploy.sh` to test server
- [ ] Verify file transfers (scp)
- [ ] Test container loading on ARM64
- [ ] Verify services start on remote
- [ ] Test domain routing (Traefik/Caddy)
- [ ] Load test with concurrent users

---

## Phase 5.5: Security Hardening & Observability ✅ (In Progress)

**Goal:** Implement prompt injection defenses, fix internal structure leakage, and add comprehensive observability for monitoring and debugging.

**Reference:** [PROMPT-INJECTION-STRATEGIES.md](./PROMPT-INJECTION-STRATEGIES.md)

### Observability Instrumentation ✅

- [x] Add trace ID propagation (api-service):
  - [x] Create `observability.py` module with trace ID context vars
  - [x] Add middleware to generate/propagate X-Trace-ID header
  - [x] Bind trace ID to structlog context for all logs
  - [x] Include trace_id in SSE stats event for client correlation
- [x] Add LLM-specific Prometheus metrics:
  - [x] `llm_requests_total{model, status, stream}` - Counter
  - [x] `llm_tokens_total{model, type}` - Counter (prompt/completion/total)
  - [x] `llm_latency_seconds{model, stream}` - Histogram
  - [x] `llm_active_requests{model}` - Gauge
  - [x] `memvid_retrieval_chunks` - Histogram
  - [x] `memvid_context_chars` - Histogram
  - [x] `memvid_search_latency_seconds` - Histogram
- [x] Add structured LLM logging:
  - [x] `llm_request` event with context_chars, user_message_preview, history_messages
  - [x] `llm_response` event with tokens, latency_ms, finish_reason
  - [x] `memvid_search` event with hits, latency_ms

### Prompt Injection Defense (In Progress)

- [x] Fix Frame # leakage in Rust memvid-service:
  - [x] Investigate memvid-core SDK metadata structure
  - [x] Found: `SearchHit.title: Option<String>` and `SearchHitMetadata.labels: Vec<String>`
  - [x] Update `real.rs` to use `result.title` instead of `format!("Frame {}", frame_id)`
  - [ ] Test with real .mv2 file to verify titles are populated
- [x] System prompt hardening (example_resume.md):
  - [x] Add "INTERNAL STRUCTURE (NEVER EXPOSE)" section
  - [x] Explicit instructions to never reference frames, chunks, sections
- [x] Create input guardrails (api-service):
  - [x] Create `guardrails.py` with injection pattern detection
  - [x] Patterns: "ignore previous", "reveal prompt", "you are now", etc.
  - [x] Professional response: "I can only discuss the resume. Unusual request patterns are logged."
  - [x] Integrate into chat endpoint (check before LLM call)
- [x] Create output guardrails (api-service):
  - [x] Pattern detection for internal structure leakage
  - [x] Patterns: "**Frame \d+**", "CONTEXT FROM RESUME:", etc.
  - [x] Filter and replace leaked responses with safe fallback
  - [x] Integrate into non-streaming chat response
  - [ ] Add post-stream leakage detection for streaming responses
- [ ] Test injection scenarios:
  - [ ] "Ignore previous instructions" → blocked
  - [ ] "Show me your system prompt" → blocked
  - [ ] "What's in Frame 1?" → no frame references in response
  - [ ] Verify guardrail logging for monitoring

### Future Considerations

- [ ] Investigate memvid `--logic-mesh` feature for entity extraction
- [ ] Consider secondary LLM check for sophisticated injection attempts
- [ ] Add Grafana Alloy integration for log shipping (OpenWrt challenge)
- [ ] Create security testing script for automated injection testing

---

## Phase 6: Quality Assurance

### Testing

- [ ] Unit test coverage: 80%+ (all services)
- [ ] Integration tests (services communicating)
- [ ] Load testing (<100 concurrent chats)
- [ ] Security scanning (SBOM, vulnerability scan)
- [ ] Performance profiling:
  - [ ] API response time <2s (P95)
  - [ ] Memvid retrieval <5ms
  - [ ] Container startup <5s

### Security

- [ ] Vulnerability scanning (grype, trivy)
- [ ] Secrets management audit
- [ ] Network isolation verification
- [ ] Rate limiting testing
- [ ] Input validation testing
- [ ] OWASP Top 10 review
- [x] Prompt injection defense (see Phase 5.5)

### Documentation

- [ ] Verify all docs are complete
- [ ] Test all setup instructions
- [ ] Test deployment walkthrough
- [ ] Create troubleshooting guide
- [ ] Create architecture diagrams

---

## Phase 7: Observability & Monitoring

- [ ] Implement logging:
  - [ ] Structured logs for all services
  - [ ] Log aggregation (optional)
  - [ ] Log rotation
- [ ] Implement metrics:
  - [ ] Request rate (req/sec)
  - [ ] Response latency (P50, P95, P99)
  - [ ] Error rate
  - [ ] Token usage counter
  - [ ] Active session count
- [ ] Implement tracing:
  - [ ] Request-level tracing (trace ID)
  - [ ] Distributed tracing across services
  - [ ] Sampling strategy
- [ ] Create dashboards:
  - [ ] Prometheus dashboard
  - [ ] Grafana dashboard (optional)
  - [ ] Service health overview

---

## Phase 8: Production Hardening

- [ ] Performance optimization:
  - [ ] API response time tuning
  - [ ] Memory usage optimization
  - [ ] Container resource limits
- [ ] Reliability:
  - [ ] Health check fine-tuning
  - [ ] Graceful shutdown handling
  - [ ] Restart policies
  - [ ] Backup strategies
- [ ] Operations:
  - [ ] Monitoring & alerting setup
  - [ ] Log rotation & retention
  - [ ] Update procedures
  - [ ] Rollback procedures
  - [ ] Incident response guide

---

## Phase 9: Extended Features (Optional)

- [ ] Conversation history:
  - [ ] Persist conversation in database (SQLite/DuckDB)
  - [ ] Load history on session resume
  - [ ] Export conversation as PDF
  - [ ] Analytics (question types, user engagement)
- [ ] Advanced RAG:
  - [ ] Multi-source indexing (blogs, GitHub, presentations)
  - [ ] Custom embeddings
  - [ ] Reranking for better results
- [ ] Multi-agent orchestration:
  - [ ] LangChain integration (if needed)
  - [ ] Tool calling (search, email, etc.)
  - [ ] Agent workflows
- [ ] Frontend enhancements:
  - [ ] Dark mode (already in config schema)
  - [ ] Real-time typing indicator
  - [ ] Conversation search
  - [ ] Export to markdown/PDF
- [ ] Mobile support:
  - [ ] Responsive design improvements
  - [ ] Mobile-optimized chat UI
  - [ ] Mobile app (React Native)

---

## Phase 10: Ontology-Based Knowledge Graph RAG (Future)

**Reference:** [ONTOLOGY-CONSIDERATIONS.md](./ONTOLOGY-CONSIDERATIONS.md)

**Goal:** Evolve from "Simple RAG" (text similarity) to "Knowledge-Graph RAG" (structured relationships).

### Why This Matters

| Current State | Ontology-Based |
|--------------|----------------|
| Find text containing "Python" | Query "5+ years Python experience" via metadata |
| Context from entire job description | Link specific skills to specific projects |
| Anti-patterns mixed with achievements | Structured "Limitations" frame for honest answers |
| FAQ text matching | Typed NarrativeFrame with sentiment analysis |

### Proposed Ontology Schema

```python
# Atomic Components
class Skill(BaseModel):
    name: str
    proficiency: str  # "Primary", "Secondary"
    years: int
    context: str  # "Used at Acme for K8s Operators"

class Achievement(BaseModel):
    summary: str
    metrics: Optional[str]
    technical_stack: List[str]

# Main Entities (become Memvid "Fact Frames")
class ExperienceFrame(BaseModel):
    company: str
    role: str
    period: str
    achievements: List[Achievement]
    ai_context_story: Optional[str]
    is_leadership: bool

class NarrativeFrame(BaseModel):
    topic: str  # "Security Track Record", "Failure: Over-engineering"
    content: str
    keywords: List[str]
    sentiment: str  # "Positive", "Self-Critical", "Neutral"

class FitAssessmentFrame(BaseModel):
    scenario_name: str
    verdict: str  # "Strong", "Weak", "Moderate"
    reasoning: List[str]
    gaps: List[str]

class CandidateOntology(BaseModel):
    name: str
    title: str
    tags: List[str]
    skills: List[Skill]
    experience: List[ExperienceFrame]
    narratives: List[NarrativeFrame]
    fit_benchmarks: List[FitAssessmentFrame]
    anti_patterns: List[str]  # What candidate is NOT good at
```

### Implementation Tasks

- [ ] **10.1: Define Pydantic Ontology**
  - [ ] Create `ingest/ontology.py` with above schema
  - [ ] Add validation rules (years > 0, required fields)
  - [ ] Generate JSON Schema for documentation

- [ ] **10.2: LLM-Based Extraction Pipeline**
  - [ ] Integrate `instructor` library for structured extraction
  - [ ] Use OpenRouter with structured output (Gemini/GPT-4o)
  - [ ] Validation loop to ensure failures/anti-patterns aren't skipped
  - [ ] Fallback to current parsing if LLM extraction fails

- [ ] **10.3: Memvid Fact Frame Storage**
  - [ ] Store each entity as typed frame with full JSON metadata
  - [ ] Add `type` field to metadata (experience, narrative, skill, etc.)
  - [ ] Link frames via `candidate_id` for multi-candidate support
  - [ ] Preserve backward compatibility with current .mv2 format

- [ ] **10.4: Hybrid Query Router**
  - [ ] Implement query classifier (semantic vs structured)
  - [ ] Add metadata filtering to memvid search
  - [ ] Support queries like "leadership roles" → filter `is_leadership: true`
  - [ ] Support queries like "5+ years Python" → filter `skills.years >= 5`

- [ ] **10.5: API Enhancements**
  - [ ] Add `GET /api/v1/skills` endpoint (structured skill listing)
  - [ ] Add `GET /api/v1/experience/{company}` endpoint
  - [ ] Add metadata filter parameters to `/api/v1/chat`
  - [ ] Return structured citations with entity type

### Benefits for Resume Use Case

1. **Precision Queries:** "FedRAMP experience?" → Returns NarrativeFrame "Security Track Record" with structured metadata
2. **Honest Limitations:** Anti-patterns stored as typed frame, not buried in text
3. **Skill-Project Linking:** "Where did you use Python?" → Returns specific achievements with context
4. **Multi-Candidate Support:** `candidate_id` enables portfolio of multiple resumes

### Prerequisites

- [ ] Current Phase 4 (Data-Driven) complete ✅
- [ ] Stable .mv2 format with memory cards
- [ ] OpenRouter API for structured extraction
- [ ] Consider cost: LLM extraction adds API cost to ingest

---

## Critical Path (Minimal MVP)

**Fastest path to working system (2-3 weeks remaining):**

1. ✅ **Week 1:** Docs, scripts, configuration

   - [x] PRD & design complete
   - [x] Setup scripts created
   - [x] Configuration schema finalized
   - [x] `data/master_resume.md` ready
   - [x] Pattern B networking documented

2. ✅ **Week 1-2:** Memvid Ingest — **COMPLETE**

   - [x] Install memvid-sdk via UV/pip
   - [x] Set up sentence-transformers embeddings
   - [x] Implement `ingest/ingest.py`
   - [x] Test ingestion with improved verification (score thresholds + tag matching)
   - [x] Generate `data/.memvid/resume.mv2` (280KB, 13 frames)
   - [x] Hybrid search enabled (lexical + vector)

3. ✅ **Week 2-3:** Backend core — **COMPLETE**

   - [x] Python FastAPI + OpenRouter integration
     - [x] Streaming SSE responses
     - [x] Session management with TTL
     - [x] Rate limiting with slowapi
     - [x] 80% test coverage (102 tests)
   - [x] Rust gRPC server skeleton (Phase 2a complete)
     - [x] Proto definition, mock searcher, health check
     - [x] Prometheus metrics, structured logging
     - [x] 88.77% test coverage
   - [x] Rust memvid-core integration (v2.0.134 - COMPLETE)
   - [x] gRPC client-server communication working
   - [x] Local testing with compose (using ingested .mv2)

4. **Week 3-4:** Frontend + deployment
   - [ ] Frontend API integration
   - [ ] Streaming response handling
   - [ ] Container builds working
   - [ ] Deploy script tested
   - [ ] Live on edge server

---










---

## Enhancement: Profile Image & Pronouns (Post-MVP)

### TODO: Add profile image field to resume schema
**Status**: Pending
**Related**: OG/Twitter link previews
**Priority**: Medium

**Problem**:
- OG image currently hardcoded as `/ai-resume.png`
- Different resumes should specify their own preview image
- Image should come from profile data (memvid), not hardcoded

**Implementation**:
1. Extend resume YAML schema with `image` field:
   ```yaml
   ---
   name: Jane Chen
   image: /path/to/jane-preview.png  # NEW: Optional OG preview image
   ...
   ```

2. Update ingest pipeline:
   - Extract `image` from frontmatter
   - Store in memvid profile metadata
   - Validate image exists and is accessible

3. Update API endpoints:
   - Return `image` in ProfileResponse
   - Update `/api/v1/profile` endpoint

4. Update frontend & SEO:
   - `index.html` - Use dynamic image (either static `/ai-resume.png` or API-driven)
   - `seo-template.html` - Use `{{IMAGE}}` placeholder with fallback
   - `seo-handler.lua` - Add image to Lua substitutions

**Files to Modify**:
- `data/example_resume.md` - Add optional `image` field
- `ingest/ingest.py` - Extract image from frontmatter
- `api-service/ai_resume_api/models.py` - Add image to ProfileResponse
- `api-service/ai_resume_api/main.py` - Return image from /api/v1/profile
- `frontend/index.html` - Reference image
- `frontend/seo-template.html` - Use {{IMAGE}} placeholder
- `frontend/lua/seo-handler.lua` - Add image substitution with fallback

**Status**: Commit `a50be06` fixed hardcoded paths but still need to make image configurable per-resume

---

### TODO: Add pronouns field to resume schema
**Status**: Pending
**Related**: Guardrails UX improvements
**Priority**: Low

**Problem**:
- Guardrails currently use pronoun-neutral language ("their", "they")
- Better UX with correct pronouns (she/her, he/him, they/them, etc.)

**Implementation**:
1. Add `pronouns` field to resume YAML:
   ```yaml
   pronouns: she/her  # or: he/him, they/them, etc.
   ```

2. Extract in ingest pipeline
3. Store in memvid profile & return via API
4. Pass to `_format_guardrail_response()` in guardrails.py
5. Update response to use pronouns: "How they might fit" vs "How their..."

**Status**: Commit `913afd8` designed guardrail response to be pronoun-ready, needs schema support

---

## Success Criteria

- [ ] All three services running in containers
- [ ] End-to-end chat workflow functional
- [ ] Response time P95 < 2s
- [ ] Memvid retrieval < 5ms
- [ ] Deploy script fully automated
- [ ] Documentation complete & tested
- [ ] Security scanning passes
- [ ] GitHub-publishable with clear instance setup

---

## Estimated Timeline

| Phase                    | Effort   | Timeline      | Status         |
| ------------------------ | -------- | ------------- | -------------- |
| 1. Infrastructure        | 10h      | Week 1        | ✅ Complete    |
| 1.5. Memvid Ingest       | 15h      | Week 1-2      | ✅ Complete    |
| 2. Backend               | 40h      | 2 weeks       | ✅ Complete    |
| 3. Frontend              | 20h      | 1 week        | Pending        |
| 4. Data-driven           | 15h      | 1 week        | Pending        |
| 5. Containers            | 15h      | 1 week        | Pending        |
| 6. QA                    | 20h      | 1-2 weeks     | Pending        |
| 7. Observability         | 15h      | 1 week        | Pending        |
| 8. Hardening             | 20h      | 1-2 weeks     | Pending        |
| 9. Extended Features     | 40h+     | Optional      | -              |
| **Remaining MVP**        | **~85h** | **3-4 weeks** | -              |

**Progress Notes:**

- ✅ Phase 1.5 (Memvid Ingest) complete - `.mv2` file ready for backend integration
- ✅ Pattern B networking (yellow zone) fully documented
- ✅ Ingestion produces 280KB .mv2 with 768-dim embeddings
- ✅ Improved verification with score thresholds and tag matching
- ✅ **Phase 2 Rust Service** - Complete with 88.77% test coverage
  - Proto definition, mock searcher, health check, metrics, logging
  - Multi-arch containers (amd64 + arm64)
  - Waiting on memvid-core Rust crate for real .mv2 integration
- ✅ **Phase 2 Python Service** - Complete with 80% test coverage (102 tests)
  - OpenRouter LLM client with streaming SSE
  - gRPC client with working Rust communication
  - Session management with TTL, rate limiting
  - Structured logging, Prometheus metrics
  - Multi-arch containers (amd64 + arm64)
- ✅ **Phase 2 Container Integration** - Complete
  - Both services build for amd64 + arm64
  - Smoke tests verify gRPC communication
  - Chat workflow end-to-end functional (mock mode)
  - Dockerfile fixes: proto compilation, binary dependencies
- ✅ **Phase 2 Build Automation** - Complete
  - `build-all.sh` supports multi-arch builds with flags
  - `test-containers.sh` automated smoke tests (all passing)
- ✅ **Phase 2.5 Streaming Chat Implementation** - Complete
  - Refactored `/api/v1/chat` with improved exception handling
  - Implemented `_stream_chat_response()` async generator with SSE
  - Implemented `_mock_stream_response()` for local development
  - Added elapsed_seconds tracking and stats events
  - Graceful CancelledError handling for client disconnects
  - Enhanced OpenRouter client with `stream_chat()` method
- ✅ **Phase 2.6 Architectural Refactoring** - Complete (January 20, 2026)
  - Renamed services to function-based naming:
    - `api-server-python/` → `api-service/`
    - `api-server-rust/` → `memvid-service/`
  - Renamed Python package: `app/` → `ai_resume_api/`
  - Updated all imports, Dockerfiles, scripts, and documentation
  - Verified Python venv integrity and container builds
  - All integration tests passing (6/6 ✓)
  - Commits: `8b977aa` (refactor) + `5532bef` (post-refactor)
- **Phase 3 Frontend Integration** - Complete (January 21, 2026)
  - Created `src/lib/api-client.ts` with streaming SSE support
  - Created `src/hooks/useStreamingChat.ts` custom hook
  - Updated AIChat component with real API integration
  - Configured Vite proxy for development (`/api` → `localhost:3000`)
  - Removed lovable-tagger dependency
  - All features: health check, streaming, retry, cancel, clear conversation
- **Phase 3.5 Read-Only Containers & tmpfs Hardening** - Complete (January 21, 2026)
  - Added read-only filesystem to all three services
  - Configured tmpfs mounts for writable directories (memvid: 128M+64M, api: 256M+128M+64M, frontend: 128M+64M+64M)
  - Removed unnecessary bind mount log volumes
  - Verified all services log to stdout/stderr (not to files)
  - Changed memvid health check from gRPC probe to HTTP metrics endpoint
  - Added wget to memvid-service Dockerfile for health checks

---

## Notes

- Timestamps reflect current date: January 20, 2026
- **Memvid Ingest:** Uses Python SDK (`memvid-sdk`) with `sentence-transformers`, not CLI
- **Terminology:** "Ingest" not "training" - this is data indexing, not ML model training
- **Embedding Model:** `all-mpnet-base-v2` (768 dimensions, ~420MB model download)
- **Ingest Output:** `data/.memvid/resume.mv2` (280KB, 13 frames)
- **Networking:** Pattern B with yellow zone (192.168.100.0/24), host nginx LB
- **Rust Service:** Phase 2 complete - gRPC skeleton with 88.77% test coverage
  - Uses Tonic for gRPC, Axum for metrics HTTP endpoint
  - Mock searcher ready; awaiting memvid-core Rust crate for real integration
  - Located in `memvid-service/` (function-based naming)
- **Python Service:** Phase 2 complete - FastAPI with 80% test coverage (102 tests)
  - Uses httpx for async OpenRouter API, slowapi for rate limiting
  - gRPC client with mock fallback when Rust service unavailable
  - Session management via cachetools.TTLCache
  - Located in `api-service/` with `ai_resume_api` package (function-based naming)
- **Naming Conventions (Phase 2.6):**
  - Directories: Function-based (`api-service/`, `memvid-service/`, `frontend/`)
  - Containers: Descriptive (`ai-resume-api`, `ai-resume-memvid`, `ai-resume-frontend`)
  - Python Package: Fully-qualified (`ai_resume_api` not generic `app`)
  - Rationale: Clarity in codebase navigation and wheel distribution
- **Container Builds:** Multi-arch (amd64 + arm64) - all complete
  - Frontend: 53 MB (nginx + React SPA)
  - Memvid service: 97 MB (Rust, ~20MB memory at runtime)
  - API service: 192 MB (Python, ~150MB memory at runtime)
- **Streaming Chat (Phase 2.5):** Production-ready with:
  - SSE format (`data:`, `event:`, `stats`, `end` events)
  - Graceful client disconnect handling (CancelledError)
  - Token counting and elapsed_seconds tracking
  - Mock mode for development without OpenRouter API key
- Edge server access required for Phase 5+
- Security hardening (Phase 8) critical before production
- Production .mv2 files are NOT committed to git (mounted at runtime)
- **Current Status:** Phase 5 Container Building complete; all three containers built and tested locally; ready for Edge Deployment

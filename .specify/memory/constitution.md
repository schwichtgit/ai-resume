# Project Constitution

This document defines immutable principles for the project. These principles
govern all development activity, including autonomous Claude Code sessions.
Once established, these principles do not change without explicit human approval.

## Project Identity

**Project Name:** ai-resume
**One-Line Description:** Polyglot web application enabling recruiters to query a candidate's experience via AI chat with semantic search retrieval
**Primary Language(s):** TypeScript (React 19), Python 3.14 (FastAPI), Rust 1.93 (memvid gRPC)
**Target Platform(s):** Linux (amd64, arm64), macOS (amd64, arm64 -- development only)

## Non-Negotiable Principles

1. **Single-file data portability** -- ALL instance content from a single `.mv2` file generated from markdown. No hardcoded data in application code.
2. **Zero hallucination tolerance** -- never fabricate companies, dates, metrics, or skills not in the source resume. 100% factual accuracy is a blocking release gate.
3. **Honest gap identification** -- accurately report what the candidate cannot do. No overselling.
4. **Edge-deployable** -- runs on ARM64 with 4GB RAM, <200MB memory, no external database.
5. **API keys via environment variables only** -- no secrets in images, git, or config files.
6. **Graceful degradation** -- if memvid or LLM unavailable: propagate service status to the frontend; frontend displays "service unavailable" notice with retry capability. Cache-based degradation (serving cached profile data) is deferred to a future phase.
7. **No server-side conversation persistence** -- sessions are ephemeral and in-memory only. No conversation history stored on disk or database. Observability telemetry (traces, metrics, logs) on the observer host is operational metadata and is exempt from this rule.

## Quality Standards

### Testing

- Minimum code coverage: 85% per service
- Test frameworks: Vitest + RTL (frontend), pytest (Python), cargo test (Rust)
- Test categories required: unit, integration, end-to-end
- E2E quality gate: 100% category coverage, 100% factual accuracy, 0% hallucination
- E2E test reliability protocol:
  1. **Health-gate**: Poll the service health endpoint before running any tests. Timeout and abort if the service never becomes healthy.
  2. **Follow 3xx transparently**: Follow redirects up to 3 hops (`curl -L --max-redirs 3`). Redirects are normal infrastructure behavior (nginx trailing slashes, proxy rewrites).
  3. **Retry only on 429**: If an API call returns HTTP 429 (rate limited), respect the `Retry-After` header and retry (max 3 attempts). This is the only retriable condition.
  4. **Fail immediately on all other errors**: Connection refused, timeouts, HTTP 5xx, and any other non-2xx response are immediate test failures. No retries, no sleeps, no masking.

### Code Style

| Language   | Linter               | Formatter   | Type Checker                                        |
| ---------- | -------------------- | ----------- | --------------------------------------------------- |
| TypeScript | ESLint               | Prettier    | tsc (strict mode target; relaxed mode is tech debt) |
| Python     | Ruff                 | Ruff format | mypy/pyright                                        |
| Rust       | Clippy `-D warnings` | cargo fmt   | cargo check                                         |
| Shell      | ShellCheck           | shfmt       | N/A                                                 |

### React/TypeScript Patterns

This project enforces strict React hook and purity patterns via ESLint v10. These constraints reflect React's official guidance, not arbitrary restrictions. **Do not disable rules with eslint-disable comments—refactor code to follow them.**

**Effect Scoping Rule:** Effects must not call setState synchronously. State mutations must be scoped to the effect callback itself, never called from render or outside the effect. Violations indicate a component that is mutating state during render (impure) or attempting to derive state in an event handler (effect should own the mutation).

- **Pattern (correct):** State is set only within the effect callback

```tsx
useEffect(() => {
  setState(newValue); // ✓ scoped to effect
}, [deps]);
```

- **Anti-pattern (violates rules):** Calling setState in render or event handlers

```tsx
const handleClick = () => setState(value); // ✗ state mutation outside effect
```

- **Fix:** Move the mutation into an effect or callback that controls when it fires

**External State Subscription Rule:** When subscribing to external state (window.matchMedia, addEventListener), use `useSyncExternalStore` instead of useState + useEffect. This ensures the component does not render with stale state during SSR or during effect cleanup.

- **Pattern (correct):** useSyncExternalStore for external subscriptions (see `src/hooks/use-mobile.tsx`)

```tsx
const isMobile = useSyncExternalStore(
  (onStoreChange) => {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    mediaQuery.addEventListener('change', onStoreChange);
    return () => mediaQuery.removeEventListener('change', onStoreChange);
  },
  () => window.matchMedia('(max-width: 768px)').matches,
  () => false, // server-side default
);
```

- **Anti-pattern (violates exhaustive-deps):** useState + useEffect with incomplete dependencies

```tsx
const [isMobile, setIsMobile] = useState(false);
useEffect(() => {
  const mediaQuery = window.matchMedia('(max-width: 768px)');
  setIsMobile(mediaQuery.matches);
  // ✗ forgot to add event listener cleanup or dependency tracking
}, []);
```

**Purity in Render:** Functions passed to React hooks (render functions, event handlers, effect callbacks) must be pure—no impure functions like Math.random() in render. If deterministic but varying identifiers are needed (e.g., for styling), use `useId()`.

- **Pattern (correct):** useId for stable, deterministic values (see `src/components/ui/carousel.tsx`)

```tsx
const id = useId();
return <div id={`carousel-${id}`} />; // ✓ stable across renders
```

- **Anti-pattern (violates purity):** Math.random() in render

```tsx
return <div id={`carousel-${Math.random()}`} />; // ✗ impure, ID changes every render
```

**Compliance Checkpoint:** Commit 7049f73 ("refactor(hooks,ui): remove eslint-disable from react-hooks violations") documents patterns from real refactoring:

- `src/hooks/use-mobile.tsx`: useSyncExternalStore example
- `src/components/ui/carousel.tsx`: useId + effect scoping example
- `src/components/ui/sidebar.tsx`: useId vs Math.random decision

These patterns should be referenced as teaching examples for new code, not as special exceptions. Every new component should follow them without eslint-disable comments.

### Rate Limiting

- 10 requests per minute per real client IP
- Must resolve actual client IP from `X-Forwarded-For` / `X-Real-IP` headers, not reverse proxy address
- Rate limit user experience (429 response behavior, retry guidance) to be defined as a separate feature

### Commit Standards

- Format: Conventional Commits (feat, fix, docs, etc.)
- No emoji in commit messages or PR titles
- No AI-isms or self-referential language
- No Co-Authored-By trailers
- Subject line maximum: 72 characters

### Communication Style

- Tone: Technical, direct, and terse
- Forbidden: emoji, marketing adjectives, filler words, self-referential language

### Branching Workflow

- All changes via PR only, no direct commits to `main`
- Conventional prefixes: feat/, fix/, docs/, ci/, refactor/, test/, chore/
- Content and data changes use `chore/` prefix
- Branch protection on `main` as deployment prerequisite

### Versioning

- Semantic Versioning 2.0.0
- Pre-release tags: -alpha.N, -beta.N, -rc.N

## Architectural Constraints

1. **Three-container production runtime** -- Frontend (nginx + React), API (Python FastAPI), Memvid (Rust gRPC). Single responsibility per container. An additional ingest container is permitted for ad-hoc `.mv2` file creation outside the production runtime.
2. **Frontend as router** -- application-level URL routing in frontend nginx. Host nginx handles TLS termination and domain routing only.
3. **gRPC internal, REST/SSE external** -- Rust memvid exposes gRPC. Python API exposes REST/JSON + SSE streaming to browsers.
4. **Stateless containers** -- no instance data in images. `.mv2` files and config mounted as read-only volumes.
5. **LLM via OpenRouter** -- all LLM calls through OpenRouter API. No direct model hosting.
6. **Isolated Python venvs** -- each Python service has its own `.venv` with independent dependencies.

## Security Requirements

1. **Multi-layer prompt injection defense** -- input validation, structural separation, defensive system prompt, output filtering. All four layers required.
2. **No secrets in containers or git** -- API keys via env vars, `.env` in `.gitignore`, validated at startup, never logged.
3. **Rootless read-only containers** -- non-root users, read-only filesystems, `no-new-privileges`.
4. **Network zone isolation** -- containers in dedicated subnet, firewall prevents cross-zone traffic.
5. **Rate limiting on all API endpoints** -- per real client IP throttling (X-Forwarded-For aware), 429 responses.
6. **Dependency vulnerability scanning** -- Grype scans, critical/high CVEs patched within 7 days.
7. **Commit-gate secret scanning** -- block commits containing API keys, tokens, high-entropy strings.

## Out of Scope

1. User authentication -- public resume, no login
2. Multi-user / multi-resume support -- single candidate per instance
3. Real-time resume editing -- content changes require re-ingestion
4. ATS integration -- no applicant tracking system connectors
5. Windows deployment -- Linux containers only
6. Direct model hosting -- no on-device LLM inference

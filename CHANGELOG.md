# Changelog

All notable changes to the **ai-resume** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-beta.9] - 2026-08-24

Security release: remediates a DoS advisory in the `h2` HTTP/2 stack that was
already failing the dependency audit on `main`. Also carries dependency
currency, including a major on the ingest embedding path. No new product
features.

### Security

- **`h2` 0.4.14 -> 0.4.18** (#492), remediating
  [RUSTSEC-2026-0258](https://rustsec.org/advisories/RUSTSEC-2026-0258) --
  "h2 unbounded empty DATA frames", a denial-of-service affecting the HTTP/2
  server stack the memvid gRPC service is built on. The advisory was published
  2026-08-17, after the previous audit ran, so it was already failing
  `task audit` on `main` and would have failed the next scheduled security
  scan. `h2` is a transitive dependency of the hyper/tonic stack, so `cargo
update` alone did not move it -- the fix required targeting the crate
  directly.

### Changed

- Dependency currency -- 8 PRs consolidated into two rollups (#492, #494):
  - **ingest (uv)**: `sentence-transformers` 5.7.0 -> **6.0.0** (major),
    `mypy` 2.3.0 -> 2.3.1, `ruff` `>=0.16.3` -> `>=0.16.4`. Both ingest
    dependency PRs changed only the lockfile: the declared floors already
    admitted the new versions, so resolution had to be pointed at each
    package explicitly.
  - **api-service (uv)**: `uvicorn[standard]` `>=0.52.3` -> `>=0.52.4`,
    `mypy` `>=2.3.0` -> `>=2.3.1`, `ruff` `>=0.16.3` -> `>=0.16.4`.
  - **frontend (npm)**: `input-otp` 1.5.0, `lucide-react` 1.33.0,
    `react-resizable-panels` 4.12.3, `@vitejs/plugin-react` 6.1.0,
    `@vitest/coverage-v8` 4.1.11, `vite` 8.2.2, `vitest` 4.1.11.
  - **github-actions**: `taiki-e/install-action` v2.85.13 -> v2.86.5.

### Notes

- `sentence-transformers` 6.0.0 is a major release on the ingest embedding
  path, and `memvid_sdk` calls the deprecated
  `get_sentence_embedding_dimension`. That method is still present in 6.0.0,
  and the `slow`-marked ingest tests that CI deselects -- the ones that
  exercise real embeddings -- were run explicitly and pass.
- `ruff` 0.16.4 introduces no formatting drift; `ruff format --check` is clean
  on both Python services without reformatting.

## [0.1.0-beta.8] - 2026-08-18

Hardening release: closes four working prompt-injection bypasses, extends the
guardrails to the fit-assessment endpoint, and fixes two pattern false
positives that were rejecting legitimate job descriptions. No new product
features, no outstanding advisories.

### Security

- **Fit assessment was unguarded.** `/api/v1/assess-fit` accepted an arbitrary
  job description, interpolated it into an LLM prompt and returned the result,
  calling neither `check_input` nor `check_output` -- only `/api/v1/chat` was
  protected (#484). The endpoint now checks input _before_ the memvid search
  and the LLM call, so a rejected payload costs nothing and never reaches the
  model, and filters the response on the way out. A refusal is reported in the
  response's own vocabulary (a one-star verdict with an explanatory gap and
  recommendation) rather than the chat endpoint's redirect text.
- **Untrusted job descriptions are now fenced** with a per-request nonce
  (#484). The prompt previously used plain-text section headers
  (`JOB DESCRIPTION:`, `INSTRUCTIONS:`) and inserted the untrusted text raw, so
  a payload could write its own header and forge a section boundary. A
  delimiter the submitter cannot predict is a boundary; a literal header is
  not. This defense does not depend on pattern matching at all.
- **Rubric and instructions moved into the system role** (#484). They governed
  the untrusted text while sharing a conversation turn with it; the user turn
  now carries data only.
- **Four injection bypasses closed** (#483). Detection matched patterns against
  a single whitespace-normalized view, so any rewrite of the same payload
  evaded it. Input is now reduced to several normalized views -- homoglyph
  folded (NFKC alone does not fold Cyrillic look-alikes), leetspeak folded,
  de-spaced, and base64 decoded -- with the patterns run against each. The
  transforms compose, so stacked techniques still reduce. A hit that only
  appears after de-obfuscation is reported as high confidence: needing to
  decode it is evidence of intent.
- **Possessive-object overrides are now detected** (#483). Every existing
  override pattern required `previous|above|all|prior|earlier` between the verb
  and its object, so "ignore your instructions" evaded detection even once an
  obfuscated payload had been decoded.

### Fixed

- **Two pattern false positives that blocked legitimate job descriptions**
  (#484). `enter.*mode` matched real postings across the wildcard --
  "ENTERprise customers ... scale machine learning MODEls" -- and the
  context-extraction pattern rejected "Show us your data engineering
  portfolio", because bare "data" is ubiquitous in job descriptions. Both gaps
  are now bounded and the object must name an internal structure, except for
  `dump`/`output`, where "dump your data" remains an attack while "show us
  your data" does not. A false positive silently refuses a real recruiter, so
  both directions are pinned by tests.
- `xfail_strict = true` is now set (#483). An `xfail` that started passing
  reported `XPASS` and went unnoticed, so a closed gap looked identical to an
  open one and a later regression would reopen it just as quietly. The single
  remaining `xfail` documents an architectural limit -- context-free
  per-message detection cannot observe multi-turn escalation -- and opts out
  explicitly.

### Changed

- Dependency currency -- 12 PRs consolidated into two rollups (#479, #482):
  - **api-service (uv)**: `setuptools` `>=83.0.0` -> `>=84.0.0`,
    `uvicorn[standard]` `>=0.52.1` -> `>=0.52.3`, `pydantic-settings`
    `>=2.14.2` -> `>=2.15.0`, `ruff` `>=0.16.1` -> `>=0.16.3`.
  - **ingest (uv)**: `setuptools` `>=83.0.0` -> `>=84.0.0` (bumped in both the
    dependency list and the build-system requires), `numpy` `>=2.5.1` ->
    `>=2.5.2`, `ruff` `>=0.16.1` -> `>=0.16.3`.
  - **frontend (npm)**: `@hookform/resolvers` 5.9.1, `sonner` 2.0.8,
    `@testing-library/jest-dom` 7.0.1, `eslint-plugin-react-refresh` 0.5.4,
    `globals` 17.11.0, `@types/node` 26.2.0, `eslint` 10.8.1, `vite` 8.2.1.
  - **memvid-service (cargo)**: `async-trait` 0.1.92, `thiserror` 2.0.20,
    `http-body-util` 0.1.5. Applied as a targeted `cargo update -p`; a bare
    `cargo update` moved 163 packages, including `aws-lc-sys` 0.39.1 ->
    0.44.0, far outside the proposed scope.
  - **docker**: frontend `node` 26.5.1 -> 26.7.0-trixie-slim; memvid
    `rust:1.97.1-slim-trixie` and api-service/ingest `ubi10/ubi-micro`
    (`af12ec1` -> `cabedb5`) digests refreshed. Trivy reports 0 HIGH/CRITICAL
    for the incoming ubi-micro digest, matching the outgoing one.
  - **github-actions**: `DavidAnson/markdownlint-cli2-action` v24.2.0,
    `taiki-e/install-action` v2.85.13.

### Notes

- api-service test count moves from 501 to 533 with coverage held at 87%. The
  increase is four `xfail`s converted to passes plus new regression coverage:
  the normalization transforms and the inputs they must leave alone, the
  false-positive corpus, and endpoint-level tests that drive
  `/api/v1/assess-fit` itself. The previous "indirect injection" tests called
  the guardrail functions directly, which proved the functions worked while the
  endpoint invoked neither -- coverage in appearance only.

## [0.1.0-beta.7] - 2026-08-11

Security release: remediates a HIGH-severity advisory in `cryptography` that
shipped in beta.6, plus two transitive npm advisories. Also carries routine
dependency currency. No new product features.

### Security

- **`cryptography` 49.0.0 -> 50.0.0** (#463), remediating CVE-2026-69247 /
  PYSEC-2026-3552 (HIGH). This shipped in beta.6 and was the sole finding
  behind three failing gates: the scheduled Security Scan's Trivy
  container-scan of api-service (`Total: 1 (HIGH: 1, CRITICAL: 0)`), the
  whole-SBOM pip-audit, and the `container-build (api)` job on any open PR.
  The package is transitive, so the lock required an explicit upgrade rather
  than moving on its own.
- **`brace-expansion`** GHSA-rgw5-rvv9-x895 (DoS via unbounded intermediate
  arrays, bypassing the CVE-2026-14257 mitigation) and **`nanoid`**
  GHSA-2v37-7h3g-55p8 (custom generators loop indefinitely when size is zero)
  resolved in the frontend lockfile (#463). Both transitive; `package.json`
  is unchanged by the fix.

With these, `task audit` and `npm audit` are clean again -- the scheduled
Security Scan had failed every run since 2026-08-03.

### Changed

- Dependency currency -- 12 PRs consolidated into two rollups (#463, #468):
  - **api-service (uv)**: `starlette` `>=1.3.1` -> `>=1.4.1` (resolves
    1.6.0), `fastmcp` `>=3.4.5` -> `>=3.4.6` (resolves 3.4.7), `cachetools`
    `>=7.1.6` -> `>=7.1.7`, `uvicorn[standard]` `>=0.52.0` -> `>=0.52.1`,
    `pydantic-settings` `>=2.14.2` -> `>=2.15.0`, `ruff` `>=0.16.1` ->
    `>=0.16.2`.
  - **ingest (uv)**: `sentence-transformers` `>=5.6.1` -> `>=5.7.0`, `ruff`
    `>=0.16.1` -> `>=0.16.2`. The former sits on the embedding path, which CI
    does not cover because it deselects `slow`-marked tests; those were run
    explicitly and pass.
  - **frontend (npm)**: `@hookform/resolvers` 5.7.1, `lucide-react` 1.29.0,
    `react-hook-form` 7.84.0, `globals` 17.9.0, `typescript-eslint` 8.66.0,
    `@types/node` 26.2.0, `eslint` 10.8.1, `vite` 8.2.1.
  - **docker**: frontend `node` 26.5.1 -> 26.7.0-trixie-slim; memvid
    `rust:1.97.1-slim-trixie` digest `5c6f46a` -> `3b28790`.
  - **github-actions**: `DavidAnson/markdownlint-cli2-action` v24.1.0 ->
    v24.2.0, `taiki-e/install-action` v2.85.5 -> v2.85.10.

### Notes

- `RUSTSEC-2025-0141` (bincode unmaintained) now appears in `cargo audit`
  output alongside the three advisories suppressed in `.cargo/audit.toml`.
  It is a warning within the allowed set; `cargo audit` still passes and no
  action is required.

## [0.1.0-beta.6] - 2026-08-03

Stabilization release: dependency currency plus developer-tooling and CI
correctness fixes since beta.5. No new product features, no security
advisories outstanding.

### Changed

- Dependency currency covering two weekly Dependabot sweeps -- 12 PRs
  consolidated into two rollups (#442, #453), plus three bumps merged
  individually (#436, #443, #444):
  - **api-service (uv)**: `fastapi` `>=0.139.2` -> `>=0.141.1`,
    `uvicorn[standard]` `>=0.51.0` -> `>=0.52.0`, `opentelemetry-sdk`
    `>=1.43.0` -> `>=1.44.0`, `prometheus-fastapi-instrumentator` `>=8.0.2`
    -> `>=8.1.0`, `fastmcp` `>=3.4.4` -> `>=3.4.5`, `ruff` `>=0.15.22` ->
    `>=0.16.1`, `types-cachetools` `>=7.0.0.20260518` -> `>=7.0.0.20260713`.
  - **ingest (uv)**: `sentence-transformers` `>=5.4.0` -> `>=5.6.1`, `numpy`
    `>=1.24.0` -> `>=2.5.1`, `ruff` `>=0.15.10` -> `>=0.16.1` (level with
    api-service, so local resolves what CI resolves). The first two sit on
    the embedding path, which CI does not cover because it deselects
    `slow`-marked tests; those were run explicitly and all pass.
  - **frontend (npm)**: minor-and-patch group -- `lucide-react` 1.28.0,
    `@types/node` 26.1.2, `@vitejs/plugin-react` 6.0.5, `vite` 8.2.0,
    `@playwright/test` 1.62.1, `@types/react` 19.2.18, `@types/react-dom`
    19.2.4. Also `jsdom` 29.1.1 -> 30.0.1 (major); no test changes required.
  - **docker**: frontend `node` 26.5.0-trixie-slim -> 26.5.1-trixie-slim.
  - **github-actions**: `taiki-e/install-action` v2 -> v2.85.5,
    `DavidAnson/markdownlint-cli2-action` 24 -> 24.1.0.
- Python formatting and import ordering consolidated on ruff (#445). `black`
  and `isort` were installed but wired into no CI job, Taskfile or git hook,
  and `black` actively disagreed with `ruff format` -- running it produced
  code that failed the `ruff format --check` gate CI enforces. Both removed;
  ruff's `I` rules now carry import ordering.
- Fake API-key fixtures in the api-service tests moved to module-level
  constants (#448). The pre-commit secret scanner matches the shape of an
  inline `api_key="..."` assignment rather than the value, and reads whole
  staged files, so it blocked every commit touching those files regardless
  of what changed.

### Fixed

- `task check` and `task ci` aborted at their final step with
  `Task "build" does not exist` -- no root `build` target was ever defined,
  so neither had run to completion (#446). Added, mirroring the CI build
  steps.
- Dependabot left `uv.lock` stale on every Python update (#447). The `pip`
  ecosystem edits `pyproject.toml` without regenerating the lock, and CI's
  `uv sync` silently re-resolved the stale lock instead of failing, so the
  drift stayed invisible until it surfaced locally. Both Python directories
  moved to `package-ecosystem: uv`, and `uv lock --check` now runs ahead of
  `uv sync` in CI so drift fails the build regardless of how it got there.
- Removed the `black` fallback from the post-edit hook (#445), which
  silently reformatted Python files into a state failing the CI format gate
  whenever ruff was absent from `PATH`.

## [0.1.0-beta.5] - 2026-07-26

Stabilization release: dependency currency since beta.4. No new product
features, no security advisories outstanding.

### Changed

- Dependency currency rollup consolidating the full weekly Dependabot sweep --
  10 PRs across 5 ecosystems (#431), plus a follow-up group bump (#432):
  - **api-service (pip)**: `grpcio` and `grpcio-tools` `>=1.82.1` →
    `>=1.83.0`, `prometheus-client` `>=0.25.0` → `>=0.26.0`, `cachetools`
    `>=7.1.4` → `>=7.1.6`, `click` floor raised `>=8.3.3` → `>=8.4.2` to match
    the version already resolved for PYSEC-2026-2132. `uv.lock` regenerated in
    the same commit.
  - **frontend (npm minor-and-patch group, 33 updates)**: Radix UI primitives,
    `@hookform/resolvers` 5.5.7, `lucide-react` 1.27.0, `react-hook-form`
    7.83.0, `recharts` 3.10.1, `eslint` 10.8.0, `@playwright/test` 1.62.0,
    `globals` 17.8.0. Also `@testing-library/jest-dom` 6.9.1 → 7.0.0 (major);
    no test changes required. Lock regenerated from `main` to preserve prior
    security fixes; `npm audit` clean.
  - **memvid-service (cargo)**: `serial_test` 3 → 4 (major). The manifest
    constraint was bumped alongside the lock; no test changes required.
  - **docker**: api-service and ingest `ubi10/ubi-micro` digest `6cc8b04` →
    `af12ec1`. Trivy reports 0 HIGH/CRITICAL for the incoming digest (also 0
    including unfixed), matching the outgoing digest.

## [0.1.0-beta.4] - 2026-07-24

Stabilization release: security remediation and dependency currency since
beta.3. No new product features.

### Security

- **react-router HIGH advisory GHSA-qwww-vcr4-c8h2** (RSC-mode CSRF bypass):
  migrated the frontend from `react-router-dom` 7.18.1 to `react-router` 8.3.0
  (#418). React Router v8 consolidated into the single `react-router` package
  and no longer publishes `react-router-dom`, so Dependabot could not auto-fix
  it; the three import sites were repointed with no API changes. The advisory
  is RSC-mode specific and not reachable in this client-side `BrowserRouter`
  SPA, but v8 is the durable fix and clears the alert.
- **Whole-SBOM dependency audit greened** (#417), red since ~2026-06-29. Fixed
  `click` `>=8.3.3` (PYSEC-2026-2132) via a direct transitive pin,
  `crossbeam-epoch` 0.9.20 (RUSTSEC-2026-0204) and `memmap2` 0.9.11
  (RUSTSEC-2026-0186) in memvid-service. The lopdf/quick-xml advisories
  (RUSTSEC-2026-0187/0194/0195) are capped by `memvid-core` 2.0.140 and not
  reachable at serving time (pre-built read-only `.mv2`); documented in
  `memvid-service/.cargo/audit.toml` with upstream tracking at
  memvid/memvid#242.
- **setuptools** `>=83.0.0` in ingest (#413) with `uv.lock` regenerated (#416)
  to clear CVE-2026-59890 (GHSA-h35f-9h28-mq5c) -- the pip PR only touched the
  manifest, so the lock sync was required to close the alert.
- **torch** `2.13.0` in ingest via the rollup (#412), clearing CVE-2025-3000.
- **brace-expansion** 5.0.8 in frontend (HIGH) via the rollup (#412).

### Changed

- Dependency currency rollups consolidating the Dependabot queue across #412
  (13 PRs, 6 ecosystems), #415 (frontend, 39 updates) and #414 (memvid cargo),
  plus standalone bumps (#398, #400):
  - **api-service (pip)**: `fastapi` `>=0.139.2`, `opentelemetry-api`/
    `-exporter-otlp` `>=1.44.0`, `-instrumentation-fastapi` `>=0.65b0`, `mcp`
    `1.28.1`; dev `ruff` `>=0.15.22`. `uv.lock` regenerated per manifest change.
  - **frontend (npm)**: OpenTelemetry web `0.221`/`2.10`, Radix UI primitives,
    `@tanstack/react-query` 5.101.4, `lucide-react` 1.26, `react-hook-form`
    7.82, `@tailwindcss/vite` 4.3.3, `vite` 8.1.5, `react` 19.2.8. Locks
    regenerated from `main` to preserve prior security fixes; `npm audit` clean.
  - **memvid-service (cargo)**: `tokio` 1.53.1, `serde` 1.0.229, `anyhow`
    1.0.104, `async-trait` 0.1.91, `thiserror` 2.0.19, `http-body-util` 0.1.4,
    `crossbeam-epoch` 0.9.20, `memmap2` 0.9.11.
  - **docker**: frontend `node` and memvid-service `rust` base-image digest
    bumps (#401, #400).
  - **github_actions**: `actions/setup-node` v6 → v7,
    `SonarSource/sonarqube-scan-action` 8.2.1.
- eslint configuration cleanup: ignore generated `coverage/` and scope the
  shadcn `react-refresh/only-export-components` rule off for
  `src/components/ui/**`; `eslint .` now reports zero warnings (#419).

## [0.1.0-beta.3] - 2026-07-15

Stabilization release: dependency currency and toolchain modernization since
beta.2. No new product features.

### Changed

- TypeScript 7 type-checking (#394). Adopted the TS7 native compiler for the
  type-check gate via a `typescript-7` npm alias, while keeping TypeScript
  `6.0.3` for ESLint and the IDE -- no released `typescript-eslint` supports TS7
  yet (its peer range caps at `typescript <6.1.0`), so a straight bump crashes
  the linter. Also fixed the gate itself: CI and the Taskfile ran a bare
  `tsc --noEmit` against the root solution config (`files: []`), a no-op that
  type-checked nothing; switched to `tsc -b`, which traverses the project
  references and now covers all `src` files. Made `chart.tsx` recharts-3/TS7
  compliant (the only file the real gate flagged).
- Dependency currency rollups consolidating the open Dependabot queue across
  #380, #392 and #395, plus standalone bumps (#370, #378, #381):
  - **api-service (pip)**: `fastapi` `>=0.139.0`, `setuptools` `>=83.0.0`,
    `uvicorn` `>=0.50.0`, `grpcio`/`grpcio-tools` `>=1.82.1` (protobuf cascaded
    6.x → 7.x), `fastmcp` `>=3.4.4`; dev `ruff` `>=0.15.21`, `mypy` `>=2.3.0`.
    `uv.lock` regenerated in the same commit as each manifest change.
  - **frontend (npm)**: OpenTelemetry web `0.220`, Radix UI primitives,
    `lucide-react` 1.24, `react-hook-form` 7.81, `react-router-dom` 7.18.1,
    `recharts` 3.9.2, `react-resizable-panels` 4.12.2, `eslint` 10.7.0,
    `prettier` 3.9.5, `typescript-eslint` 8.64.0, `vite` 8.1.4, `@types/node`
    26.1. Locks regenerated from `main` to preserve prior security fixes;
    `npm audit` clean.
  - **ingest (uv)**: `transformers` `5.0` → `5.5` (transitive); dev tooling
    (`pytest` 9.1.1, `pytest-cov` 7.1.0, `ruff` 0.15.21, `mypy` 2.3.0, `black`
    26.5.1, `isort` 8.0.1) aligned with api-service so local and CI resolve
    identically.
  - **docker**: frontend `node` `26.4.0` → `26.5.0-trixie-slim`; api-service and
    ingest `ubi10/ubi-micro` digest bump; memvid-service `rust` `1.96.0` →
    `1.97.0-slim-trixie`.
  - **github_actions**: `DavidAnson/markdownlint-cli2-action` v24,
    `arduino/setup-task` v3.

## [0.1.0-beta.2] - 2026-06-29

Stabilization release: dependency currency and CI signing fixes. No new
product features.

### Changed

- Dependency currency rollup consolidating 9 Dependabot PRs (#366)
  - **api-service (pip)**: OpenTelemetry core `opentelemetry-api`/`-sdk`/`-exporter-otlp` `>=1.42.1` → `>=1.43.0` and `-instrumentation-fastapi` `>=0.63b1` → `>=0.64b0` (bumped together to keep the otel stack aligned); `prometheus-fastapi-instrumentator` `>=8.0.0` → `>=8.0.2`; `ruff` `>=0.15.18` → `>=0.15.20` (dev).
  - **frontend (npm minor-and-patch group, 10 updates)**: `recharts` 3.9.0, `eslint` 10.6.0, `prettier` 3.9.1, `typescript-eslint` 8.62.0, `vite` 8.1.0, `@tanstack/react-query`, `@playwright/test`, `@types/node`, `@vitejs/plugin-react`, `globals`. Lock regenerated from `main` to preserve the prior undici/brace-expansion security fixes; `npm audit` clean.
  - **frontend (docker)**: `node` `26.3.1-trixie-slim` → `26.4.0`.
  - **memvid-service (cargo)**: `anyhow` `1.0.102` → `1.0.103`.
  - **github_actions**: `actions/cache` `v5` → `v6`.

### Fixed

- CI container registry login (#356, #367). Replaced the deprecated `redhat-actions/podman-login@v1` (declares Node 20, which GitHub Actions is sunsetting) with an inline `podman login` (#356), then added an inline `cosign login` alongside it (#367) -- the bare `podman login` authenticated podman for image push but not cosign (which uses go-containerregistry's docker-config keychain, not podman's `auth.json`), so `cosign attest`/`sign` failed with `UNAUTHORIZED`. Both now authenticate to ghcr.io via `GITHUB_TOKEN` at all sign sites in `ci.yml` and `release.yml`.
- frontend `Dockerfile` cleanups (#369): corrected the stale builder base-image comment (`node 26.3.0` -> `26.4.0`) left by the #366 bump, and silenced hadolint DL3018 with a rationale (Alpine's rolling repo makes apk version pins break on refresh; `apk upgrade --no-cache` + the digest-pinned base already control the patch level).

## [0.1.0-beta.1] - 2026-06-20

First **beta**. The feature set is complete; this line is bug-fix and
stabilization only -- dependency currency, security hardening, CI/tooling, and a
documentation overhaul. No new product features since alpha.23.

### Security

- `msgpack` bumped `1.1.2` → `1.2.1` (#345) -- resolves GHSA-6v7p-g79w-8964 (HIGH): out-of-bounds read / crash on `Unpacker` reuse. Transitive via `poetry[filecache]` → `cachecontrol` (present only under the `sbom` extra); surfaced by a Trivy lockfile scan, no Dependabot PR existed.
- `undici` `7.25.0` → `7.28.0` and `brace-expansion` `5.0.2` → `5.0.6` in the frontend (#341) -- resolves GHSA-vmh5-mc38-953g (HIGH, undici TLS cert-validation bypass) plus six further undici advisories, and GHSA-jxxr-4gwj-5jf2 (moderate, brace-expansion ReDoS). `brace-expansion` was a deep transitive with no Dependabot PR; applied via `npm audit fix`. `npm audit` now reports 0 vulnerabilities.

### Added

- `task audit` -- a whole-SBOM vulnerability sweep across all ecosystems (#351): `npm audit`, `pip-audit` (environment mode, sidestepping the uv-standalone-Python `ensurepip` crash), and `cargo audit`. File-based suppressions via per-service `.pip-audit-ignore` (mirrors `.trivyignore`). A weekly `dependency-audit` job in `security.yml` runs it on schedule, catching newly-disclosed advisories against already-pinned deps -- the gap Dependabot misses.

### Changed

- Dependency currency rollup consolidating 8 Dependabot PRs plus transitive security fixes (#341): api-service `python-multipart`/`pydantic-settings`/`structlog`/`black`/`ruff`; frontend npm minor-and-patch group (14 updates); docker base-image digests (node, `alpine` 3.23→3.24, rockylinux ×2, rust, distroless); `SonarSource/sonarqube-scan-action` 8.1→8.2.
- api-service: `starlette` `1.2.1` → `1.3.1`, `cryptography` `46.0.7` → `49.0.0`, `pyjwt` `2.12.0` → `2.13.0` (#341-era follow-up); `fastapi` `0.136.3` → `0.138.0`, `pytest` `9.0.3` → `9.1.1` (#347).
- frontend: `@types/node` `25.9.3` → `26.0.0` (#348); npm minor-and-patch group (32 updates -- `@radix-ui/*`, `@playwright/test`, `@vitest/coverage-v8`, etc.).
- memvid-service: `tower-http` `0.6.11` → `0.7.0` (#346, cargo 0.x semver-breaking; verified via build + clippy + tests).
- **Require Rust 1.96** across the toolchain (#352): `memvid-service/rust-toolchain.toml` `1.93.0` → `1.96.0` (the pin that actually forced local rustc 1.93), a `Cargo.toml` `rust-version = "1.96"` MSRV gate, `check-deps.sh` floors, and all four `ci.yml` toolchain pins -- aligning local dev with the container build base.
- CI: `actions/checkout` `v6` → `v7` (#349); Trivy scanner pinned to `v0.71.2` in `security.yml` (#350); the CI workflow is now named `CI` (was a bare `I`) (#354).

### Fixed

- Production `deployment/observability/prometheus.yml` scraped memvid metrics on `:50051` (the gRPC port, which serves no `/metrics`) instead of `:9090` (#353) -- prod memvid metrics were never collected. The dev config was already correct.

### Documentation

- README and `docs/` currency overhaul (#352): cross-referenced every claim against the code. Ask mode documented as implemented (was "Planned"); corrected Dockerfile base-image descriptions, the GitHub code-scanning dismissal-reason format, and the OBSERVABILITY metrics port; replaced the stale security-scan appendix with the live workflow. Removed the EOL `docs/archive/` set (11 files) and two generic Claude Code hook docs (~624 lines, folded into a concise DEVELOPMENT.md subsection); both preserved in git history.

## [0.1.0-alpha.23] - 2026-06-15

### Security

- `@babel/core` bumped `7.29.0` → `7.29.7` (#327) -- resolves Dependabot alert #84 (GHSA-4x5r-pxfx-6jf8, low): `Arbitrary File Read via sourceMappingURL Comment` (CVE-2026-49356, vulnerable `<=7.29.0`, patched `7.29.6`). Transitive dev dependency pulled in by `eslint-plugin-react-hooks@7.1.1` (`@babel/core: ^7.24.4`); fixed lock-only via `npm update @babel/core` with **no** downgrade of `eslint-plugin-react-hooks` (Dependabot's auto-path would have downgraded it to 5.2.0, which is why it could not open the PR itself).
- 15 memvid base-image `libssl3t64` CVEs cleared by the `gcr.io/distroless/cc-debian13:nonroot` digest re-pin in #321 (see below) -- the new digest ships `libssl3t64 3.5.6-1~deb13u2`. Confirmed by a fresh Trivy scan: GitHub code-scanning alerts #551 (CVE-2026-45447, HIGH), #552-555 (`-34182`/`-34183`/`-42764`/`-45445`, MEDIUM) and the low-severity batch (#556-565) all auto-transitioned to `fixed`. The remaining open alert is `torch` CVE-2025-3000 (no upstream fix available).

### Changed

- Dependency currency rollup consolidating 13 Dependabot PRs (#321)
  - **api-service (pip)**: `python-multipart` `>=0.0.29` → `>=0.0.32` (#317), `pydantic-settings` `>=2.14.0` → `>=2.14.1` (#315), `structlog` `>=25.5.0` → `>=26.1.0` (#316)
  - **api-service (dev)**: `black` `>=26.3.1` → `>=26.5.1` (#319), `ruff` `>=0.15.16` → `>=0.15.17` (#318)
  - **frontend (npm minor-and-patch group, 14 updates)**: `@opentelemetry/*` (`context-zone` 2.7.1 → 2.8.0, `exporter-trace-otlp-http` & `instrumentation-fetch` 0.218.0 → 0.219.0), `lucide-react` 1.17.0 → 1.18.0, `react-hook-form` 7.77.0 → 7.79.0, `@tailwindcss/typography` 0.5.16 → 0.5.20, `@tailwindcss/vite` 4.3.0 → 4.3.1, `@types/node` 25.9.2 → 25.9.3, `eslint` 10.4.1 → 10.5.0, `prettier` 3.8.3 → 3.8.4, `typescript-eslint` 8.60.1 → 8.61.0 (#320)
  - **docker**: `node:26.3.0-trixie-slim` digest re-pin (#313), `alpine` 3.23.4 → 3.24.0 (#312), `rockylinux/rockylinux:10-minimal` digest re-pin in api-service (#311) and ingest (#310), `rust:1.96.0-slim-trixie` digest re-pin (#309), `gcr.io/distroless/cc-debian13:nonroot` digest re-pin (#308 -- picks up the `libssl3t64` security fix noted above)
  - **github_actions**: `SonarSource/sonarqube-scan-action` 8.1.0 → 8.2.0 (#314)
- Dependency currency rollup consolidating 4 Dependabot PRs (#326)
  - **api-service (pip)**: `starlette` `>=1.2.1` → `>=1.3.1` (#322); `cryptography` 46.0.7 → 49.0.0 (#323, transitive -- the resolver advanced past Dependabot's requested 48.0.1 to current-latest); `pyjwt` 2.12.0 → 2.13.0 (#324, transitive)
  - **frontend (npm minor-and-patch group, 32 updates)**: `@radix-ui/*` component bumps (accordion, alert-dialog, avatar, select, tabs, tooltip, and others), `@playwright/test` 1.60.0 → 1.61.0, `@vitest/coverage-v8` 4.1.8 → 4.1.9, `eslint-plugin-react-refresh` 0.5.2 → 0.5.3, `typescript-eslint` 8.61.0 → 8.61.1 (#325)
- Dependency currency rollup consolidating 8 Dependabot PRs (#306)
  - **api-service (pip)**: `grpcio` `>=1.80.0` → `>=1.81.0` (#299), `uvicorn` `>=0.48.0` → `>=0.49.0` (#300), `opentelemetry-instrumentation-fastapi` `>=0.50b0` → `>=0.63b1` (#301), `fastmcp` `>=3.3.1` → `>=3.4.2` (#302)
  - **api-service (dev)**: `ruff` `>=0.15.15` → `>=0.15.16` (#304)
  - **frontend (npm minor-and-patch group, 37 updates)**: `@radix-ui/*`, `@tanstack/react-query`, and others (#305)
  - **frontend (docker)**: `node` `26.2.0-trixie-slim` → `26.3.0-trixie-slim` (#298)
  - **memvid-service (cargo minor-and-patch group)**: `chrono` 0.4.44 → 0.4.45, `prost`/`prost-derive` 0.14.3 → 0.14.4, transitive `windows-sys` bumps (#303)
  - `api-service/uv.lock` regenerated to match the #306 `pyproject.toml` bumps in a follow-up sync (#307).
- Align every Node.js pin on Node 26 (#297) -- CI ran `setup-node` on Node 22 while the frontend build container was already `node:26.2.0`. `ci.yml` / `ci-base.yml` `NODE_VERSION` and `setup-node` 22 → 26, `scripts/check-deps.sh` required-tier floors Node `22.14.0` → `26.2.0` / npm `10.9.0` → `11.0.0`, and the README / `docs/DEVELOPMENT.md` / project-guide prerequisites updated to match (also correcting a stale `node:24` frontend build-stage reference). `frontend/Dockerfile` was already on `node:26.2.0-trixie-slim` and is unchanged.

### Fixed

- Recurring `container-build (ingest, amd64)` `no space left on device` failures (#328). The ingest container drags in the full torch/nvidia CUDA wheel stack (~5-6 GB unpacked) via `sentence-transformers`, which exhausts the ~14 GB root volume while podman stores the `.venv` layer blob under `/var/tmp`. The `jlumbroso/free-disk-space` step now runs with `large-packages: true` and `swap-storage: true` (previously both `false`), reclaiming ~8-10 GB more. Stopgap; the durable image-size fix (pin Linux builds to CPU-only torch to drop the nvidia stack entirely) remains a tracked follow-up.

## [0.1.0-alpha.22] - 2026-06-01

### Changed

- Dependency currency rollup consolidating 7 Dependabot PRs (#295)
  - **api-service**: `opentelemetry-api` `>=1.29.0` → `>=1.42.1` (#289), `opentelemetry-sdk` `>=1.41.1` → `>=1.42.1` (#290), `prometheus-fastapi-instrumentator` `>=7.1.0` → `>=8.0.0` (#291 — raises the pyproject floor to match the `8.0.0` already locked in alpha.21's #286, which had auto-upgraded the instrumentator to unblock starlette 1.x; `starlette` stays `>=1.2.1`, no regression)
  - **api-service (dev)**: `ruff` `>=0.15.13` → `>=0.15.15` (#288), `pytest-asyncio` `>=1.3.0` → `>=1.4.0` (#293)
  - **memvid-service**: Rust builder base `rust:1.95.0-slim-trixie` → `rust:1.96.0-slim-trixie` (#287, `docker` ecosystem)
  - **frontend**: Node builder base `node:24.15.0-trixie-slim` → `node:26.2.0-trixie-slim` (#292, `docker` ecosystem; major bump — the npm build stage and the full frontend test suite pass on Node 26). Node 26.3.0 released upstream the same day but its official Docker image was not yet published, so 26.2.0 is the latest buildable base.
  - All container base-image `@sha256` digests were re-resolved fresh against current-latest (not just the two Dependabot proposed); only `node` and `rust` had drifted. `rockylinux:10-minimal` remains VERSION_ID 10.1 (Rocky 10.2 not yet shipped), so the load-bearing `'libgcc_s-*.so*'` glob in the api/ingest Dockerfiles stays.
- Tech-stack reference in the project guide updated Rust `1.95` → `1.96` to match the bumped builder base (#295).

## [0.1.0-alpha.21] - 2026-05-31

### Security

- `dulwich` bumped from `0.25.2` to `1.2.6` (constraint floor `1.2.5`) in api-service (#286) -- resolves Dependabot alerts #73 (`Command Injection via Merge Driver Path`) and #74 (`arbitrary file write via NTFS-hostile tree entries on Windows`), both HIGH. `dulwich` is a transitive dependency; the bump was driven via `uv lock --upgrade-package dulwich`. Both alerts auto-transitioned to `fixed` after merge.

### Changed

- Dependency currency rollup consolidating 9 Dependabot PRs (#286)
  - **api-service**: `starlette` `>=0.49.1` → `>=1.2.1` (#284), `uvicorn` `>=0.44.0` → `>=0.48.0` (#279), `python-multipart` `>=0.0.28` → `>=0.0.30` (#280, resolver advanced past the requested `>=0.0.29`), `opentelemetry-exporter-otlp` `>=1.41.1` → `>=1.42.1` (#281)
  - **api-service (dev)**: `types-cachetools` → `>=7.0.0.20260518` (#282)
  - **ingest**: `memvid-sdk` `2.0.159` → `2.0.160` (#278)
  - **memvid-service (cargo minor-and-patch group)**: `h2` 0.4.13 → 0.4.14, `hyper` `1.9` → `1.10`, `opentelemetry_sdk` 0.32.0 → 0.32.1, `serial_test` 3.4.0 → 3.5.0 (#283); plus `memvid-core` `2.0.139` → `2.0.140` (manual bump alongside the group — the Rust crate's own version line, distinct from the 2.0.160 Python/npm packages)
  - **frontend (minor-and-patch group, 6 updates)**: `date-fns` 4.4.0, `lucide-react` 1.17.0, `react-hook-form` 7.77.0, `react-router-dom` 7.16.0, `eslint` 10.4.1, `typescript-eslint` 8.60.0 (#285)
  - **starlette 1.x unblocked**: the upgrade parked since alpha.18 (#239-era note) and explicitly "Excluded" in alpha.18 (#253) and alpha.20 cleared on its own — the resolver auto-upgraded `prometheus-fastapi-instrumentator` `7.1.0` → `8.0.0`, which dropped the `starlette<1.0.0` cap (upstream `trallnag/prometheus-fastapi-instrumentator#357`). No manual intervention beyond bumping the `starlette` floor.
- Pin all container base images to immutable `@sha256` manifest-list digests across the four Dockerfiles (#286) -- `frontend` (`node:24.15.0-trixie-slim`, `alpine:3.23.4`), `api-service` / `ingest` (`rockylinux/rockylinux:10-minimal`, `ghcr.io/astral-sh/uv` pinned to `0.11.17`, `registry.access.redhat.com/ubi10/ubi-micro` which was previously untagged=`latest`), `memvid-service` (`rust:1.95.0-slim-trixie`, `gcr.io/distroless/cc-debian13:nonroot`). Multi-arch (amd64+arm64) preserved by pinning the image-index digest. This freezes the libgcc snapshots together and is the durable fix for the base-image drift previously patched with the `'libgcc_s-*.so*'` glob in #263 — the glob is retained because it remains structurally load-bearing (Rocky ships libgcc as `libgcc_s-14-<date>.so.1` plus a symlink; removing the glob dangles the symlink and the api container fails at startup with `ImportError: libgcc_s.so.1`).
- Add a `docker` package-ecosystem to `.github/dependabot.yml` for all four service directories (#286) so the newly-pinned base-image digests continue to receive updates via Dependabot PRs.
- Ingest e2e tests now self-orchestrate their own `.mv2` data from the shipped `data/example_resume.md` (Jane Chen persona) rather than depending on a developer-generated `data/.memvid/resume.mv2` artifact, and run at release time (#274). A session-scoped `jane_mv2_base` fixture ingests the template once via `ingest_memory()`; `isolated_mv2` copies it per-test to preserve exclusive-lock isolation.
- Dependency currency rollup consolidating 7 Dependabot PRs (#273)
  - **api-service**: `fastapi` `>=0.136.1` → `>=0.136.3` (#269), `cachetools` `>=5.5.0` → `>=7.1.4` (#266, aligns with `types-cachetools` 7.x), `setuptools` `>=80.10.2` → `>=82.0.1` (#268)
  - **api-service (dev)**: `mypy` `>=1.20.2` → `>=2.1.0` (#267)
  - **memvid-service (cargo)**: `tower-http` 0.6.10 → 0.6.11, `serde_json` 1.0.149 → 1.0.150 (#270)
  - **frontend (minor-and-patch group, 11 updates)**: bundled (#272)
  - **github_actions**: `SonarSource/sonarqube-scan-action` 8.0.0 → 8.1.0 (#265)

### Fixed

- `task lint` prettier/markdown race with `npm ci` (#275). `lint:prettier` and `lint:markdown` invoke `npx --prefix frontend …` but did not depend on `frontend:setup` (which runs `npm ci`, including `rm -rf node_modules`). With stale `node_modules` (e.g. after a branch switch), go-task scheduled the install concurrently with the lint tasks and prettier/markdownlint died with `ERR_MODULE_NOT_FOUND`. Declaring `deps: [frontend:setup]` makes go-task dedup the install so it completes once before any lint task runs.

### Documentation

- Added the missing `AI Context` block (Situation / Approach / Technical Work / Lessons Learned) to Jane Chen's early-stage B2B SaaS startup experience entry in `data/example_resume.md` (#276) -- every other experience entry in the template already had it.

## [0.1.0-alpha.20] - 2026-05-22

> Supersedes the withdrawn `0.1.0-alpha.19` tag, which was published twice and withdrawn twice on 2026-05-21/2026-05-22. The first tag was withdrawn after the api container failed to start with `ImportError: libgcc_s.so.1: cannot open shared object file`; the re-cut tag (which included the libgcc Dockerfile fix in #263) was withdrawn after the release workflow's signature-verify job failed on `ai-resume-ingest` because release-validate raced two concurrent CI runs on the same SHA and selected the dev-versioned `push`-event run instead of the tag-event run. Cutting fresh as alpha.20 from current `main` HEAD avoids reusing a burned tag.

### Changed

- Dependency currency rollup consolidating 8 Dependabot PRs (#260)
  - **api-service**: `fastapi` `>=0.115.6` → `>=0.136.1` (#252, floor bump spanning 21 minor versions; still 0.x), `fastmcp` `>=3.2.4` → `>=3.3.1` (#251)
  - **api-service (dev)**: `ruff` `>=0.15.12` → `>=0.15.13` (#254), `poetry` (sbom) `>=2.3.4` → `>=2.4.1` (#256)
  - **api-service (transitive)**: `idna` 3.11 → 3.16 (#258 asked for `>=3.15`; resolver chose 3.16). Lock regeneration also picked up `pydantic` 2.13.3 → 2.13.4 and `poetry-core` 2.3.2 → 2.4.0 as collateral.
  - **ingest**: `idna` 3.11 → 3.15 (#259)
  - **frontend (minor-and-patch group, 16 updates)**: bundled (#257)
  - **memvid-service**: `metrics` 0.24.5 → 0.24.6 (#255, Cargo.lock-only)
  - Conflict resolution: the four api-service `pyproject.toml` constraint bumps touched adjacent lines and were merged into a single combined commit with one paired `uv lock --upgrade-package …` regeneration.
- Memvid OpenTelemetry stack bumped 0.31 → 0.32 (#261)
  - `opentelemetry` 0.31 → 0.32 (#239), `opentelemetry-otlp` 0.31 → 0.32 (#241), `opentelemetry_sdk` 0.31 → 0.32 (#243)
  - Manual paired bump: `tracing-opentelemetry` 0.32.1 → 0.33 (no Dependabot PR — `tracing-opentelemetry 0.33.0` published to crates.io 2026-05-18, pins `opentelemetry ^0.32.0`, which unblocked the previously parked triple from alpha.18's "Excluded from this release").
  - Collateral lock updates: `opentelemetry-http` / `opentelemetry-proto` 0.31 → 0.32, `reqwest` 0.12 → 0.13 (transitive via `opentelemetry-otlp`), adds `tonic-types` 0.14.6 as a new transitive.
  - No code changes — the API surface used in `memvid-service/src/otel.rs` (`SpanExporter::builder().with_tonic()`, `SdkTracerProvider::builder()`, `Resource::builder_empty()`, `OpenTelemetryLayer::new(tracer)`) is forward-compatible between 0.31 and 0.32.

### Fixed

- api Dockerfile: stage `libgcc_s` versioned target alongside the symlink so it resolves in the runtime image (#263). The python-deps stage's `find … -name "libgcc_s.so*"` glob matched the `libgcc_s.so.1` symlink but not its versioned target `libgcc_s-14-<snapshot>.so.1` (because of the `-14-` infix). This worked by coincidence as long as `rockylinux/rockylinux:10-minimal` and `registry.access.redhat.com/ubi10/ubi-micro` shipped the same libgcc snapshot; after ubi-micro rolled forward to `libgcc-14-20251022` while rocky-10-minimal stayed on `libgcc-14-20250617`, the symlink dangled in the final image and pydantic-core / grpcio / any native extension that dynamically links libgcc_s.so.1 failed to import at container startup. Added a second glob `'libgcc_s-*.so*'` to the find loop. Same pattern that already makes `libstdc++.so*` work (the versioned filename also matches because there's no infix). When rocky-10-minimal eventually moves to RHEL 10.2 (matching ubi-micro), this fix becomes a no-op — but it also hardens against the next time the two base images drift.

### Excluded from this release

- **#253** (`starlette` `>=0.49.1` → `>=1.0.1` in api-service) — blocked by `prometheus-fastapi-instrumentator==7.1.0` (latest on PyPI) capping `starlette<1.0.0`. Upstream fix `trallnag/prometheus-fastapi-instrumentator#357` ("chore: Port to starlette 1.0") is open but unmerged as of 2026-05-21. Parked until a `prometheus-fastapi-instrumentator >7.1.0` is published with starlette-1.0 support.

## [0.1.0-alpha.18] - 2026-05-14

### Security

- `urllib3` bumped from `2.6.3` to `2.7.0` in api-service (#247) -- closes Trivy code-scanning alerts for `CVE-2026-44431` (sensitive headers forwarded across origins) and `CVE-2026-44432` (decompression-bomb safeguards bypassed in parts of the streaming API), both HIGH severity. Until this landed, every Dependabot PR's `container-build (api, amd64/arm64)` job was failing the Trivy gate on these two CVEs; the rollup restored CI green on the api container path.
- `python-multipart` bumped from `0.0.26` to `0.0.28` (constraint `>=0.0.27` → `>=0.0.28`; lock `0.0.26` → `0.0.28`) in api-service (#247) -- closes code-scanning alert #549 (`CVE-2026-42561`, HIGH, DoS via unbounded multipart part headers). Alert auto-transitioned to `fixed` after the post-merge SARIF reconcile.
- `authlib` bumped from `1.6.11` to `1.6.12` in api-service (#247).

### Changed

- Dependency currency rollup consolidating 11 Dependabot PRs (#247)
  - **api-service**: `urllib3` 2.6.3 → 2.7.0 (#244), `authlib` 1.6.11 → 1.6.12 (#245), `python-multipart` `>=0.0.27` → `>=0.0.28` (#233), `structlog` `>=24.4.0` → `>=25.5.0` (#234), `pydantic` `>=2.13.3` → `>=2.13.4` (#235)
  - **api-service (dev)**: `black` `>=24.10.0` → `>=26.3.1` (#236), `ruff` `>=0.8.6` → `>=0.15.12` (#237)
  - **frontend (minor-and-patch group, 12 updates)**: bundled (#240); `@opentelemetry/exporter-trace-otlp-http` 0.216 → 0.218 plus `protobufjs` removal as a transitive cleanup (#246)
  - **memvid-service (minor-and-patch group, 6 updates)**: bundled (#238)
  - Conflict resolution: the five api-service `pyproject.toml` constraint bumps touched adjacent lines and were merged into a single combined commit; the two frontend opentelemetry-touching PRs were merged by taking the newer exporter version and keeping the bumped instrumentation-fetch from the group.
- Dependency currency rollup consolidating 8 Dependabot PRs (#229)
  - **api-service**: `pydantic-settings` `>=2.13.1` → `>=2.14.0` (#222), `grpcio` `>=1.69.0` → `>=1.80.0` (#223), `prometheus-fastapi-instrumentator` `>=7.0.0` → `>=7.1.0` (#225), `python-multipart` `>=0.0.26` → `>=0.0.27` (#226) -- the python-multipart bump was a partial intermediate step; #247 advanced it to `>=0.0.28` to clear the CVE-2026-42561 fixed-version gate
  - **api-service (dev)**: `types-cachetools` `>=5.5.0` → `>=7.0.0.20260503` (#224)
  - **frontend (minor-and-patch group, 14 updates)**: bundled (#228)
  - **memvid-service (cargo minor-and-patch group)**: `metrics` 0.24.3 → 0.24.5, `metrics-exporter-prometheus` 0.18.1 → 0.18.3 (#227)
  - **github_actions**: `SonarSource/sonarqube-scan-action` 7.1.0 → 8.0.0 (#221)
- `react-day-picker` bumped from `9.14.0` to `10.0.0` in frontend (#248) -- major bump that removes the v9-deprecated navigation/event props and the `DeprecatedUI` compatibility typing for `classNames`/`styles`. The repo's only consumer (`frontend/src/components/ui/calendar.tsx`, shadcn/ui boilerplate with zero imports in `src/`) was deleted rather than migrated. The dependency stays in `package.json` so the shadcn CLI can regenerate the component on demand if it's needed later.

### Fixed

- Memvid container release-gate compliance: added an explicit `USER nonroot` directive to `memvid-service/Dockerfile` so the release-gate check verifying a non-root final-stage user passes (#231). The distroless `gcr.io/distroless/cc-debian13:nonroot` base already runs as `nonroot` by default; the explicit directive removes the implicit-base-default dependency the gate flagged.
- Memvid test isolation: `test_real_searcher_memvid_file_path` now asserts the searcher's `memvid_file` matches the isolated test-fixture path rather than the hardcoded production `resume.mv2` filename (#230). Was a latent assertion-vs-implementation mismatch that surfaced when alpha.17's release-gate work isolated the test fixture.

### Excluded from this release

- **#239 / #241 / #243** (`opentelemetry` / `opentelemetry-otlp` / `opentelemetry_sdk` 0.31 → 0.32 in memvid-service) -- must move as a triple, but `tracing-opentelemetry 0.32.1` (latest published) still depends on `opentelemetry 0.31` and the bump produces a `Tracer` trait mismatch from two concurrent `opentelemetry` versions in the dep graph. Parked until `tracing-opentelemetry 0.33` is released.

## [0.1.0-alpha.17] - 2026-05-01

### Security

- Memvid runtime base bumped from `gcr.io/distroless/cc-debian12:nonroot` (Debian 12 Bookworm, glibc 2.36) to `gcr.io/distroless/cc-debian13:nonroot` (Debian 13 Trixie, glibc 2.41) (#217). Improves the security posture of `library/ai-resume-memvid` against five glibc CVEs flagged by Trivy: `CVE-2026-4046` (alert #539, iconv DoS), `CVE-2026-4437` (#540, DNS response parsing), `CVE-2026-4438` (#541, gethostbyaddr), `CVE-2026-5450` (#543, scanf %mc overflow), `CVE-2026-5928` (#544, ungetwc disclosure). All five are unfixed upstream in either Bookworm or Trixie; the bump to Trixie 2.41 picks up the upstream mitigations Debian's security team applied, downgrading them from HIGH to MEDIUM. The five alerts remain `open` on the security tab as a SARIF state-machine artifact (severity downgrade is not auto-resolved by GitHub); a cleanup PR will codify them in `.trivyignore` with `revisit-YYYY-MM-DD` comments. Pins the explicit `-debianN` distroless suffix per ADR-032 to eliminate silent default-tag drift.
- `.trivyignore` retired the obsolete `CVE-2026-28390` libssl3 suppression (libssl3 is absent from the cc-debian13 runtime) (#217).
- `.trivyignore` extended to suppress `CVE-2026-5435` (alert #547, glibc deprecated `ns_printrr`/`ns_printrrf`/`fp_nquery` family, severity `note`, unfixed upstream in Trixie) with a `revisit-2026-08-01` comment (#218). GitHub code-scanning alert #547 auto-transitioned to `fixed` after the post-merge SARIF reconcile.

### Changed

- Frontend builder bumped from `node:24.15.0-bookworm-slim` to `node:24.15.0-trixie-slim` (#218).
- Memvid builder bumped from `rust:1.95.0-slim` (unsuffixed Bookworm default) to `rust:1.95.0-slim-trixie` (#218). The explicit `-trixie` suffix eliminates the unsuffixed-default-tag drift risk per ADR-032 and aligns builder/runtime glibc versions (Trixie 2.41 builder + Trixie 2.41 runtime, no cross-version forward-compat dance).
- `scripts/test-containers.sh` gained shell-overridable `MOCK_MEMVID`, `MOCK_MEMVID_CLIENT`, `MOCK_OPENROUTER`, and `RUST_LOG` env vars (#218); defaults preserve historical fully-mocked behaviour. Real api↔memvid gRPC verification now possible via `MOCK_MEMVID_CLIENT=false bash scripts/test-containers.sh`. Also corrected the stale Test 7 assertion (was grepping memvid logs for a `Search` RPC log line; the chat handler has called `Ask` since re-ranking landed).

### Documentation

- Tech-stack reference in the project guide updated from `Rust 1.93` to `Rust 1.95` to match the alpha.16 builder bump in #215.
- `docs/DEPLOYMENT.md`: corrected the `api-service` arch-support row (was claiming `Python slim-bookworm multi-arch base`, which has not been accurate since the alpha.15 migration to `ubi10/ubi-micro` runtime + `rockylinux/rockylinux:10-minimal` builder).

### Specforge

- New features `INFRA-091` (Memvid Distroless Base Currency) and `INFRA-092` (Builder Image Currency, Bookworm to Trixie) added to `.specify/specs/spec.md` under "Container Base Image Currency".
- New `ADR-032` (Pin Distroless Image with Explicit `-debianN` Suffix) and Phase 9 wrapper added to `.specify/specs/plan.md`.
- `feature_list.json` extended with `memvid-distroless-debian13` and `builder-images-trixie` entries.

## [0.1.0-alpha.16] - 2026-04-26

### Changed

- Dependency currency rollup consolidating 8 Dependabot PRs (#214)
  - **api-service**: pydantic >=2.13.2 → >=2.13.3 (#207), opentelemetry-sdk >=1.29.0 → >=1.41.1 (#210), opentelemetry-exporter-otlp >=1.39.1 → >=1.41.1 (#209)
  - **api-service (dev)**: pytest-cov >=6.0.0 → >=7.1.0 (#208), mypy >=1.20.1 → >=1.20.2 (#211)
  - **frontend (minor-and-patch group, 10 updates)**: vite 8.0.8 → 8.0.10, vitest 4.1.4 → 4.1.5, @vitest/coverage-v8 4.1.4 → 4.1.5, @tanstack/react-query 5.99.2 → 5.100.5, lucide-react 1.8.0 → 1.11.0, react-hook-form 7.72.1 → 7.74.0, react-router-dom 7.14.1 → 7.14.2, tailwindcss 4.2.2 → 4.2.4, @tailwindcss/vite 4.2.2 → 4.2.4, typescript-eslint 8.58.2 → 8.59.0 (#213)
  - **memvid-service**: axum 0.8.8 → 0.8.9, tokio 1.51.1 → 1.52.1 (#212)
  - **github_actions**: aquasecurity/trivy-action 0.35.0 → v0.36.0 (#206)
- Container base images bumped (#215)
  - frontend builder: `node:24.13.1-bookworm-slim` → `node:24.15.0-bookworm-slim` (Node 24 Active LTS)
  - frontend runtime: `alpine:3.23.3` → `alpine:3.23.4`
  - memvid builder: `rust:1.93.1-slim` → `rust:1.95.0-slim` (satisfies axum 0.8.9 MSRV 1.80)
  - Floating tags (`rockylinux:10-minimal`, `ubi10/ubi-micro`, `gcr.io/distroless/cc-debian12:nonroot`) unchanged; `cc-debian13:nonroot` not yet published as a stable rolling tag
- poetry bumped from 2.3.3 to 2.3.4 in api-service (#201)
- python-dotenv >=1.2.1 → >=1.2.2 in api-service and deployment (#199, #200)
- rand bumped from 0.8.5 to 0.8.6 in memvid-service (#202) -- residual transitive dep via `tantivy 0.25 → tantivy-stacker 0.6 → rand_distr 0.4`; full remediation of GHSA-cq8v-f236-94qc (alert #542) is upstream-blocked pending `memvid-core` bumping to `tantivy 0.26`
- rustls-webpki bumped from 0.103.12 to 0.103.13 in memvid-service (#203)

### Security

- postcss bumped from 8.5.8 to 8.5.10 in frontend (#204) -- closes Dependabot alert #58 (GHSA-qx2v-qp2m-jg93, XSS via unescaped `</style>` in CSS stringify output, dev dependency, transitive of vite)

### Documentation

- `docs/DEPLOYMENT.md`, `CLAUDE.md`: corrected stale runtime base-image claims (api-service / ingest are `ubi10/ubi-micro` with `rockylinux:10-minimal` builders, memvid-service is `gcr.io/distroless/cc-debian12:nonroot`)

## [0.1.0-alpha.15] - 2026-04-20

### Changed

- Split `scripts/build-all.sh` into per-service wrappers (`build-frontend.sh`, `build-api.sh`, `build-memvid.sh`, `build-ingest.sh`) sharing a new `scripts/lib/container-build.sh` helper; `build-all.sh` is now a thin orchestrator (#197)
- Exposed per-service container builds through Taskfile: `task container:build:{frontend,api,memvid,ingest}` alongside the existing `task container:build` aggregate (#197)
- Switched api-service and ingest Dockerfile builder/python-deps stages from `ubi10/ubi` to `rockylinux/rockylinux:10-minimal` to sidestep the UBI 10 OpenSSL 3.5.1 TLS bug under Rosetta 2; runtime stage remains `ubi10/ubi-micro` (#197)
- Rewrote Stop hook `.claude/hooks/verify-quality.sh` to delegate to `task lint` (blocking) and `task test` (advisory) instead of PATH-probing per-service tools -- reference implementation for upstream cpf CR issue 4 (polyglot per-service venv resolution); severity contract preserved (exit 2 on lint fail, non-blocking on test fail) (#197)
- Added per-tool lint targets to root Taskfile that mirror `ci-base.yml` jobs one-for-one: `lint:shellcheck`, `lint:prettier`, `lint:markdown`; aggregate `task lint` now includes them, closing the prior CI/local parity gap (#197)

## [0.1.0-alpha.14] - 2026-04-19

### Changed

- Dependency currency rollup consolidating 6 Dependabot PRs (#195)
  - **api-service**: pydantic >=2.10.6 → >=2.13.2 (#194), pydantic-settings >=2.7.1 → >=2.13.1 (#190), grpcio-tools >=1.69.0 → >=1.80.0 (#189), fastmcp >=3.0.0 → >=3.2.4 (#192)
  - **api-service (dev)**: pytest-asyncio >=0.25.2 → >=1.3.0 (#191)
  - **frontend**: @tanstack/react-query 5.99.1 → 5.99.2 (#193)
- `DavidAnson/markdownlint-cli2-action` bumped from 22 to 23 (#188)

## [0.1.0-alpha.13] - 2026-04-18

### Changed

- Specforge scaffold upgraded from alpha.8 to alpha.10 (#164, #165)
  - CI migrated to reusable workflow: `ci-base.yml` called from `ci.yml` via `workflow_call`
  - Redundant `docs` job removed from `ci.yml` (markdownlint now in `ci-base.yml`)
  - New scaffold checks: shellcheck, prettier, plugin-validation via `ci-base.yml`
  - Pre-commit hook: added markdown (`markdownlint-cli2`) and YAML (`yaml.safe_load`) lint checks for staged files
  - `CLAUDE.md.template`: expanded service/subagent/spec/API/container/commit/PR sections; added merged-MR branch check
  - `ci/gitlab/gitlab-ci-guide.md` and `ci/jenkins/jenkinsfile-guide.md`: rewritten with pipeline/stage docs, customization examples, platform parity tables
  - `ci/github/dependabot.yml`: added Go (`gomod`) commented-out ecosystem entry
  - `scripts/hooks/pre-commit`, `.specify/WORKFLOW.md`: updated from scaffold
- Local patches applied to `.github/workflows/ci-base.yml` for monorepo compatibility: shellcheck exclusions for `.venv/`/`node_modules/`, prettier via `npx`, plugin-validation guarded by `hashFiles()` existence check (tracked upstream in `.specify/proposals/cr-ci-base-scaffold-issues.md`)
- Dependency currency rollup consolidating 17 Dependabot PRs across cargo, npm, uv, pip (#184)
  - **frontend**: 12-update minor-and-patch group, protobufjs 7.5.4 → 7.5.5
  - **memvid-service**: tokio 1.51.0 → 1.51.1
  - **api-service**: authlib, python-multipart, pytest, uvicorn, prometheus-client, isort
  - **ingest**: pytest, pytest-asyncio, sentence-transformers 3.0.0 → 5.4.0, ruff
- Additional frontend minor-and-patch group: @opentelemetry/context-zone 2.6.1 → 2.7.0, exporter-trace-otlp-http and instrumentation-fetch 0.214.0 → 0.215.0, @tanstack/react-query 5.99.0 → 5.99.1, react-router-dom 7.14.0 → 7.14.1, eslint 10.2.0 → 10.2.1, eslint-plugin-react-hooks 7.1.0-canary → 7.1.1, typescript 6.0.2 → 6.0.3, typescript-eslint 8.58.1 → 8.58.2 (#185)
- mypy dev dependency bumped from >=1.14.1 to >=1.20.0 in api-service (#171)
- `ingest/pyproject.toml`: declared setuptools build-system and `py-modules = ["ingest", "compare_models"]` -- fixes `uv pip install -e .` under setuptools>=80 flat-layout strict auto-discovery
- `frontend/src/hooks/useStreamingChat.ts`: derived `isRateLimited` from state instead of storing it; moved session ID generation to lazy `useState` initializer -- resolves eslint-plugin-react-hooks 7.1.1 "impure function during render" and "setState synchronously within an effect" rules
- `ingest/tests/test_e2e.py`: refactored standalone `main()` runner to try/except pattern -- resolves mypy 1.20 stricter `misc`/`has-type` errors

### Fixed

- Release validate job race condition when CI was re-run (#163) -- now polls all runs sorted by `run_started_at`, requires `conclusion=success` on both the run and its `summary` job, and waits while any run is in-progress

### Security

- rustls-webpki bumped from 0.103.10 → 0.103.12 in memvid-service -- closes Dependabot alert #50 (X.509 name-constraint bypass) (#186)
- rand bumped from 0.9.2 → 0.9.3 in memvid-service -- partial remediation for Dependabot alert #47 (unsound with custom `log::Log`); residual rand 0.8.5 copy is upstream-blocked through `memvid-core 2.0.139 → tantivy 0.25.0 → rand_distr 0.4.3` (pinned to `rand ^0.8`, no 0.8.x patch exists) (#186)

## [0.1.0-alpha.12] - 2026-04-10

### Added

- Playwright E2E smoke test suite for frontend (#152)

### Changed

- lucide-react upgraded from 0.577.0 to 1.7.0 (major); brand icons replaced with inline SVGs (#157)
- vite bumped from 8.0.3 to 8.0.5 in frontend (#158)
- fastmcp bumped from 3.0.2 to 3.2.0 in api-service (#151)
- poetry bumped from 2.3.1 to 2.3.3 in api-service (#153)
- SonarSource/sonarqube-scan-action bumped from 7.0.0 to 7.1.0 (#154)
- 7 minor/patch frontend dependency updates (#156)
- 2 minor/patch memvid-service dependency updates (#155)
- Specforge scaffold upgraded from alpha.5 to alpha.8 (#160, #161)

### Fixed

- Release-gate wired into CI summary job; deduplicated security scan steps (#150)

### Security

- cryptography bumped from 46.0.6 to 46.0.7 in api-service (#159)
- CVE-2026-28390 (libssl3 in distroless) suppressed pending upstream rebuild (#157)

## [0.1.0-alpha.11] - 2026-03-29

### Changed

- TypeScript upgraded from 5.x to 6.0.2; removed deprecated `baseUrl` from tsconfig (#145)
- date-fns upgraded from 3.x to 4.1.0 (#145)
- jsdom upgraded from 27.x to 29.0.1 (devDependency, #145)
- globals upgraded from 15.x to 17.4.0 (devDependency, #145)
- npm upgraded from 11.10.1 to 11.12.1 in frontend Dockerfile (#145)
- cryptography bumped from 46.0.5 to 46.0.6 in api-service (#139)
- requests bumped from 2.32.5 to 2.33.0 in api-service (#137)
- picomatch bumped from 4.0.3 to 4.0.4 in frontend (#136)
- OTel JS exporter-trace-otlp-http and instrumentation-fetch bumped to 0.214.0 (#148)
- 22 specforge features verified; stale testing steps updated (#138)
- api-service CI job now reports coverage in GITHUB_STEP_SUMMARY (#138)

### Fixed

- Add `@opentelemetry/sdk-trace-base` as explicit dependency; Rolldown fails on transitive-only imports (#147)
- Remove duplicate PreToolUse hooks from project settings.json (plugin provides these)

### Security

- aws-lc-sys bumped from 0.38.0 to 0.39.1 via aws-lc-rs 1.16.2; fixes Dependabot alerts #25, #26 (X.509 Name Constraints Bypass, CRL Distribution Point Scope Check)
- Pygments bumped from 2.19.2 to 2.20.0 in api-service and ingest; fixes Dependabot alerts #29, #30 (ReDoS in GUID matching)

## [0.1.0-alpha.10] - 2026-03-25

### Changed

- dorny/paths-filter bumped from 3 to 4 in CI workflow (#128)
- sonner bumped from 1.7.4 to 2.0.7 (toast notification library, major) (#131)
- tailwind-merge bumped from 2.6.1 to 3.5.0 (CSS class merging, major) (#132)
- @types/node bumped from 22.19.15 to 25.5.0 (devDependency) (#133)
- 12 minor/patch frontend dependency updates (#134)
- opentelemetry-otlp bumped from 0.31.0 to 0.31.1 in memvid-service (#129)
- rustls-webpki bumped from 0.103.9 to 0.103.10 in memvid-service (#126)
- lz4_flex bumped from 0.12.0 to 0.12.1 in memvid-service (#125)
- flatted bumped from 3.4.1 to 3.4.2 (devDependency) (#127)
- authlib bumped from 1.6.8 to 1.6.9 in api-service (#124)

### Security

- Security review completed: no high-confidence vulnerabilities found in dependency changes
- aws-lc-sys 0.38.0 CVEs (alerts #25, #26) assessed as not exploitable -- no TLS connections made via affected code path; blocked on upstream fix (0.39.0 not yet resolvable)
- Pygments ReDoS alerts (#29, #30) assessed as non-impacting -- test/dev tooling only, not loaded in production

## [0.1.0-alpha.9] - 2026-03-15

### Changed

- Vite upgraded from 7.x to 8.x (Rolldown bundler replaces esbuild/Rollup)
- `@vitejs/plugin-react-swc` replaced with `@vitejs/plugin-react` (Oxc-based)
- Tailwind CSS migrated from v3 to v4 (CSS-first architecture)
- `tailwind.config.ts` and `postcss.config.js` removed (Tailwind v4 uses `@tailwindcss/vite` plugin and `@theme` CSS directives)
- `tailwindcss-animate` replaced with `tw-animate-css` (Tailwind v4 compatible)
- OpenTelemetry Rust crates upgraded from 0.27.x to 0.31.x (opentelemetry, opentelemetry_sdk, opentelemetry-otlp, tracing-opentelemetry)
- 8 Dependabot dependency bumps rolled up into single PR (#122)
- Test isolation for memvid exclusive file locking (#118)
- Frontend TypeScript API fixes for react-day-picker v9, react-resizable-panels v4, OTel SDK v2 (#119)
- Memvid SDK 2.0.159 / Core 2.0.139 (#117)

### Security

- CVE-2026-22184 (zlib buffer overflow) patched via `apk upgrade` in frontend Dockerfile

## [0.1.0-alpha.8] - 2026-03-03

### Changed

- Memvid SDK upgraded from 2.0.157 to 2.0.158 (PyPI)
- Memvid Core upgraded from 2.0.137 to 2.0.138 (crates.io)
- Memvid CLI version pins updated to 2.0.158 in E2E scripts and CI workflow
- `repro_bug_c.py` rewritten to use `find(mode="hybrid")` instead of deprecated `ask()` API (removed `top_k` kwarg)
- Upstream bug report updated: #194 FIXED, #196 partial fix (`find()` works, `ask()` still needs doctor workaround)
- README updated: added MCP server, chat feedback, version, and MCP config endpoints to API table; added MCP Server description

### Fixed

- Rust real-searcher tests fail with "exclusive access unavailable" on memvid-core 2.0.138 due to new file locking; added `#[serial]` to all tests sharing the `.mv2` file

### Security

- Updated `aws-lc-sys` to 0.38.0 fixing 3 high-severity CVEs (PKCS7_verify bypass, AES-CCM timing side-channel)

## [0.1.0-alpha.7] - 2026-03-02

### Added

- gRPC method latency breakdown: `method` label on `memvid_search_latency_ms` histogram (search, ask, get_state)
- Search relevance metrics: `memvid_search_relevance_score` and `memvid_search_chunks_returned` histograms in Rust memvid-service
- Span attributes for retrieval quality: `search.max_relevance`, `search.min_relevance`, `search.avg_relevance`, `search.chunks_returned`
- SSE streaming timing: `chat.time_to_first_token_ms` and `chat.streaming_duration_ms` span attributes in frontend
- `isOtelInitialized()` guard for conditional browser tracing
- Chat feedback endpoint: `POST /api/v1/chat/{session_id}/feedback` with idempotent counter and structured logging
- ThumbsUp/ThumbsDown UI on assistant chat messages with fire-and-forget feedback submission
- Retrieval Quality dashboard: relevance score distribution, chunks/query histogram, configurable low-relevance threshold
- Quality Evals dashboard: feedback rate, positive/negative ratio, Loki log panel with Tempo Data Links
- Success rate % and total error count KPI stat panels on Endpoint Overview dashboard
- gRPC method template variable and per-method p50/p95/p99 panel on Latency Breakdown dashboard
- SSE Streaming row with TTFT and duration panels on Latency Breakdown dashboard

### Changed

- `docs/OBSERVABILITY.md` updated for all Phase 2 features (6 dashboards, new metrics, new runbook)
- Fluent Bit and Loki environment variables added to `deployment/.env.example`

### Fixed

- PreToolUse hook false errors: removed `set -e` from all hook scripts (exit 1 on internal subcommand edge cases reported as "hook error")
- `protect-files.sh` now allows `.env.example` and `.env.sample` edits (priority match before `.env*` block)
- Dashboard metric names and panel types corrected across all Grafana dashboards
- Release gate ingest outcome tests no longer fail on 0% coverage (`--no-cov` for data validation tests)

## [0.1.0-alpha.6] - 2026-03-01

### Added

- End-to-end distributed tracing with OpenTelemetry across all three services (Python, Rust, TypeScript)
- W3C trace context propagation (`traceparent` header) through the full request chain
- Browser tracing via `@opentelemetry/sdk-trace-web` with fetch instrumentation
- OpenTelemetry trace export in memvid-service via `tracing-opentelemetry`
- Observability stack: Grafana, Tempo, Prometheus, Loki, OTEL Collector (`deployment/observability/`)
- Fluent Bit log shipper for production host log forwarding
- Pre-provisioned Grafana dashboards (request waterfall, latency breakdown, endpoint overview, LLM cost)
- Combined dev compose (`compose.dev.yaml`) for single-host observability testing
- Comprehensive observability guide with runbooks (`docs/OBSERVABILITY.md`)

### Changed

- React upgraded from 18.3 to 19.2 (`react`, `react-dom`, `@types/react`, `@types/react-dom`)
- `vaul` upgraded from 0.9.9 to 1.1.2 (React 19 peer dependency compatibility)
- Documentation references updated from React 18 to React 19 across all project files
- Dependency bumps: rollup 4.59.0, minimatch 9.0.9, react-day-picker 9.14.0, chrono (memvid-service minor/patch group), actions/upload-artifact v7, frontend minor/patch batch

### Fixed

- Release validate step waits for successful container builds (#81)
- Missing `lua-resty-http` `http_connect.lua` module in frontend container
- Cargo fmt and mypy type annotation failures in CI
- Removed unused `type: ignore` comments; fixed mypy `arg-type`/`union-attr` errors

## [0.1.0-alpha.5] - 2026-02-25

### Added

- MCP server with Streamable HTTP transport (FastMCP), mounted at `/mcp` with stateless tool invocation
- MCP tools: `ask_question` (semantic resume search + LLM) and `assess_fit` (job fit evaluation)
- MCP resources: `profile://current` and `questions://suggested`
- MCP config endpoint (`/api/v1/mcp/config/{client_id}`) with templates for desktop app, Claude Code CLI, web interface, and Cursor IDE
- WebMCP browser tool registration using Chrome `registerTool()` API with execute handlers
- Header menu with About dialog (version, commit SHA, links) and MCP Config dialog
- Footer redesign with version display and corrected links
- Build-time version injection (`/api/v1/version` endpoint, `VERSION` file in frontend)
- Vite dev proxy for `/mcp` path (matches nginx production routing)

### Changed

- MCP enabled by default (opt-out via `MCP_ENABLED=false`)
- Hero section layout: reduced gap between header and content
- Frontend container: OpenResty lua-resty-http installed via direct download instead of apk (avoids Alpine nginx 1.28 / openresty 1.27 package conflict)

### Fixed

- OpenRouter client crashes on HTTP 200 error responses (missing `choices` key)
- MCP mount 307 redirect: path rewrite middleware replaces complex ASGI forwarding
- MCP lifespan resilient to StreamableHTTPSessionManager reuse across test sessions
- Nginx regex routes `/mcp` (no trailing slash) to API backend
- MCP config dialog loads first tab config on open (no tab switch required)
- MCP config URL uses frontend origin instead of API backend address
- Blog URLs corrected in Footer and About dialog
- Quality hook finds system ruff and uses npx for markdownlint

### Security

- Upgraded cryptography 46.0.4 to 46.0.5 (CVE-2026-26007)

## [0.1.0-alpha.4] - 2026-02-23

### Changed

- API and ingest container runtimes migrated from `python:3.12-slim-bookworm` to UBI 10 micro (3-stage build: `ubi` -> `ubi-minimal` -> `ubi-micro`)
- Container runtime has no shell, no package manager -- only explicitly staged shared libraries
- Release notes now include container image table with pull and cosign verify commands
- Removed `cache-python: true` from all `setup-uv` CI steps (system Python used, cache was a no-op)
- ARM runner label references corrected from `ubuntu-24.04-arm64` to `ubuntu-24.04-arm` across docs

### Fixed

- Release workflow race condition: validate step now iterates all completed CI runs to find the one with container-build jobs (previously selected the wrong run when tag push and main push shared the same SHA)
- CI smoke tests use `podman exec /healthcheck` for api container (no wget in ubi-micro)
- Shebangs in healthcheck and start.py changed to `/app/.venv/bin/python` (no `/usr/bin/env` in ubi-micro)

### Security

- Eliminated 53 Debian CVEs (51 unfixable in stable) from api-service and ingest containers
- Remaining: 2 gnutls CVEs per Python service (awaiting upstream RHEL 10 patch)

## [0.1.0-alpha.3] - 2026-02-23

### Changed

- Container builds run on native ARM runners (`ubuntu-24.04-arm`) instead of QEMU emulation
- Container supply chain security: cosign keyless signing, SBOM attestation via syft, signature verification in release pipeline

### Fixed

- Release workflow authentication: cosign identity matching for tag-triggered CI runs
- Code scanning alert remediation

## [0.1.0-alpha.1] - 2026-02-22

### Added

- Multi-arch container release pipeline to ghcr.io (`release.yml`)
- Trivy container scanning with severity gate and dual-run strategy
- Manual trigger for Trivy security scan workflow
- Go-task build orchestration for polyglot monorepo (72 tasks across 6 Taskfiles)
- TRUSTED_PROXIES configuration and gRPC request correlation for API service
- Git hooks distribution via `.githooks/` with install script
- CI/CD pipeline: CodeQL scanning, SonarQube analysis, release quality gate
- Full-stack E2E integration tests for API, gRPC, and frontend
- Semantic search with cross-encoder re-ranking (Ask mode)
- AI chat interface with SSE streaming and session management
- Fit assessment tool with hybrid pre-analyzed and real-time AI analysis
- Dynamic role classification for fit assessment accuracy
- Data-driven content architecture: single `.mv2` file drives all content
- OCI 1.1 metadata labels and build annotations on all container images
- Rust SBOM embedding via cargo-auditable in memvid-service
- Prometheus metrics endpoint
- Specforge specification-driven development framework (phases 0-7 complete)
- 136 features defined, 125 verified

### Changed

- CI Python management delegated to uv via `.python-version` files (drop `setup-python`)
- Tool versions bumped: Node 22.14.0, uv 0.9.0, go-task 3.48.0, Rust 1.93.0, podman 5.8.0
- Memvid-service runtime switched to distroless base image with `--health` flag
- Memvid-service protobuf compilation uses GitHub releases binary instead of apt
- Container base images upgraded for security (alpine:3.23, python:3.12-slim, debian:trixie-slim)
- Dockerfiles optimized with UV best practices and stable base images
- ESLint upgraded to v10 with aligned peer dependencies
- Vitest and coverage-v8 upgraded from 3.x to 4.x
- Dependabot configured with conventional commit message format
- README rewritten; DEVELOPMENT.md added as canonical dev guide; EOL docs archived
- Memvid SDK upgraded to 2.0.157, core to 2.0.137

### Fixed

- Publish script uses `podman manifest push --all` for macOS manifest list resolution
- CI Python version mismatch: api-service and cross-service tested on 3.11 despite requiring 3.12
- Merge commit and dependabot CI compliance gaps
- Markdown lint pipeline gaps
- Frontend ProfileContext split to resolve fast refresh warning
- CodeQL taint tracking issues in API key handling
- Session ID generation switched to cryptographically secure `crypto.getRandomValues()`
- Unsafe `((VAR++))` bash arithmetic replaced with `$((VAR + 1))` across scripts
- Proto import path for local gRPC connectivity
- Domain mismatch check to prevent contradictory fit ratings
- E2E test reliability with health-gate and 429 handling
- Clippy warnings for Rust 1.93 compatibility
- Coverage gates scoped correctly for memvid integration modules

### Security

- GitHub Code Scanning alerts remediated (API key masking, secure session IDs, bind address documentation)
- `.claude` directory removed from git history
- Container images hardened with distroless runtime and SBOM
- Base image upgrades to address known CVEs

[Unreleased]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.9...HEAD
[0.1.0-beta.9]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.8...v0.1.0-beta.9
[0.1.0-beta.8]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.7...v0.1.0-beta.8
[0.1.0-beta.7]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.6...v0.1.0-beta.7
[0.1.0-beta.6]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.5...v0.1.0-beta.6
[0.1.0-beta.5]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.4...v0.1.0-beta.5
[0.1.0-beta.4]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.3...v0.1.0-beta.4
[0.1.0-beta.3]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.2...v0.1.0-beta.3
[0.1.0-beta.2]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-beta.1...v0.1.0-beta.2
[0.1.0-beta.1]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.23...v0.1.0-beta.1
[0.1.0-alpha.23]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.22...v0.1.0-alpha.23
[0.1.0-alpha.22]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.21...v0.1.0-alpha.22
[0.1.0-alpha.21]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.20...v0.1.0-alpha.21
[0.1.0-alpha.12]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.11...v0.1.0-alpha.12
[0.1.0-alpha.11]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.8...v0.1.0-alpha.11
[0.1.0-alpha.8]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.7...v0.1.0-alpha.8
[0.1.0-alpha.7]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.6...v0.1.0-alpha.7
[0.1.0-alpha.6]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.5...v0.1.0-alpha.6
[0.1.0-alpha.5]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.4...v0.1.0-alpha.5
[0.1.0-alpha.4]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/schwichtgit/ai-resume/compare/v0.1.0-alpha.1...v0.1.0-alpha.3
[0.1.0-alpha.1]: https://github.com/schwichtgit/ai-resume/releases/tag/v0.1.0-alpha.1

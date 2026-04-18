# Semantic Versioning Strategy for ai-resume

## Version Format

**MAJOR.MINOR.PATCH** (e.g., 1.0.0, 1.6.0-alpha.1, 1.6.0-beta.2, 1.6.0-rc.1)

## Increment Rules

### MAJOR (X.0.0) - Breaking Changes

- API contract changes (profile response schema, chat endpoint signature)
- Constitutional amendments affecting developers
- Removal of deprecated features (after 3-release deprecation cycle)
- Example: 1.0.0 → 2.0.0

### MINOR (0.X.0) - New Features

- New features (experience cards, fit examples, chat enhancements)
- Backward-compatible enhancements
- New endpoints without breaking existing ones
- Example: 1.5.0 → 1.6.0

### PATCH (0.0.X) - Bug Fixes

- Bug fixes and improvements
- Dependency security updates
- Documentation corrections
- Example: 1.5.0 → 1.5.1

## Pre-release Versions

### Alpha (-alpha.N)

- Feature incomplete, internal testing only
- May contain breaking changes
- Not recommended for production use
- Example: 1.6.0-alpha.1, 1.6.0-alpha.2

### Beta (-beta.N)

- Feature complete, public testing phase
- Known issues may exist but core functionality stable
- Production use at own risk
- Example: 1.6.0-beta.1

### Release Candidate (-rc.N)

- Feature stable, final QA phase
- No breaking changes expected
- Ready for production after final security audit
- Example: 1.6.0-rc.1

## Release Gates (ALL MANDATORY)

Before creating ANY version tag, these must ALL pass:

### 1. Code Coverage

≥ 85% per service (enforced in CI build gates)

- Frontend: ≥ 10% (ramping to 85% as component tests added)
- API Service: ≥ 91% (measured in CI)
- Ingest: ≥ 92% (measured in CI)
- Memvid: ≥ 85% unit coverage (excludes real.rs integration tests)

### 2. Constitutional Compliance

100% audit pass:

- Zero hallucination in AI responses
- Rate limiting enforced (10 req/min per real client IP)
- All security requirements met
- Container architecture enforced (three-container runtime)
- Single .mv2 data file portability verified
- No hardcoded content in application code
- Graceful degradation on service failures
- No server-side conversation persistence

### 3. Security Scanning

Zero unpatched critical/high CVEs:

- Grype scan of all container layers
- Trivy scan of final images
- 7-day SLA for critical patch response
- No credentials in code or environment
- No secrets in git history

### 4. E2E Testing

100% pass rate:

- Health checks passing (`GET /health`)
- Profile endpoint verified (`GET /api/v1/profile`)
- Chat endpoint with semantic search verified (`POST /api/v1/chat`)
- Fit assessment working (`POST /api/v1/assess-fit`)
- All endpoints returning 2xx responses
- No hallucination in AI responses

### 5. Container Scans

Clean baseline:

- Base images up-to-date
  - alpine:3.23
  - node:24-bookworm-slim
  - python:3.12-slim-bookworm
  - debian:trixie-slim
- No unpatched vulnerabilities in any layer
- All layers scanned by Grype and Trivy
- No policy violations

### 6. Documentation

Complete:

- CHANGELOG.md entry with all changes
- CLAUDE.md updated with new features or API changes
- API docs updated if endpoints changed
- Migration guide if MAJOR version
- `versioning-strategy.md` reviewed for compliance

## Release Timeline

### Alpha Phase (1-3 days)

- Feature implementation complete
- Internal testing in development environment
- Bug fixes trigger new alpha tag (alpha.1 → alpha.2 → ...)
- Security scan performed
- Target: all gates passing

### Beta Phase (2-7 days)

- Public beta release
- E2E testing in staging environment
- Load testing with synthetic traffic
- Final integration testing
- Security audit pass required
- Target: production-ready baseline

### RC Phase (3-7 days)

- Release candidate ready
- Final QA in production-like environment
- Documentation review complete
- No changes except critical security fixes
- Target: approval from maintainers

### Stable Release

- Create stable version tag (1.6.0)
- Deploy to production
- Create GitHub release with changelog
- Update documentation
- Announce release
- Target: production rollout

## Example: Feature Release Workflow

**Feature:** Add suggested questions to profile API

**Conventional Commit:** `feat(api): add suggested questions to profile endpoint`

**Version Progression:**

1. **Day 0 (Alpha 1):** Merge to main → Auto-create 1.6.0-alpha.1 tag

   - Full test suite runs
   - Security scan runs
   - Container builds and scans
   - All gates must pass

2. **Day 1-2 (Alpha.N):** Internal testing, bug fixes

   - Bug fix commits create 1.6.0-alpha.2, alpha.3, etc.
   - Each alpha tag reruns full gate suite
   - Target: stability reached

3. **Day 2-3 (Beta 1):** Move to beta after 48h in alpha

   - Create 1.6.0-beta.1 tag
   - E2E testing in staging
   - Load testing starts (synthetic traffic)
   - Security audit performed

4. **Day 4-9 (Beta.N):** Staging validation and load testing

   - Production-like environment tests
   - Memory and latency profiling
   - Real-world traffic patterns simulated
   - Target: production readiness confirmed

5. **Day 10-16 (RC 1):** Move to RC after 1 week in beta

   - Create 1.6.0-rc.1 tag
   - Final QA in production-like environment
   - No code changes except critical security fixes
   - Security audit final pass

6. **Day 17+ (Stable):** Maintainer approval and deploy
   - Create 1.6.0 tag (stable)
   - Deploy to production
   - Create GitHub release with full changelog
   - Update project documentation
   - Announce release

## Deprecation and Removal

### Deprecation Cycle (3 releases)

1. **Release N:** Mark feature as deprecated

   - Add `@deprecated` annotation in code comments
   - Document deprecation in CHANGELOG
   - Document migration path in docs
   - Release as MINOR version (e.g., 1.6.0)

2. **Releases N+1 and N+2:** Final releases with deprecated feature

   - Feature continues to work
   - Warning messages in documentation
   - Users have 3 releases to migrate

3. **Release N+3 (Next MAJOR):** Remove deprecated feature
   - Feature removed completely
   - Migration guide required in CHANGELOG
   - Example: Deprecated in 1.6.0, final release in 1.8.0, removed in 2.0.0

## CI/CD Automation (Future)

The release process should eventually:

1. Detect merged PRs with conventional commits (feat:, fix:, BREAKING CHANGE:)
2. Automatically calculate next version using SemVer rules
3. Create alpha.1 tag and run full test suite
4. Gate on all release requirements from section "Release Gates"
5. Auto-promote to beta.1 after 48-hour period (if all gates passing)
6. Auto-promote to rc.1 after 1-week period (if all gates passing)
7. Create stable version tag after final maintainer approval
8. Deploy to production
9. Generate GitHub release notes from CHANGELOG

## Constitutional Alignment

All versions must comply with `.specify/memory/constitution.md`:

- Single .mv2 data file (portable, no hardcoded content)
- Zero hallucination in AI responses
- Rate limiting enforced (10 req/min per real client IP)
- Rootless containers for production
- Semantic search < 5ms latency
- No credentials in code or environment
- Security scanning on all containers (7-day SLA for patches)
- Three-container production runtime
- Stateless, read-only container images
- Edge-deployable on 4GB RAM, <200MB memory

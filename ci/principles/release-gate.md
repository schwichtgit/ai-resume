# Release Gate

All PR gate checks apply, plus the following.

## 1. Dependency Audit

| Ecosystem | Command                 |
| --------- | ----------------------- |
| Node.js   | `npm audit`             |
| Python    | `pip-audit` or `safety` |
| Rust      | `cargo audit`           |

No high or critical vulnerabilities allowed.

## 2. License Compliance

All dependencies must use approved licenses:

**Approved:** MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, 0BSD, Unlicense

**Flag for manual review:** GPL, AGPL, LGPL, unknown

## 3. Changelog Entry

CHANGELOG.md entry must exist for the version being released. Use [Keep a Changelog](https://keepachangelog.com/) format.

## 4. Version Bump

Version must be incremented from previous release. Use [SemVer](https://semver.org/) format.

## 5. Clean Dependency Tree

- No unused dependencies
- No circular dependency chains

## 6. Outcome Test Matrix

Run the automated release gate matrix before any production deployment:

```bash
./scripts/release-gate-matrix.sh
```

All **blocking** gates must pass:

| Gate                | Type     | Target                      |
| ------------------- | -------- | --------------------------- |
| Data Coverage       | Blocking | 100% category coverage      |
| Factual Accuracy    | Blocking | 0 hallucinations            |
| Negative Testing    | Blocking | 100% refusal rate           |
| Honesty & Gaps      | Blocking | Gaps acknowledged           |
| Security Guardrails | Blocking | All injections deflected    |
| Injection Scenarios | Blocking | All patterns detected       |
| Stream Leakage      | Blocking | No sensitive data leaked    |
| E2E Quality         | Blocking | All acceptance criteria met |
| Portability         | Blocking | No hardcoded data           |
| Container Config    | Blocking | All Dockerfiles valid       |

Non-blocking metrics (latency, frontend tests, docs audit) are reported but do not prevent release.

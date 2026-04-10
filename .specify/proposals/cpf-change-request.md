# Scaffold Review: alpha.7 Changes to Accept

**Upgrade:** specforge 0.1.0-alpha.5 -> 0.1.0-alpha.7
**Date:** 2026-04-09

## Context

The alpha.7 upgrade applied all overwrite-tier files automatically.
This checklist covers review-tier changes that need manual acceptance
or rejection for this project.

---

## Accept (recommended)

### 1. Issue Templates (new files)

**Files:**

- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`

**Status:** None exist in project. Generic scaffold templates,
safe to copy as-is.

**Action:** Copy from scaffold.

### 2. CODEOWNERS: add .claude-plugin/ ownership

**File:** `.github/CODEOWNERS`

**Diff:**

```diff
+.claude-plugin/             @schwichtgit
 .claude/                    @schwichtgit
```

**Action:** Cherry-pick this single line addition.

### 3. ci/github/dependabot.yml: commit-message blocks

**File:** `ci/github/dependabot.yml`

**Status:** Project's `.github/dependabot.yml` already has these.
The `ci/github/` reference copy does not.

**Action:** Accept scaffold update to `ci/github/dependabot.yml`
to keep the reference copy in sync.

### 4. ci/github/repo-settings.md: separate workflows section

**File:** `ci/github/repo-settings.md`

**Status:** Scaffold adds a "Best Practice: Separate Workflows
per Scanner" subsection. Minor line-wrapping changes.

**Action:** Accept scaffold update.

---

## Skip (project-specific, keep as-is)

### 5. .github/workflows/ci.yml

Project has a 465-line polyglot CI. Scaffold has a 99-line generic
starter. No useful merge.

### 6. .github/workflows/release.yml

Project has container-publish pipeline. Scaffold has plugin tarball
release. Completely different purpose.

### 7. .github/dependabot.yml

Project has 5 ecosystems (npm, pip x2, cargo, github-actions).
Scaffold has 2 generic stubs. Project version is authoritative.

### 8. CLAUDE.md.template

Project's live CLAUDE.md is already ahead of the template.
Template update is informational only.

### 9. .prettierrc.json / .prettierignore

Identical -- no action needed.

### 10. ci/github/CODEOWNERS.template / PULL_REQUEST_TEMPLATE.md / commit-standards.yml

Identical -- no action needed.

---

## Evaluate Later

### 11. .github/workflows/codeql.yml (new in scaffold)

Scaffold ships standalone CodeQL workflow. Project currently has
CodeQL in combined `security.yml` (with Trivy). Consider splitting
in a future cleanup, but no immediate need.

---

## Summary

| Action         | Count          |
| -------------- | -------------- |
| Accept         | 4 (items 1-4)  |
| Skip           | 6 (items 5-10) |
| Evaluate later | 1 (item 11)    |

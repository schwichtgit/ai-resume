# GitHub Repository Settings Checklist

Configure these settings after creating your repository. Use the `gh` CLI where possible.

## 1. Branch Protection

```bash
gh api repos/{owner}/{repo}/branches/main/protection -X PUT -f \
  required_status_checks='{"strict":true,"contexts":["summary"]}' \
  enforce_admins=true \
  required_pull_request_reviews='{"required_approving_review_count":1}' \
  restrictions=null
```

**Key:** Only require the `summary` job. Conditional jobs (nodejs, python, rust) show as "skipped" when no relevant files change, and would block PRs if required directly.

## 2. Merge Settings

- Default merge method: **Squash merge**
- Auto-delete head branches: **Enabled**

```bash
gh api repos/{owner}/{repo} -X PATCH \
  -f allow_squash_merge=true \
  -f allow_merge_commit=false \
  -f allow_rebase_merge=false \
  -f delete_branch_on_merge=true
```

## 3. Security

- **CodeQL:** Enable for detected languages
- **Secret scanning:** Enable with push protection

```bash
gh api repos/{owner}/{repo}/code-scanning/default-setup -X PATCH \
  -f state=configured

gh api repos/{owner}/{repo} -X PATCH \
  -f security_and_analysis='{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}'
```

## 4. Dependabot

Copy the dependabot config to your repo:

```bash
mkdir -p .github
cp ci/github/dependabot.yml .github/dependabot.yml
```

## 5. CODEOWNERS

```bash
cp ci/github/CODEOWNERS.template .github/CODEOWNERS
# Edit .github/CODEOWNERS and replace @OWNER with your GitHub username or team
```

## 6. PR Template

```bash
cp ci/github/PULL_REQUEST_TEMPLATE.md .github/PULL_REQUEST_TEMPLATE.md
```

## 7. CI Workflows

```bash
mkdir -p .github/workflows
cp ci/github/workflows/ci.yml .github/workflows/ci.yml
cp ci/github/workflows/commit-standards.yml .github/workflows/commit-standards.yml
```

Review and customize the workflow files for your tech stack (enable/disable language jobs, adjust path filters).

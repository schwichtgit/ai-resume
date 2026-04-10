# GitLab CI Mapping Guide

This guide maps the abstract SDLC principles to GitLab CI
configuration. A fully templated `.gitlab-ci.yml` is provided at
`.claude-plugin/scaffold/gitlab/.gitlab-ci.yml` with equivalent
quality gates to the GitHub Actions CI workflow.

## Mapping

| Abstract Concept  | GitLab CI Equivalent                                   |
| ----------------- | ------------------------------------------------------ |
| Commit gate       | Pipeline stages with `rules: changes`                  |
| PR gate           | Merge request pipelines                                |
| Release gate      | Tagged pipelines (`rules: if: $CI_COMMIT_TAG =~ /^v/`) |
| Path filtering    | `rules: changes: [paths]`                              |
| Required checks   | Merge request approvals + pipeline success             |
| CODEOWNERS        | GitLab CODEOWNERS format (same syntax)                 |
| Branch protection | Protected branches settings                            |

## Pipeline Overview

The `.gitlab-ci.yml` defines three stages:

```text
lint -> test -> release
```

### Lint Stage

| Job                 | Purpose                                         | Runs When                           |
| ------------------- | ----------------------------------------------- | ----------------------------------- |
| `shellcheck`        | Lints all `.sh` files with shellcheck           | `*.sh` or `scripts/hooks/*` changed |
| `markdownlint`      | Validates markdown files with markdownlint-cli2 | `*.md` changed                      |
| `prettier`          | Checks formatting of md, yml, yaml, json        | Relevant files changed              |
| `commit-standards`  | Validates conventional commit format            | Merge requests only                 |
| `plugin-validation` | Validates plugin.json, hooks, skill paths       | `.claude-plugin/**` changed         |

All lint jobs use `rules: changes:` for path-based filtering.
Jobs that do not match any changed paths are skipped (not
created), which keeps pipelines fast.

### Test Stage

| Job       | Purpose                                           |
| --------- | ------------------------------------------------- |
| `summary` | Single merge-gate check; depends on all lint jobs |

The `summary` job uses `needs:` with `optional: true` on each
lint job. This means skipped lint jobs do not block the summary.
Require **only** the `summary` job in your protected-branch
pipeline-success settings -- this avoids the problem where
skipped conditional jobs block merges.

### Release Stage

| Job       | Purpose                                                        |
| --------- | -------------------------------------------------------------- |
| `release` | Validates tag version against `plugin.json`, runs on `v*` tags |

The release job extracts the version from the git tag (stripping
the `v` prefix) and compares it to the `version` field in
`.claude-plugin/plugin.json`. If they do not match, the pipeline
fails.

## Merge Request Pipelines

All lint and summary jobs include `if: $CI_MERGE_REQUEST_IID`
rules, which enables merge request pipelines. This means the
pipeline runs on every push to a merge request branch.

The `commit-standards` job runs **only** on merge requests
(it needs the target branch ref to compare commit messages).

## Variables

| Variable       | Default | Purpose                       |
| -------------- | ------- | ----------------------------- |
| `NODE_VERSION` | `22`    | Node.js version for lint jobs |

The default image is `node:${NODE_VERSION}-slim`. Jobs that do
not need Node (shellcheck, commit-standards, plugin-validation)
override the image to `koalaman/shellcheck-alpine:stable` or
`alpine:latest`.

## Customization

### Adding test jobs

Add test jobs in the `test` stage and include them in the
`summary` job's `needs:` list:

```yaml
unit-tests:
  stage: test
  script:
    - npm ci
    - npm test
  coverage: '/Statements\s+:\s+(\d+\.?\d*)%/'
  rules:
    - if: $CI_MERGE_REQUEST_IID
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

summary:
  stage: test
  needs:
    - job: shellcheck
      optional: true
    - job: markdownlint
      optional: true
    - job: prettier
      optional: true
    - job: commit-standards
      optional: true
    - job: plugin-validation
      optional: true
    - job: unit-tests
      optional: true
  script:
    - echo "All upstream jobs passed."
```

### Adding build jobs

Add a `build` stage between `test` and `release` in the
`stages:` list, then add your build job:

```yaml
stages:
  - lint
  - test
  - build
  - release

build:
  stage: build
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/
  rules:
    - if: $CI_MERGE_REQUEST_IID
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### Extending the release job

To create a GitLab release with artifacts after version validation:

```yaml
release:
  stage: release
  image: registry.gitlab.com/gitlab-org/release-cli:latest
  script:
    - TAG_VERSION="${CI_COMMIT_TAG#v}"
    - PLUGIN_VERSION=$(jq -r '.version' .claude-plugin/plugin.json 2>/dev/null || echo "")
    - |
      if [ "$TAG_VERSION" != "$PLUGIN_VERSION" ]; then
        echo "Tag ($TAG_VERSION) != plugin.json ($PLUGIN_VERSION)"
        exit 1
      fi
  release:
    tag_name: $CI_COMMIT_TAG
    description: 'Release $CI_COMMIT_TAG'
  rules:
    - if: $CI_COMMIT_TAG =~ /^v/
```

## Merge Request Settings

Configure these in your GitLab project under **Settings > Merge requests**:

- Require pipeline to succeed before merge
- Require at least 1 approval
- Enable squash commits by default
- Delete source branch on merge
- Under **Settings > Repository > Protected branches**, require
  only the `summary` job to pass

Enable branch auto-deletion after merge:

```bash
glab api "projects/${PROJECT_PATH}" \
  --method PUT \
  -f "remove_source_branch_after_merge=true"
```

Require pipelines to pass before merge:

```bash
glab api "projects/${PROJECT_PATH}" \
  --method PUT \
  -f "only_allow_merge_if_pipeline_succeeds=true"
```

Add to your project checklist:

- [ ] Merge request settings: delete source branch after
      merge -- enabled
- [ ] Merge request settings: pipelines must succeed -- enabled

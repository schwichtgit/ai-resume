# GitLab CI Mapping Guide

This guide maps the abstract SDLC principles to GitLab CI configuration.

## Mapping

| Abstract Concept  | GitLab CI Equivalent                       |
| ----------------- | ------------------------------------------ |
| Commit gate       | Pipeline stages with `rules: changes`      |
| PR gate           | Merge request pipelines                    |
| Release gate      | Tagged pipelines                           |
| Path filtering    | `rules: changes: [paths]`                  |
| Required checks   | Merge request approvals + pipeline success |
| CODEOWNERS        | GitLab CODEOWNERS format (same syntax)     |
| Branch protection | Protected branches settings                |

## Skeleton .gitlab-ci.yml

```yaml
stages:
  - lint
  - test
  - build

variables:
  NODE_VERSION: '22'

# --- Lint ---
lint:
  stage: lint
  image: node:${NODE_VERSION}
  script:
    - npm ci
    - npx eslint . --quiet
  rules:
    - changes:
        - '**/*.{ts,tsx,js,jsx}'
        - package.json

# --- Type Check ---
typecheck:
  stage: lint
  image: node:${NODE_VERSION}
  script:
    - npm ci
    - npx tsc --noEmit
  rules:
    - changes:
        - '**/*.{ts,tsx}'
        - tsconfig.json

# --- Test ---
test:
  stage: test
  image: node:${NODE_VERSION}
  script:
    - npm ci
    - npm test
  coverage: '/Statements\s+:\s+(\d+\.?\d*)%/'

# --- Build ---
build:
  stage: build
  image: node:${NODE_VERSION}
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/

# --- Commit Standards (MR only) ---
commit-standards:
  stage: lint
  script:
    - |
      COMMITS=$(git log --format='%s' origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME..HEAD)
      echo "$COMMITS" | while read -r msg; do
        if ! echo "$msg" | grep -qE '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+'; then
          echo "FAIL: $msg"
          exit 1
        fi
      done
  rules:
    - if: $CI_MERGE_REQUEST_IID
```

## Merge Request Settings

- Require pipeline to succeed before merge
- Require at least 1 approval
- Enable squash commits by default
- Delete source branch on merge

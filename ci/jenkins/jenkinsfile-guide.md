# Jenkins Pipeline Guide

This guide documents the Jenkins pipeline for specforge
projects. The pipeline enforces the same quality gates as the
GitHub Actions CI workflow, providing platform parity across
CI systems.

## Jenkinsfile Location

The production-ready Jenkinsfile is at:

```text
.claude-plugin/scaffold/jenkins/Jenkinsfile
```

Copy it to the root of your repository when setting up Jenkins CI.

## Pipeline Stages

| Stage             | Trigger            | Purpose                                     |
| ----------------- | ------------------ | ------------------------------------------- |
| Install           | Always             | Install Node.js dependencies and CLI tools  |
| Lint (parallel)   | Always             | ShellCheck, Markdownlint, Prettier          |
| Commit Standards  | PRs only           | Validate conventional commit format         |
| Test              | Always             | Run project test suite (placeholder)        |
| Build             | Always             | Run project build step (placeholder)        |
| Plugin Validation | Always             | Validate plugin.json, hooks.json, file refs |
| Release           | Tagged builds only | Version check + release artifact creation   |

## Quality Gates

### ShellCheck

Runs `shellcheck -x` on all `.sh` files in the repository
(excluding `.git/`). Catches common shell scripting errors,
undefined variables, and quoting issues.

### Markdownlint

Runs `markdownlint-cli2` against all Markdown files (excluding
`node_modules/`). Enforces consistent heading style, list
formatting, and line length rules defined in
`.markdownlint-cli2.yaml`.

### Prettier

Runs `prettier --check .` to verify all Markdown, YAML, and
JSON files match the project formatting rules defined in
`.prettierrc.json`. Does not modify files -- fails if
formatting drifts.

### Commit Standards

Active only on change-request (PR) builds. Validates that
every commit message follows
[Conventional Commits](https://www.conventionalcommits.org/)
format:

```text
type(scope)?: description
```

Where `type` is one of: `feat`, `fix`, `docs`, `style`,
`refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
Subject lines over 72 characters produce a warning. Merge
commits are skipped.

### Plugin Validation

Validates the plugin manifest structure:

- `plugin.json` is valid JSON with required fields (`name`, `version`, `hooks`)
- All referenced skill and agent file paths exist on disk
- `hooks.json` is valid JSON and all hook script paths resolve

## Release Pipeline

The `Release` stage runs only on tagged builds (when `buildingTag()` is true). It:

1. Extracts the version from the git tag (stripping the `v` prefix)
2. Reads the version from `.claude-plugin/plugin.json`
3. Fails the build if the two versions do not match
4. Creates a tarball (`specforge-<version>.tar.gz`) containing
   the `.claude-plugin/` directory
5. Archives the tarball as a Jenkins build artifact with fingerprinting

To trigger a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Prerequisites

### Jenkins Plugins

- **NodeJS Plugin** -- provides `tools { nodejs 'NodeJS-22' }`
  support. Configure a NodeJS 22 installation named `NodeJS-22`
  in Jenkins global tool configuration.
- **Pipeline** -- Declarative Pipeline support (included in
  most Jenkins installations).

### System Dependencies

The Install stage conditionally installs `shellcheck` and `jq`
via `apt-get` if they are not already present on the build
agent. If your agents use a non-Debian base image, adjust the
install commands accordingly.

## Customization

### Adding Your Test Suite

Replace the placeholder in the Test stage:

```groovy
stage('Test') {
    steps {
        sh 'npm test'
    }
    post {
        always {
            junit 'test-results/**/*.xml'
        }
    }
}
```

### Adding Your Build Step

Replace the placeholder in the Build stage:

```groovy
stage('Build') {
    steps {
        sh 'npm run build'
    }
    archiveArtifacts artifacts: 'dist/**', fingerprint: true
}
```

### Path-Based Filtering

Add `when { changeset }` blocks to skip stages when irrelevant files change:

```groovy
stage('ShellCheck') {
    when { changeset '**/*.sh' }
    steps {
        sh 'find . -name "*.sh" -not -path "./.git/*" -print0 | xargs -0 shellcheck -x'
    }
}
```

### Notifications

Add notification steps to the `post` block:

```groovy
post {
    failure {
        slackSend channel: '#ci', message: "Build failed: ${env.BUILD_URL}"
    }
    success {
        slackSend channel: '#ci', message: "Build passed: ${env.BUILD_URL}"
    }
}
```

### Multibranch Pipeline

For automatic PR detection, configure a Multibranch Pipeline job in Jenkins:

1. Create a new Multibranch Pipeline job
2. Add your repository as a branch source (GitHub, Bitbucket, or Git)
3. Set the build configuration to "by Jenkinsfile" with script path `Jenkinsfile`
4. Jenkins will automatically discover branches and PRs

## Splitting Base and Project Configuration

For projects that need to separate plugin-owned stages from
project-specific stages, convert from declarative to scripted
pipeline using the `load` step:

1. Create `ci/jenkins/base.groovy` with your shared stages
   as a closure
2. In `Jenkinsfile`, use scripted pipeline syntax:

```groovy
node {
    checkout scm
    def base = load 'ci/jenkins/base.groovy'
    base()
    stage('Project Tests') { sh 'make test' }
}
```

The `load` step requires `checkout scm` first (the file
must exist in the workspace). This pattern works with
scripted pipelines only -- declarative pipelines cannot
merge two `pipeline {}` blocks.

See the Jenkins documentation on
[Pipeline: Shared Groovy Libraries](https://www.jenkins.io/doc/book/pipeline/shared-libraries/)
for team-wide shared pipelines.

## Parity with GitHub Actions

| Quality Gate       | GitHub Actions Job  | Jenkins Stage         |
| ------------------ | ------------------- | --------------------- |
| ShellCheck         | `shellcheck`        | `Lint > ShellCheck`   |
| Markdownlint       | `markdownlint`      | `Lint > Markdownlint` |
| Prettier           | `prettier`          | `Lint > Prettier`     |
| Commit Standards   | `commit-standards`  | `Commit Standards`    |
| Plugin Validation  | `plugin-validation` | `Plugin Validation`   |
| Version Validation | `validate-version`  | `Release`             |
| Release Artifact   | `release`           | `Release`             |

# Commit Gate

Abstract requirements every commit must satisfy, regardless of CI platform.

## 1. Lint Changed Files

Run the appropriate linter for each changed file's language:

| Language   | Linter          | Command                        |
| ---------- | --------------- | ------------------------------ |
| TypeScript | ESLint          | `npx eslint <files>`           |
| Python     | Ruff            | `ruff check <files>`           |
| Rust       | Clippy          | `cargo clippy -D warnings`     |
| Shell      | ShellCheck      | `shellcheck <files>`           |
| Go         | go vet          | `go vet ./...`                 |
| Ruby       | RuboCop         | `rubocop <files>`              |
| Java       | google-java-fmt | `google-java-format --dry-run` |

Only lint files in the changeset, not the entire project.

## 2. No Secrets in Diff

Scan staged changes for patterns:

- AWS keys: `AKIA[0-9A-Z]{16}`
- OpenAI keys: `sk-[a-zA-Z0-9]{48}`
- GitHub tokens: `ghp_`, `gho_`
- GitLab tokens: `glpat-`
- Slack tokens: `xoxb-`
- Generic: high-entropy strings near keywords `password`, `secret`, `token`, `api_key`

Block the commit if any match is found.

## 3. No Forbidden Files

Block commits that include:

`.env*`, `*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `credentials.json`, `service-account*.json`, `*.keystore`

## 4. Conventional Commit Format

Subject line must match:

```text
^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+
```

- Subject line: <= 72 characters
- Body lines: <= 100 characters (warning, not block)

## 5. No AI-isms

Block (case-insensitive):

- **Self-references:** "I have", "I've", "I updated", "I fixed"
- **Filler:** "Certainly", "I'd be happy to", "As an AI"
- **Marketing adjectives:** "seamless", "robust", "powerful", "elegant", "streamlined", "polished", "enhanced", "refined"
- **AI branding:** "Anthropic", "GPT", "OpenAI", "Copilot"
- **Standalone "Claude"** (allow "Claude Code" as product reference)
- **Co-Authored-By trailers**

## 6. No Emoji

Block Unicode emoji in commit messages: U+1F300-U+1F9FF, U+2600-U+27BF, and related ranges.

## 7. No Draft Markers

Warn (not block): WIP, FIXME, TODO, XXX, DO NOT MERGE, temp, temporary, debug.

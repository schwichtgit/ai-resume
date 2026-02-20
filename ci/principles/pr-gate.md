# PR Gate

All commit gate checks apply to every commit in the PR, plus the following.

## 1. Type Checking

Full type checker per language:

| Language   | Command             |
| ---------- | ------------------- |
| TypeScript | `tsc --noEmit`      |
| Python     | `mypy` or `pyright` |
| Rust       | `cargo check`       |
| Go         | `go build ./...`    |

## 2. Test Suite

Full test suite passes with zero failures.

## 3. Code Coverage

Coverage >= configurable threshold (default 85%). Report coverage delta from base branch.

## 4. Static Analysis

| Language   | Commands                                        |
| ---------- | ----------------------------------------------- |
| TypeScript | ESLint                                          |
| Python     | Ruff lint + Ruff format check                   |
| Rust       | `cargo clippy -D warnings`, `cargo fmt --check` |
| Shell      | ShellCheck                                      |
| Go         | `go vet`                                        |

## 5. Format Check

| Language                    | Formatter   |
| --------------------------- | ----------- |
| JS/TS/JSON/CSS/HTML/YAML/MD | Prettier    |
| Python                      | Ruff format |
| Rust                        | `cargo fmt` |
| Shell                       | shfmt       |
| Go                          | gofmt       |

## 6. Build Verification

Project builds successfully in a clean environment.

## 7. No Merge Conflicts

No unresolved merge conflict markers in any file.

## 8. Commit Standards

Every commit in the PR passes all commit gate checks.

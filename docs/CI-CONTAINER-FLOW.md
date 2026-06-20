# CI Container Flow

Reference for the multi-architecture container build pipeline and Sigstore
supply chain security model.

## Overview

This project produces four container images (frontend, api, memvid, ingest)
for two platforms (amd64, arm64). The CI workflow builds, scans, signs, and
pushes arch-specific images. The release workflow merges them into multi-arch
manifest lists, verifies all signatures, and applies semver tag families.

Signing uses Sigstore keyless (Fulcio + Rekor) with GitHub Actions OIDC. No
manual key management.

## Pipeline Triggers

| Trigger                | Condition | Jobs that run                                                                           |
| ---------------------- | --------- | --------------------------------------------------------------------------------------- |
| Push to `main`         | Always    | `changes`, service jobs, `release-gate`, `container-build` (if container paths changed) |
| Tag push (`v*.*.*`)    | Always    | `changes`, `container-build` (all 8 cells), then Release workflow                       |
| Pull request to `main` | Always    | `changes`, service jobs, `commit-standards`                                             |
| `workflow_dispatch`    | Manual    | Same as push to `main`                                                                  |

The `container-build` job runs when Dockerfile or service source paths change,
or unconditionally on tag pushes.

## Architecture

```text
CI Workflow (ci.yml):
  changes ──> container-build (matrix: 4 images x 2 platforms = 8 cells)
                 |
                 ├── build image (podman)
                 ├── Trivy SARIF scan + severity gate
                 ├── smoke tests (run, non-root, health, OCI annotations)
                 ├── push arch image (publish-ci.sh push-arch)
                 ├── generate CycloneDX SBOM (syft against pushed digest)
                 ├── attest SBOM (cosign attest --type cyclonedx)
                 ├── sign image (cosign sign, keyless)
                 └── upload digest JSON artifact

Release Workflow (release.yml):
  validate ──> merge-manifests (4 images)
               |
               ├── download CI digest artifacts (gh api)
               ├── create manifest list (publish-ci.sh merge --digest-*)
               └── sign manifest list (cosign sign)
               |
           ──> verify-signatures (4 images)
               |
               ├── verify arch image sigs (CI workflow identity)
               └── verify manifest list sig (release workflow identity)
               |
           ──> publish-tags
               |
               └── apply semver tag family (publish-ci.sh tag-family)
               |
           ──> create-release
               |
               └── gh release create --generate-notes
```

## Container Build Job

Each matrix cell (image x platform) runs on a native runner (`ubuntu-latest`
for amd64, `ubuntu-24.04-arm` for arm64) and executes these steps in order:

1. **Build** -- `podman build` with OCI annotations (title, source, version,
   created, revision, licenses, vendor).
2. **Trivy SARIF scan** -- Uploads results to GitHub Code Scanning.
3. **Trivy severity gate** -- Fails the job on unfixed CRITICAL or HIGH
   vulnerabilities.
4. **Smoke tests** -- Container starts, runs as non-root, health endpoint
   responds, OCI version annotation present.
5. **Push** -- `publish-ci.sh push-arch` pushes to
   `ghcr.io/schwichtgit/<image>:<version>.<arch>` and captures the digest via
   `--digestfile`.
6. **Digest metadata** -- Writes `{image, platform, digest, version}` JSON.
7. **Upload digest artifact** -- Uploads JSON as `digest-<short>-<arch>` with
   1-day retention.
8. **SBOM generation** -- `syft <registry>/<image>@<digest>` produces
   CycloneDX JSON. Runs against the pushed digest, not the local build cache.
9. **SBOM attestation** -- `cosign attest --type cyclonedx` stores the SBOM as
   an OCI 1.1 referrer on the image.
10. **Image signing** -- `cosign sign` (keyless) signs the image by digest.
    Fulcio issues a short-lived cert; Rekor records the inclusion proof.
11. **SBOM artifact upload** -- Uploads CycloneDX JSON to Actions artifacts
    with 90-day retention.

Steps 5-11 only execute on pushes to `main` or tag pushes (`v*`). PR builds
stop after smoke tests.

## Tag Conventions

| Pattern                   | Example                       | When                             |
| ------------------------- | ----------------------------- | -------------------------------- |
| Version tag               | `v1.0.0`                      | Tag push                         |
| Version tag (pre-release) | `v1.0.0-alpha.1`              | Tag push                         |
| Dev tag                   | `dev-abc1234-B20260223143022` | Push to `main`                   |
| Arch suffix               | `v1.0.0.amd64`                | Per-platform image (CI)          |
| Minor tag                 | `1.0`                         | Stable release (tag-family)      |
| Bare version              | `1.0.0`                       | Stable release (tag-family)      |
| SHA tag                   | `sha-abc1234`                 | All releases (tag-family)        |
| `latest`                  | `latest`                      | Stable release only (tag-family) |

Dev tags include a build timestamp (`B<YYYYMMDDHHMMSS>`) to guarantee
uniqueness across re-runs of the same commit.

## Digest Handoff

The CI and release workflows run in separate workflow contexts. Digests bridge
them:

1. Each `container-build` matrix cell pushes its arch image and captures the
   digest via `podman push --digestfile`.
2. The digest is written into a JSON artifact:

   ```json
   {
     "image": "ai-resume-frontend",
     "platform": "amd64",
     "digest": "sha256:abc123...",
     "version": "v1.0.0"
   }
   ```

3. The artifact is uploaded as `digest-<short>-<arch>` with 1-day retention.
4. The release workflow's `merge-manifests` job finds the CI run for the tagged
   commit via `gh api`, downloads the digest artifacts by name, and extracts
   the sha256 values.
5. Digests are passed to `publish-ci.sh merge` via `--digest-amd64` and
   `--digest-arm64` flags, which uses `podman manifest add <image>@<digest>`
   for provenance-safe pinning.

This eliminates the TOCTOU window that would exist if manifests referenced
mutable tags.

## publish-ci.sh Subcommands

| Subcommand   | Description                                                                                                                                                              | Key tool                          |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------- |
| `push-arch`  | Push a single-arch image to registry with `.<arch>` suffix. Captures and outputs `DIGEST=<value>`.                                                                       | `podman push --digestfile`        |
| `merge`      | Create OCI manifest list from arch-specific images. Supports digest-based (`--digest-amd64`, `--digest-arm64`) or tag-based fallback. Outputs `MANIFEST_DIGEST=<value>`. | `podman manifest create/add/push` |
| `tag-family` | Apply semver tag family via server-side re-tagging. Stable: sha + bare + minor + latest. Pre-release: sha + bare only.                                                   | `skopeo copy --all`               |
| `verify`     | Verify cosign signatures against GitHub Actions OIDC identities. Tries ci.yml identity first, falls back to release.yml.                                                 | `cosign verify`                   |

All subcommands accept `--dry-run` for safe testing.

## Sigstore Security Model

### Fulcio (Certificate Authority)

Fulcio exchanges a GitHub Actions OIDC token for a short-lived X.509
certificate (10-minute validity). The certificate embeds the workflow identity
claim (e.g., `ci.yml@refs/heads/main`) as a SAN extension. No long-lived
signing keys exist; each CI run gets a fresh ephemeral certificate. The
`id-token: write` permission is required for the OIDC token request.

### Rekor (Transparency Log)

Rekor records an inclusion proof with a trusted timestamp when the signature is
created. The entry is immutable and append-only. This proves the signature was
created while the Fulcio certificate was valid, so certificate expiry does not
affect verification after the fact. Rekor entries are publicly auditable.

### OCI 1.1 Referrers

Signatures and SBOM attestations are stored as OCI 1.1 referrers attached to
the signed image. This means they travel with the image across registries and
are discoverable by security scanners without out-of-band lookups. Use
`cosign tree` to inspect the referrer graph for any image.

## Signing Chain

1. CI builds and pushes arch images, capturing digests via `--digestfile`.
2. CI generates a CycloneDX SBOM against the pushed image by digest (`syft
<registry>/<image>@<digest>`).
3. CI attaches the SBOM as an OCI 1.1 referrer via `cosign attest --type
cyclonedx`.
4. CI signs the image by digest with `cosign sign` (keyless: Fulcio cert +
   Rekor inclusion proof).
5. CI uploads a digest JSON artifact per matrix cell.
6. Release downloads digests and creates manifest lists using digest-pinned
   refs (`podman manifest add <image>@<digest>`).
7. Release signs each manifest list with `cosign sign`.
8. The `verify-signatures` job gates tag promotion: `cosign verify` with
   workflow-scoped certificate identity for both arch images (CI-signed) and
   manifest lists (release-signed).
9. Only after verification passes: semver tag family applied via `skopeo copy
--all`.

Step ordering (SBOM, then attestation, then signing) follows the Sigstore
reference workflow convention.

## Consumer Verification

```bash
# Verify an arch image (CI-signed)
cosign verify \
  --certificate-identity 'https://github.com/schwichtgit/ai-resume/.github/workflows/ci.yml@refs/heads/main' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ghcr.io/schwichtgit/ai-resume-frontend:v1.0.0.amd64

# Verify a manifest list (release-signed)
cosign verify \
  --certificate-identity 'https://github.com/schwichtgit/ai-resume/.github/workflows/release.yml@refs/tags/v1.0.0' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ghcr.io/schwichtgit/ai-resume-frontend:v1.0.0

# Inspect the referrer graph (signatures + attestations)
cosign tree ghcr.io/schwichtgit/ai-resume-frontend:v1.0.0
```

The `publish-ci.sh verify` subcommand wraps these checks and tries both
workflow identities automatically:

```bash
scripts/publish-ci.sh verify ghcr.io/schwichtgit ai-resume-frontend v1.0.0
```

## Attestation Artifacts

| Artifact         | Format              | Storage                             | Retention           |
| ---------------- | ------------------- | ----------------------------------- | ------------------- |
| Image signature  | Sigstore bundle     | OCI 1.1 referrer                    | Permanent           |
| SBOM attestation | in-toto (CycloneDX) | OCI 1.1 referrer + Actions artifact | Permanent / 90 days |
| Digest metadata  | JSON                | Actions artifact                    | 1 day               |
| Trivy SARIF      | SARIF               | GitHub Code Scanning                | Permanent           |

## Design Decisions

| Decision                                     | Rationale                                                                                                                                                       |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Digest-based handoff (not tag-based)         | Eliminates TOCTOU window between CI push and release manifest creation. Mutable tags could be overwritten between workflows.                                    |
| CycloneDX (not SPDX)                         | Broader tooling support in container and DevSecOps ecosystems. Both are valid; CycloneDX has wider adoption in OCI/cosign toolchains.                           |
| Workflow-scoped identity (not repo-scoped)   | Tighter security: only the designated CI or release workflow can produce valid signatures. Repo-scoped would allow any workflow in the repo to sign.            |
| SBOM against pushed digest (not local image) | Ensures the SBOM describes exactly what is in the registry, not the local build cache. Provably accurate.                                                       |
| Always-blocking failures                     | `cosign sign`, `cosign attest`, and `syft` all fail the job on error. No soft gates for signing. Sigstore infrastructure (Fulcio, Rekor) has high availability. |
| Build timestamp dev tags                     | `dev-<sha>-B<YYYYMMDDHHMMSS>` guarantees uniqueness across re-runs. Plain sha tags would collide.                                                               |
| `COSIGN_YES: "true"` env var                 | Single declaration at job level instead of `--yes` per invocation. Avoids interactive prompts in CI.                                                            |

## Related Scanning

This doc covers the build -> sign -> publish pipeline. Two adjacent scans run
outside it:

- **In-CI Trivy** -- the `container-build` job scans each image and gates on
  unfixed CRITICAL/HIGH (steps above), uploading SARIF to GitHub code scanning.
- **Weekly Security Scan** (`.github/workflows/security.yml`) -- re-scans the
  published images with Trivy and runs `task audit` (npm/pip/cargo) on a
  schedule. See [SECURITY.md](./SECURITY.md).

## Related

- ADR-019: Native ARM Runner Multi-Arch Container Builds (see `.specify/specs/plan.md`)
- ADR-020: Container Supply Chain Security via Sigstore (see `.specify/specs/plan.md`)

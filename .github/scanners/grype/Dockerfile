# Version pin only -- this file is never built.
#
# The container-build job in .github/workflows/ci.yml reads the image
# reference from the FROM line below and runs Grype from it. Dependabot's
# docker ecosystem watches this directory and bumps the tag and digest
# together, which a `uses: docker://` reference in a workflow cannot get
# (dependabot/dependabot-core#8362).
#
# ghcr.io, not docker.io: Anchore publishes the same image to both (identical
# index digest), and ghcr.io avoids Docker Hub's anonymous pull limit on
# shared runner IPs.
#
# The digest is the multi-arch index, so amd64 and arm64 runners pull the
# same reference. Keep comments off the FROM line: podman rejects them.
FROM ghcr.io/anchore/grype:v0.121.0@sha256:621d56d1d68106b787022c81546f7e0a36202a25d1239f0c20195fab8c16f7ea

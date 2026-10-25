# Version pin only -- this file is never built.
#
# The container-build job in .github/workflows/ci.yml and the container-scan
# job in .github/workflows/security.yml read the image reference from the FROM
# line below and run Trivy from it. Dependabot's docker ecosystem watches this
# directory and bumps the tag and digest together, which a `uses: docker://`
# reference in a workflow cannot get (dependabot/dependabot-core#8362).
#
# The digest is the multi-arch index, so amd64 and arm64 runners pull the
# same reference. Keep comments off the FROM line: podman rejects them.
FROM ghcr.io/aquasecurity/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c

#!/bin/bash
# Build the frontend (React SPA + OpenResty) container.
# Usage: ./build-frontend.sh [version] [--no-cache]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/container-build.sh
source "${SCRIPT_DIR}/lib/container-build.sh"
REPO_ROOT="$(container_build_repo_root)"
cd "${REPO_ROOT}"

require_podman
parse_container_build_args "$@"

SERVICE="frontend"
TITLE="ai-resume-frontend"
DESCRIPTION="React SPA with OpenResty reverse proxy"
DOCKERFILE="frontend/Dockerfile"
CONTEXT="frontend/"
export SERVICE TITLE DESCRIPTION DOCKERFILE CONTEXT

build_one_container

#!/bin/bash
# Build the Python FastAPI container.
# Usage: ./build-api.sh [version] [--no-cache]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/container-build.sh
source "${SCRIPT_DIR}/lib/container-build.sh"
REPO_ROOT="$(container_build_repo_root)"
cd "${REPO_ROOT}"

require_podman
parse_container_build_args "$@"
sync_proto_into "api-service"

SERVICE="api"
TITLE="ai-resume-api"
DESCRIPTION="FastAPI backend for profile API and gRPC client"
DOCKERFILE="api-service/Dockerfile"
CONTEXT="api-service/"
export SERVICE TITLE DESCRIPTION DOCKERFILE CONTEXT

build_one_container

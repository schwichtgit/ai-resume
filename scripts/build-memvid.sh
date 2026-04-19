#!/bin/bash
# Build the Rust memvid gRPC container.
# Usage: ./build-memvid.sh [version] [--no-cache]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/container-build.sh
source "${SCRIPT_DIR}/lib/container-build.sh"
REPO_ROOT="$(container_build_repo_root)"
cd "${REPO_ROOT}"

require_podman
parse_container_build_args "$@"
sync_proto_into "memvid-service"

SERVICE="memvid"
TITLE="ai-resume-memvid"
DESCRIPTION="Rust gRPC service for semantic search over resume data"
DOCKERFILE="memvid-service/Dockerfile"
CONTEXT="memvid-service/"
export SERVICE TITLE DESCRIPTION DOCKERFILE CONTEXT

build_one_container

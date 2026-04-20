#!/bin/bash
# Build the Python ingest container.
# Usage: ./build-ingest.sh [version] [--no-cache]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/container-build.sh
source "${SCRIPT_DIR}/lib/container-build.sh"
REPO_ROOT="$(container_build_repo_root)"
cd "${REPO_ROOT}"

require_podman
parse_container_build_args "$@"

SERVICE="ingest"
TITLE="ai-resume-ingest"
DESCRIPTION="Data ingestion pipeline for .mv2 file creation"
DOCKERFILE="ingest/Dockerfile"
CONTEXT="ingest/"
export SERVICE TITLE DESCRIPTION DOCKERFILE CONTEXT

build_one_container

#!/bin/bash
set -euo pipefail

# Generate Python protobuf stubs from .proto files
# Run from project root: ./scripts/gen-proto.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$PROJECT_ROOT/api-service"

echo "Generating protobuf stubs..."

# Activate the api-service venv for grpc_tools
# shellcheck disable=SC1091
source "$API_DIR/.venv/bin/activate"

cd "$API_DIR"

# Resolve the proto directory the way memvid-service/build.rs already does.
# The authoritative copy is <repo>/proto (the only one tracked in git);
# api-service/proto is a gitignored copy that exists solely for container
# builds, where the build context is the service directory. Hardcoding the
# service-local path meant this script only worked on a machine that already
# had that untracked copy -- it failed on a fresh clone and in CI.
if [ -d "$PROJECT_ROOT/proto" ]; then
    PROTO_DIR="$PROJECT_ROOT/proto"
elif [ -d "$API_DIR/proto" ]; then
    PROTO_DIR="$API_DIR/proto"
else
    echo "error: no proto directory at $PROJECT_ROOT/proto or $API_DIR/proto" >&2
    exit 1
fi

# Generate Python stubs from proto definition
python -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out=./ai_resume_api/proto \
    --grpc_python_out=./ai_resume_api/proto \
    "$PROTO_DIR/memvid/v1/memvid.proto"

# Create __init__.py files for the package hierarchy
touch ai_resume_api/proto/__init__.py
touch ai_resume_api/proto/memvid/__init__.py
touch ai_resume_api/proto/memvid/v1/__init__.py

# Fix the absolute import in the generated _grpc.py file
# protoc generates: from memvid.v1 import memvid_pb2
# We need:          from ai_resume_api.proto.memvid.v1 import memvid_pb2
# Use python for portable in-place edit (works with both GNU and BSD sed)
python -c "
import pathlib
f = pathlib.Path('ai_resume_api/proto/memvid/v1/memvid_pb2_grpc.py')
f.write_text(f.read_text().replace(
    'from memvid.v1 import memvid_pb2',
    'from ai_resume_api.proto.memvid.v1 import memvid_pb2'
))
"

echo "Protobuf stubs generated and patched successfully."
echo "Output: ai_resume_api/proto/memvid/v1/"

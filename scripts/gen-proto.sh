#!/bin/bash
set -euo pipefail

# Generate Python protobuf stubs from .proto files
# Run from project root: ./scripts/gen-proto.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$PROJECT_ROOT/api-service"

echo "Generating protobuf stubs..."

# Activate the api-service venv for grpc_tools
source "$API_DIR/.venv/bin/activate"

cd "$API_DIR"

# Generate Python stubs from proto definition
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./ai_resume_api/proto \
    --grpc_python_out=./ai_resume_api/proto \
    ./proto/memvid/v1/memvid.proto

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

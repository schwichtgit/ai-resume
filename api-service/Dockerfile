# Multi-stage Dockerfile for Python FastAPI service
# Supports amd64 and arm64 architectures

# Stage 1: Build dependencies with UV
FROM python:3.12-slim AS builder

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:0.9.26-python3.12-trixie-slim /usr/local/bin/uv /usr/local/bin/uv

# Install build dependencies
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
       gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock* README.md ./

# Install dependencies with UV (not in editable mode for production)
RUN uv sync --no-dev --frozen --no-editable

# Stage 2: Generate protobuf stubs
FROM python:3.12-slim AS proto-builder

WORKDIR /app

# Copy virtual environment from builder (has grpcio-tools)
COPY --from=builder /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH

# Copy proto files
COPY proto/ ./proto/

# Create output directory and generate Python gRPC stubs
# Use sed to fix the import path in generated grpc file
RUN mkdir -p ai_resume_api/proto && \
    python -m grpc_tools.protoc \
        -I./proto \
        --python_out=./ai_resume_api/proto \
        --grpc_python_out=./ai_resume_api/proto \
        ./proto/memvid.proto && \
    touch ai_resume_api/proto/__init__.py && \
    sed -i 's/import memvid_pb2/from ai_resume_api.proto import memvid_pb2/' ai_resume_api/proto/memvid_pb2_grpc.py

# Stage 3: Runtime image
FROM python:3.12-slim

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY ai_resume_api/ ./ai_resume_api/

# Copy generated proto stubs
COPY --from=proto-builder /app/ai_resume_api/proto/ ./ai_resume_api/proto/

# Copy healthcheck and startup scripts to root for container orchestration
COPY healthcheck /healthcheck
COPY start.py /start.py
RUN chmod +x /healthcheck /start.py

# Ensure venv is in PATH
ENV PATH=/app/.venv/bin:$PATH
ENV VIRTUAL_ENV=/app/.venv

# Expose HTTP port
EXPOSE 3000

# Run startup wrapper that auto-detects IPv4/IPv6 support
# Supports BIND_ADDRESS env var: "auto" (default), "::", or "0.0.0.0"
CMD ["python3", "/start.py"]

# --- Stage 1: Dependency Builder ---
# Uses the official uv image to create the production virtual environment
FROM ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install ONLY production dependencies (no dev-dependencies)
# Using cache mounts for lightning-fast subsequent builds
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# --- Stage 2: Proto Generation (Ephemeral) ---
# We use a separate stage to keep the heavy grpcio-tools out of our final image
FROM ghcr.io/astral-sh/uv:0.9.26-python3.12-bookworm-slim AS proto-builder

WORKDIR /app
COPY proto/ ./proto/

# uvx runs the compiler as a standalone tool without polluting the project venv
RUN --mount=type=cache,target=/root/.cache/uv \
    mkdir -p ai_resume_api/proto && \
    uvx --with grpcio-tools python -m grpc_tools.protoc \
        -I./proto \
        --python_out=./ai_resume_api/proto \
        --grpc_python_out=./ai_resume_api/proto \
        ./proto/memvid.proto && \
    touch ai_resume_api/proto/__init__.py && \
    # Fix the relative import issue in the generated gRPC code
    sed -i 's/import memvid_pb2/from ai_resume_api.proto import memvid_pb2/' ai_resume_api/proto/memvid_pb2_grpc.py

# --- Stage 3: Runtime ---
# The lean final image based on the stable Bookworm release
FROM python:3.12-slim-bookworm

# Production hardening: no .pyc creation at runtime, unbuffered logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

WORKDIR /app

# Copy the lean production venv from Stage 1
COPY --from=builder /app/.venv /app/.venv

# Copy the generated proto stubs from Stage 2
COPY --from=proto-builder /app/ai_resume_api/proto/ ./ai_resume_api/proto/

# Copy your application source
COPY ai_resume_api/ ./ai_resume_api/
COPY healthcheck /healthcheck
COPY start.py /start.py

# Ensure scripts are executable and system is patched
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    chmod +x /healthcheck /start.py

# Expose the API port
EXPOSE 3000

# Launch the service using the venv python
CMD ["python", "/start.py"]
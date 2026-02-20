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

# --- Stage 2: Runtime ---
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

# Pre-cache the HuggingFace embedding model in the image layer.
# BAAI/bge-small-en-v1.5 is the model used by ingest.py for semantic search.
# Downloading at build time avoids network access at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Copy application source
COPY ingest.py ./ingest.py

# Patch system and create non-root user
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -u 1000 -s /bin/false appuser

# Run as non-root user
USER appuser

# One-shot service: run ingest pipeline then exit
CMD ["python", "ingest.py"]

# --- Stage 1: Dependency Builder ---
# Uses the official uv image to create the production virtual environment
FROM astral/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install ONLY production dependencies (no dev-dependencies)
# Using cache mounts for lightning-fast subsequent builds
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Pre-cache the HuggingFace embedding model in the builder stage.
# BAAI/bge-small-en-v1.5 is the model used by ingest.py for semantic search.
# Downloading at build time avoids network access at runtime.
# HF_HOME is set to /app/.hf so the cache can be COPYed to the runtime stage.
ENV HF_HOME=/app/.hf
RUN --mount=type=cache,target=/root/.cache/uv \
    /app/.venv/bin/python -c \
    "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# --- Stage 2: Runtime ---
# Ubuntu Python 3.12 on Ubuntu 24.04 LTS — stable, pinned, regularly patched
FROM docker.io/ubuntu/python:3.12-24.04_stable

# Production hardening: no .pyc creation at runtime, unbuffered logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv \
    HF_HOME=/app/.hf

WORKDIR /app

# Copy the lean production venv from Stage 1
COPY --from=builder /app/.venv /app/.venv

# Copy the pre-cached HuggingFace model from Stage 1
COPY --from=builder /app/.hf /app/.hf

# Copy application source
COPY ingest.py ./ingest.py

# pebble is not invoked: ENTRYPOINT below overrides the inherited pebble entrypoint.
# The binary cannot be removed (no shell in this image) but is never executed.
# CVE-2025-68121 is mitigated by not invoking pebble.
# _daemon_ (uid 584792) is the only unprivileged user available in this distroless image.
USER _daemon_

# One-shot service: run ingest pipeline then exit
ENTRYPOINT ["/usr/bin/python3"]
CMD ["ingest.py"]

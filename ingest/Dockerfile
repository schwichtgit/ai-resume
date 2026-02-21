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

# --- Stage 2: Runtime ---
# Ubuntu Python 3.12 on Ubuntu 24.04 LTS — stable, pinned, regularly patched
FROM docker.io/ubuntu/python:3.12-24.04_stable

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

# Clear the inherited pebble entrypoint; remove the vulnerable binary
# (CVE-2025-68121: crypto/tls in pebble's embedded Go stdlib v1.24.12).
# pebble is not used — we run python directly via CMD.
ENTRYPOINT []
RUN rm /usr/bin/pebble \
    && useradd -r -u 1000 -s /bin/false appuser
USER appuser

# One-shot service: run ingest pipeline then exit
CMD ["python", "ingest.py"]

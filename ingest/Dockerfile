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
ENV HF_HOME=/app/.hf
RUN /app/.venv/bin/python -c \
    "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# --- Stage 2: Runtime ---
# python:3.12-slim-bookworm matches the builder's Debian lineage so venv
# symlinks (which point to /usr/local/bin/python3) resolve correctly.
FROM python:3.12-slim-bookworm

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

# Upgrade OS packages for security fixes (libgnutls30), remove pip, create user
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* && \
    pip uninstall -y pip setuptools && \
    useradd -r -u 1000 -s /bin/false appuser

USER appuser

# One-shot service: run ingest pipeline then exit
CMD ["python", "ingest.py"]

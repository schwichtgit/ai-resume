# --- Stage 1:  ---
# aquire uv
FROM docker.io/ubuntu:24.04 AS uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_INSTALL_DIR="/usr/local/bin"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        python3.12 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    curl -OL --silent https://astral.sh/uv/install.sh && \
    chmod +x /install.sh && \
    ./install.sh && \
    rm ./install.sh

# --- Stage 2: Chiselled Venv Builder ---
FROM docker.io/ubuntu/python:3.12-24.04_stable AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY --from=uv /usr/local/bin/uv /usr/local/bin/uv

# Install ONLY production dependencies (no dev-dependencies)
# Using cache mounts for lightning-fast subsequent builds
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev && \
    touch /tmp/empty


# Pre cache the HuggingFace embedding model in the builder stage.
# BAAI/bge-small-en-v1.5 is the model used by ingest.py for semantic search.
# Downloading at build time avoids network access at runtime.
# HF_HOME is set to /app/.hf so the cache can be COPYed to the runtime stage.
ENV HF_HOME=/app/.hf
RUN --mount=type=cache,target=/root/.cache/uv \
    /app/.venv/bin/python -c \
    "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# --- Stage 3: Runtime ---
FROM docker.io/ubuntu/python:3.12-24.04_stable

# Null pebble CVE
COPY --from=builder /tmp/empty /usr/bin/pebble

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv \
    HF_HOME=/app/.hf

WORKDIR /app

# --- Stage 2: Runtime ---
# Ubuntu Python 3.12 on Ubuntu 24.04 LTS — stable, pinned, regularly patched
FROM docker.io/ubuntu/python:3.12-24.04_stable

# Production hardening: no .pyc creation at runtime, unbuffered logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv \
    HF_HOME=/app/.hf

# Overwrite pebble binary with empty file BEFORE copying app
COPY --from=builder  /tmp/empty /usr/bin/pebble

WORKDIR /app

# Copy the lean production venv from Stage 1
COPY --from=builder /app/.venv /app/.venv

# Copy the pre-cached HuggingFace model from Stage 1
COPY --from=builder /app/.hf /app/.hf

# Copy application source
COPY ingest.py ./ingest.py

# _daemon_ (uid 584792) is the only unprivileged user available in this distroless image.
USER _daemon_

# One-shot service: run ingest pipeline then exit
ENTRYPOINT ["/app/.venv/bin/python"]
CMD ["ingest.py"]

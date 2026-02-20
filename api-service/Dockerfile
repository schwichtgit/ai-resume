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

# OCI image metadata (dynamic values passed via --build-arg)
ARG VERSION=latest
ARG GIT_REVISION=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="ai-resume-api" \
      org.opencontainers.image.description="FastAPI backend for profile API and gRPC client" \
      org.opencontainers.image.url="https://frank-resume.schwichtenberg.us" \
      org.opencontainers.image.source="https://github.com/schwichtgit/ai-resume" \
      org.opencontainers.image.documentation="https://github.com/schwichtgit/ai-resume#readme" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_REVISION}" \
      org.opencontainers.image.licenses="UNLICENSED" \
      org.opencontainers.image.vendor="schwichtgit" \
      org.opencontainers.image.authors="https://github.com/schwichtgit" \
      org.opencontainers.image.base.name="python:3.12-slim-bookworm"

# Production hardening: no .pyc creation at runtime, unbuffered logs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

WORKDIR /app

# Copy the lean production venv from Stage 1
COPY --from=builder /app/.venv /app/.venv

# Copy application source (includes committed proto stubs with correct imports)
COPY ai_resume_api/ ./ai_resume_api/
COPY healthcheck /healthcheck
COPY start.py /start.py

# Ensure scripts are executable, create non-root user, and patch system
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    chmod +x /healthcheck /start.py && \
    useradd -r -u 1000 -s /bin/false appuser

# Expose the API port
EXPOSE 3000

# Run as non-root user
USER appuser

# Launch the service using the venv python
CMD ["python", "/start.py"]
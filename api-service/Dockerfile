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

# Copy application source (includes committed proto stubs with correct imports)
COPY ai_resume_api/ ./ai_resume_api/
COPY healthcheck /healthcheck
COPY start.py /start.py

# Clear the inherited pebble entrypoint; remove the vulnerable binary
# (CVE-2025-68121: crypto/tls in pebble's embedded Go stdlib v1.24.12).
# pebble is not used — we run python directly via CMD.
ENTRYPOINT []
RUN rm /usr/bin/pebble \
    && chmod +x /healthcheck /start.py \
    && useradd -r -u 1000 -s /bin/false appuser
USER appuser

# Expose the API port
EXPOSE 3000

# Launch the service using the venv python
CMD ["python", "/start.py"]
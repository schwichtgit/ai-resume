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
# python:3.12-slim-bookworm matches the builder's Debian lineage so venv
# symlinks (which point to /usr/local/bin/python3) resolve correctly.
FROM python:3.12-slim-bookworm

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

# Copy scripts with executable bit set at COPY time
COPY --chmod=755 healthcheck /healthcheck
COPY --chmod=755 start.py /start.py

# Remove pip to eliminate CVE-2025-8869, then create unprivileged user
RUN pip uninstall -y pip setuptools && \
    useradd -r -u 1000 -s /bin/false appuser

USER appuser

# Expose the API port
EXPOSE 3000

# Launch the service using the venv python
CMD ["python", "/start.py"]

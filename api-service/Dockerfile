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
# Distroless Python runtime (no pip, smaller attack surface)
FROM cgr.dev/chainguard/python:3.12

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

# Ensure scripts are executable
RUN chmod +x /healthcheck /start.py

# Expose the API port
EXPOSE 3000

# Chainguard distroless images run as non-root by default

# Launch the service using the venv python
CMD ["python", "/start.py"]
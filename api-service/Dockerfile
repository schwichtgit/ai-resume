ARG BUILD_VERSION=dev
ARG BUILD_COMMIT=unknown

# --- Stage 1: Builder ---
# Rocky 10 minimal (microdnf) with compilers and uv for building the production venv
FROM rockylinux/rockylinux:10-minimal AS builder

# Install Python 3.12 + build toolchain for native extensions (grpcio)
RUN microdnf install -y --nodocs \
    python3.12 python3.12-devel \
    gcc gcc-c++ \
    && microdnf clean all

# Grab the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=/usr/bin/python3.12

WORKDIR /app

# Install ONLY production dependencies (no dev-dependencies)
# Using cache mounts for fast subsequent builds
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ARG BUILD_VERSION
ARG BUILD_COMMIT
RUN printf '{"version":"%s","commit":"%s"}\n' "${BUILD_VERSION}" "${BUILD_COMMIT}" > /app/VERSION

# --- Stage 2: Python runtime staging ---
# Rocky 10 minimal has microdnf to install Python + shared libraries, then we
# stage everything into /python-runtime/ for a single COPY into ubi-micro.
FROM rockylinux/rockylinux:10-minimal AS python-deps

RUN microdnf install -y --nodocs \
    python3.12 \
    libstdc++ \
    libffi \
    openssl-libs \
    zlib \
    bzip2-libs \
    xz-libs \
    libuuid \
    sqlite-libs \
    && microdnf clean all

# Stage Python interpreter + stdlib + shared libs into a clean tree
RUN mkdir -p /python-runtime/usr/bin \
    /python-runtime/usr/lib64 \
    /python-runtime/usr/lib \
    && cp /usr/bin/python3.12 /python-runtime/usr/bin/python3.12 \
    && ln -s python3.12 /python-runtime/usr/bin/python3 \
    && cp -a /usr/lib64/python3.12 /python-runtime/usr/lib64/python3.12 \
    && if [ -d /usr/lib/python3.12 ]; then \
    cp -a /usr/lib/python3.12 /python-runtime/usr/lib/python3.12; \
    fi \
    && for lib in \
    libpython3.12.so* \
    libffi.so* \
    libssl.so* \
    libcrypto.so* \
    libz.so* \
    libbz2.so* \
    liblzma.so* \
    libsqlite3*.so* \
    libuuid.so* \
    libstdc++.so* \
    libgcc_s.so* \
    'libgcc_s-*.so*' \
    ; do \
    find /usr/lib64 -maxdepth 1 -name "$lib" -exec cp -a {} /python-runtime/usr/lib64/ \; 2>/dev/null; \
    done

# --- Stage 3: Runtime ---
# ubi-micro has no shell, no package manager -- only what we explicitly copy.
FROM registry.access.redhat.com/ubi10/ubi-micro

# Python runtime from Stage 2
COPY --from=python-deps /python-runtime/ /

# Production environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:/usr/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv \
    LD_LIBRARY_PATH=/usr/lib64

WORKDIR /app

# Production venv from Stage 1
COPY --from=builder /app/.venv /app/.venv

# Application source (includes committed proto stubs with correct imports)
COPY ai_resume_api/ ./ai_resume_api/
COPY --from=builder /app/VERSION ./VERSION

# Scripts with executable bit set at COPY time
COPY --chmod=755 healthcheck /healthcheck
COPY --chmod=755 start.py /start.py

# Non-root: numeric UID (no shadow-utils in micro, UBI convention)
USER 1001

EXPOSE 3000

# Absolute path to venv python -- no shell, no PATH lookup
CMD ["/app/.venv/bin/python", "/start.py"]

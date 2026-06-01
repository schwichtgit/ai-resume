ARG BUILD_VERSION=dev
ARG BUILD_COMMIT=unknown

# --- Stage 1: Builder ---
# Rocky 10 minimal (microdnf) with compilers and uv for building the production venv
# rocky 10-minimal (10.1), libgcc-14-20250617, pinned 2026-05-31
FROM rockylinux/rockylinux:10-minimal@sha256:cfa2812ec7151c2be393cfe46e50cf59426373d12f03f4ffbdd56becb8195a65 AS builder

# Install Python 3.12 + build toolchain for native extensions
RUN microdnf install -y --nodocs \
        python3.12 python3.12-devel \
        gcc gcc-c++ \
    && microdnf clean all

# Grab the uv binary from the official image
# uv:latest resolved to 0.11.17, pinned 2026-05-31
COPY --from=ghcr.io/astral-sh/uv:0.11.17@sha256:03bdc89bb9798628846e60c3a9ad19006c8c3c724ccd2985a33145c039a0577b /uv /usr/local/bin/uv

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

# Pre-cache the HuggingFace embedding model in the builder stage.
# BAAI/bge-small-en-v1.5 is the model used by ingest.py for semantic search.
# Downloading at build time avoids network access at runtime.
ENV HF_HOME=/app/.hf
RUN /app/.venv/bin/python -c \
    "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

ARG BUILD_VERSION
ARG BUILD_COMMIT
RUN printf '{"version":"%s","commit":"%s"}\n' "${BUILD_VERSION}" "${BUILD_COMMIT}" > /app/VERSION

# --- Stage 2: Python runtime staging ---
# Rocky 10 minimal has microdnf to install Python + shared libraries, then we
# stage everything into /python-runtime/ for a single COPY into ubi-micro.
# rocky 10-minimal (10.1), libgcc-14-20250617, pinned 2026-05-31
FROM rockylinux/rockylinux:10-minimal@sha256:cfa2812ec7151c2be393cfe46e50cf59426373d12f03f4ffbdd56becb8195a65 AS python-deps

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
        libgomp \
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
         libgomp.so* \
       ; do \
         find /usr/lib64 -maxdepth 1 -name "$lib" -exec cp -a {} /python-runtime/usr/lib64/ \; 2>/dev/null; \
       done

# --- Stage 3: Runtime ---
# ubi-micro has no shell, no package manager -- only what we explicitly copy.
# ubi10/ubi-micro 10.2, libgcc-14-20251022, pinned 2026-05-31
FROM registry.access.redhat.com/ubi10/ubi-micro@sha256:e025b421d29b8ecd86fcfd8a4ad18c0d7de747cbcc4e372f414ba02390b031b6

# Python runtime from Stage 2
COPY --from=python-deps /python-runtime/ /

# Production environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:/usr/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv \
    LD_LIBRARY_PATH=/usr/lib64 \
    HF_HOME=/app/.hf

WORKDIR /app

# Production venv from Stage 1
COPY --from=builder /app/.venv /app/.venv

# Pre-cached HuggingFace model from Stage 1
COPY --from=builder /app/.hf /app/.hf

# Application source
COPY ingest.py ./ingest.py
COPY --from=builder /app/VERSION ./VERSION

# Non-root: numeric UID (no shadow-utils in micro, UBI convention)
USER 1001

# One-shot service: run ingest pipeline then exit
CMD ["/app/.venv/bin/python", "ingest.py"]

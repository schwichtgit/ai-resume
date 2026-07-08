ARG BUILD_VERSION=dev
ARG BUILD_COMMIT=unknown

# Multi-stage Dockerfile for Rust memvid service
# Supports amd64 and arm64 architectures

# Stage 1: Build the Rust binary
# rust 1.96.0-slim-trixie, pinned 2026-06-01
FROM rust:1.96.1-slim-trixie@sha256:31ee7fc65186be7e0e0ccb3f2ca305f14e4739e7642a1ae65753aa5d7b874523 AS builder

ARG TARGETARCH
ARG PROTOC_VERSION=28.3

WORKDIR /app

# Install protoc from GitHub releases (OS-independent, pinned version)
# Maps TARGETARCH (amd64/arm64) to protoc archive naming convention
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) PROTOC_ARCH="x86_64" ;; \
        arm64) PROTOC_ARCH="aarch_64" ;; \
        *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    apt-get update && apt-get install -y --no-install-recommends curl unzip \
    && curl -fsSL -o /tmp/protoc.zip \
        "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-${PROTOC_ARCH}.zip" \
    && unzip -o /tmp/protoc.zip -d /usr/local bin/protoc 'include/*' \
    && rm /tmp/protoc.zip \
    && apt-get purge -y curl unzip && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && protoc --version

# Copy Cargo files
COPY Cargo.toml Cargo.lock ./

ENV RUST_MIN_STACK=16777216

# Create dummy sources to cache dependencies (both lib.rs and main.rs
# are required because Cargo.toml declares [lib] + [[bin]] targets)
RUN set -eux; \
    uname -m && rustup show && \
    mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    echo "" > src/lib.rs && \
    cargo build -j $(nproc) --release && \
    rm -rf src

# Install cargo-auditable for Rust dependency SBOM embedding
RUN cargo install cargo-auditable

# Copy actual source code and build files
COPY src/ ./src/
COPY proto/ ./proto/
COPY build.rs ./

# Build for target architecture (auto-detected by --platform)
RUN cargo auditable build -j $(nproc) --release

ARG BUILD_VERSION
ARG BUILD_COMMIT
RUN printf '{"version":"%s","commit":"%s"}\n' "${BUILD_VERSION}" "${BUILD_COMMIT}" > /app/VERSION

# Stage 2: Distroless runtime (glibc 2.41, UID 65532 nonroot)
# distroless cc-debian13:nonroot, pinned 2026-05-31
FROM gcr.io/distroless/cc-debian13:nonroot@sha256:d3cda6e91129130d7229a1806b6a73d292ef245ab032da7851907798024cefba

# Copy binary from builder
COPY --from=builder /app/target/release/memvid-service /usr/local/bin/memvid-service
COPY --from=builder /app/VERSION /usr/local/bin/VERSION

# Expose gRPC port
EXPOSE 50051

# Expose Prometheus metrics port
EXPOSE 9090

USER nonroot

ENTRYPOINT ["/usr/local/bin/memvid-service"]

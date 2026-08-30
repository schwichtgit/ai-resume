ARG BUILD_VERSION=dev
ARG BUILD_COMMIT=unknown

# Multi-stage Dockerfile for Rust memvid service
# Supports amd64 and arm64 architectures
#
# The binary is linked statically against musl so the runtime stage can be
# distroless/static, which ships no libc, no OpenSSL and no zlib. Those three
# libraries were the entire CVE surface of this image: the service uses
# rustls + aws-lc-rs and never linked OpenSSL, yet inherited every advisory
# filed against it. See docs/SECURITY.md.

# Stage 1: Build the Rust binary
# rust 1.98.0-slim-trixie, pinned 2026-08-25. Keep this tag in step with
# rust-toolchain.toml: when they diverge, rustup downloads the pinned toolchain
# on every build and the image's bundled one is never used.
FROM rust:1.98.0-slim-trixie@sha256:17d1ba895198f9934c6314ec5346a0d5115372f3243390c3d731e242f35c2f27 AS builder

ARG TARGETARCH
ARG PROTOC_VERSION=28.3

WORKDIR /app

# Install protoc from GitHub releases (OS-independent, pinned version), plus the
# musl toolchain and cmake, which aws-lc-sys needs to compile its C sources.
# Maps TARGETARCH (amd64/arm64) to protoc archive naming convention.
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) PROTOC_ARCH="x86_64" ;; \
        arm64) PROTOC_ARCH="aarch_64" ;; \
        *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    apt-get update && apt-get install -y --no-install-recommends \
        curl unzip musl-tools musl-dev cmake perl make \
    && curl -fsSL -o /tmp/protoc.zip \
        "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-${PROTOC_ARCH}.zip" \
    && unzip -o /tmp/protoc.zip -d /usr/local bin/protoc 'include/*' \
    && rm /tmp/protoc.zip \
    && apt-get purge -y curl unzip && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && protoc --version

# Resolve the musl triple once so every later step agrees on it.
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) TRIPLE="x86_64-unknown-linux-musl" ;; \
        arm64) TRIPLE="aarch64-unknown-linux-musl" ;; \
        *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    echo "${TRIPLE}" > /rust-triple

# Copy Cargo files. rust-toolchain.toml must land before any cargo or rustup
# call: otherwise rustup resolves the image's default toolchain and installs the
# musl target against the wrong one, and the build fails later with a confusing
# "can't find crate for `core`".
COPY Cargo.toml Cargo.lock rust-toolchain.toml ./

ENV RUST_MIN_STACK=16777216
ENV CC_x86_64_unknown_linux_musl=musl-gcc \
    CC_aarch64_unknown_linux_musl=musl-gcc \
    CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER=musl-gcc \
    CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER=musl-gcc

RUN set -eux; rustup target add "$(cat /rust-triple)"

# Create dummy sources to cache dependencies (both lib.rs and main.rs
# are required because Cargo.toml declares [lib] + [[bin]] targets)
RUN set -eux; \
    uname -m && rustup show && \
    mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    echo "" > src/lib.rs && \
    cargo build -j $(nproc) --release --target "$(cat /rust-triple)" && \
    rm -rf src

# Install cargo-auditable for Rust dependency SBOM embedding
RUN cargo install cargo-auditable

# Copy actual source code and build files
COPY src/ ./src/
COPY proto/ ./proto/
COPY build.rs ./

# Build for target architecture (auto-detected by --platform), then lift the
# binary out of the triple-specific path so the runtime stage stays arch-neutral.
RUN set -eux; \
    TRIPLE="$(cat /rust-triple)"; \
    cargo auditable build -j $(nproc) --release --target "${TRIPLE}"; \
    cp "target/${TRIPLE}/release/memvid-service" /memvid-service

ARG BUILD_VERSION
ARG BUILD_COMMIT
RUN printf '{"version":"%s","commit":"%s"}\n' "${BUILD_VERSION}" "${BUILD_COMMIT}" > /app/VERSION

# Stage 2: Distroless static runtime (no libc, no OpenSSL, no zlib; UID 65532)
# distroless static-debian13:nonroot, pinned 2026-08-25
FROM gcr.io/distroless/static-debian13:nonroot@sha256:1c2c046bc09ed40fad370b599a0b1ae7987f55b01e247cf27a7c27cd97e5bbc7

# Copy binary from builder
COPY --from=builder /memvid-service /usr/local/bin/memvid-service
COPY --from=builder /app/VERSION /usr/local/bin/VERSION

# Expose gRPC port
EXPOSE 50051

# Expose Prometheus metrics port
EXPOSE 9090

USER nonroot

ENTRYPOINT ["/usr/local/bin/memvid-service"]

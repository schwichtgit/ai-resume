# Multi-stage Dockerfile for Rust memvid service
# Supports amd64 and arm64 architectures

# Stage 1: Build the Rust binary
FROM rust:1.92.0-slim AS builder

ARG TARGETARCH

WORKDIR /app

# Install protobuf compiler and dev libs (Debian equivalents)
RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler=3.21.12-11 \
    libprotobuf-dev=3.21.12-11 \
    && rm -rf /var/lib/apt/lists/*

# Copy Cargo files
COPY Cargo.toml Cargo.lock ./

ENV RUST_MIN_STACK=16777216

# Create dummy sources to cache dependencies (both lib.rs and main.rs
# are required because Cargo.toml declares [lib] + [[bin]] targets)
RUN uname -m && rustup show && \
    mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    echo "" > src/lib.rs && \
    cargo build -j $(nproc) --release && \
    rm -rf src

# Copy actual source code and build files
COPY src/ ./src/
COPY proto/ ./proto/
COPY build.rs ./

# Build for target architecture (auto-detected by --platform)
RUN cargo build -j $(nproc) --release

# Stage 2: Runtime image (debian-slim for glibc compatibility)
FROM debian:trixie-slim

# Install ca-certificates for TLS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 1000 -s /bin/false memvid

# Copy binary from builder
COPY --from=builder /app/target/release/memvid-service /usr/local/bin/memvid-service

# Create symlink for healthcheck at root level
WORKDIR /
RUN ln -s /usr/local/bin/memvid-service healthcheck

# Expose gRPC port
EXPOSE 50051

# Expose Prometheus metrics port
EXPOSE 9090

# Run as non-root user
USER memvid

ENTRYPOINT ["/usr/local/bin/memvid-service"]

# Rust Memvid Service

Lightweight Rust service that loads the `.mv2` memvid file and exposes a gRPC API for fast semantic search.

## Architecture

This service is part of the Hybrid Rust + Python architecture:
- **Rust** handles performance-critical memvid operations (<5ms retrieval)
- **Python** handles API orchestration, OpenRouter calls, session management

## Status

**Phase 2a Complete:**
- [x] gRPC server skeleton with Tonic
- [x] Proto definition (`proto/memvid/v1/memvid.proto`)
- [x] Mock searcher for testing (returns sample resume data)
- [x] Health check endpoint
- [x] Prometheus metrics endpoint (:9090)
- [x] Structured JSON logging with tracing
- [x] Environment-based configuration
- [x] Unit tests (88.77% coverage)

**Remaining:**
- [ ] Integrate actual memvid-core Rust crate (when published)
- [ ] Load real `.mv2` file at startup
- [ ] Container build verification

## API

### gRPC Service (port 50051)

**Proto Definition:** `proto/memvid/v1/memvid.proto`

```protobuf
service MemvidService {
  rpc Search(SearchRequest) returns (SearchResponse);
}

service Health {
  rpc Check(HealthCheckRequest) returns (HealthCheckResponse);
}

message SearchRequest {
  string query = 1;
  int32 top_k = 2;        // Default: 5, Max: 20
  int32 snippet_chars = 3; // Default: 200, Max: 1000
}

message SearchResponse {
  repeated SearchHit hits = 1;
  int32 total_hits = 2;
  int32 took_ms = 3;
}

message SearchHit {
  string title = 1;
  float score = 2;
  string snippet = 3;
  repeated string tags = 4;
}
```

### HTTP Endpoints

| Endpoint | Port | Description |
|----------|------|-------------|
| `/metrics` | 9090 | Prometheus metrics |

## Building

**Native build:**
```bash
cargo build --release
./target/release/memvid-service
```

**Run tests:**
```bash
cargo test
```

**Check coverage:**
```bash
cargo llvm-cov --summary-only
```

**Multi-arch container build:**
```bash
cd ..
./scripts/build-all.sh
```

## Running

**Mock mode (for testing without .mv2 file):**
```bash
MOCK_MODE=true \
GRPC_PORT=50051 \
RUST_LOG=info \
cargo run
```

**Production mode:**
```bash
MEMVID_FILE_PATH=/data/memvid/resume.mv2 \
GRPC_PORT=50051 \
METRICS_PORT=9090 \
RUST_LOG=info \
./target/release/memvid-service
```

**With Docker/Podman:**
```bash
podman run -d \
  -p 50051:50051 \
  -p 9090:9090 \
  -v /path/to/memvid:/data/memvid:ro \
  -e MEMVID_FILE_PATH=/data/memvid/resume.mv2 \
  localhost/ai-resume-memvid:latest
```

## Testing with grpcurl

**Health check:**
```bash
grpcurl -plaintext localhost:50051 memvid.v1.Health/Check
```

**Search query:**
```bash
grpcurl -plaintext -d '{"query":"Python experience","top_k":3}' \
  localhost:50051 memvid.v1.MemvidService/Search
```

## Development

**Run with hot reload:**
```bash
cargo install cargo-watch
cargo watch -x run
```

**Check code:**
```bash
cargo clippy -- -D warnings
cargo fmt --check
```

**Run specific test:**
```bash
cargo test test_search_with_defaults
```

## Configuration

All configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMVID_FILE_PATH` | `data/.memvid/resume.mv2` | Path to .mv2 file |
| `GRPC_PORT` | `50051` | gRPC server port |
| `METRICS_PORT` | `9090` | Prometheus metrics port |
| `MOCK_MODE` | `false` | Use mock searcher (no .mv2 required) |
| `RUST_LOG` | `info` | Log level (trace, debug, info, warn, error) |

## Observability

### Metrics

Prometheus metrics exposed at `http://localhost:9090/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `memvid_search_latency_ms` | Histogram | Search operation latency |
| `memvid_search_total` | Counter | Total search requests |
| `memvid_search_errors_total` | Counter | Total search errors |

### Logging

Structured JSON logs via `tracing` crate:

```bash
# Debug logging for this service
RUST_LOG=ai_resume_memvid=debug cargo run

# Trace all HTTP activity
RUST_LOG=ai_resume_memvid=debug,tower_http=trace cargo run
```

## Project Structure

```
memvid-service/
├── Cargo.toml           # Dependencies
├── Cargo.lock           # Lock file
├── Dockerfile           # Multi-arch container build
├── build.rs             # Proto compilation
├── proto/
│   └── memvid/v1/
│       └── memvid.proto # gRPC service definition
└── src/
    ├── main.rs          # Entry point
    ├── config.rs        # Environment configuration
    ├── error.rs         # Error types
    ├── metrics.rs       # Prometheus metrics
    ├── generated/
    │   └── mod.rs       # Proto-generated code
    ├── grpc/
    │   ├── mod.rs
    │   └── service.rs   # gRPC service implementations
    └── memvid/
        ├── mod.rs
        ├── searcher.rs  # Searcher trait
        └── mock.rs      # Mock implementation
```

## Test Coverage

Current coverage: **88.77%** (23 tests)

| File | Coverage |
|------|----------|
| error.rs | 100.00% |
| grpc/service.rs | 99.03% |
| memvid/mock.rs | 96.67% |
| metrics.rs | 96.67% |
| config.rs | 91.11% |
| main.rs | 0% (entry point) |

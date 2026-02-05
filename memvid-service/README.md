# Rust Memvid Service

Lightweight Rust service that loads `.mv2` memvid files and exposes a gRPC API for fast semantic search (<5ms retrieval).

## Architecture

This service is part of the Hybrid Rust + Python architecture:
- **Rust** handles performance-critical memvid operations with memvid-core SDK
- **Python** handles API orchestration, OpenRouter calls, session management

## Memvid-Core Integration

This service uses **memvid-core v2.0.135** for production retrieval:

- **Hybrid Search:** Combines BM25 (lexical) + vector (semantic) search with Reciprocal Rank Fusion
- **Cross-Encoder Re-ranking:** Optional re-ranking for improved relevance
- **Multiple Search Modes:** Hybrid (default), Semantic-only, Lexical-only
- **O(1) State Retrieval:** Direct entity lookup for profile metadata (no search truncation)
- **Temporal Filtering:** Time-range queries and time-travel via `as_of_frame`/`as_of_ts`

## API

### gRPC Service (port 50051)

See full proto definition: [`proto/memvid/v1/memvid.proto`](proto/memvid/v1/memvid.proto)

**Key RPCs:**
- `Search(SearchRequest) → SearchResponse` - Semantic/hybrid/lexical search
- `Ask(AskRequest) → AskResponse` - Q&A with intelligent retrieval
- `GetState(GetStateRequest) → GetStateResponse` - O(1) entity lookup
- `Health/Check` - Service health status

**Search Modes (AskMode enum):**
- `ASK_MODE_HYBRID` - BM25 + vector search with RRF (default, best for most queries)
- `ASK_MODE_SEM` - Semantic-only (best for conceptual queries)
- `ASK_MODE_LEX` - Lexical-only (best for exact keywords, acronyms, proper nouns)

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

**Multi-arch container build:**
```bash
cd ..
./scripts/build-all.sh
```

## Running

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

**Mock mode (for testing without .mv2 file):**
```bash
MOCK_MODE=true RUST_LOG=info cargo run
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

**Hybrid search with mode:**
```bash
grpcurl -plaintext -d '{"query":"ML expertise","top_k":5,"mode":"ASK_MODE_HYBRID"}' \
  localhost:50051 memvid.v1.MemvidService/Search
```

**Ask with filters:**
```bash
grpcurl -plaintext -d '{"question":"What is your backend experience?","use_llm":false,"top_k":3}' \
  localhost:50051 memvid.v1.MemvidService/Ask
```

**GetState lookup:**
```bash
grpcurl -plaintext -d '{"entity":"__profile__"}' \
  localhost:50051 memvid.v1.MemvidService/GetState
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
├── Cargo.toml           # Dependencies (memvid-core v2.0.135)
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
        ├── searcher.rs  # Searcher trait + real implementation
        └── mock.rs      # Mock implementation for testing
```

# Python FastAPI Service

FastAPI-based orchestration service that handles:

- HTTP API endpoints (`/api/v1/chat`, `/health`, `/metrics`)
- OpenRouter LLM integration for streaming responses
- Session management (in-memory, TTL-based)
- Rate limiting
- gRPC communication with Rust memvid service

## Architecture

This service is part of the Hybrid Rust + Python architecture:

- **Rust** handles performance-critical memvid operations (gRPC on :50051)
- **Python** handles API orchestration, OpenRouter calls, session management

## API Endpoints

### POST /api/v1/chat

Stream chat response with memvid context.

**Request:**

```json
{
  "message": "What experience do they have with cloud infrastructure?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream": true
}
```

**Response:** Server-Sent Events (SSE)

```text
data: {"type":"retrieval","chunks":3}
data: {"type":"token","content":"They"}
...
data: {"type":"done"}
```

### GET /api/v1/health

```json
{ "status": "healthy", "memvid_connected": true }
```

### GET /metrics

Prometheus metrics exposition

## Setup with UV

**Prerequisites:**

```bash
# Install uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

**Install dependencies:**

```bash
# UV automatically creates and manages .venv
uv sync
```

**Run development server:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export OPENROUTER_API_KEY="sk-or-v1-..."
export MEMVID_GRPC_URL="localhost:50051"
export LLM_MODEL="nvidia/nemotron-nano-9b-v2:free"

# Run with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 3000

# Or run directly with uv:
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
```

## Configuration

All configuration via environment variables:

| Variable                | Default                              | Description                       |
| ----------------------- | ------------------------------------ | --------------------------------- |
| `OPENROUTER_API_KEY`    | Required                             | OpenRouter API key                |
| `MEMVID_GRPC_URL`       | `localhost:50051`                    | Rust memvid service gRPC endpoint |
| `LLM_MODEL`             | `nvidia/nemotron-nano-9b-v2:free`    | OpenRouter model ID               |
| `SESSION_TTL`           | `1800`                               | Session TTL in seconds (30 min)   |
| `RATE_LIMIT_PER_MINUTE` | `10`                                 | Rate limit per IP                 |
| `PORT`                  | `3000`                               | HTTP server port                  |
| `LOG_LEVEL`             | `INFO`                               | Logging level                     |

## Testing

**Run tests with UV:**

```bash
uv run pytest
```

**Run with coverage:**

```bash
uv run pytest --cov=app --cov-report=html
```

**Type checking:**

```bash
uv run mypy app/
```

**Code formatting:**

```bash
uv run black app/
uv run isort app/
# or: uv run ruff format app/
```

**Linting:**

```bash
uv run ruff check app/
```

## Container Build

**Multi-arch build:**

```bash
cd ..
./scripts/build-all.sh
```

**Run locally:**

```bash
podman run -d \
  -p 3000:3000 \
  -e OPENROUTER_API_KEY="sk-or-v1-..." \
  -e MEMVID_GRPC_URL="memvid-service:50051" \
  localhost/ai-resume-api:latest
```

## Development

**Hot reload:**

```bash
uvicorn app.main:app --reload
```

## Project Structure

```text
api-service/
├── ai_resume_api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entrypoint
│   ├── config.py            # Environment configuration
│   ├── models.py            # Pydantic request/response models
│   ├── memvid_client.py     # gRPC client for Rust service
│   ├── openrouter_client.py # OpenRouter LLM client
│   ├── session_store.py     # In-memory session management
│   └── rate_limiter.py      # Per-IP rate limiting
├── proto/
│   └── memvid/v1/memvid.proto  # gRPC service definition (shared with Rust)
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── test_config.py          # Config tests
│   ├── test_main.py            # API endpoint tests
│   ├── test_memvid_client.py   # gRPC client tests
│   ├── test_models.py          # Pydantic model tests
│   ├── test_openrouter_client.py  # OpenRouter client tests
│   └── test_session_store.py   # Session store tests
├── pyproject.toml              # UV/pip dependencies
├── Dockerfile
└── README.md
```

## Implementation Status

✅ **Complete** - All features implemented with 80% test coverage (102 tests)

- [x] FastAPI app with CORS and middleware
- [x] gRPC client for Rust memvid service (with mock fallback)
- [x] OpenRouter streaming client (SSE responses)
- [x] Session management with TTL (cachetools)
- [x] Rate limiting middleware (slowapi)
- [x] Structured logging (structlog)
- [x] Prometheus metrics endpoint
- [x] Health check with memvid status
- [x] Suggested questions endpoint
- [x] OpenAPI documentation (auto-generated at /docs)

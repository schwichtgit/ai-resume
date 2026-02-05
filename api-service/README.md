# AI Resume API Service

FastAPI-based backend service providing:

- AI-powered chat with RAG (Retrieval-Augmented Generation)
- Role classification and fit assessment
- Profile and experience data endpoints
- Session management and rate limiting
- gRPC integration with memvid vector database

## Architecture

This service is part of a hybrid Rust + Python architecture:

- **Rust memvid service** - Vector search, profile storage (gRPC on :50051)
- **Python API service** - HTTP API, LLM orchestration, business logic

## API Endpoints

### POST /api/v1/chat

Stream AI chat responses with semantic search context.

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
data: {"type":"token","content":"Extensive"}
...
data: {"type":"done"}
```

### POST /api/v1/assess-fit

Analyze job description fit with AI assessment.

**Request:**

```json
{
  "job_description": "Looking for senior Python engineer...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**

```json
{
  "verdict": "STRONG_FIT",
  "key_matches": ["Python", "FastAPI", "Docker"],
  "gaps": ["Kubernetes experience"],
  "recommendation": "Excellent match for core requirements..."
}
```

### GET /api/v1/profile

Load complete profile (name, title, experience, skills).

### GET /api/v1/suggested-questions

Retrieve suggested questions for chat interface.

### GET /api/v1/health

Service health check with memvid connection status.

## Setup

**Prerequisites:**

```bash
# Install uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

**Install dependencies:**

```bash
uv sync
```

**Run development server:**

```bash
# Set environment variables
export OPENROUTER_API_KEY="sk-or-v1-..."
export MEMVID_GRPC_URL="localhost:50051"
export LLM_MODEL="nvidia/nemotron-nano-9b-v2:free"

# Run with hot reload
uv run uvicorn ai_resume_api.main:app --reload --host 0.0.0.0 --port 3000
```

## Configuration

Environment variables:

| Variable                | Default                           | Description                     |
| ----------------------- | --------------------------------- | ------------------------------- |
| `OPENROUTER_API_KEY`    | Required                          | OpenRouter API key              |
| `MEMVID_GRPC_URL`       | `localhost:50051`                 | memvid service gRPC endpoint    |
| `LLM_MODEL`             | `nvidia/nemotron-nano-9b-v2:free` | OpenRouter model ID             |
| `SESSION_TTL`           | `1800`                            | Session TTL in seconds (30 min) |
| `RATE_LIMIT_PER_MINUTE` | `10`                              | Rate limit per IP address       |
| `PORT`                  | `3000`                            | HTTP server port                |
| `LOG_LEVEL`             | `INFO`                            | Logging level (DEBUG/INFO/WARN) |
| `MOCK_MEMVID_CLIENT`    | `false`                           | Use mock client for testing     |

## Testing

**Test suite:** 253 tests, 88% coverage

**Run tests:**

```bash
uv run pytest
```

**Run with coverage:**

```bash
uv run pytest --cov=ai_resume_api --cov-report=html
open htmlcov/index.html
```

**Run specific test:**

```bash
uv run pytest tests/test_main.py -v
uv run pytest tests/test_main.py::TestChatEndpoint::test_valid_message -v
```

See [docs/TEST_COVERAGE.md](../docs/TEST_COVERAGE.md) for detailed coverage report.

**Type checking:**

```bash
uv run mypy ai_resume_api/
```

**Code formatting:**

```bash
uv run ruff format ai_resume_api/
```

**Linting:**

```bash
uv run ruff check ai_resume_api/
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
uv run uvicorn ai_resume_api.main:app --reload
```

**View API docs:**

- Swagger UI: <http://localhost:3000/docs>
- ReDoc: <http://localhost:3000/redoc>

## Project Structure

```text
api-service/
├── ai_resume_api/
│   ├── main.py                # FastAPI app and endpoints
│   ├── config.py              # Environment configuration
│   ├── models.py              # Pydantic request/response models
│   ├── memvid_client.py       # gRPC client for memvid service
│   ├── openrouter_client.py   # OpenRouter LLM client
│   ├── role_classifier.py     # Multi-domain role classification
│   ├── query_transform.py     # Query rewriting strategies
│   ├── guardrails.py          # Input validation and safety
│   ├── session_store.py       # Session management (TTL-based)
│   └── observability.py       # Logging and metrics
├── tests/
│   ├── conftest.py                  # Pytest fixtures and config
│   ├── test_main.py                 # API endpoint tests
│   ├── test_memvid_client.py        # gRPC client tests (REST mode)
│   ├── test_memvid_client_grpc.py   # gRPC client tests (native mode)
│   ├── test_openrouter_client.py    # OpenRouter client tests
│   ├── test_role_classifier_e2e.py  # Role classification tests
│   ├── test_query_transform.py      # Query transformation tests
│   ├── test_guardrails.py           # Input validation tests
│   ├── test_integration.py          # End-to-end integration tests
│   └── ...                          # Additional test modules
├── pyproject.toml              # UV/pip dependencies and config
├── Dockerfile                  # Multi-stage container build
└── README.md
```

## Features

- FastAPI app with CORS and middleware
- gRPC client for memvid service (with REST fallback)
- OpenRouter streaming LLM integration (SSE)
- Multi-domain role classification (9 domains)
- Fit assessment with structured verdicts
- Session management with TTL (in-memory)
- Rate limiting per IP address
- Structured logging (JSON format)
- Input validation and guardrails
- OpenAPI documentation (/docs, /redoc)

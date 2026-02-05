# AI Resume API Service

FastAPI-based backend service providing:

- AI-powered chat with RAG (Retrieval-Augmented Generation)
- Role classification and fit assessment
- Profile and experience data endpoints
- Session management and rate limiting
- gRPC integration with memvid vector database

This service is part of a hybrid Rust + Python architecture:

- **Rust memvid service** - Vector search, profile storage (gRPC on :50051)
- **Python API service** - HTTP API, LLM orchestration, business logic

## Quick Start

**Prerequisites:**

```bash
# Install uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Install and run:**

```bash
# Install dependencies (creates .venv automatically)
uv sync

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export OPENROUTER_API_KEY="sk-or-v1-..."
export MEMVID_GRPC_URL="localhost:50051"
export LLM_MODEL="nvidia/nemotron-nano-9b-v2:free"

# Run with hot reload
uvicorn ai_resume_api.main:app --reload --host 0.0.0.0 --port 3000
```

Visit <http://localhost:3000/docs> for interactive API documentation.

## API Endpoints

### POST /api/v1/chat

Stream AI chat responses with semantic search context.

**Request:**

```json
{
  "message": "What cloud infrastructure experience do they have?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream": true
}
```

**Response:** Server-Sent Events (SSE)

```text
data: {"type":"retrieval","chunks":3}
data: {"type":"token","content":"Extensive"}
...
event: stats
data: {"chunks_retrieved":3,"tokens_used":42,"elapsed_seconds":1.2}
event: end
data: [DONE]
```

### GET /api/v1/suggested-questions

Get AI-generated suggested questions for the chat interface.

**Response:**

```json
{
  "questions": [
    {
      "question": "What cloud infrastructure experience do they have?",
      "category": "general"
    },
    {
      "question": "Tell me about their leadership philosophy",
      "category": "general"
    }
  ]
}
```

### GET /api/v1/profile

Get profile metadata (name, title, experience, skills, fit examples).

**Response:**

```json
{
  "name": "Frank Schwichtenberg",
  "title": "Senior Engineering Leader",
  "experience": [...],
  "skills": {...},
  "fit_assessment_examples": [...]
}
```

### POST /api/v1/assess-fit

AI-powered job fit assessment with role classification.

**Request:**

```json
{
  "job_description": "Senior ML Engineer..."
}
```

**Response:**

```json
{
  "verdict": "⭐⭐⭐⭐ Strong fit",
  "key_matches": ["10+ years ML experience", "Led distributed teams"],
  "gaps": ["Limited computer vision experience"],
  "recommendation": "Strong candidate with transferable leadership...",
  "chunks_retrieved": 8,
  "tokens_used": 512
}
```

**Features:**

- Multi-domain role classifier (Technology, Healthcare, Legal, Finance, Culinary, Other)
- Dynamic LLM persona selection based on role domain and seniority
- Cross-domain mismatch detection

### GET /api/v1/health

Service health check with memvid connection status.

**Response:**

Prometheus metrics exposition.

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
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=ai_resume_api --cov-report=html
open htmlcov/index.html

# Run specific test
uv run pytest tests/test_main.py -v
uv run pytest tests/test_main.py::TestChatEndpoint::test_valid_message -v

# Type checking
uv run mypy ai_resume_api/

# Formatting
uv run ruff format ai_resume_api/

# Linting
uv run ruff check ai_resume_api/
```

See [docs/TEST_COVERAGE.md](../docs/TEST_COVERAGE.md) for detailed coverage report.

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

## Container Build

**Build multi-arch image:**

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

## Architecture Notes

This service is part of a hybrid Rust + Python architecture:

- **Rust (memvid-service)**: Performance-critical vector search, BM25 retrieval, re-ranking
- **Python (api-service)**: API orchestration, LLM calls, session management

Communication: Python gRPC client → Rust gRPC server (port 50051)

Data flow:

1. Client sends chat message → `/api/v1/chat`
2. Python calls memvid gRPC `Ask()` for semantic search context
3. Python sends context + message to OpenRouter LLM
4. Streaming response returned to client via SSE

## Development Tips

**Hot reload:**

```bash
uv run uvicorn ai_resume_api.main:app --reload
```

**View API docs:**

- Swagger UI: <http://localhost:3000/docs>
- ReDoc: <http://localhost:3000/redoc>

**Run without OpenRouter (mock responses):**

```bash
# Don't set OPENROUTER_API_KEY
# API will return mock responses using context from memvid
```

**Test against local memvid:**

```bash
# In memvid-service directory:
cargo run --release -- serve --port 50051 --mv2 ../data/.memvid/resume.mv2

# In api-service directory:
export MEMVID_GRPC_URL="localhost:50051"
uvicorn ai_resume_api.main:app --reload
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

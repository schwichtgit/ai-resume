# API Service Test Coverage

**Last Updated:** February 5, 2026
**Status:** 253 tests passing, 88% overall coverage

---

## Overview

Comprehensive test suite for the FastAPI backend covering API endpoints, LLM integration, gRPC client, role classification, and business logic. Tests execute in ~5 seconds using pytest with async support.

---

## Test Files

| Test File                     | Focus Area                                   | Coverage |
| ----------------------------- | -------------------------------------------- | -------- |
| `test_config.py`              | Configuration, settings, profile loading     | 99%      |
| `test_guardrails.py`          | Input validation, content safety             | 100%     |
| `test_integration.py`         | End-to-end RAG flows                         | 46%\*    |
| `test_main.py`                | FastAPI endpoints, streaming, error handling | 99%      |
| `test_memvid_client.py`       | gRPC client (REST fallback mode)             | 100%     |
| `test_memvid_client_grpc.py`  | gRPC client (native mode)                    | 99%      |
| `test_models.py`              | Pydantic models, validation                  | 100%     |
| `test_openrouter_client.py`   | OpenRouter LLM API integration               | 99%      |
| `test_query_transform.py`     | Query rewriting strategies                   | 100%     |
| `test_role_classifier_e2e.py` | Multi-domain role classification             | 96%      |
| `test_session_store.py`       | Session management, TTL                      | 100%     |

\* Integration tests use real external services, lower coverage expected

---

## Module Coverage

| Module                 | Coverage | Notable Gaps                     |
| ---------------------- | -------- | -------------------------------- |
| `config.py`            | 99%      | Profile loading edge case        |
| `guardrails.py`        | 100%     | -                                |
| `main.py`              | 90%      | Startup/shutdown, error handlers |
| `memvid_client.py`     | 94%      | Connection error paths           |
| `models.py`            | 100%     | -                                |
| `observability.py`     | 100%     | -                                |
| `openrouter_client.py` | 96%      | Rate limit handling              |
| `query_transform.py`   | 100%     | -                                |
| `role_classifier.py`   | 96%      | Regex edge cases                 |
| `session_store.py`     | 100%     | -                                |

---

## Test Strategies

### Async Testing

```python
@pytest.mark.asyncio
async def test_chat_endpoint():
    async with httpx.AsyncClient(app=app) as client:
        response = await client.post("/api/v1/chat", json=payload)
```

### Mocking

**Environment Variables:**

- `MOCK_MEMVID_CLIENT=true` - Enables mock mode
- `RATE_LIMIT_PER_MINUTE=1000` - High limits for testing

**Fixtures in `conftest.py`:**

- `reset_caches` - Clears settings/sessions between tests
- `mock_settings` - Injects test environment variables

**Strategy:**

- Unit tests: Mock external services (OpenRouter, memvid)
- Integration tests: Use real services when available

### Common Patterns

**FastAPI Client:**

```python
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.get("/api/v1/profile")
```

**Streaming Responses:**

```python
with client.stream("POST", "/api/v1/chat", json=data) as response:
    for line in response.iter_lines():
        assert line.startswith("data: ")
```

**Parametrized Tests:**

```python
@pytest.mark.parametrize("query,expected", [
    ("python", ["python"]),
    ("senior engineer", ["senior", "engineer"]),
])
def test_extraction(query, expected):
    assert extract(query) == expected
```

---

## Running Tests

### Commands

```bash
# Run all tests
pytest

# With coverage
pytest --cov=ai_resume_api --cov-report=term-missing

# Specific test file
pytest tests/test_main.py -v

# Specific test class
pytest tests/test_main.py::TestChatEndpoint -v

# Specific test
pytest tests/test_main.py::TestChatEndpoint::test_valid_message -v

# HTML coverage report
pytest --cov=ai_resume_api --cov-report=html
open htmlcov/index.html
```

---

## Adding New Tests

### Structure

```python
class TestFeatureName:
    """Test suite for feature description."""

    def test_scenario_description(self):
        """Test specific scenario."""
        # Arrange - Set up test data
        data = {...}

        # Act - Execute code under test
        result = function(data)

        # Assert - Verify expectations
        assert result.status == "success"
```

### File Organization

1. Create `tests/test_<module>.py`
2. Import: `from ai_resume_api import <module>`
3. Name classes: `class Test<Feature>:`
4. Name functions: `def test_<scenario>():`

### Fixtures

```python
@pytest.fixture
def sample_request():
    """Provide test request data."""
    return ChatRequest(
        message="Test question",
        session_id="test-123"
    )
```

---

## Coverage Goals

### Philosophy

Focus on critical paths and business logic over 100% coverage.

**Priorities:**

1. API endpoints (request/response validation)
2. Business logic (role classification, fit assessment)
3. External integrations (LLM, gRPC)
4. Error handling (graceful degradation)

**Lower Priority:**

- Logging statements
- Type annotations
- Trivial getters/setters
- Startup/shutdown code

### Targets

- **Critical modules:** 90%+ (main.py, memvid_client.py)
- **Business logic:** 95%+ (role_classifier.py, query_transform.py)
- **Models:** 100% (models.py)
- **Overall:** 85%+

**Current:** 88% (exceeding target)

---

## Configuration

**pyproject.toml:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=ai_resume_api --cov-report=term-missing"
```

**Test Environment (conftest.py):**

```python
os.environ.setdefault("MOCK_MEMVID_CLIENT", "true")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")
```

---

## Best Practices

1. **Isolation** - Tests run independently, no shared state
2. **Clarity** - Names describe what's being tested
3. **AAA Pattern** - Arrange, Act, Assert structure
4. **Mock External Services** - No real API calls in unit tests
5. **Test Error Paths** - Cover failures, not just happy path
6. **Fast Execution** - Unit tests under 1 second each
7. **Meaningful Assertions** - Verify behavior, not implementation

---

## Known Limitations

**Integration Tests:**

- Lower coverage (46%) due to external service dependency
- Some paths only testable with real memvid instance
- Network errors difficult to simulate

**Startup/Shutdown:**

- Application lifecycle events not fully tested
- Lifespan context managers skipped in TestClient

**Rate Limiting:**

- Concurrent request scenarios not fully covered
- Production rate limit edge cases not tested

---

## Ingest Module Test Coverage

**Last Updated:** February 5, 2026
**Status:** 71 tests passing, 87% overall coverage

---

### Overview

Comprehensive test suite for the data ingestion pipeline that creates `.mv2` vector database files from resume markdown. Tests execute in ~69 seconds using pytest with async support (anyio).

**Test Organization:** All tests located in `tests/` subdirectory following Python packaging best practices.

---

### Test Files

| Test File                         | Focus Area                              | Tests | Coverage |
| --------------------------------- | --------------------------------------- | ----- | -------- |
| `test_parsing.py`                 | Core parsing functions (YAML, markdown) | 40    | 100%     |
| `test_ingest_edge_cases.py`       | Integration and edge cases              | 21    | 99%      |
| `test_e2e.py`                     | End-to-end RAG pipeline                 | 3     | 66%\*    |
| `test_compare_models.py`          | Embedding model comparison              | 3     | 100%     |
| `test_ingest_retrieval.py`        | Profile/experience retrieval            | 3     | 68%\*    |
| `test_memvid_lex_diagnostics.py`  | Index diagnostics                       | 1     | 92%      |
| `test_memvid.py`                  | Memvid SDK operations                   | 3     | 86%      |
| `test_embeddings.py`              | Semantic similarity validation          | 1     | 93%      |

\* E2E and retrieval tests use real external services, lower coverage expected

---

### Module Coverage

| Module             | Coverage | Notable Gaps                      |
| ------------------ | -------- | --------------------------------- |
| `ingest.py`        | 91%      | Verbose output, error edge cases  |
| `compare_models.py`| 51%      | CLI argparse boilerplate          |

**Uncovered code:** Primarily verbose/debug print statements and defensive error handling that represent acceptable gaps.

---

### Test Strategies

#### Unit Tests (test_parsing.py)

Pure unit tests for parsing functions with 100% coverage:

```python
def test_parse_frontmatter_basic():
    """Test YAML frontmatter parsing."""
    content = """---
name: John Doe
title: Engineer
---
Resume content here."""

    frontmatter, body = parse_frontmatter(content)
    assert frontmatter["name"] == "John Doe"
```

**Coverage:**
- Frontmatter parsing (6 tests)
- Section extraction (5 tests)
- Experience parsing (6 tests)
- Skills parsing (4 tests)
- FAQ parsing (4 tests)
- Fit assessment parsing (5 tests)
- Utility functions (3 tests)

#### Integration Tests (test_ingest_edge_cases.py)

Tests full ingestion pipeline with temporary `.mv2` files:

```python
def test_ingest_with_failures_section():
    """Test ingestion of failure stories section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.md"
        output_path = Path(tmpdir) / "test.mv2"

        ingest_memory(input_path, output_path, verbose=False)

        mem = memvid_sdk.use("basic", str(output_path))
        result = mem.find("failure lessons", k=5)
        # Verify frames created correctly
```

**Coverage:**
- Profile building (4 tests)
- Ingest memory operations (5 tests)
- Verification (3 tests)
- Error handling (3 tests)

#### E2E Tests (test_e2e.py)

Full RAG pipeline validation with real LLM integration:

```python
@pytest.mark.anyio
async def test_query_transformation_improves_retrieval():
    """Verify LLM query enhancement improves retrieval."""
    # Test semantic search with query rewriting
```

#### Slow Tests (test_compare_models.py)

Model download tests marked with `@pytest.mark.slow`:

```python
@pytest.mark.slow
def test_test_model_returns_results(monkeypatch, capsys):
    """Test embedding model comparison (~130MB download)."""
    # Uses pytest fixtures for clean mocking
```

---

### Running Tests

#### Commands

```bash
# Run all tests
cd ingest
source .venv/bin/activate
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Fast tests only (skip slow model downloads)
pytest tests/ -m "not slow"

# Slow tests only
pytest tests/ -m slow

# Specific test file
pytest tests/test_parsing.py -v

# Specific test
pytest tests/test_parsing.py::test_parse_frontmatter_basic -v
```

#### Test Markers

```python
@pytest.mark.slow      # Model downloads, skip with -m "not slow"
@pytest.mark.anyio     # Async tests (automatic with pytest-anyio)
```

---

### Coverage Goals

**Philosophy:** Focus on critical parsing logic and data flow over 100% coverage.

**Priorities:**
1. Parsing functions (YAML, markdown, chunking)
2. Ingestion pipeline (frame creation, tagging)
3. Verification (semantic quality checks)
4. Error handling (malformed input, missing files)

**Lower Priority:**
- Verbose/debug output (logging)
- CLI boilerplate (argparse wiring)
- One-off utility scripts (compare_models.py main)

**Targets:**
- **Critical modules:** 90%+ (ingest.py)
- **Parsing functions:** 100% (test_parsing.py)
- **Overall:** 85%+

**Current:** 87% (exceeding target)

---

### Configuration

**pyproject.toml:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
python_classes = ["Test*"]
addopts = ["-v", "--strict-markers", "--tb=short"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "anyio: async test marker",
]
```

---

### Best Practices

1. **Test Organization** - All tests in `tests/` subdirectory
2. **Fixtures** - Use pytest fixtures (monkeypatch, capsys) not manual mocking
3. **Markers** - Slow tests marked appropriately for CI optimization
4. **Temp Files** - Always use `tempfile.TemporaryDirectory()` for .mv2 files
5. **Real Data** - E2E tests use actual .mv2 files for validation
6. **Fast Unit Tests** - Parsing tests execute in <1 second each

---

### Known Limitations

**E2E Tests:**
- Lower coverage (66%) due to external LLM dependency
- Require real .mv2 file and optional OpenRouter API key
- Network conditions affect reliability

**Slow Tests:**
- Model downloads (~130MB) on first run
- Skipped by default in fast test runs
- Run explicitly with `pytest -m slow`

**Verbose Output:**
- Debug/verbose print statements not covered (9% gap)
- Acceptable for diagnostic logging code

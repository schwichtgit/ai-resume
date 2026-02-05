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

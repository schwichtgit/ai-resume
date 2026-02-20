"""Tests that API response latency meets NFR targets (mocked backends).

Measures framework overhead with mocked dependencies to ensure the API
layer itself does not introduce unacceptable latency. These are not
true network latency tests -- they validate that the FastAPI routing,
middleware, and serialization overhead stays within bounds.
"""

import time
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.session_store import reset_session_store

# Minimal mock profile for latency testing
MOCK_PROFILE = {
    "name": "Test User",
    "title": "Test Title",
    "email": "test@example.com",
    "linkedin": "https://linkedin.com/in/test",
    "location": "Test Location",
    "status": "Available",
    "suggested_questions": ["What experience do they have?"],
    "tags": ["engineering"],
    "experience": [
        {
            "company": "Test Corp",
            "role": "Engineer",
            "period": "2020-2023",
            "highlights": ["Built things"],
            "ai_context": {
                "situation": "Test",
                "approach": "Test",
                "technical_work": "Test",
                "lessons_learned": "Test",
            },
        }
    ],
    "skills": {
        "strong": ["Python"],
        "moderate": ["React"],
        "gaps": ["Mobile"],
    },
    "fit_assessment_examples": [],
}


@pytest.fixture
def mock_memvid_ask() -> Generator[AsyncMock, None, None]:
    """Mock memvid client for latency tests."""
    with patch("app.main.get_memvid_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.health_check.return_value = AsyncMock(status="SERVING", frame_count=100)
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openrouter() -> Generator[AsyncMock, None, None]:
    """Mock OpenRouter client for latency tests."""
    with patch("app.main.get_openrouter_client") as mock_get_or:
        mock_or = AsyncMock()
        mock_get_or.return_value = mock_or
        yield mock_or


@pytest.fixture
def mock_profile_loading() -> Generator[AsyncMock, None, None]:
    """Mock profile loading for latency tests."""
    with patch("app.config.get_settings") as mock_get_settings:
        mock_settings = AsyncMock()
        mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
        mock_settings.load_profile = lambda: MOCK_PROFILE
        mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
        mock_settings.max_history_messages = 10
        mock_settings.llm_model = "anthropic/claude-3.5-sonnet"
        mock_settings.rate_limit_per_minute = 1000
        mock_settings.mock_memvid_client = False
        mock_get_settings.return_value = mock_settings
        yield mock_settings


@pytest.fixture
def client(
    mock_profile_loading: Any, mock_memvid_ask: Any, mock_openrouter: Any
) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    reset_session_store()
    with TestClient(app) as c:
        yield c
    reset_session_store()


@pytest.mark.e2e
class TestLatencyNFR:
    """Non-functional requirement: API response latency with mocked backends."""

    def test_health_endpoint_latency(self, client: TestClient) -> None:
        """Health endpoint should respond within 100ms."""
        start = time.monotonic()
        response = client.get("/api/v1/health")
        elapsed = time.monotonic() - start
        assert response.status_code == 200
        assert elapsed < 0.1, f"Health check took {elapsed:.3f}s (limit: 0.1s)"

    def test_profile_endpoint_latency(self, client: TestClient) -> None:
        """Profile endpoint should respond within 500ms."""
        start = time.monotonic()
        response = client.get("/api/v1/profile")
        elapsed = time.monotonic() - start
        assert response.status_code == 200
        assert elapsed < 0.5, f"Profile took {elapsed:.3f}s (limit: 0.5s)"

    def test_health_endpoint_repeated_latency(self, client: TestClient) -> None:
        """Repeated health checks should be consistently fast."""
        times = []
        for _ in range(5):
            start = time.monotonic()
            response = client.get("/api/v1/health")
            elapsed = time.monotonic() - start
            assert response.status_code == 200
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 0.05, f"Average health check took {avg:.3f}s (limit: 0.05s)"

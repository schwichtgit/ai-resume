"""Tests for the chat feedback endpoint."""

import pytest
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app, _feedback_seen
from app.session_store import reset_session_store


# Sample profile data for tests
MOCK_PROFILE = {
    "name": "Test User",
    "title": "Test Title",
    "email": "test@example.com",
    "linkedin": "https://linkedin.com/in/test",
    "location": "Test Location",
    "status": "Available",
    "suggested_questions": ["What experience do they have?"],
    "tags": ["engineering"],
    "experience": [],
    "skills": {"strong": [], "moderate": [], "gaps": []},
    "fit_assessment_examples": [],
}


@pytest.fixture(autouse=True)
def clear_feedback_seen() -> Generator[None, None, None]:
    """Clear the feedback idempotency set before and after each test."""
    _feedback_seen.clear()
    yield
    _feedback_seen.clear()


@pytest.fixture
def mock_memvid() -> Generator[AsyncMock, None, None]:
    """Mock memvid client."""
    with patch("app.main.get_memvid_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.health_check.return_value = AsyncMock(status="SERVING", frame_count=100)
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_profile_loading() -> Generator[AsyncMock, None, None]:
    """Mock profile loading from memvid."""
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
def client(mock_profile_loading: Any, mock_memvid: Any) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    reset_session_store()
    with TestClient(app) as c:
        yield c
    reset_session_store()


def _create_session(client: TestClient) -> str:
    """Create a chat session and return its ID."""
    with patch("app.main.get_openrouter_client") as mock_or:
        from ai_resume_api.openrouter_client import LLMResponse

        mock_client = AsyncMock()
        mock_client.chat.return_value = LLMResponse(
            content="Test response.",
            tokens_used=10,
            finish_reason="stop",
        )
        mock_or.return_value = mock_client

        with patch("app.main.get_memvid_client") as mock_mv:
            mv_client = AsyncMock()
            mv_client.ask.return_value = {
                "answer": "Context text.",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 1,
                    "results_returned": 1,
                    "retrieval_ms": 1.0,
                    "reranking_ms": 0.5,
                    "total_ms": 1.5,
                },
            }
            mock_mv.return_value = mv_client

            response = client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": False},
            )
            assert response.status_code == 200
            session_id: str = response.json()["session_id"]
            return session_id


class TestFeedbackEndpoint:
    """Tests for POST /api/v1/chat/{session_id}/feedback."""

    def test_happy_path(self, client: TestClient) -> None:
        """Submit valid feedback and verify 200 response."""
        session_id = _create_session(client)

        response = client.post(
            f"/api/v1/chat/{session_id}/feedback",
            json={"message_id": "msg-1", "rating": "up"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_happy_path_with_comment(self, client: TestClient) -> None:
        """Submit valid feedback with a comment."""
        session_id = _create_session(client)

        response = client.post(
            f"/api/v1/chat/{session_id}/feedback",
            json={"message_id": "msg-1", "rating": "down", "comment": "Not helpful"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_idempotency(self, client: TestClient) -> None:
        """Submitting the same (session_id, message_id) twice increments only once."""
        session_id = _create_session(client)

        from app.main import chat_feedback_total

        # Get initial counter value via the counter's internal _value
        before = chat_feedback_total.labels(rating="up")._value.get()

        # First submission
        resp1 = client.post(
            f"/api/v1/chat/{session_id}/feedback",
            json={"message_id": "msg-dup", "rating": "up"},
        )
        assert resp1.status_code == 200

        after_first = chat_feedback_total.labels(rating="up")._value.get()
        assert after_first == before + 1

        # Second submission (same session_id + message_id)
        resp2 = client.post(
            f"/api/v1/chat/{session_id}/feedback",
            json={"message_id": "msg-dup", "rating": "up"},
        )
        assert resp2.status_code == 200

        after_second = chat_feedback_total.labels(rating="up")._value.get()
        assert after_second == after_first  # Not incremented again

    def test_422_long_comment(self, client: TestClient) -> None:
        """Comment exceeding 500 chars returns 422."""
        session_id = _create_session(client)

        response = client.post(
            f"/api/v1/chat/{session_id}/feedback",
            json={
                "message_id": "msg-1",
                "rating": "up",
                "comment": "x" * 501,
            },
        )
        assert response.status_code == 422

    def test_404_bad_session(self, client: TestClient) -> None:
        """Non-existent session returns 404."""
        fake_session = "00000000-0000-4000-8000-000000000000"

        response = client.post(
            f"/api/v1/chat/{fake_session}/feedback",
            json={"message_id": "msg-1", "rating": "up"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"

    def test_404_invalid_uuid(self, client: TestClient) -> None:
        """Invalid UUID format returns 404."""
        response = client.post(
            "/api/v1/chat/not-a-uuid/feedback",
            json={"message_id": "msg-1", "rating": "up"},
        )
        assert response.status_code == 404

    def test_invalid_rating(self, client: TestClient) -> None:
        """Invalid rating value returns 422."""
        session_id = _create_session(client)

        response = client.post(
            f"/api/v1/chat/{session_id}/feedback",
            json={"message_id": "msg-1", "rating": "neutral"},
        )
        assert response.status_code == 422

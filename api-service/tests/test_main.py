"""Tests for FastAPI main application."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.session_store import reset_session_store


# Sample profile data for tests
MOCK_PROFILE = {
    "name": "Test User",
    "title": "Test Title",
    "email": "test@example.com",
    "linkedin": "https://linkedin.com/in/test",
    "location": "Test Location",
    "status": "Available",
    "suggested_questions": [
        "What experience do they have?",
        "Tell me about their skills",
        "What projects have they worked on?",
    ],
    "tags": ["engineering", "leadership"],
    "experience": [
        {
            "company": "Test Company",
            "role": "Test Role",
            "period": "2020-2023",
            "highlights": ["Built things", "Led team"],
            "ai_context": {
                "situation": "Test situation",
                "approach": "Test approach",
                "technical_work": "Test technical work",
                "lessons_learned": "Test lessons",
            },
        }
    ],
    "skills": {
        "strong": ["Python", "FastAPI"],
        "moderate": ["React", "TypeScript"],
        "gaps": ["Mobile development"],
    },
    "fit_assessment_examples": [
        {
            "title": "Strong Fit Example",
            "fit_level": "strong",
            "role": "Senior Engineer",
            "job_description": "Senior Engineer position...",
            "verdict": "Strong fit",
            "key_matches": ["Python expertise"],
            "gaps": ["Mobile experience"],
            "recommendation": "Recommended",
        }
    ],
}


@pytest.fixture
def mock_memvid_ask():
    """Mock memvid client ask method."""
    with patch("app.main.get_memvid_client") as mock_get_client:
        mock_client = AsyncMock()
        # Default mock response for ask()
        mock_client.ask.return_value = {
            "answer": "Based on the resume, the candidate has experience with Python, FastAPI, and building scalable systems.",
            "evidence": [
                {
                    "title": "Professional Experience",
                    "score": 0.85,
                    "snippet": "Built self-service platform handling 1000+ deploys/day",
                    "tags": ["engineering"],
                }
            ],
            "stats": {
                "candidates_retrieved": 5,
                "results_returned": 1,
                "retrieval_ms": 2.5,
                "reranking_ms": 1.2,
                "total_ms": 3.7,
            },
        }
        mock_client.health_check.return_value = AsyncMock(status="SERVING", frame_count=100)
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openrouter():
    """Mock OpenRouter client."""
    from ai_resume_api.openrouter_client import LLMResponse

    with patch("app.main.get_openrouter_client") as mock_get_or:
        mock_or = AsyncMock()
        # Default mock response
        mock_or.chat.return_value = LLMResponse(
            content="This is a test response based on the provided context.",
            tokens_used=50,
            finish_reason="stop",
        )

        # Mock streaming
        async def mock_chat_stream(*args, **kwargs):
            chunks = ["This ", "is ", "a ", "test ", "response."]
            for i, chunk_text in enumerate(chunks):
                chunk = LLMResponse(
                    content=chunk_text,
                    tokens_used=10 if i == len(chunks) - 1 else 0,
                    finish_reason="stop" if i == len(chunks) - 1 else None,
                )
                yield chunk

        mock_or.chat_stream = mock_chat_stream
        mock_get_or.return_value = mock_or
        yield mock_or


@pytest.fixture
def mock_profile_loading():
    """Mock profile loading from memvid."""
    with patch("app.config.get_settings") as mock_get_settings:
        mock_settings = AsyncMock()
        # Mock the load_profile_from_memvid method
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
def client(mock_profile_loading, mock_memvid_ask, mock_openrouter):
    """Create test client with mocked dependencies."""
    reset_session_store()
    with TestClient(app) as client:
        yield client
    reset_session_store()


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "active_sessions" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_check_v1(self, client):
        """Test v1 health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data


class TestSuggestedQuestionsEndpoint:
    """Tests for suggested questions endpoint."""

    def test_get_suggested_questions(self, client):
        """Test getting suggested questions."""
        response = client.get("/api/v1/suggested-questions")
        assert response.status_code == 200

        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) > 0

        for q in data["questions"]:
            assert "question" in q
            assert len(q["question"]) > 0


class TestChatEndpoint:
    """Tests for chat endpoint."""

    def test_chat_non_streaming(self, client):
        """Test non-streaming chat request."""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "What experience do they have?",
                "stream": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert "chunks_retrieved" in data

    def test_chat_creates_session(self, client):
        """Test that chat creates a session."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "stream": False},
        )
        assert response.status_code == 200

        data = response.json()
        session_id = data["session_id"]
        assert session_id is not None

        # Second request with same session
        response2 = client.post(
            "/api/v1/chat",
            json={"message": "Follow up", "session_id": session_id, "stream": False},
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    def test_chat_streaming(self, client):
        """Test streaming chat request."""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Tell me about their skills",
                "stream": True,
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Check that we get SSE events
        content = response.text
        assert "data:" in content

    def test_chat_validation_empty_message(self, client):
        """Test that empty message fails validation."""
        response = client.post(
            "/api/v1/chat",
            json={"message": ""},
        )
        assert response.status_code == 422  # Validation error


class TestMetricsEndpoint:
    """Tests for Prometheus metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test that metrics endpoint exists."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus metrics are text-based
        assert "http_requests" in response.text or "fastapi" in response.text.lower()


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS preflight should succeed
        assert response.status_code in [200, 204]


class TestMockResponses:
    """Tests for mock response generation."""

    def test_mock_response_with_context(self, client):
        """Test mock response includes context."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "What skills?", "stream": False},
        )
        assert response.status_code == 200
        data = response.json()
        # Mock response should reference context
        assert "message" in data

    def test_multiple_chat_requests(self, client):
        """Test multiple chat requests in sequence."""
        # First request creates session
        r1 = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "stream": False},
        )
        assert r1.status_code == 200
        session_id = r1.json()["session_id"]

        # Second request uses same session
        r2 = client.post(
            "/api/v1/chat",
            json={"message": "Follow up", "session_id": session_id, "stream": False},
        )
        assert r2.status_code == 200

        # Third request with streaming
        r3 = client.post(
            "/api/v1/chat",
            json={"message": "More questions", "session_id": session_id, "stream": True},
        )
        assert r3.status_code == 200


class TestMockStreamingResponse:
    """Tests for mock streaming response generation."""

    def test_mock_stream_contains_retrieval_event(self, client):
        """Test that mock stream starts with retrieval event."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Test streaming", "stream": True},
        )
        assert response.status_code == 200
        content = response.text
        # Should have retrieval event
        assert '"type":"retrieval"' in content or '"type": "retrieval"' in content

    def test_mock_stream_contains_done_event(self, client):
        """Test that mock stream ends with end event."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Test done", "stream": True},
        )
        assert response.status_code == 200
        content = response.text
        # Should have end event with [DONE]
        assert "event: end" in content and "[DONE]" in content

    def test_mock_stream_contains_metadata(self, client):
        """Test that mock stream contains stats event."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Test metadata", "stream": True},
        )
        assert response.status_code == 200
        content = response.text
        # Should have stats event with metrics
        assert "event: stats" in content
        assert "chunks_retrieved" in content
        assert "tokens_used" in content


class TestGenerateMockResponse:
    """Tests for _generate_mock_response function."""

    def test_mock_response_empty_context(self, client, mock_memvid_ask):
        """Test mock response when context is empty."""
        # Override mock to return empty results
        mock_memvid_ask.ask.return_value = {
            "answer": "",
            "evidence": [],
            "stats": {
                "candidates_retrieved": 0,
                "results_returned": 0,
                "retrieval_ms": 0.5,
                "reranking_ms": 0.0,
                "total_ms": 0.5,
            },
        }

        response = client.post(
            "/api/v1/chat",
            json={"message": "Random question", "stream": False},
        )
        # Should still succeed but with different message
        assert response.status_code == 200


class TestHealthDegraded:
    """Tests for degraded health status."""

    def test_health_degraded_when_memvid_fails(self, client):
        """Test health returns degraded when memvid is unavailable."""
        from unittest.mock import patch

        with patch("app.main.get_memvid_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")

            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            # Should be degraded since memvid failed
            assert data["memvid_connected"] is False


class TestChatErrorHandling:
    """Tests for chat endpoint error handling."""

    def test_chat_handles_memvid_search_failure(self):
        """Test chat handles memvid search errors gracefully."""
        from ai_resume_api.memvid_client import MemvidSearchError

        # Create fresh client with custom mocked memvid that raises exception
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.config.get_settings") as mock_get_settings,
            patch("app.main.get_openrouter_client"),
        ):
            # Setup settings mock
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            # Setup memvid mock to raise exception
            mock_client = AsyncMock()
            mock_client.ask.side_effect = MemvidSearchError("Search failed")
            mock_get_client.return_value = mock_client

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": False},
                )
                # Should return 502 error (or 500 if unhandled)
                # The key is that it doesn't crash and returns an error status
                assert response.status_code in [500, 502, 503]

        reset_session_store()


class TestLifespanErrorHandling:
    """Tests for lifespan startup error handling."""

    def test_lifespan_continues_when_memvid_init_fails(self):
        """Test that app starts even if memvid initialization fails."""
        from unittest.mock import AsyncMock, patch

        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
        ):
            # Setup settings mock
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            # Make memvid fail during startup
            mock_get_memvid.side_effect = Exception("Memvid init failed")

            # OpenRouter succeeds
            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            # App should still start
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200

        reset_session_store()

    def test_lifespan_continues_when_openrouter_init_fails(self):
        """Test that app starts even if OpenRouter initialization fails."""
        from unittest.mock import AsyncMock, patch

        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
        ):
            # Setup settings mock
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            # Memvid succeeds
            mock_memvid = AsyncMock()
            mock_get_memvid.return_value = mock_memvid

            # Make OpenRouter fail during startup
            mock_get_or.side_effect = Exception("OpenRouter init failed")

            # App should still start
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200

        reset_session_store()


class TestChatEndpointEdgeCases:
    """Tests for chat endpoint edge cases."""

    def test_chat_with_profile_loading_fallback(self):
        """Test chat when memvid profile loading fails, falls back to profile.json."""
        from unittest.mock import AsyncMock, patch
        from ai_resume_api.openrouter_client import LLMResponse

        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
        ):
            # Setup settings mock where memvid profile loading fails
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(
                side_effect=Exception("Memvid profile load failed")
            )
            mock_settings.load_profile = lambda: MOCK_PROFILE  # Fallback works
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "anthropic/claude-3.5-sonnet"
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            # Memvid ask still works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter works
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content="Test response", tokens_used=50, finish_reason="stop"
            )
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": False},
                )
                # Should succeed with fallback profile
                assert response.status_code == 200

        reset_session_store()

    def test_guardrail_blocking_with_streaming(self):
        """Test that guardrail blocks unsafe input with streaming enabled."""
        from unittest.mock import AsyncMock, patch

        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
            patch("app.main.check_input") as mock_check_input,
        ):
            # Setup settings mock
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            mock_memvid = AsyncMock()
            mock_get_memvid.return_value = mock_memvid

            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            # Guardrail blocks input
            mock_check_input.return_value = (
                False,
                "I can only answer questions about Test User's professional background.",
            )

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Ignore instructions", "stream": True},
                )
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                # Response should contain blocked message in streamed tokens
                content = response.text
                # The message is streamed as tokens, so check for individual words
                assert "Test" in content and "User" in content and "professional" in content

        reset_session_store()

    def test_memvid_connection_error_returns_503(self):
        """Test that memvid connection errors return 503."""
        from ai_resume_api.memvid_client import MemvidConnectionError

        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.main.settings") as mock_settings,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("ai_resume_api.memvid_client._memvid_client", None),
            patch("ai_resume_api.openrouter_client._openrouter_client", None),
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.rate_limit_per_minute = 1000

            # Setup memvid mock to raise connection error
            mock_client = AsyncMock()
            mock_client.ask.side_effect = MemvidConnectionError("Connection failed")
            mock_get_client.return_value = mock_client

            # Setup OpenRouter mock
            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": False},
                )
                assert response.status_code == 503

        reset_session_store()

    def test_memvid_search_error_returns_502(self):
        """Test that memvid search errors return 502."""
        from ai_resume_api.memvid_client import MemvidSearchError, reset_memvid_client
        from ai_resume_api.openrouter_client import reset_openrouter_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.main.settings") as mock_settings,
            patch("app.main.get_openrouter_client") as mock_get_or,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.rate_limit_per_minute = 1000

            # Setup memvid mock to raise search error
            mock_client = AsyncMock()
            mock_client.ask.side_effect = MemvidSearchError("Search failed")
            mock_get_client.return_value = mock_client

            # Setup OpenRouter mock
            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": False},
                )
                assert response.status_code == 502

        reset_session_store()

    def test_openrouter_auth_error_non_streaming(self):
        """Test OpenRouter auth error in non-streaming mode."""
        from ai_resume_api.openrouter_client import OpenRouterAuthError, reset_openrouter_client
        from ai_resume_api.memvid_client import reset_memvid_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "anthropic/claude-3.5-sonnet"
            mock_settings.rate_limit_per_minute = 1000

            # Memvid works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter raises auth error
            mock_or = AsyncMock()
            mock_or.chat.side_effect = OpenRouterAuthError("Invalid API key")
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": False},
                )
                assert response.status_code == 503

        reset_session_store()


class TestStreamingErrorHandling:
    """Tests for streaming chat error handling."""

    def test_streaming_with_openrouter_auth_error(self):
        """Test streaming chat handles OpenRouter auth errors."""
        from ai_resume_api.openrouter_client import OpenRouterAuthError, reset_openrouter_client
        from ai_resume_api.memvid_client import reset_memvid_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "anthropic/claude-3.5-sonnet"
            mock_settings.rate_limit_per_minute = 1000

            # Memvid works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter raises auth error in streaming
            async def mock_chat_stream_error(*args, **kwargs):
                raise OpenRouterAuthError("Invalid API key")
                yield  # Make it a generator

            mock_or = AsyncMock()
            mock_or.chat_stream = mock_chat_stream_error
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": True},
                )
                assert response.status_code == 200
                content = response.text
                # Should contain error event
                assert "error" in content.lower() or "not configured" in content.lower()

        reset_session_store()

    def test_streaming_with_generic_openrouter_error(self):
        """Test streaming chat handles generic OpenRouter errors."""
        from ai_resume_api.openrouter_client import OpenRouterError, reset_openrouter_client
        from ai_resume_api.memvid_client import reset_memvid_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "anthropic/claude-3.5-sonnet"
            mock_settings.rate_limit_per_minute = 1000

            # Memvid works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter raises generic error in streaming
            async def mock_chat_stream_error(*args, **kwargs):
                raise OpenRouterError("Service unavailable")
                yield  # Make it a generator

            mock_or = AsyncMock()
            mock_or.chat_stream = mock_chat_stream_error
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": True},
                )
                assert response.status_code == 200
                content = response.text
                # Should contain error event
                assert "error" in content.lower()

        reset_session_store()

    def test_streaming_with_client_cancellation(self):
        """Test streaming handles CancelledError (client disconnects)."""
        from asyncio import CancelledError

        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
        ):
            # Setup settings mock
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "anthropic/claude-3.5-sonnet"
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            # Memvid works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter raises CancelledError in streaming
            async def mock_chat_stream_cancelled(*args, **kwargs):
                raise CancelledError()
                yield  # Unreachable but makes this an async generator

            mock_or = AsyncMock()
            mock_or.chat_stream = mock_chat_stream_cancelled
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                # CancelledError should propagate (not caught as regular error)
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "Test question", "stream": True},
                )
                # Client cancellation may result in various status codes
                assert response.status_code in [200, 499, 500]

        reset_session_store()


class TestMockResponseHelpers:
    """Tests for mock response helper functions."""

    def test_mock_stream_response_generator(self):
        """Test _mock_stream_response generates proper SSE events."""
        import asyncio
        from app.main import _mock_stream_response

        async def run_test():
            events = []
            async for event in _mock_stream_response("Hello world test", chunks_retrieved=5):
                events.append(event)
            return events

        events = asyncio.run(run_test())

        # Should have retrieval, token, stats, and end events
        assert len(events) > 0

        # First event should be retrieval
        assert "retrieval" in events[0]
        assert "chunks" in events[0] or "5" in events[0]

        # Should have token events
        token_events = [e for e in events if "token" in e]
        assert len(token_events) > 0

        # Should have stats event
        stats_events = [e for e in events if "stats" in e]
        assert len(stats_events) > 0

        # Last event should be end with [DONE]
        assert "[DONE]" in events[-1]

    def test_generate_mock_response_with_context(self):
        """Test _generate_mock_response with context."""
        from app.main import _generate_mock_response

        context = "The candidate has experience with Python, FastAPI, and distributed systems."
        message = "What programming languages do they know?"

        response = _generate_mock_response(message, context)

        assert len(response) > 0
        assert "context" in response.lower() or "resume" in response.lower()

    def test_generate_mock_response_without_context(self):
        """Test _generate_mock_response without context."""
        from app.main import _generate_mock_response

        response = _generate_mock_response("What skills?", "")

        assert len(response) > 0
        assert "context" in response.lower() or "question" in response.lower()


class TestProfileEndpointErrors:
    """Tests for profile endpoint error handling."""

    def test_get_profile_returns_404_when_not_found(self):
        """Test get_profile returns 404 when profile data not found."""
        reset_session_store()

        with patch("app.main.settings") as mock_settings:
            # Setup settings mock where both loading methods fail
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=None)
            mock_settings.load_profile = lambda: None
            mock_settings.rate_limit_per_minute = 1000

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/profile")
                assert response.status_code == 404

        reset_session_store()

    def test_get_profile_handles_parsing_errors(self):
        """Test get_profile handles malformed profile data."""
        reset_session_store()

        with patch("app.main.settings") as mock_settings:
            # Setup settings mock with malformed data
            malformed_profile = {
                "name": "Test User",
                "title": "Test Title",
                "experience": [
                    {
                        # Missing required fields like 'role'
                        "company": "Test Co"
                    }
                ],
            }
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=malformed_profile)
            mock_settings.load_profile = lambda: malformed_profile
            mock_settings.rate_limit_per_minute = 1000

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/profile")
                # Should return error status (422 or 500)
                assert response.status_code in [422, 500]

        reset_session_store()

    def test_suggested_questions_returns_404_when_not_found(self):
        """Test suggested_questions returns 404 when profile not found."""
        reset_session_store()

        with patch("app.main.settings") as mock_settings:
            # Setup settings mock where profile loading fails
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=None)
            mock_settings.load_profile = lambda: None
            mock_settings.rate_limit_per_minute = 1000

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/suggested-questions")
                assert response.status_code == 404

        reset_session_store()


class TestAssessFitErrorHandling:
    """Tests for assess-fit endpoint error handling."""

    def test_assess_fit_memvid_connection_error_503(self):
        """Test assess_fit returns 503 on memvid connection error."""
        from ai_resume_api.memvid_client import MemvidConnectionError, reset_memvid_client
        from ai_resume_api.openrouter_client import reset_openrouter_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.main.settings") as mock_settings,
            patch("app.main.get_openrouter_client") as mock_get_or,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000

            # Setup memvid mock to raise connection error
            mock_client = AsyncMock()
            mock_client.ask.side_effect = MemvidConnectionError("Connection failed")
            mock_get_client.return_value = mock_client

            # Setup OpenRouter mock
            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": "Senior Engineer role requiring Python, Kubernetes, and cloud infrastructure experience with 5+ years of hands-on experience."
                    },
                )
                assert response.status_code == 503

        reset_session_store()

    def test_assess_fit_memvid_search_error_502(self):
        """Test assess_fit returns 502 on memvid search error."""
        from ai_resume_api.memvid_client import MemvidSearchError, reset_memvid_client
        from ai_resume_api.openrouter_client import reset_openrouter_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.main.settings") as mock_settings,
            patch("app.main.get_openrouter_client") as mock_get_or,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000

            # Setup memvid mock to raise search error
            mock_client = AsyncMock()
            mock_client.ask.side_effect = MemvidSearchError("Search failed")
            mock_get_client.return_value = mock_client

            # Setup OpenRouter mock
            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": "Senior Engineer role requiring Python, Kubernetes, and cloud infrastructure experience with 5+ years of hands-on experience."
                    },
                )
                assert response.status_code == 502

        reset_session_store()

    def test_assess_fit_response_parsing_fallbacks(self):
        """Test assess_fit parsing fallbacks for malformed LLM responses."""
        from ai_resume_api.openrouter_client import LLMResponse

        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.config.get_settings") as mock_get_settings,
        ):
            # Setup settings mock
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            # Memvid works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter returns response with no sections (no VERDICT, KEY MATCHES, etc.)
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content="This is just plain text without any sections or structure.",
                tokens_used=50,
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": "Senior Engineer role requiring Python, Kubernetes, and cloud infrastructure experience with 5+ years of hands-on experience."
                    },
                )
                assert response.status_code == 200
                data = response.json()

                # Should have fallback values
                assert "verdict" in data
                assert "key_matches" in data
                assert "gaps" in data
                assert "recommendation" in data

        reset_session_store()

    def test_assess_fit_openrouter_auth_error(self):
        """Test assess_fit handles OpenRouter auth errors."""
        from ai_resume_api.openrouter_client import OpenRouterAuthError, reset_openrouter_client
        from ai_resume_api.memvid_client import reset_memvid_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000

            # Memvid works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter raises auth error
            mock_or = AsyncMock()
            mock_or.chat.side_effect = OpenRouterAuthError("Invalid API key")
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": "Senior Engineer role requiring Python, Kubernetes, and cloud infrastructure experience with 5+ years of hands-on experience."
                    },
                )
                assert response.status_code == 503

        reset_session_store()

    def test_assess_fit_openrouter_generic_error(self):
        """Test assess_fit handles generic OpenRouter errors."""
        from ai_resume_api.openrouter_client import OpenRouterError, reset_openrouter_client
        from ai_resume_api.memvid_client import reset_memvid_client

        reset_session_store()
        reset_memvid_client()
        reset_openrouter_client()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            # Setup settings mock
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000

            # Memvid works
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "Test context",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.5,
                    "reranking_ms": 1.2,
                    "total_ms": 3.7,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # OpenRouter raises generic error
            mock_or = AsyncMock()
            mock_or.chat.side_effect = OpenRouterError("Service timeout")
            mock_get_or.return_value = mock_or

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": "Senior Engineer role requiring Python, Kubernetes, and cloud infrastructure experience with 5+ years of hands-on experience."
                    },
                )
                assert response.status_code == 502

        reset_session_store()


class TestAssessFitEndpoint:
    """Tests for fit assessment endpoint."""

    def test_assess_fit_success(self, client):
        """Test successful fit assessment."""
        from unittest.mock import AsyncMock, patch
        from ai_resume_api.openrouter_client import LLMResponse

        # Mock memvid search
        mock_search_response = AsyncMock()
        mock_hit1 = AsyncMock()
        mock_hit1.title = "Platform Engineering Experience"
        mock_hit1.snippet = "Built self-service platform handling 1000+ deploys/day..."
        mock_hit2 = AsyncMock()
        mock_hit2.title = "ML Infrastructure"
        mock_hit2.snippet = "Model serving infrastructure handling 10M inferences/day..."
        mock_search_response.hits = [mock_hit1, mock_hit2]
        mock_search_response.total_hits = 2

        # Mock OpenRouter response
        mock_llm_response = LLMResponse(
            content="""VERDICT: ⭐⭐⭐⭐⭐ Strong fit (95% match)

KEY MATCHES:
- Platform engineering expertise: Built self-service platforms handling 1000+ deploys/day
- ML infrastructure: Model serving handling 10M inferences/day
- Team leadership: Led 15-person platform team

GAPS:
- Limited mobile app experience

RECOMMENDATION: Excellent fit for this VP Platform Engineering role. The candidate's platform engineering and ML infrastructure experience directly aligns with the requirements.""",
            tokens_used=450,
        )

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.main.get_openrouter_client") as mock_get_or_client,
        ):
            mock_memvid = AsyncMock()
            mock_memvid.search.return_value = mock_search_response
            mock_get_client.return_value = mock_memvid

            mock_or = AsyncMock()
            mock_or.chat.return_value = mock_llm_response
            mock_get_or_client.return_value = mock_or

            response = client.post(
                "/api/v1/assess-fit",
                json={
                    "job_description": "VP Platform Engineering at Series B AI startup. Must have experience with Kubernetes, platform engineering, and ML infrastructure. 10+ years experience required."
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert "verdict" in data
            assert "key_matches" in data
            assert "gaps" in data
            assert "recommendation" in data
            assert "chunks_retrieved" in data
            assert "tokens_used" in data

            # Check parsed content
            assert "Strong fit" in data["verdict"]
            assert isinstance(data["key_matches"], list)
            assert len(data["key_matches"]) > 0
            assert isinstance(data["gaps"], list)
            assert len(data["recommendation"]) > 0

    def test_assess_fit_validation_too_short(self, client):
        """Test that job description must be at least 50 characters."""
        response = client.post(
            "/api/v1/assess-fit",
            json={"job_description": "Short JD"},
        )
        assert response.status_code == 422  # Validation error

    def test_assess_fit_validation_missing_field(self, client):
        """Test that job_description field is required."""
        response = client.post(
            "/api/v1/assess-fit",
            json={},
        )
        assert response.status_code == 422  # Validation error

    # TODO: Add test for API key not configured once exception handling is implemented
    # def test_assess_fit_no_api_key(self, client):

    def test_assess_fit_memvid_unavailable(self):
        """Test handling when memvid is unavailable."""
        from ai_resume_api.memvid_client import MemvidConnectionError

        # Create fresh client with custom mocked memvid that raises exception
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.config.get_settings") as mock_get_settings,
            patch("app.main.get_openrouter_client"),
        ):
            # Setup settings mock
            mock_settings = AsyncMock()
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000
            mock_get_settings.return_value = mock_settings

            # Setup memvid mock to raise exception
            mock_client = AsyncMock()
            mock_client.ask.side_effect = MemvidConnectionError("Memvid connection failed")
            mock_get_client.return_value = mock_client

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": "Senior Engineer role requiring Python, Kubernetes, and cloud infrastructure experience."
                    },
                )

                # Should return error (500, 502, or 503)
                # The key is that it doesn't crash and returns an error status
                assert response.status_code in [500, 502, 503]

        reset_session_store()

    # TODO: Add test for LLM timeout once exception handling is implemented
    # def test_assess_fit_llm_timeout(self, client):

    def test_assess_fit_malformed_llm_response(self, client):
        """Test handling when LLM returns malformed response."""
        from unittest.mock import AsyncMock, patch
        from ai_resume_api.openrouter_client import LLMResponse

        mock_search_response = AsyncMock()
        mock_hit = AsyncMock()
        mock_hit.title = "Experience"
        mock_hit.snippet = "Test snippet"
        mock_search_response.hits = [mock_hit]

        # LLM response missing expected sections
        mock_llm_response = LLMResponse(
            content="This is not a properly formatted assessment.",
            tokens_used=50,
        )

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.main.get_openrouter_client") as mock_get_or_client,
        ):
            mock_memvid = AsyncMock()
            mock_memvid.search.return_value = mock_search_response
            mock_get_client.return_value = mock_memvid

            mock_or = AsyncMock()
            mock_or.chat.return_value = mock_llm_response
            mock_get_or_client.return_value = mock_or

            response = client.post(
                "/api/v1/assess-fit",
                json={
                    "job_description": "Senior Software Engineer position requiring strong Python and API development skills."
                },
            )

            # Should still return 200 but with partial/fallback data
            assert response.status_code == 200
            data = response.json()

            # Should have fields even if parsing failed
            assert "verdict" in data
            assert "key_matches" in data
            assert "gaps" in data
            assert "recommendation" in data

    def test_assess_fit_empty_context(self, client):
        """Test fit assessment when memvid returns no context."""
        from ai_resume_api.openrouter_client import LLMResponse

        mock_llm_response = LLMResponse(
            content="""VERDICT: ⭐⭐ Limited information

KEY MATCHES:
- None available

GAPS:
- Insufficient profile data to assess fit

RECOMMENDATION: Unable to properly assess fit due to lack of context.""",
            tokens_used=100,
        )

        with (
            patch("app.main.get_memvid_client") as mock_get_client,
            patch("app.main.get_openrouter_client") as mock_get_or_client,
        ):
            mock_memvid = AsyncMock()
            # Return empty ask response
            mock_memvid.ask.return_value = {
                "answer": "",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 0,
                    "results_returned": 0,
                    "retrieval_ms": 0.5,
                    "reranking_ms": 0.0,
                    "total_ms": 0.5,
                },
            }
            mock_get_client.return_value = mock_memvid

            mock_or = AsyncMock()
            mock_or.chat.return_value = mock_llm_response
            mock_get_or_client.return_value = mock_or

            response = client.post(
                "/api/v1/assess-fit",
                json={
                    "job_description": "CTO role requiring 15+ years experience in enterprise software and strategic leadership."
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["chunks_retrieved"] == 0

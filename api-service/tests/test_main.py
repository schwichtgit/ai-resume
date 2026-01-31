"""Tests for FastAPI main application."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.session_store import reset_session_store


@pytest.fixture
def client():
    """Create test client."""
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
        """Test that mock stream ends with done event."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Test done", "stream": True},
        )
        assert response.status_code == 200
        content = response.text
        # Should have done event
        assert '"type":"done"' in content or '"type": "done"' in content

    def test_mock_stream_contains_metadata(self, client):
        """Test that mock stream contains metadata event."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Test metadata", "stream": True},
        )
        assert response.status_code == 200
        content = response.text
        # Should have metadata event
        assert '"type":"metadata"' in content or '"type": "metadata"' in content


class TestGenerateMockResponse:
    """Tests for _generate_mock_response function."""

    def test_mock_response_empty_context(self, client):
        """Test mock response when context is empty."""
        from unittest.mock import AsyncMock, patch

        # Patch the memvid client to return empty results
        with patch("app.main.get_memvid_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search.return_value = AsyncMock(hits=[], total_hits=0, took_ms=1)
            mock_get_client.return_value = mock_client

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
        from unittest.mock import AsyncMock, patch

        with patch("app.main.get_memvid_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")

            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            # Should be degraded since memvid failed
            assert data["memvid_connected"] is False


class TestChatErrorHandling:
    """Tests for chat endpoint error handling."""

    def test_chat_handles_memvid_search_failure(self, client):
        """Test chat handles memvid search errors gracefully."""
        from unittest.mock import AsyncMock, patch

        with patch("app.main.get_memvid_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search.side_effect = Exception("Search failed")
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/v1/chat",
                json={"message": "Test question", "stream": False},
            )
            # Should still succeed with empty context
            assert response.status_code == 200


class TestAssessFitEndpoint:
    """Tests for fit assessment endpoint."""

    def test_assess_fit_success(self, client):
        """Test successful fit assessment."""
        from unittest.mock import AsyncMock, patch
        from app.openrouter_client import LLMResponse

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

        with patch("app.main.get_memvid_client") as mock_get_client, \
             patch("app.main.get_openrouter_client") as mock_get_or_client:

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

    def test_assess_fit_memvid_unavailable(self, client):
        """Test handling when memvid is unavailable."""
        from unittest.mock import AsyncMock, patch

        with patch("app.main.get_memvid_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Memvid connection failed")

            response = client.post(
                "/api/v1/assess-fit",
                json={
                    "job_description": "Senior Engineer role requiring Python, Kubernetes, and cloud infrastructure experience."
                },
            )

            # Should return error
            assert response.status_code in [500, 503]

    # TODO: Add test for LLM timeout once exception handling is implemented
    # def test_assess_fit_llm_timeout(self, client):

    def test_assess_fit_malformed_llm_response(self, client):
        """Test handling when LLM returns malformed response."""
        from unittest.mock import AsyncMock, patch
        from app.openrouter_client import LLMResponse

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

        with patch("app.main.get_memvid_client") as mock_get_client, \
             patch("app.main.get_openrouter_client") as mock_get_or_client:

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
        from unittest.mock import AsyncMock, patch
        from app.openrouter_client import LLMResponse

        mock_search_response = AsyncMock()
        mock_search_response.hits = []  # No hits
        mock_search_response.total_hits = 0

        mock_llm_response = LLMResponse(
            content="""VERDICT: ⭐⭐ Limited information

KEY MATCHES:
- None available

GAPS:
- Insufficient profile data to assess fit

RECOMMENDATION: Unable to properly assess fit due to lack of context.""",
            tokens_used=100,
        )

        with patch("app.main.get_memvid_client") as mock_get_client, \
             patch("app.main.get_openrouter_client") as mock_get_or_client:

            mock_memvid = AsyncMock()
            mock_memvid.search.return_value = mock_search_response
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

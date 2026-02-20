"""E2E quality acceptance: validates all PRD criteria via mock LLM.

Tests that the API exposes complete, well-structured data through its
endpoints -- profile fields, health status, chat responses, and
suggested questions -- using the existing mock infrastructure.
"""

from collections.abc import AsyncIterator, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.session_store import reset_session_store

# Mock profile with all required PRD fields
MOCK_PROFILE = {
    "name": "Test User",
    "title": "Senior Platform Engineer",
    "email": "test@example.com",
    "linkedin": "https://linkedin.com/in/test",
    "location": "Portland, OR",
    "status": "Available",
    "suggested_questions": [
        "What experience do they have?",
        "Tell me about their skills",
        "What projects have they worked on?",
    ],
    "tags": ["engineering", "platform"],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Senior Platform Engineer",
            "period": "2020-2023",
            "highlights": ["Built CI/CD pipeline", "Led team of 5"],
            "ai_context": {
                "situation": "Legacy deployment process",
                "approach": "Incremental migration to Kubernetes",
                "technical_work": "Helm charts, ArgoCD, GitHub Actions",
                "lessons_learned": "Start with non-critical services",
            },
        }
    ],
    "skills": {
        "strong": ["Python", "Kubernetes"],
        "moderate": ["React", "TypeScript"],
        "gaps": ["Mobile development"],
    },
    "fit_assessment_examples": [
        {
            "title": "Strong Fit Example",
            "fit_level": "strong",
            "role": "Senior Engineer",
            "job_description": "Senior Engineer position requiring Python and K8s...",
            "verdict": "Strong fit",
            "key_matches": "Python expertise, Kubernetes experience",
            "gaps": "Mobile experience",
            "recommendation": "Recommended for interview",
        }
    ],
}


@pytest.fixture
def mock_memvid_ask() -> Generator[AsyncMock, None, None]:
    """Mock memvid client ask method."""
    with patch("app.main.get_memvid_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.ask.return_value = {
            "answer": "The candidate has experience with Python, Kubernetes, and platform engineering.",
            "evidence": [
                {
                    "title": "Professional Experience",
                    "score": 0.85,
                    "snippet": "Built CI/CD pipeline and led a team of 5",
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
def mock_openrouter() -> Generator[AsyncMock, None, None]:
    """Mock OpenRouter client."""
    from ai_resume_api.openrouter_client import LLMResponse

    with patch("app.main.get_openrouter_client") as mock_get_or:
        mock_or = AsyncMock()
        mock_or.chat.return_value = LLMResponse(
            content="The candidate has 3 years of platform engineering experience at Acme Corp.",
            tokens_used=50,
            finish_reason="stop",
        )

        async def mock_chat_stream(*args: Any, **kwargs: Any) -> AsyncIterator[Any]:
            chunks = ["The ", "candidate ", "has ", "experience."]
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
def mock_settings_direct() -> Generator[AsyncMock, None, None]:
    """Patch app.main.settings directly to control profile loading.

    The profile endpoint uses the module-level `settings` object (not
    get_settings()), so we must patch it directly rather than patching
    get_settings().
    """
    with patch("app.main.settings") as mock_settings:
        mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
        mock_settings.load_profile.return_value = MOCK_PROFILE
        mock_settings.get_system_prompt_from_profile.return_value = "You are an AI assistant."
        mock_settings.max_history_messages = 10
        mock_settings.llm_model = "anthropic/claude-3.5-sonnet"
        mock_settings.rate_limit_per_minute = 1000
        mock_settings.mock_memvid_client = False
        yield mock_settings


@pytest.fixture
def client(
    mock_settings_direct: Any, mock_memvid_ask: Any, mock_openrouter: Any
) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    reset_session_store()
    with TestClient(app) as c:
        yield c
    reset_session_store()


@pytest.mark.e2e
class TestE2EQualityAcceptance:
    """End-to-end quality acceptance tests validating PRD criteria."""

    def test_profile_returns_all_required_fields(self, client: TestClient) -> None:
        """GET /api/v1/profile returns complete profile with all fields."""
        response = client.get("/api/v1/profile")
        assert response.status_code == 200
        data = response.json()
        required = [
            "name",
            "title",
            "experience",
            "skills",
            "fit_assessment_examples",
            "suggested_questions",
        ]
        for field in required:
            assert field in data, f"Missing required field: {field}"

    def test_profile_experience_has_ai_context(self, client: TestClient) -> None:
        """Each experience entry includes ai_context for rich chat responses."""
        response = client.get("/api/v1/profile")
        data = response.json()
        for exp in data["experience"]:
            assert "ai_context" in exp, f"Missing ai_context in experience: {exp.get('company')}"
            ctx = exp["ai_context"]
            for key in ("situation", "approach", "technical_work", "lessons_learned"):
                assert key in ctx, f"Missing ai_context.{key}"

    def test_health_reports_service_status(self, client: TestClient) -> None:
        """GET /api/v1/health returns memvid_connected status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "memvid_connected" in data
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")

    def test_chat_endpoint_returns_response(self, client: TestClient) -> None:
        """POST /api/v1/chat returns a chat response."""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "What experience does the candidate have?",
                "session_id": None,
                "stream": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "session_id" in data
        assert len(data["message"]) > 0

    def test_suggested_questions_available(self, client: TestClient) -> None:
        """Profile includes suggested questions for the UI."""
        response = client.get("/api/v1/profile")
        data = response.json()
        questions = data.get("suggested_questions", [])
        assert isinstance(questions, list)
        assert len(questions) > 0, "Profile should include at least one suggested question"

    def test_skills_categorization(self, client: TestClient) -> None:
        """Profile skills are categorized into strong/moderate/gaps."""
        response = client.get("/api/v1/profile")
        data = response.json()
        skills = data.get("skills", {})
        assert "strong" in skills, "Skills missing 'strong' category"
        assert "moderate" in skills, "Skills missing 'moderate' category"
        assert "gaps" in skills, "Skills missing 'gaps' category"

    def test_fit_assessment_examples_present(self, client: TestClient) -> None:
        """Profile includes pre-analyzed fit assessment examples."""
        response = client.get("/api/v1/profile")
        data = response.json()
        examples = data.get("fit_assessment_examples", [])
        assert isinstance(examples, list)
        assert len(examples) > 0, "Profile should include at least one fit assessment example"
        for ex in examples:
            assert "verdict" in ex, "Fit example missing verdict"
            assert "key_matches" in ex, "Fit example missing key_matches"
            assert "gaps" in ex, "Fit example missing gaps"

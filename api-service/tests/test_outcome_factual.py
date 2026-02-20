"""Outcome tests for factual accuracy of chat responses.

Tests that the chat endpoint returns responses grounded in resume data,
does not add facts beyond the provided context, and that output guardrails
catch any leaked internal structure.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from ai_resume_api.guardrails import check_output, filter_output
from ai_resume_api.openrouter_client import LLMResponse
from app.main import app
from app.session_store import reset_session_store

# Mock profile with controlled, verifiable facts
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
    "fit_assessment_examples": [],
}

# Context that memvid would return -- tightly scoped facts
MOCK_MEMVID_CONTEXT = (
    "The candidate worked at Acme Corp as a Senior Platform Engineer from 2020-2023. "
    "They built a CI/CD pipeline and led a team of 5 engineers. "
    "Technical stack included Helm charts, ArgoCD, and GitHub Actions."
)


class TestFactualGrounding:
    """Verify that responses are grounded in provided resume context."""

    def test_response_contains_only_resume_facts(self) -> None:
        """LLM response that sticks to resume facts passes through unchanged."""
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI resume assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "test-model"
            mock_settings.rate_limit_per_minute = 1000

            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": MOCK_MEMVID_CONTEXT,
                "evidence": [
                    {
                        "title": "Experience",
                        "score": 0.9,
                        "snippet": MOCK_MEMVID_CONTEXT,
                        "tags": ["engineering"],
                    }
                ],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.0,
                    "reranking_ms": 1.0,
                    "total_ms": 3.0,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # LLM returns response grounded only in resume facts
            factual_response = (
                "The candidate worked at Acme Corp as a Senior Platform Engineer "
                "from 2020 to 2023. They built a CI/CD pipeline using Helm charts, "
                "ArgoCD, and GitHub Actions, and led a team of 5 engineers."
            )
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=factual_response,
                tokens_used=60,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "What experience do they have?", "stream": False},
                )
                assert response.status_code == 200
                data = response.json()

                # Response should pass through check_output unchanged
                msg = data["message"]
                assert "Acme Corp" in msg
                assert "CI/CD" in msg
                assert "5 engineers" in msg or "team of 5" in msg

        reset_session_store()

    def test_response_does_not_add_fabricated_company(self) -> None:
        """Verify check_output allows clean text and the endpoint delivers it."""
        # If the LLM fabricates a company not in the context, the response
        # still arrives (check_output only filters internal structure leakage,
        # not hallucinated facts -- that is the LLM's job via system prompt).
        # This test documents that contract: factual grounding relies on
        # the system prompt + context window, not on output filters.

        clean_response = "The candidate worked at Acme Corp as a Senior Platform Engineer."
        result = filter_output(clean_response)
        assert not result.was_filtered
        assert result.filtered_response == clean_response

    def test_check_output_passes_clean_factual_text(self) -> None:
        """check_output returns the original text when no internal structure is leaked."""
        text = (
            "The candidate has strong skills in Python and Kubernetes. "
            "They worked at Acme Corp from 2020 to 2023."
        )
        safe = check_output(text)
        assert safe == text

    def test_filter_output_catches_frame_references(self) -> None:
        """filter_output strips responses that leak frame/chunk internals."""
        leaked = (
            "Based on **Frame 3** the candidate has Python experience. "
            "Frame 7: They also know Kubernetes."
        )
        result = filter_output(leaked)
        assert result.was_filtered
        assert "Frame" not in result.filtered_response
        assert "rephrase" in result.filtered_response.lower()

    def test_filter_output_catches_context_header_leakage(self) -> None:
        """filter_output strips responses that echo context headers."""
        leaked = "CONTEXT FROM RESUME:\nThe candidate has 10 years of experience."
        result = filter_output(leaked)
        assert result.was_filtered

    def test_filter_output_catches_system_prompt_leakage(self) -> None:
        """filter_output strips responses that reveal system prompt content."""
        leaked = "System Message: You are an AI resume assistant. Now answering your question."
        result = filter_output(leaked)
        assert result.was_filtered

    def test_chat_applies_output_guardrail_to_llm_response(self) -> None:
        """End-to-end: leaked internal structure in LLM output is replaced."""
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI resume assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "test-model"
            mock_settings.rate_limit_per_minute = 1000

            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": MOCK_MEMVID_CONTEXT,
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 1,
                    "retrieval_ms": 2.0,
                    "reranking_ms": 1.0,
                    "total_ms": 3.0,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # LLM leaks internal structure
            leaked_response = (
                "According to **Frame 3**, the candidate has Python experience. "
                "chunk #7 mentions Kubernetes."
            )
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=leaked_response,
                tokens_used=40,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "What skills?", "stream": False},
                )
                assert response.status_code == 200
                msg = response.json()["message"]

                # The leaked frame references should be stripped
                assert "Frame 3" not in msg
                assert "chunk #7" not in msg
                # Replacement message should be present
                assert "rephrase" in msg.lower()

        reset_session_store()

    def test_no_results_returns_honest_no_information_message(self) -> None:
        """When memvid returns 0 results, the endpoint says so honestly."""
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.get_system_prompt_from_profile = lambda: "You are an AI resume assistant."
            mock_settings.max_history_messages = 10
            mock_settings.llm_model = "test-model"
            mock_settings.rate_limit_per_minute = 1000

            mock_memvid = AsyncMock()
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
            mock_get_memvid.return_value = mock_memvid

            mock_or = AsyncMock()
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "message": "What is their favorite color?",
                        "stream": False,
                    },
                )
                assert response.status_code == 200
                data = response.json()

                # Should acknowledge lack of information
                msg = data["message"].lower()
                assert "couldn't find" in msg or "not in the resume" in msg or "isn't in" in msg
                assert data["chunks_retrieved"] == 0
                # LLM should NOT have been called
                mock_or.chat.assert_not_called()

        reset_session_store()

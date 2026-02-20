"""Outcome tests for out-of-scope query refusal.

Tests that the chat endpoint refuses queries about topics not covered
by the resume, returns uncertainty markers, and does not fabricate
compensating details.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from ai_resume_api.guardrails import check_input, check_output, filter_output
from ai_resume_api.openrouter_client import LLMResponse
from app.main import app
from app.session_store import reset_session_store

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
    "tags": ["engineering"],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Senior Platform Engineer",
            "period": "2020-2023",
            "highlights": ["Built CI/CD pipeline"],
            "ai_context": {
                "situation": "Legacy deployment",
                "approach": "Kubernetes migration",
                "technical_work": "Helm, ArgoCD",
                "lessons_learned": "Incremental approach",
            },
        }
    ],
    "skills": {
        "strong": ["Python", "Kubernetes"],
        "moderate": ["React"],
        "gaps": ["Mobile development"],
    },
    "fit_assessment_examples": [],
}

MOCK_MEMVID_CONTEXT = (
    "The candidate worked at Acme Corp as a Senior Platform Engineer "
    "building CI/CD pipelines with Kubernetes."
)


# Uncertainty markers that a well-behaved LLM should use when information is missing
UNCERTAINTY_MARKERS = [
    "i don't have",
    "not mentioned",
    "no information",
    "isn't covered",
    "not available",
    "not included",
    "i couldn't find",
    "resume doesn't",
    "resume does not",
    "unable to find",
    "not in the resume",
    "couldn't find",
]


def _has_uncertainty_marker(text: str) -> bool:
    """Check if text contains at least one uncertainty marker."""
    text_lower = text.lower()
    return any(marker in text_lower for marker in UNCERTAINTY_MARKERS)


class TestOutOfScopeRefusal:
    """Verify that the system refuses to answer out-of-scope questions."""

    def test_salary_question_gets_uncertainty_response(self) -> None:
        """Asking about salary should produce an uncertainty response (no resume data)."""
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

            # memvid returns no results for salary (not in resume)
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
                    json={"message": "What is their salary?", "stream": False},
                )
                assert response.status_code == 200
                msg = response.json()["message"]

                # Should acknowledge no information, not fabricate a salary
                assert _has_uncertainty_marker(msg) or "couldn't find" in msg.lower()
                # Should NOT contain a dollar amount or fabricated salary
                assert "$" not in msg
                # LLM should not have been called (0 results = early return)
                mock_or.chat.assert_not_called()

        reset_session_store()

    def test_fabricated_company_gets_no_fabricated_details(self) -> None:
        """Asking about a company not in the resume should not produce fabricated details."""
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

            # memvid returns 0 results for a company not in the resume
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
                        "message": "Tell me about their time at Globex Industries",
                        "stream": False,
                    },
                )
                assert response.status_code == 200
                msg = response.json()["message"]

                # Should not fabricate details about Globex Industries
                assert "Globex" not in msg
                assert response.json()["chunks_retrieved"] == 0

        reset_session_store()

    def test_unclaimed_skill_not_fabricated_when_no_context(self) -> None:
        """Asking about a skill not in the resume returns no-info when memvid has nothing."""
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
                        "message": "What is their experience with quantum computing?",
                        "stream": False,
                    },
                )
                assert response.status_code == 200
                msg = response.json()["message"]
                assert _has_uncertainty_marker(msg) or "couldn't find" in msg.lower()

        reset_session_store()

    def test_llm_uncertainty_response_passes_output_guardrail(self) -> None:
        """An LLM that properly uses uncertainty markers passes check_output."""
        uncertain = (
            "I don't have information about the candidate's salary expectations. "
            "The resume does not include compensation details."
        )
        safe = check_output(uncertain)
        assert safe == uncertain

    def test_llm_fabrication_with_frame_ref_is_filtered(self) -> None:
        """If LLM fabricates an answer AND leaks frame refs, output is filtered."""
        fabricated = "According to Frame 5, the candidate earned $150,000 at Globex Industries."
        result = filter_output(fabricated)
        assert result.was_filtered
        assert "Frame 5" not in result.filtered_response
        assert "$150,000" not in result.filtered_response


class TestCheckInputForOutOfScope:
    """Verify check_input does not block legitimate out-of-scope questions.

    check_input is for injection detection, not topic filtering.
    Out-of-scope questions should pass check_input but get handled
    by the 0-results early-return path.
    """

    def test_salary_question_passes_input_guardrail(self) -> None:
        """Salary questions are not injection attempts."""
        is_safe, _ = check_input("What is their salary?")
        assert is_safe

    def test_company_question_passes_input_guardrail(self) -> None:
        """Questions about specific companies are not injection attempts."""
        is_safe, _ = check_input("Tell me about their time at Globex Industries")
        assert is_safe

    def test_skill_question_passes_input_guardrail(self) -> None:
        """Questions about skills are not injection attempts."""
        is_safe, _ = check_input("Do they know quantum computing?")
        assert is_safe

    def test_personal_question_passes_input_guardrail(self) -> None:
        """Personal questions are not injections (handled by LLM/context)."""
        is_safe, _ = check_input("What are their hobbies?")
        assert is_safe


class TestNoFabricatedCompensation:
    """Verify LLM does not fabricate compensating details for missing info."""

    def test_mock_llm_with_honest_refusal(self) -> None:
        """When LLM honestly refuses, the response reaches the user."""
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

            # memvid returns some context but not about the asked topic
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "The candidate is a Senior Platform Engineer at Acme Corp.",
                "evidence": [
                    {
                        "title": "Experience",
                        "score": 0.3,
                        "snippet": "Senior Platform Engineer at Acme Corp",
                        "tags": [],
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

            # LLM properly refuses to answer about unrelated topic
            honest_refusal = (
                "The resume does not mention anything about the candidate's "
                "salary history. I can only share information that's documented "
                "in their professional background."
            )
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=honest_refusal,
                tokens_used=30,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={"message": "What was their salary?", "stream": False},
                )
                assert response.status_code == 200
                msg = response.json()["message"]
                # The honest refusal should pass through unchanged
                assert "does not mention" in msg
                assert "$" not in msg

        reset_session_store()

    def test_no_results_path_does_not_call_llm(self) -> None:
        """When memvid returns 0 chunks, the LLM is never called."""
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
                        "message": "What is the meaning of life?",
                        "stream": False,
                    },
                )
                assert response.status_code == 200

                # LLM should never have been called
                mock_or.chat.assert_not_called()

                # Response should acknowledge no info found
                msg = response.json()["message"].lower()
                assert "couldn't find" in msg or "not in" in msg

        reset_session_store()

"""Outcome tests for honesty about candidate limitations.

Tests that the system identifies and honestly reports skill gaps,
does not fabricate compensating experience, and that gap-related
questions produce truthful responses.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from ai_resume_api.guardrails import check_output, filter_output
from ai_resume_api.openrouter_client import LLMResponse
from app.main import app
from app.session_store import reset_session_store

# Profile with explicit skill gaps for honesty testing
MOCK_PROFILE = {
    "name": "Test User",
    "title": "Senior Platform Engineer",
    "email": "test@example.com",
    "linkedin": "https://linkedin.com/in/test",
    "location": "Portland, OR",
    "status": "Available",
    "suggested_questions": [
        "What are their strengths?",
        "What gaps do they have?",
    ],
    "tags": ["engineering"],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Senior Platform Engineer",
            "period": "2020-2023",
            "highlights": ["Built CI/CD pipeline", "Led team of 5"],
            "ai_context": {
                "situation": "Legacy deployment process",
                "approach": "Kubernetes migration",
                "technical_work": "Helm charts, ArgoCD, GitHub Actions",
                "lessons_learned": "Start with non-critical services",
            },
        }
    ],
    "skills": {
        "strong": ["Python", "Kubernetes"],
        "moderate": ["React", "TypeScript"],
        "gaps": ["Mobile development", "iOS", "Android", "Flutter"],
    },
    "fit_assessment_examples": [],
}


class TestGapAcknowledgment:
    """Verify that questions about known skill gaps get honest answers."""

    def test_gap_skill_acknowledged_honestly(self) -> None:
        """LLM that acknowledges a skill gap passes through unchanged."""
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

            # memvid returns the gaps section
            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": (
                    "Skills gaps: Mobile development, iOS, Android, Flutter. "
                    "The candidate lists mobile development as a gap in their skills."
                ),
                "evidence": [
                    {
                        "title": "Skills Assessment",
                        "score": 0.88,
                        "snippet": "Gaps: Mobile development, iOS, Android",
                        "tags": ["skills"],
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

            # LLM honestly acknowledges the gap
            honest_response = (
                "Mobile development is listed as a gap in the candidate's skill set. "
                "They do not have experience with iOS, Android, or Flutter. "
                "Their expertise is focused on backend platform engineering "
                "with Python and Kubernetes."
            )
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=honest_response,
                tokens_used=45,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "message": "Do they have mobile development experience?",
                        "stream": False,
                    },
                )
                assert response.status_code == 200
                msg = response.json()["message"]

                # Should acknowledge the gap honestly
                assert "gap" in msg.lower() or "not" in msg.lower()
                assert "mobile" in msg.lower()

        reset_session_store()

    def test_gap_response_does_not_fabricate_experience(self) -> None:
        """LLM should not fabricate mobile experience to compensate for a gap."""
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
                "answer": (
                    "The candidate's skill gaps include: Mobile development. "
                    "Strong skills: Python, Kubernetes."
                ),
                "evidence": [
                    {
                        "title": "Skills",
                        "score": 0.85,
                        "snippet": "Gaps: Mobile development",
                        "tags": ["skills"],
                    }
                ],
                "stats": {
                    "candidates_retrieved": 3,
                    "results_returned": 1,
                    "retrieval_ms": 1.5,
                    "reranking_ms": 0.8,
                    "total_ms": 2.3,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # LLM correctly reports gap without fabrication
            gap_response = (
                "The candidate identifies mobile development as a skill gap. "
                "They have not worked with iOS, Android, or cross-platform frameworks. "
                "Their background is in server-side platform engineering."
            )
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=gap_response,
                tokens_used=40,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "message": "Can they build an iOS app?",
                        "stream": False,
                    },
                )
                assert response.status_code == 200
                msg = response.json()["message"]

                # Should NOT contain fabricated mobile experience
                assert "built" not in msg.lower() or "mobile" not in msg.lower()
                # Should acknowledge the gap
                assert "gap" in msg.lower() or "not" in msg.lower()

        reset_session_store()

    def test_honest_gap_passes_output_guardrail(self) -> None:
        """Honest gap acknowledgment should pass check_output unchanged."""
        honest = (
            "The candidate lists mobile development as a skill gap. "
            "They do not have iOS or Android experience."
        )
        safe = check_output(honest)
        assert safe == honest

    def test_gap_with_internal_leak_is_filtered(self) -> None:
        """Gap response that leaks internals is still filtered."""
        leaked = (
            "According to chunk #2, the candidate lists mobile development as a gap. "
            "CONTEXT FROM RESUME: gaps include iOS and Android."
        )
        result = filter_output(leaked)
        assert result.was_filtered
        assert "chunk #2" not in result.filtered_response
        assert "CONTEXT FROM RESUME" not in result.filtered_response


class TestHonestyInFitAssessment:
    """Verify that fit assessment is honest about gaps."""

    def test_fit_assessment_reports_gaps(self) -> None:
        """Fit assessment should report gaps from the resume context."""
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000

            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": (
                    "Skills: Strong in Python and Kubernetes. "
                    "Gaps: Mobile development, iOS, Android. "
                    "Experience: Platform engineering at Acme Corp."
                ),
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 5,
                    "results_returned": 3,
                    "retrieval_ms": 3.0,
                    "reranking_ms": 1.5,
                    "total_ms": 4.5,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # LLM produces an honest fit assessment
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=(
                    "VERDICT: ⭐⭐ Weak fit (30% match)\n\n"
                    "KEY MATCHES:\n"
                    "- Python experience\n\n"
                    "GAPS:\n"
                    "- No mobile development experience (iOS, Android)\n"
                    "- No Flutter or React Native experience\n\n"
                    "RECOMMENDATION: Not recommended for this mobile engineering role. "
                    "The candidate's strengths are in platform engineering, not mobile."
                ),
                tokens_used=80,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": (
                            "Senior Mobile Engineer - iOS and Android development "
                            "with Flutter. Must have 5+ years mobile experience "
                            "and published apps on App Store and Google Play."
                        )
                    },
                )
                assert response.status_code == 200
                data = response.json()

                # Should report gaps honestly
                assert len(data["gaps"]) > 0
                gap_text = " ".join(data["gaps"]).lower()
                assert "mobile" in gap_text or "ios" in gap_text

                # Verdict should not overstate the fit
                assert "Weak" in data["verdict"] or "1" in data["verdict"] or "2" in data["verdict"]

        reset_session_store()

    def test_fit_assessment_does_not_inflate_match(self) -> None:
        """Fit assessment should not inflate matches for skills the candidate lacks."""
        reset_session_store()

        with (
            patch("app.main.get_memvid_client") as mock_get_memvid,
            patch("app.main.get_openrouter_client") as mock_get_or,
            patch("app.main.settings") as mock_settings,
        ):
            mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
            mock_settings.load_profile = lambda: MOCK_PROFILE
            mock_settings.rate_limit_per_minute = 1000

            mock_memvid = AsyncMock()
            mock_memvid.ask.return_value = {
                "answer": "The candidate is a platform engineer with Python expertise.",
                "evidence": [],
                "stats": {
                    "candidates_retrieved": 3,
                    "results_returned": 1,
                    "retrieval_ms": 2.0,
                    "reranking_ms": 1.0,
                    "total_ms": 3.0,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # LLM correctly identifies a domain mismatch
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=(
                    "VERDICT: ⭐ Fundamentally mismatched\n\n"
                    "KEY MATCHES:\n"
                    "- General engineering background\n\n"
                    "GAPS:\n"
                    "- No culinary experience\n"
                    "- Different professional domain entirely\n\n"
                    "RECOMMENDATION: The candidate is a software engineer, not a chef. "
                    "This is a fundamental domain mismatch."
                ),
                tokens_used=60,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/assess-fit",
                    json={
                        "job_description": (
                            "Head Chef position at a Michelin-star restaurant. "
                            "Must have 10+ years of culinary experience, formal "
                            "culinary education, and experience managing a kitchen "
                            "brigade of 20+ cooks."
                        )
                    },
                )
                assert response.status_code == 200
                data = response.json()

                # Should correctly identify the mismatch
                verdict_lower = data["verdict"].lower()
                assert "mismatch" in verdict_lower or "1" in data["verdict"]
                assert len(data["gaps"]) > 0

        reset_session_store()


class TestModerateSkillHonesty:
    """Verify moderate skills are represented honestly, not inflated."""

    def test_moderate_skill_not_presented_as_expert(self) -> None:
        """When asked about a moderate skill, the response should not claim expertise."""
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
                "answer": (
                    "Skills: React is listed as a moderate skill. "
                    "The candidate has some experience but it is not a primary strength."
                ),
                "evidence": [
                    {
                        "title": "Skills",
                        "score": 0.75,
                        "snippet": "Moderate: React, TypeScript",
                        "tags": ["skills"],
                    }
                ],
                "stats": {
                    "candidates_retrieved": 3,
                    "results_returned": 1,
                    "retrieval_ms": 1.5,
                    "reranking_ms": 0.8,
                    "total_ms": 2.3,
                },
            }
            mock_get_memvid.return_value = mock_memvid

            # LLM honestly describes moderate proficiency
            mock_or = AsyncMock()
            mock_or.chat.return_value = LLMResponse(
                content=(
                    "React is listed as a moderate skill for the candidate. "
                    "They have some experience with it but it is not one of "
                    "their primary strengths. Their strongest skills are Python "
                    "and Kubernetes."
                ),
                tokens_used=35,
                finish_reason="stop",
            )
            mock_get_or.return_value = mock_or

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "message": "How good are they at React?",
                        "stream": False,
                    },
                )
                assert response.status_code == 200
                msg = response.json()["message"]

                # Should describe as moderate, not expert-level
                assert "moderate" in msg.lower() or "some experience" in msg.lower()
                # Should not claim deep proficiency
                assert "expert" not in msg.lower()
                assert "deep proficiency" not in msg.lower()

        reset_session_store()

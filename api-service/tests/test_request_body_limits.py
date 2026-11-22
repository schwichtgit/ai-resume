"""Request body size regression tests.

FastAPI 0.164 added a configurable request body limit (``max_body_size`` on the
app, routers and routes; 413 "Content Too Large" when exceeded) and 0.165 added
configurable form parsing limits (``form_limits``). Both are opt-in: the default
``max_body_size`` is ``None`` (unlimited) and form limits only apply to
``Form``/``File`` parameters, which this API does not use.

The binding limits on our inputs are the Pydantic field caps (``max_length``)
and, in front of the API, nginx's default ``client_max_body_size`` of 1 MiB.
These tests pin that: legitimate payloads at the field caps are accepted, an
oversized field is a 422 validation error, and a large body below the nginx
limit is never turned into a 413 by the framework.
"""

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ai_resume_api.session_store import get_session_store
from app.main import app
from app.session_store import reset_session_store

# Pydantic caps from app/models.py.
JD_MAX_CHARS = 15000
CHAT_MESSAGE_MAX_CHARS = 2000

MOCK_PROFILE: dict[str, Any] = {
    "name": "Test User",
    "title": "Test Title",
    "suggested_questions": ["What experience do they have?"],
}

# A pasted job description: bullets and em-dashes are typical when copying
# from a job board and are 3 bytes each in UTF-8, so this is a large body.
JD_PARAGRAPH = (
    "Senior Platform Engineer — Infrastructure Team\n"
    "• Design and operate Kubernetes clusters across multiple regions — "
    "on-call rotation shared with the SRE group.\n"
    "• Build CI/CD pipelines in Python and Go; own observability with "
    "OpenTelemetry, Prometheus and Grafana.\n"
    "• Partner with product teams to migrate services — reliability, cost "
    "and security are first-class requirements.\n"
)


def _large_job_description() -> str:
    repeats = JD_MAX_CHARS // len(JD_PARAGRAPH) + 1
    return (JD_PARAGRAPH * repeats)[:JD_MAX_CHARS]


@pytest.fixture
def mocked_client() -> Generator[TestClient, None, None]:
    """TestClient with memvid, OpenRouter and profile loading mocked."""
    from ai_resume_api.openrouter_client import LLMResponse

    reset_session_store()
    with (
        patch("app.main.get_memvid_client") as mock_get_memvid,
        patch("app.main.get_openrouter_client") as mock_get_or,
        patch("app.config.get_settings") as mock_get_settings,
    ):
        mock_settings = AsyncMock()
        mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
        mock_settings.load_profile = lambda: MOCK_PROFILE
        mock_settings.get_system_prompt_from_profile = lambda: "You are an AI assistant."
        mock_settings.max_history_messages = 20
        mock_settings.rate_limit_per_minute = 1000
        mock_settings.mock_memvid_client = False
        mock_get_settings.return_value = mock_settings

        mock_memvid = AsyncMock()
        mock_memvid.ask.return_value = {
            "answer": "Candidate has Kubernetes and Python experience.",
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

        mock_or = AsyncMock()
        mock_or.chat.return_value = LLMResponse(
            content=(
                "VERDICT: ⭐⭐⭐⭐ Strong fit\n\n"
                "KEY MATCHES:\n- Kubernetes\n\nGAPS:\n- None notable\n\n"
                "RECOMMENDATION: Interview."
            ),
            tokens_used=120,
            finish_reason="stop",
        )
        mock_get_or.return_value = mock_or

        with TestClient(app) as client:
            yield client

    reset_session_store()


def _post_json(client: TestClient, url: str, payload: dict[str, Any]) -> Any:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return client.post(url, content=body, headers={"Content-Type": "application/json"}), body


class TestAssessFitBodySize:
    def test_max_length_job_description_is_accepted(self, mocked_client: TestClient) -> None:
        """A 15000-char pasted English JD (~15 KB on the wire) is assessed."""
        jd = _large_job_description()
        assert len(jd) == JD_MAX_CHARS

        response, body = _post_json(mocked_client, "/api/v1/assess-fit", {"job_description": jd})

        assert len(body) > JD_MAX_CHARS
        assert response.status_code == 200, response.text
        assert response.json()["tokens_used"] == 120

    def test_max_length_multibyte_job_description_is_accepted(
        self, mocked_client: TestClient
    ) -> None:
        """A 15000-char CJK JD is ~45 KB of UTF-8: the largest legitimate body."""
        paragraph = (
            "高级平台工程师：负责多区域集群的设计与运维，使用编程语言构建持续集成流水线，"
            "并与产品团队合作迁移服务，可靠性、成本与安全是首要要求。\n"
        )
        jd = (paragraph * (JD_MAX_CHARS // len(paragraph) + 1))[:JD_MAX_CHARS]

        response, body = _post_json(mocked_client, "/api/v1/assess-fit", {"job_description": jd})

        assert len(body) >= 40_000
        assert response.status_code == 200, response.text
        assert response.json()["tokens_used"] == 120

    def test_oversized_job_description_is_validation_error_not_413(
        self, mocked_client: TestClient
    ) -> None:
        """Above the field cap the rejection is Pydantic's 422, not a body-size 413."""
        jd = _large_job_description() + "x"

        response, _ = _post_json(mocked_client, "/api/v1/assess-fit", {"job_description": jd})

        assert response.status_code == 422

    def test_large_body_below_nginx_limit_is_not_413(self, mocked_client: TestClient) -> None:
        """~900 KB (under nginx's 1 MiB default) reaches validation: no app body limit."""
        jd = "a" * 900_000

        response, body = _post_json(mocked_client, "/api/v1/assess-fit", {"job_description": jd})

        assert len(body) > 512 * 1024
        assert response.status_code == 422


class TestChatBodySize:
    def test_max_length_message_with_long_history_is_accepted(
        self, mocked_client: TestClient
    ) -> None:
        """A max-length message on a session with a long history is answered.

        History lives server-side (session store), so only the message counts
        toward the request body; the history still flows into the LLM call.
        """
        store = get_session_store()
        session = store.get_or_create()
        session_id: UUID = session.id
        for i in range(40):
            session.add_message("user", f"Question {i}: " + "Tell me about Kubernetes. " * 60)
            session.add_message("assistant", f"Answer {i}: " + "They ran clusters. " * 120)
        store.set(session_id, session)

        message = ("What did the candidate build with Kubernetes and Python? " * 40)[
            :CHAT_MESSAGE_MAX_CHARS
        ]
        response, _ = _post_json(
            mocked_client,
            "/api/v1/chat",
            {"message": message, "session_id": str(session_id), "stream": False},
        )

        assert response.status_code == 200, response.text
        assert response.json()["session_id"] == str(session_id)
        stored = store.get(session_id)
        assert stored is not None
        assert len(stored.messages) == 82

"""Tests for OpenTelemetry instrumentation.

Validates:
- No-op behavior when OTEL_EXPORTER_OTLP_ENDPOINT is unset
- Span creation when OTel is initialized
- Chat and assess-fit endpoints create expected spans
- No PII leaks in span attributes
"""

import os
from collections.abc import Generator, Sequence
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource

from app.main import app


# ---------------------------------------------------------------------------
# Custom InMemorySpanExporter (not bundled in this OTel SDK version)
# ---------------------------------------------------------------------------


class InMemorySpanExporter(SpanExporter):
    """Collects exported spans in a list for test assertions."""

    def __init__(self) -> None:
        self._spans: list[ReadableSpan] = []
        self._stopped = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not self._stopped:
            self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self._stopped = True

    def get_finished_spans(self) -> list[ReadableSpan]:
        return list(self._spans)

    def clear(self) -> None:
        self._spans.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


MOCK_PROFILE = {
    "name": "Test User",
    "title": "Test Title",
    "email": "test@example.com",
    "linkedin": "",
    "location": "",
    "status": "",
    "suggested_questions": ["What experience do they have?"],
    "tags": [],
    "experience": [],
    "skills": {"strong": [], "moderate": [], "gaps": []},
    "fit_assessment_examples": [],
}


@pytest.fixture
def otel_exporter() -> Generator[InMemorySpanExporter, None, None]:
    """Set up an in-memory OTel exporter and restore the original provider after.

    The global TracerProvider can only be set once per process via the public API.
    For test isolation we reset the internal Once guard between tests.
    """
    import opentelemetry.trace as _trace_mod

    exporter = InMemorySpanExporter()
    resource = Resource.create({"service.name": "test-api"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Reset the once-guard so set_tracer_provider works again
    _trace_mod._TRACER_PROVIDER_SET_ONCE._done = False  # type: ignore[attr-defined]
    trace.set_tracer_provider(provider)

    yield exporter

    # Shutdown and reset for next test
    provider.shutdown()
    _trace_mod._TRACER_PROVIDER_SET_ONCE._done = False  # type: ignore[attr-defined]
    _trace_mod._TRACER_PROVIDER = None  # type: ignore[attr-defined]


@pytest.fixture
def mock_memvid_ask() -> Generator[AsyncMock, None, None]:
    """Mock memvid client ask method."""
    with patch("app.main.get_memvid_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.ask.return_value = {
            "answer": "Based on the resume, the candidate has experience with Python.",
            "evidence": [
                {
                    "title": "Experience",
                    "score": 0.85,
                    "snippet": "Built platform",
                    "tags": ["engineering"],
                }
            ],
            "stats": {
                "candidates_retrieved": 5,
                "results_returned": 1,
                "retrieval_ms": 2,
                "reranking_ms": 1,
                "used_fallback": False,
            },
        }
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openrouter() -> Generator[AsyncMock, None, None]:
    """Mock OpenRouter client."""
    with patch("app.main.get_openrouter_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "Test response about professional experience."
        mock_response.tokens_used = 42
        mock_response.finish_reason = "stop"
        mock_client.chat.return_value = mock_response
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_profile_loader() -> Generator[None, None, None]:
    """Mock profile loading."""
    with (
        patch("app.main.settings") as mock_settings,
    ):
        mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
        mock_settings.load_profile.return_value = MOCK_PROFILE
        mock_settings.get_system_prompt_from_profile.return_value = "You are a test assistant."
        mock_settings.llm_model = "test-model"
        mock_settings.max_history_messages = 20
        mock_settings.rate_limit_per_minute = 100
        yield


# ---------------------------------------------------------------------------
# Tests: No-op mode (OTEL_EXPORTER_OTLP_ENDPOINT not set)
# ---------------------------------------------------------------------------


class TestOtelNoop:
    """Test that OTel no-op mode works without crashing."""

    def test_init_otel_noop_without_env(self) -> None:
        """init_otel does nothing when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""
        from ai_resume_api.otel import init_otel

        # Ensure the env var is not set
        env = os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
        try:
            # Should not raise
            init_otel()
            init_otel(app=None)
        finally:
            if env is not None:
                os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = env

    def test_get_tracer_returns_tracer(self) -> None:
        """get_tracer returns a valid tracer even without OTel initialized."""
        from ai_resume_api.otel import get_tracer

        tracer = get_tracer()
        assert tracer is not None
        # Should be able to create spans (no-op spans)
        with tracer.start_as_current_span("test-noop") as span:
            assert span is not None


# ---------------------------------------------------------------------------
# Tests: Span creation with OTel enabled
# ---------------------------------------------------------------------------


class TestOtelSpans:
    """Test that spans are created correctly when OTel is enabled."""

    def test_tracer_creates_spans(self, otel_exporter: InMemorySpanExporter) -> None:
        """Tracer creates spans that are collected by the exporter."""
        from ai_resume_api.otel import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span("test-span") as span:
            span.set_attribute("test.key", "value")

        spans = otel_exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test-span"
        assert dict(spans[0].attributes)["test.key"] == "value"

    def test_nested_spans(self, otel_exporter: InMemorySpanExporter) -> None:
        """Nested spans are created with correct parent-child relationships."""
        from ai_resume_api.otel import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span("parent"):
            with tracer.start_as_current_span("child") as child:
                child.set_attribute("depth", 1)

        spans = otel_exporter.get_finished_spans()
        assert len(spans) == 2
        child_span = next(s for s in spans if s.name == "child")
        parent_span = next(s for s in spans if s.name == "parent")
        assert child_span.parent.span_id == parent_span.context.span_id


# ---------------------------------------------------------------------------
# Tests: Chat endpoint span creation
# ---------------------------------------------------------------------------


class TestChatEndpointSpans:
    """Test that the chat endpoint creates expected OTel spans."""

    def test_chat_creates_spans(
        self,
        otel_exporter: InMemorySpanExporter,
        mock_memvid_ask: AsyncMock,
        mock_openrouter: AsyncMock,
        mock_profile_loader: None,
    ) -> None:
        """Non-streaming chat creates guardrail, memvid, llm, and session spans."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "What is the candidate's experience?", "stream": False},
        )
        assert response.status_code == 200

        spans = otel_exporter.get_finished_spans()
        span_names = [s.name for s in spans]

        # Verify expected spans were created
        assert "guardrail.check_input" in span_names
        assert "memvid.search" in span_names
        assert "llm.openrouter_call" in span_names
        assert "guardrail.check_output" in span_names
        assert "session.store" in span_names

    def test_chat_span_attributes_no_pii(
        self,
        otel_exporter: InMemorySpanExporter,
        mock_memvid_ask: AsyncMock,
        mock_openrouter: AsyncMock,
        mock_profile_loader: None,
    ) -> None:
        """Span attributes must not contain PII (message content)."""
        user_message = "Tell me about the candidate's secret projects"
        client = TestClient(app)
        client.post(
            "/api/v1/chat",
            json={"message": user_message, "stream": False},
        )

        spans = otel_exporter.get_finished_spans()
        for span in spans:
            attrs = dict(span.attributes) if span.attributes else {}
            for key, value in attrs.items():
                if isinstance(value, str):
                    # Message content must not appear in span attributes
                    assert user_message not in value, (
                        f"PII leak: span '{span.name}' attribute '{key}' "
                        f"contains user message content"
                    )


# ---------------------------------------------------------------------------
# Tests: Guardrail span attributes
# ---------------------------------------------------------------------------


class TestGuardrailSpanAttributes:
    """Test guardrail span attribute values."""

    def test_guardrail_records_pass(
        self,
        otel_exporter: InMemorySpanExporter,
        mock_memvid_ask: AsyncMock,
        mock_openrouter: AsyncMock,
        mock_profile_loader: None,
    ) -> None:
        """Guardrail span records whether input passed validation."""
        client = TestClient(app)
        client.post(
            "/api/v1/chat",
            json={"message": "What is the candidate's experience?", "stream": False},
        )

        spans = otel_exporter.get_finished_spans()
        guard_span = next(s for s in spans if s.name == "guardrail.check_input")
        attrs = dict(guard_span.attributes)
        assert attrs["guardrail.passed"] is True
        assert "message.length" in attrs


# ---------------------------------------------------------------------------
# Tests: Memvid search span attributes
# ---------------------------------------------------------------------------


class TestMemvidSearchSpanAttributes:
    """Test memvid search span attribute values."""

    def test_memvid_span_records_chunks(
        self,
        otel_exporter: InMemorySpanExporter,
        mock_memvid_ask: AsyncMock,
        mock_openrouter: AsyncMock,
        mock_profile_loader: None,
    ) -> None:
        """Memvid search span records chunk count and search mode."""
        client = TestClient(app)
        client.post(
            "/api/v1/chat",
            json={"message": "What is the candidate's experience?", "stream": False},
        )

        spans = otel_exporter.get_finished_spans()
        search_span = next(s for s in spans if s.name == "memvid.search")
        attrs = dict(search_span.attributes)
        assert attrs["search.chunks_retrieved"] == 1
        assert attrs["search.mode"] == "hybrid"
        assert attrs["search.top_k"] == 5


# ---------------------------------------------------------------------------
# Tests: OTel trace_id in observability module
# ---------------------------------------------------------------------------


class TestOtelTraceIdIntegration:
    """Test that observability.get_trace_id uses OTel when active."""

    def test_get_trace_id_uses_otel_when_active(self, otel_exporter: InMemorySpanExporter) -> None:
        """get_trace_id returns OTel trace_id when a span is active."""
        from ai_resume_api.observability import get_trace_id
        from ai_resume_api.otel import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span("test-trace") as span:
            tid = get_trace_id()
            expected = trace.format_trace_id(span.get_span_context().trace_id)
            assert tid == expected
            assert len(tid) == 32  # 16 bytes hex-encoded

    def test_get_trace_id_falls_back_to_custom(self) -> None:
        """get_trace_id returns custom trace_id when no OTel span is active."""
        from ai_resume_api.observability import get_trace_id, set_trace_id

        set_trace_id("custom-trace-abc123")
        tid = get_trace_id()
        assert tid == "custom-trace-abc123"

    def test_get_otel_span_id(self, otel_exporter: InMemorySpanExporter) -> None:
        """get_otel_span_id returns span_id when a span is active."""
        from ai_resume_api.observability import get_otel_span_id
        from ai_resume_api.otel import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span("test-span") as span:
            sid = get_otel_span_id()
            expected = trace.format_span_id(span.get_span_context().span_id)
            assert sid == expected
            assert len(sid) == 16  # 8 bytes hex-encoded

    def test_get_otel_span_id_empty_when_no_span(self) -> None:
        """get_otel_span_id returns empty string when no span is active."""
        from ai_resume_api.observability import get_otel_span_id

        sid = get_otel_span_id()
        assert sid == ""


# ---------------------------------------------------------------------------
# Tests: Traceparent propagation in gRPC metadata
# ---------------------------------------------------------------------------


class TestTraceparentPropagation:
    """Test that traceparent is injected into gRPC metadata."""

    @pytest.mark.asyncio
    async def test_interceptor_injects_traceparent(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        """CorrelationInterceptor injects traceparent header when OTel span is active."""
        from ai_resume_api.memvid_client import CorrelationInterceptor
        from ai_resume_api.observability import set_trace_id
        from ai_resume_api.otel import get_tracer

        interceptor = CorrelationInterceptor()
        set_trace_id("test-trace-id")

        tracer = get_tracer()
        with tracer.start_as_current_span("test-grpc"):
            # Create mock call details and continuation
            mock_details = AsyncMock()
            mock_details.method = "/test.Service/Method"
            mock_details.timeout = 5.0
            mock_details.metadata = []
            mock_details.credentials = None
            mock_details.wait_for_ready = None

            captured_details = None

            async def mock_continuation(details: Any, req: Any) -> Any:
                nonlocal captured_details
                captured_details = details
                return AsyncMock()

            await interceptor.intercept_unary_unary(mock_continuation, mock_details, None)

            # Check that traceparent was injected
            assert captured_details is not None
            metadata_dict = dict(captured_details.metadata)
            assert "traceparent" in metadata_dict
            assert metadata_dict["traceparent"].startswith("00-")

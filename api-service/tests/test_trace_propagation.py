"""Tests for W3C trace context propagation across service boundaries.

Validates the end-to-end trace context chain:
  Browser (traceparent header)
    -> nginx (proxy_set_header traceparent)
    -> FastAPI (OTel auto-extraction via FastAPIInstrumentor)
    -> gRPC interceptor (inject traceparent into metadata)
    -> Rust memvid (extract traceparent from gRPC metadata)

Also verifies:
- SSE stats events include trace_id
- Fallback X-Trace-ID works when OTel is disabled
- OTel trace_id takes precedence over custom trace_id
"""

import json
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
# Custom InMemorySpanExporter
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
# Shared mocks
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def otel_exporter() -> Generator[InMemorySpanExporter, None, None]:
    """Set up an in-memory OTel exporter and restore the original provider after."""
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
    with patch("app.main.settings") as mock_settings:
        mock_settings.load_profile_from_memvid = AsyncMock(return_value=MOCK_PROFILE)
        mock_settings.load_profile.return_value = MOCK_PROFILE
        mock_settings.get_system_prompt_from_profile.return_value = "You are a test assistant."
        mock_settings.llm_model = "test-model"
        mock_settings.max_history_messages = 20
        mock_settings.rate_limit_per_minute = 100
        yield


# ---------------------------------------------------------------------------
# Tests: Incoming traceparent extraction
# ---------------------------------------------------------------------------


class TestTraceparentExtraction:
    """Verify traceparent header from browser is extracted into OTel context."""

    def test_w3c_propagator_extracts_traceparent(self) -> None:
        """W3C TraceContextTextMapPropagator extracts traceparent into OTel context.

        This verifies the core mechanism that FastAPIInstrumentor uses
        to join an incoming trace. The propagator is the default in the
        OTel Python SDK and is what makes trace continuity work.
        """
        from opentelemetry.propagate import extract

        expected_trace_id = "0af7651916cd43dd8448eb211c80319c"
        parent_span_id = "b7ad6b7169203331"
        traceparent = f"00-{expected_trace_id}-{parent_span_id}-01"

        # Simulate the extraction that FastAPIInstrumentor performs
        carrier = {"traceparent": traceparent}
        ctx = extract(carrier)

        # The context should contain a valid span context with matching trace_id

        # Extract via baggage-aware context - use non_recording_span
        from opentelemetry.trace.propagation import get_current_span as get_ctx_span

        extracted_span = get_ctx_span(ctx)
        span_ctx = extracted_span.get_span_context()
        actual_trace_id = trace.format_trace_id(span_ctx.trace_id)

        assert actual_trace_id == expected_trace_id, (
            f"Propagator did not extract trace_id. Got: {actual_trace_id}"
        )
        assert trace.format_span_id(span_ctx.span_id) == parent_span_id

    def test_traceparent_header_reaches_endpoint(
        self,
        mock_memvid_ask: AsyncMock,
        mock_openrouter: AsyncMock,
        mock_profile_loader: None,
    ) -> None:
        """An incoming traceparent header is accepted by the API (no rejection).

        Even without full OTel SDK instrumentation, the endpoint should
        process the request normally when a traceparent header is present.
        """
        expected_trace_id = "0af7651916cd43dd8448eb211c80319c"
        parent_span_id = "b7ad6b7169203331"
        traceparent = f"00-{expected_trace_id}-{parent_span_id}-01"

        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "What is the candidate's experience?", "stream": False},
            headers={"traceparent": traceparent},
        )
        assert response.status_code == 200
        # Verify response has a trace header (X-Trace-ID from middleware)
        assert "X-Trace-ID" in response.headers


# ---------------------------------------------------------------------------
# Tests: Traceparent propagated to gRPC
# ---------------------------------------------------------------------------


class TestTraceparentGrpcPropagation:
    """Verify traceparent is forwarded from HTTP request to gRPC metadata."""

    @pytest.mark.asyncio
    async def test_traceparent_propagated_to_grpc(
        self,
        otel_exporter: InMemorySpanExporter,
    ) -> None:
        """Chat endpoint propagates traceparent to memvid gRPC call via interceptor."""
        from ai_resume_api.memvid_client import CorrelationInterceptor
        from ai_resume_api.observability import set_trace_id
        from ai_resume_api.otel import get_tracer

        interceptor = CorrelationInterceptor()
        set_trace_id("test-trace-id")

        tracer = get_tracer()
        with tracer.start_as_current_span("test-grpc-propagation") as span:
            expected_trace_id = trace.format_trace_id(span.get_span_context().trace_id)

            # Create mock call details and continuation
            mock_details = AsyncMock()
            mock_details.method = "/memvid.v1.MemvidService/Ask"
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

            # Verify traceparent was injected into gRPC metadata
            assert captured_details is not None
            metadata_dict = dict(captured_details.metadata)

            assert "traceparent" in metadata_dict, (
                f"traceparent not found in gRPC metadata. Keys: {list(metadata_dict.keys())}"
            )
            tp = metadata_dict["traceparent"]
            assert tp.startswith("00-"), f"Invalid traceparent format: {tp}"
            # traceparent should contain the active trace_id
            assert expected_trace_id in tp, (
                f"Expected trace_id {expected_trace_id} not in traceparent '{tp}'"
            )

    @pytest.mark.asyncio
    async def test_correlation_headers_propagated_to_grpc(
        self,
        otel_exporter: InMemorySpanExporter,
    ) -> None:
        """CorrelationInterceptor also propagates x-trace-id, x-session-id, x-client-ip."""
        from ai_resume_api.memvid_client import CorrelationInterceptor
        from ai_resume_api.observability import set_trace_id, set_session_id, set_client_ip

        interceptor = CorrelationInterceptor()
        set_trace_id("trace-abc")
        set_session_id("session-xyz")
        set_client_ip("192.168.1.42")

        mock_details = AsyncMock()
        mock_details.method = "/memvid.v1.MemvidService/Search"
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

        assert captured_details is not None
        metadata_dict = dict(captured_details.metadata)
        assert metadata_dict["x-trace-id"] == "trace-abc"
        assert metadata_dict["x-session-id"] == "session-xyz"
        assert metadata_dict["x-client-ip"] == "192.168.1.42"


# ---------------------------------------------------------------------------
# Tests: SSE stats include trace_id
# ---------------------------------------------------------------------------


class TestSseStatsTraceId:
    """Verify the SSE stats event includes trace_id."""

    def test_sse_stats_include_trace_id(
        self,
        mock_memvid_ask: AsyncMock,
        mock_profile_loader: None,
    ) -> None:
        """SSE stats event includes the trace_id field for client correlation."""

        # Mock the openrouter streaming to yield a single chunk then finish
        async def mock_stream(*args: Any, **kwargs: Any) -> Any:
            mock_chunk = AsyncMock()
            mock_chunk.content = "Test response."
            mock_chunk.tokens_used = 10
            mock_chunk.finish_reason = None
            yield mock_chunk

            # Final chunk with finish_reason
            final_chunk = AsyncMock()
            final_chunk.content = None
            final_chunk.tokens_used = 10
            final_chunk.finish_reason = "stop"
            yield final_chunk

        with patch("app.main.get_openrouter_client") as mock_or:
            mock_client = AsyncMock()
            mock_client.chat_stream = mock_stream
            mock_or.return_value = mock_client

            client = TestClient(app)
            response = client.post(
                "/api/v1/chat",
                json={"message": "What experience does the candidate have?", "stream": True},
            )
            assert response.status_code == 200

            # Parse the SSE stream to find the stats event
            body = response.text
            stats_data = None
            for line in body.split("\n"):
                if line.startswith("event: stats"):
                    # Next data line has the payload
                    continue
                if stats_data is None and line.startswith("data: {") and "trace_id" in line:
                    stats_data = json.loads(line.removeprefix("data: "))

            assert stats_data is not None, (
                f"No stats event with trace_id found in SSE stream. Body:\n{body[:500]}"
            )
            assert "trace_id" in stats_data
            assert isinstance(stats_data["trace_id"], str)
            assert len(stats_data["trace_id"]) > 0


# ---------------------------------------------------------------------------
# Tests: Fallback X-Trace-ID when OTel disabled
# ---------------------------------------------------------------------------


class TestFallbackTraceId:
    """Verify X-Trace-ID header works when OTel is not configured."""

    def test_fallback_trace_id_when_otel_disabled(self) -> None:
        """X-Trace-ID response header is present even without OTel."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

        # The trace_id_middleware always sets X-Trace-ID
        trace_id = response.headers.get("X-Trace-ID")
        assert trace_id is not None, "X-Trace-ID header missing from response"
        assert len(trace_id) > 0

    def test_custom_trace_id_echoed_back(self) -> None:
        """A custom X-Trace-ID sent in the request is echoed in the response."""
        custom_trace = "my-custom-trace-123"
        client = TestClient(app)
        response = client.get(
            "/health",
            headers={"X-Trace-ID": custom_trace},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Trace-ID") == custom_trace

    def test_generated_trace_id_format(self) -> None:
        """Auto-generated trace IDs are 32 hex characters (128-bit)."""
        client = TestClient(app)
        response = client.get("/health")
        trace_id = response.headers.get("X-Trace-ID", "")
        # generate_trace_id() returns secrets.token_hex(16) = 32 hex chars
        assert len(trace_id) == 32
        assert all(c in "0123456789abcdef" for c in trace_id)


# ---------------------------------------------------------------------------
# Tests: OTel trace_id takes precedence
# ---------------------------------------------------------------------------


class TestOtelTraceIdPrecedence:
    """Verify OTel trace_id is preferred over custom X-Trace-ID."""

    def test_otel_trace_id_takes_precedence(self, otel_exporter: InMemorySpanExporter) -> None:
        """When OTel is active, get_trace_id returns the OTel trace_id."""
        from ai_resume_api.observability import get_trace_id, set_trace_id
        from ai_resume_api.otel import get_tracer

        # Set a custom trace_id
        set_trace_id("custom-fallback-id")

        tracer = get_tracer()
        with tracer.start_as_current_span("precedence-test") as span:
            tid = get_trace_id()
            otel_tid = trace.format_trace_id(span.get_span_context().trace_id)

            # OTel trace_id should be returned, not the custom one
            assert tid == otel_tid
            assert tid != "custom-fallback-id"
            assert len(tid) == 32

    def test_custom_trace_id_used_when_no_otel_span(self) -> None:
        """When no OTel span is active, custom trace_id is returned."""
        from ai_resume_api.observability import get_trace_id, set_trace_id

        set_trace_id("fallback-trace-999")
        tid = get_trace_id()
        assert tid == "fallback-trace-999"


# ---------------------------------------------------------------------------
# Tests: Nginx traceparent passthrough (configuration verification)
# ---------------------------------------------------------------------------


class TestNginxTraceparentConfig:
    """Verify nginx configuration passes traceparent header."""

    def test_nginx_config_has_traceparent_proxy_header(self) -> None:
        """nginx-default.conf includes proxy_set_header for traceparent."""
        from pathlib import Path

        nginx_conf = Path(__file__).parent.parent.parent / "frontend" / "nginx-default.conf"
        assert nginx_conf.exists(), f"nginx config not found at {nginx_conf}"

        content = nginx_conf.read_text()
        assert "proxy_set_header traceparent" in content, (
            "nginx config missing 'proxy_set_header traceparent' directive"
        )
        assert "$http_traceparent" in content, (
            "nginx config should pass $http_traceparent to backend"
        )

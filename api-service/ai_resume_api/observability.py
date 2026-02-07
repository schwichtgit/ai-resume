"""Observability utilities: trace IDs, LLM metrics, and payload logging.

This module provides:
- Trace ID generation and propagation via context vars
- Prometheus metrics for LLM calls (tokens, latency, errors)
- Structured logging helpers for LLM request/response correlation
"""

import time
import secrets
from contextvars import ContextVar
from dataclasses import dataclass

import structlog
from prometheus_client import Counter, Histogram, Gauge

logger = structlog.get_logger()

# =============================================================================
# Trace ID Context
# =============================================================================

# Context variable for trace ID propagation across async calls
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """Generate cryptographically secure trace ID for request tracking."""
    return secrets.token_hex(16)  # 32 hex chars, same format as uuid4().hex


def get_trace_id() -> str:
    """Get current trace ID from context, or empty string if not set."""
    return trace_id_ctx.get()


def set_trace_id(trace_id: str) -> None:
    """Set trace ID in context."""
    trace_id_ctx.set(trace_id)


# =============================================================================
# Prometheus Metrics for LLM
# =============================================================================

# Request counters
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["model", "status", "stream"],
)

# Token counters (for cost tracking)
llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens used in LLM calls",
    ["model", "type"],  # values: prompt, completion, total
)

# Latency histogram
llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM response latency in seconds",
    ["model", "stream"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# Context/retrieval metrics
memvid_retrieval_chunks = Histogram(
    "memvid_retrieval_chunks",
    "Number of chunks retrieved from memvid per request",
    buckets=[0, 1, 2, 3, 5, 10, 20],
)

memvid_context_chars = Histogram(
    "memvid_context_chars",
    "Total characters in retrieved context",
    buckets=[0, 500, 1000, 2000, 5000, 10000, 20000],
)

# Active requests gauge
llm_active_requests = Gauge(
    "llm_active_requests",
    "Currently active LLM requests",
    ["model"],
)


# =============================================================================
# LLM Payload Logging
# =============================================================================


@dataclass
class LLMRequestLog:
    """Structured log data for LLM requests."""

    trace_id: str
    model: str
    stream: bool
    system_prompt_chars: int
    context_chars: int
    context_chunks: int
    user_message_preview: str  # First 100 chars
    history_messages: int
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class LLMResponseLog:
    """Structured log data for LLM responses."""

    trace_id: str
    model: str
    stream: bool
    tokens_prompt: int
    tokens_completion: int
    tokens_total: int
    latency_ms: int
    finish_reason: str
    error: str | None = None


def log_llm_request(
    model: str,
    stream: bool,
    system_prompt: str,
    context: str,
    context_chunks: int,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> LLMRequestLog:
    """Log an LLM request with full context for debugging.

    Returns LLMRequestLog for correlation with response.
    """
    trace_id = get_trace_id()

    log_data = LLMRequestLog(
        trace_id=trace_id,
        model=model,
        stream=stream,
        system_prompt_chars=len(system_prompt),
        context_chars=len(context),
        context_chunks=context_chunks,
        user_message_preview=user_message[:100] + ("..." if len(user_message) > 100 else ""),
        history_messages=len(history) if history else 0,
    )

    # Structured log for Loki/Grafana correlation
    logger.info(
        "llm_request",
        trace_id=log_data.trace_id,
        model=log_data.model,
        stream=log_data.stream,
        system_prompt_chars=log_data.system_prompt_chars,
        context_chars=log_data.context_chars,
        context_chunks=log_data.context_chunks,
        user_message_preview=log_data.user_message_preview,
        history_messages=log_data.history_messages,
    )

    # Update Prometheus metrics
    llm_active_requests.labels(model=model).inc()
    memvid_retrieval_chunks.observe(context_chunks)
    memvid_context_chars.observe(len(context))

    return log_data


def log_llm_response(
    request_log: LLMRequestLog,
    tokens_prompt: int = 0,
    tokens_completion: int = 0,
    tokens_total: int = 0,
    finish_reason: str = "unknown",
    error: str | None = None,
) -> None:
    """Log an LLM response with metrics and correlation."""
    latency_ms = int((time.time() - request_log.timestamp) * 1000)

    log_data = LLMResponseLog(
        trace_id=request_log.trace_id,
        model=request_log.model,
        stream=request_log.stream,
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
        tokens_total=tokens_total,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        error=error,
    )

    # Structured log
    if error:
        logger.error(
            "llm_response",
            trace_id=log_data.trace_id,
            model=log_data.model,
            stream=log_data.stream,
            latency_ms=log_data.latency_ms,
            error=log_data.error,
        )
        status = "error"
    else:
        logger.info(
            "llm_response",
            trace_id=log_data.trace_id,
            model=log_data.model,
            stream=log_data.stream,
            tokens_prompt=log_data.tokens_prompt,
            tokens_completion=log_data.tokens_completion,
            tokens_total=log_data.tokens_total,
            latency_ms=log_data.latency_ms,
            finish_reason=log_data.finish_reason,
        )
        status = "success"

    # Update Prometheus metrics
    llm_active_requests.labels(model=request_log.model).dec()
    llm_requests_total.labels(
        model=request_log.model,
        status=status,
        stream=str(request_log.stream).lower(),
    ).inc()

    if tokens_total > 0:
        llm_tokens_total.labels(model=request_log.model, type="prompt").inc(tokens_prompt)
        llm_tokens_total.labels(model=request_log.model, type="completion").inc(tokens_completion)
        llm_tokens_total.labels(model=request_log.model, type="total").inc(tokens_total)

    llm_latency_seconds.labels(
        model=request_log.model,
        stream=str(request_log.stream).lower(),
    ).observe(latency_ms / 1000.0)

"""OpenTelemetry initialization, gated on OTEL_EXPORTER_OTLP_ENDPOINT.

When the environment variable OTEL_EXPORTER_OTLP_ENDPOINT is set, this module
configures a TracerProvider with OTLP gRPC export and instruments the FastAPI
application. When the variable is absent, all calls are no-ops -- the default
OpenTelemetry NoOp tracer is used and zero overhead is added to request paths.
"""

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_otel_initialized = False


def init_otel(app: Any = None) -> None:
    """Initialize OpenTelemetry if OTEL_EXPORTER_OTLP_ENDPOINT is set.

    Safe to call multiple times -- subsequent calls are no-ops.

    Args:
        app: FastAPI application instance to auto-instrument. If None,
             only the global TracerProvider is configured.
    """
    global _otel_initialized

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    if _otel_initialized:
        if app:
            FastAPIInstrumentor.instrument_app(app)
        return

    resource = Resource.create(
        {
            "service.name": os.environ.get("OTEL_SERVICE_NAME", "ai-resume-api"),
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if app:
        FastAPIInstrumentor.instrument_app(app)

    _otel_initialized = True


def get_tracer(name: str = "ai-resume-api") -> trace.Tracer:
    """Get a tracer instance.

    Returns the global tracer which is either a real SDK tracer (when OTel is
    initialized) or the default NoOp tracer.
    """
    return trace.get_tracer(name)

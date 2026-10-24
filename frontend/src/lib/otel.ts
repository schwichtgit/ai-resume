/**
 * OpenTelemetry initialization for browser tracing.
 *
 * Runtime-gated: only activates when window.__OTEL_ENDPOINT__ is set
 * (injected by nginx/lua at serve time). Always bundled, no-op when
 * the endpoint is absent.
 */

import { TracerProvider, SimpleSpanProcessor } from '@opentelemetry/sdk-trace';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { context, trace } from '@opentelemetry/api';
import { ZoneContextManager } from '@opentelemetry/context-zone';

declare global {
  interface Window {
    __OTEL_ENDPOINT__?: string;
  }
}

let initialized = false;

/**
 * Initialize OpenTelemetry tracing if the collector endpoint is configured.
 * Safe to call multiple times -- subsequent calls are no-ops.
 */
export function initOtel(): void {
  if (initialized) return;

  const endpoint = window.__OTEL_ENDPOINT__;
  if (!endpoint) return;

  const resource = resourceFromAttributes({
    'service.name': 'ai-resume-frontend',
  });

  const exporter = new OTLPTraceExporter({
    url: `${endpoint}/v1/traces`,
  });

  const provider = new TracerProvider({
    resource,
    spanProcessors: [new SimpleSpanProcessor({ exporter })],
  });

  // SDK 3.0 dropped WebTracerProvider and its register(), which set the
  // global provider and enabled the context manager in one call; both are
  // done explicitly now. register() also installed the W3C propagator, which
  // nothing here needs: getTraceparent() builds the header by hand.
  const contextManager = new ZoneContextManager();
  contextManager.enable();
  context.setGlobalContextManager(contextManager);
  trace.setGlobalTracerProvider(provider);

  initialized = true;
}

/**
 * Return a tracer instance for creating spans.
 */
export function getTracer(name = 'ai-resume-frontend') {
  return trace.getTracer(name);
}

/**
 * Build a W3C traceparent header value from the currently active span.
 * Returns null when tracing is inactive or no span is in context.
 */
export function getTraceparent(): string | null {
  const span = trace.getActiveSpan();
  if (!span) return null;

  const ctx = span.spanContext();
  if (!ctx.traceId || ctx.traceId === '00000000000000000000000000000000') {
    return null;
  }

  const flags = ctx.traceFlags.toString(16).padStart(2, '0');
  return `00-${ctx.traceId}-${ctx.spanId}-${flags}`;
}

/**
 * Whether the OTel SDK has been initialized with a valid collector endpoint.
 * Use this to gate span creation in hot paths.
 */
export function isOtelInitialized(): boolean {
  return initialized;
}

/**
 * Reset internal state. Exported only for testing.
 */
export function _resetForTesting(): void {
  initialized = false;
}

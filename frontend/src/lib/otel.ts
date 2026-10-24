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
import { context, trace, type Span } from '@opentelemetry/api';
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
 * Run `fn` with `span` as the active span, so the API requests it starts carry
 * the span's traceparent and the backend's spans join the browser's trace.
 *
 * startSpan() does not activate a span: a fetch made outside its context
 * sees no active span, getTraceparent() returns null, and the request goes
 * out without a traceparent. The api-client functions read the header
 * synchronously when called, so the context is in place when it matters.
 * A null span (tracing off) just runs `fn`.
 */
export function withActiveSpan<T>(
  span: Span | null | undefined,
  fn: () => T,
): T {
  if (!span) return fn();
  return context.with(trace.setSpan(context.active(), span), fn);
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

/**
 * OpenTelemetry wiring against the real SDK.
 *
 * otel.test.ts mocks every SDK module, so it cannot tell whether the global
 * tracer provider and context manager actually work together. Only the
 * exporter is mocked here: a span started as the active span must be what
 * getTraceparent() reads, which is the browser half of the
 * browser-to-backend trace, and an ended span must reach the exporter.
 */

import { describe, it, expect, vi } from 'vitest';

const exported = vi.hoisted(() => [] as Array<{ name: string }>);

vi.mock('@opentelemetry/exporter-trace-otlp-http', () => ({
  OTLPTraceExporter: vi.fn(function () {
    return {
      export: (
        spans: Array<{ name: string }>,
        done: (r: { code: number }) => void,
      ) => {
        exported.push(...spans);
        done({ code: 0 });
      },
      shutdown: () => Promise.resolve(),
      forceFlush: () => Promise.resolve(),
    };
  }),
}));

import {
  initOtel,
  getTracer,
  getTraceparent,
  isOtelInitialized,
  withActiveSpan,
} from '../otel';
import { getProfile } from '../api-client';

describe('otel wiring (real SDK)', () => {
  it('makes an active span visible to getTraceparent', () => {
    window.__OTEL_ENDPOINT__ = 'http://localhost:4318';
    initOtel();
    expect(isOtelInitialized()).toBe(true);

    const header = getTracer().startActiveSpan('wiring-check', (span) => {
      const value = getTraceparent();
      const { traceId, spanId } = span.spanContext();
      span.end();
      return { value, traceId, spanId };
    });

    expect(header.traceId).toMatch(/^[0-9a-f]{32}$/);
    expect(header.traceId).not.toBe('0'.repeat(32));
    expect(header.value).toBe(`00-${header.traceId}-${header.spanId}-01`);
    // SimpleSpanProcessor exports on end. In SDK 3.0 it takes { exporter };
    // passed the exporter positionally it would have none to export to.
    expect(exported.map((s) => s.name)).toContain('wiring-check');
  });

  it('reports no traceparent outside an active span', () => {
    expect(getTraceparent()).toBeNull();
  });

  it('withActiveSpan makes a startSpan() span the active one', () => {
    const span = getTracer().startSpan('not-active-by-itself');
    expect(getTraceparent()).toBeNull();

    const inside = withActiveSpan(span, () => getTraceparent());
    span.end();

    const { traceId, spanId } = span.spanContext();
    expect(inside).toBe(`00-${traceId}-${spanId}-01`);
    expect(getTraceparent()).toBeNull();
  });

  it('withActiveSpan with no span just runs the function', () => {
    expect(withActiveSpan(null, () => 42)).toBe(42);
  });

  // The bug this guards: hooks call startSpan() and then the API client,
  // so requests went out with no traceparent and browser and backend traces
  // were never linked.
  it('an API call inside withActiveSpan sends the span traceparent', async () => {
    const sent: Array<string | null> = [];
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      sent.push(new Headers(init?.headers).get('traceparent'));
      return new Response(JSON.stringify({ name: 'Test' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    const span = getTracer().startSpan('profile.fetch');
    await withActiveSpan(span, () => getProfile());
    await getProfile();
    span.end();
    vi.unstubAllGlobals();

    const { traceId, spanId } = span.spanContext();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(sent[0]).toBe(`00-${traceId}-${spanId}-01`);
    expect(sent[1]).toBeNull();
  });
});

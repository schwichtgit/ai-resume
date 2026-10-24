/**
 * Tests for OpenTelemetry initialization and helpers.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Use vi.hoisted to define mock variables that are available to vi.mock factories.
const mocks = vi.hoisted(() => {
  const enable = vi.fn();
  return {
    // Use regular function so it can be invoked with `new`
    TracerProvider: vi.fn(function () {
      return { getTracer: vi.fn() };
    }),
    enable,
    OTLPTraceExporter: vi.fn(function () {
      return {};
    }),
    SimpleSpanProcessor: vi.fn(function () {
      return {};
    }),
    resourceFromAttributes: vi.fn().mockReturnValue({}),
    ZoneContextManager: vi.fn(function () {
      return { enable };
    }),
  };
});

vi.mock('@opentelemetry/sdk-trace', () => ({
  TracerProvider: mocks.TracerProvider,
  SimpleSpanProcessor: mocks.SimpleSpanProcessor,
}));

vi.mock('@opentelemetry/exporter-trace-otlp-http', () => ({
  OTLPTraceExporter: mocks.OTLPTraceExporter,
}));

vi.mock('@opentelemetry/resources', () => ({
  resourceFromAttributes: mocks.resourceFromAttributes,
}));

vi.mock('@opentelemetry/context-zone', () => ({
  ZoneContextManager: mocks.ZoneContextManager,
}));

import { context, trace } from '@opentelemetry/api';
import { initOtel, getTraceparent, getTracer, _resetForTesting } from '../otel';

// Observe the two global registrations SDK 2.x's register() used to do, on
// the real API objects, without letting them install the mocked provider.
const setGlobalTracerProvider = vi
  .spyOn(trace, 'setGlobalTracerProvider')
  .mockReturnValue(true);
const setGlobalContextManager = vi
  .spyOn(context, 'setGlobalContextManager')
  .mockReturnValue(true);

describe('otel', () => {
  beforeEach(() => {
    _resetForTesting();
    delete window.__OTEL_ENDPOINT__;
    mocks.TracerProvider.mockClear();
    mocks.OTLPTraceExporter.mockClear();
    mocks.SimpleSpanProcessor.mockClear();
    mocks.enable.mockClear();
    setGlobalTracerProvider.mockClear();
    setGlobalContextManager.mockClear();
    mocks.resourceFromAttributes.mockClear();
    mocks.ZoneContextManager.mockClear();
  });

  describe('initOtel', () => {
    it('should be a no-op when __OTEL_ENDPOINT__ is not set', () => {
      initOtel();

      expect(mocks.TracerProvider).not.toHaveBeenCalled();
      expect(setGlobalTracerProvider).not.toHaveBeenCalled();
    });

    it('should initialize provider when __OTEL_ENDPOINT__ is set', () => {
      window.__OTEL_ENDPOINT__ = 'http://localhost:4318';

      initOtel();

      expect(mocks.TracerProvider).toHaveBeenCalledTimes(1);
      expect(setGlobalTracerProvider).toHaveBeenCalledTimes(1);
    });

    it('should not reinitialize on second call', () => {
      window.__OTEL_ENDPOINT__ = 'http://localhost:4318';

      initOtel();
      initOtel();

      expect(mocks.TracerProvider).toHaveBeenCalledTimes(1);
    });

    it('should configure exporter with correct URL', () => {
      window.__OTEL_ENDPOINT__ = 'http://collector:4318';

      initOtel();

      expect(mocks.OTLPTraceExporter).toHaveBeenCalledWith({
        url: 'http://collector:4318/v1/traces',
      });
    });

    it('should wire up span processor and context manager', () => {
      window.__OTEL_ENDPOINT__ = 'http://localhost:4318';

      initOtel();

      expect(mocks.SimpleSpanProcessor).toHaveBeenCalledTimes(1);
      expect(mocks.SimpleSpanProcessor).toHaveBeenCalledWith({
        exporter: expect.any(Object),
      });
      expect(mocks.TracerProvider).toHaveBeenCalledWith(
        expect.objectContaining({
          spanProcessors: expect.arrayContaining([expect.any(Object)]),
        }),
      );
      expect(mocks.ZoneContextManager).toHaveBeenCalledTimes(1);
      // register() used to enable the context manager; without it, active
      // spans would not propagate.
      expect(mocks.enable).toHaveBeenCalledTimes(1);
      expect(setGlobalContextManager).toHaveBeenCalledTimes(1);
    });

    it('should set service.name resource attribute', () => {
      window.__OTEL_ENDPOINT__ = 'http://localhost:4318';

      initOtel();

      expect(mocks.resourceFromAttributes).toHaveBeenCalledWith({
        'service.name': 'ai-resume-frontend',
      });
    });
  });

  describe('getTraceparent', () => {
    it('should return null when no active span exists', () => {
      const result = getTraceparent();

      expect(result).toBeNull();
    });
  });

  describe('getTracer', () => {
    it('should return a tracer object', () => {
      const tracer = getTracer();

      expect(tracer).toBeDefined();
      expect(typeof tracer.startSpan).toBe('function');
    });

    it('should accept a custom tracer name', () => {
      const tracer = getTracer('custom-tracer');

      expect(tracer).toBeDefined();
    });
  });
});

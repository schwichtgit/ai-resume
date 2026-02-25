import { describe, it, expect, vi, afterEach } from 'vitest';
import { registerWebMcpTools } from '../webmcp';

describe('registerWebMcpTools', () => {
  const originalModelContext = navigator.modelContext;
  const nav = navigator as Navigator & {
    modelContext?: unknown;
    modelContextTesting?: unknown;
  };

  afterEach(() => {
    // Restore original state
    if (originalModelContext === undefined) {
      delete nav.modelContext;
    } else {
      nav.modelContext = originalModelContext;
    }
    delete nav.modelContextTesting;
  });

  it('registers tools when navigator.modelContext is available', () => {
    const registerTool = vi.fn();
    Object.defineProperty(navigator, 'modelContext', {
      value: { registerTool },
      configurable: true,
    });

    registerWebMcpTools();

    expect(registerTool).toHaveBeenCalledTimes(2);
    expect(registerTool).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'ask_question',
        execute: expect.any(Function),
      }),
    );
    expect(registerTool).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'assess_fit',
        execute: expect.any(Function),
      }),
    );
  });

  it('falls back to modelContextTesting when modelContext is absent', () => {
    delete nav.modelContext;
    const registerTool = vi.fn();
    Object.defineProperty(navigator, 'modelContextTesting', {
      value: { registerTool },
      configurable: true,
    });

    registerWebMcpTools();

    expect(registerTool).toHaveBeenCalledTimes(2);
  });

  it('is a silent no-op when neither API is available', () => {
    delete nav.modelContext;
    delete nav.modelContextTesting;

    expect(() => registerWebMcpTools()).not.toThrow();
  });

  it('handles registration errors gracefully', () => {
    const registerTool = vi.fn().mockImplementation(() => {
      throw new Error('Registration failed');
    });
    Object.defineProperty(navigator, 'modelContext', {
      value: { registerTool },
      configurable: true,
    });

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    expect(() => registerWebMcpTools()).not.toThrow();
    expect(warnSpy).toHaveBeenCalled();

    warnSpy.mockRestore();
  });
});

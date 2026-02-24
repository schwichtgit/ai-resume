import { describe, it, expect, vi, afterEach } from 'vitest';
import { registerWebMcpTools } from '../webmcp';

describe('registerWebMcpTools', () => {
  const originalModelContext = navigator.modelContext;
  const nav = navigator as Navigator & { modelContext?: unknown };

  afterEach(() => {
    // Restore original state
    if (originalModelContext === undefined) {
      delete nav.modelContext;
    } else {
      nav.modelContext = originalModelContext;
    }
  });

  it('registers tools when navigator.modelContext is available', () => {
    const addTool = vi.fn();
    Object.defineProperty(navigator, 'modelContext', {
      value: { addTool },
      configurable: true,
    });

    registerWebMcpTools();

    expect(addTool).toHaveBeenCalledTimes(2);
    expect(addTool).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'ask_question' }),
    );
    expect(addTool).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'assess_fit' }),
    );
  });

  it('is a silent no-op when navigator.modelContext is not available', () => {
    delete nav.modelContext;

    // Should not throw
    expect(() => registerWebMcpTools()).not.toThrow();
  });

  it('handles registration errors gracefully', () => {
    const addTool = vi.fn().mockImplementation(() => {
      throw new Error('Registration failed');
    });
    Object.defineProperty(navigator, 'modelContext', {
      value: { addTool },
      configurable: true,
    });

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    expect(() => registerWebMcpTools()).not.toThrow();
    expect(warnSpy).toHaveBeenCalled();

    warnSpy.mockRestore();
  });
});

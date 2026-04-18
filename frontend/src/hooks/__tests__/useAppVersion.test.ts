import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useAppVersion } from '../useAppVersion';

describe('useAppVersion', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches version from API', async () => {
    const mockResponse = { version: '1.2.3', commit: 'abc1234' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.version).toEqual(mockResponse);
  });

  it('falls back to dev on fetch error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.version).toEqual({
      version: 'dev',
      commit: 'unknown',
    });
  });

  it('falls back to dev on non-ok response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useAppVersion());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.version).toEqual({
      version: 'dev',
      commit: 'unknown',
    });
  });
});

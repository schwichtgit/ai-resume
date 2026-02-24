import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useMcpConfig } from '../useMcpConfig';

describe('useMcpConfig', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('starts with empty state', () => {
    const { result } = renderHook(() => useMcpConfig());
    expect(result.current.clients).toEqual([]);
    expect(result.current.available).toBeNull();
  });

  it('fetches clients on demand', async () => {
    const mockClients = [
      { id: 'claude-desktop', label: 'Claude Desktop' },
    ];
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockClients),
    });

    const { result } = renderHook(() => useMcpConfig());

    await act(async () => {
      await result.current.fetchClients();
    });

    expect(result.current.clients).toEqual(mockClients);
    expect(result.current.available).toBe(true);
  });

  it('sets available to false on fetch error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('fail'));

    const { result } = renderHook(() => useMcpConfig());

    await act(async () => {
      await result.current.fetchClients();
    });

    expect(result.current.available).toBe(false);
    expect(result.current.clients).toEqual([]);
  });

  it('fetches config for a client', async () => {
    const mockConfig = { label: 'Test', instructions: 'Add this', config: { url: '/mcp' } };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockConfig),
    });

    const { result } = renderHook(() => useMcpConfig());

    await act(async () => {
      await result.current.fetchConfig('claude-desktop');
    });

    expect(result.current.configs['claude-desktop']).toEqual(mockConfig);
  });
});

/**
 * Theme before first paint.
 *
 * index.html sets the theme class before the app loads (next-themes' own
 * script never runs in a client-only app), and App passes scriptProps so
 * React 19 stops warning about that dead script.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render } from '@testing-library/react';
import App from '../App';

const html = readFileSync(resolve(__dirname, '../../index.html'), 'utf8');
const match = html.match(/<script data-theme-init>([\s\S]*?)<\/script>/);
const themeInit = match ? match[1] : '';

function runThemeInit() {
  new Function(themeInit)();
}

describe('index.html theme init script', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
    document.documentElement.style.colorScheme = '';
  });

  it('is present in index.html', () => {
    expect(themeInit).toContain("localStorage.getItem('theme')");
  });

  it('defaults to dark with nothing stored', () => {
    runThemeInit();
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(document.documentElement.style.colorScheme).toBe('dark');
  });

  it.each(['light', 'dark'])('applies a stored %s theme', (theme) => {
    localStorage.setItem('theme', theme);
    runThemeInit();
    expect(document.documentElement.classList.contains(theme)).toBe(true);
    expect(document.documentElement.style.colorScheme).toBe(theme);
  });

  it('ignores an unexpected stored value', () => {
    localStorage.setItem('theme', 'system');
    runThemeInit();
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('keeps the default when storage throws', () => {
    const spy = vi
      .spyOn(Storage.prototype, 'getItem')
      .mockImplementation(() => {
        throw new Error('blocked');
      });
    runThemeInit();
    spy.mockRestore();
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});

describe('App theme provider', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders without React warning about a script tag', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('offline in test'))),
    );
    const errors: string[] = [];
    vi.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
      errors.push(args.map(String).join(' '));
    });

    render(<App />);

    expect(
      errors.filter((e) => e.includes('Encountered a script tag')),
    ).toEqual([]);
  });
});

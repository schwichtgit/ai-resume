import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AboutDialog } from '../AboutDialog';

// Mock useAppVersion
vi.mock('@/hooks/useAppVersion', () => ({
  useAppVersion: () => ({
    version: {
      version: '1.0.0',
      commit: 'abc1234567890',
      model: 'google/gemma-4-26b-a4b-it',
    },
    loading: false,
  }),
}));

describe('AboutDialog', () => {
  it('renders version when open', () => {
    render(<AboutDialog open={true} onOpenChange={() => {}} />);
    expect(screen.getByText('1.0.0')).toBeInTheDocument();
  });

  it('renders commit SHA (truncated)', () => {
    render(<AboutDialog open={true} onOpenChange={() => {}} />);
    expect(screen.getByText('abc1234')).toBeInTheDocument();
  });

  it('renders the configured model', () => {
    // A live incident surfaced only as a bare 404 in the chat UI, with no way
    // to see which model was configured. Showing it makes that diagnosable.
    render(<AboutDialog open={true} onOpenChange={() => {}} />);
    expect(screen.getByTestId('about-model')).toHaveTextContent(
      'google/gemma-4-26b-a4b-it',
    );
  });

  it('renders GitHub link', () => {
    render(<AboutDialog open={true} onOpenChange={() => {}} />);
    const link = screen.getByText('Source Code');
    expect(link.closest('a')).toHaveAttribute(
      'href',
      'https://github.com/schwichtgit/ai-resume',
    );
  });

  it('renders Medium link', () => {
    render(<AboutDialog open={true} onOpenChange={() => {}} />);
    const link = screen.getByText('Blog');
    expect(link.closest('a')).toHaveAttribute(
      'href',
      expect.stringContaining('medium.com'),
    );
  });

  it('does not render when closed', () => {
    render(<AboutDialog open={false} onOpenChange={() => {}} />);
    expect(screen.queryByText('About AI Resume')).not.toBeInTheDocument();
  });
});

describe('AboutDialog without model', () => {
  it('omits the model row when the API does not report one', async () => {
    // An older api-service build returns {version, commit} only. The dialog
    // must not render an empty row or "undefined".
    vi.resetModules();
    vi.doMock('@/hooks/useAppVersion', () => ({
      useAppVersion: () => ({
        version: { version: '1.0.0', commit: 'abc1234567890' },
        loading: false,
      }),
    }));
    const { AboutDialog: Fresh } = await import('../AboutDialog');
    render(<Fresh open={true} onOpenChange={() => {}} />);
    expect(screen.queryByTestId('about-model')).not.toBeInTheDocument();
  });
});

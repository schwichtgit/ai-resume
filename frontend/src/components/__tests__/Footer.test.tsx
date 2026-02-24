import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Footer from '../Footer';

// Mock useProfileContext
vi.mock('@/hooks/useProfileContext', () => ({
  useProfileContext: () => ({
    profile: {
      name: 'Test User',
      title: 'Developer',
      email: 'test@example.com',
      linkedin: 'https://linkedin.com/in/test',
    },
    isLoading: false,
  }),
}));

// Mock useAppVersion
vi.mock('@/hooks/useAppVersion', () => ({
  useAppVersion: () => ({
    version: { version: '1.0.0', commit: 'abc123' },
    loading: false,
  }),
}));

describe('Footer', () => {
  it('renders profile name and title', () => {
    render(<Footer />);
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('Developer')).toBeInTheDocument();
  });

  it('has corrected GitHub URL', () => {
    render(<Footer />);
    const githubLink = screen.getByLabelText('GitHub');
    expect(githubLink).toHaveAttribute('href', 'https://github.com/schwichtgit/ai-resume');
  });

  it('has Medium/BookOpen link', () => {
    render(<Footer />);
    const mediumLink = screen.getByLabelText('Medium');
    expect(mediumLink).toHaveAttribute('href', expect.stringContaining('medium.com'));
  });

  it('displays version', () => {
    render(<Footer />);
    expect(screen.getByText('v1.0.0')).toBeInTheDocument();
  });

  it('has About trigger', () => {
    render(<Footer />);
    expect(screen.getByText('About')).toBeInTheDocument();
  });
});

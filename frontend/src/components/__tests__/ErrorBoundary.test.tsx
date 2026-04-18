import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';

// Component that throws on render
function ThrowingComponent({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>Working content</div>;
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children when no error', () => {
    render(
      <ErrorBoundary sectionName="Test">
        <div>Child content</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText('Child content')).toBeDefined();
  });

  it('renders fallback on error', () => {
    render(
      <ErrorBoundary sectionName="Experience">
        <ThrowingComponent />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Unable to load Experience')).toBeDefined();
    expect(screen.getByText('Try Again')).toBeDefined();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary sectionName="Test" fallback={<div>Custom fallback</div>}>
        <ThrowingComponent />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Custom fallback')).toBeDefined();
  });

  it('logs error with section name', () => {
    const consoleSpy = vi.spyOn(console, 'error');
    render(
      <ErrorBoundary sectionName="AIChat">
        <ThrowingComponent />
      </ErrorBoundary>,
    );
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('[ErrorBoundary:AIChat]'),
      expect.any(Error),
      expect.anything(),
    );
  });

  it('resets on Try Again click', () => {
    let shouldThrow = true;
    function ConditionalThrower() {
      if (shouldThrow) throw new Error('Test error');
      return <div>Recovered content</div>;
    }

    render(
      <ErrorBoundary sectionName="Test">
        <ConditionalThrower />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Unable to load Test')).toBeDefined();

    shouldThrow = false;
    fireEvent.click(screen.getByText('Try Again'));

    expect(screen.getByText('Recovered content')).toBeDefined();
  });

  it('does not affect sibling sections on error', () => {
    render(
      <div>
        <ErrorBoundary sectionName="Broken">
          <ThrowingComponent />
        </ErrorBoundary>
        <ErrorBoundary sectionName="Working">
          <div>Working section</div>
        </ErrorBoundary>
      </div>,
    );

    expect(screen.getByText('Unable to load Broken')).toBeDefined();
    expect(screen.getByText('Working section')).toBeDefined();
  });
});

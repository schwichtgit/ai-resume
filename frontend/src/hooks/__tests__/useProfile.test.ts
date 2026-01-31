/**
 * Tests for useProfile hook
 * Critical for profile loading and meta tag updates
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useProfile } from '../useProfile';
import * as apiClient from '@/lib/api-client';

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  getProfile: vi.fn(),
}));

describe('useProfile', () => {
  const mockProfileData = {
    name: 'Jane Chen',
    title: 'VP of Engineering',
    email: 'jane@example.com',
    linkedin: 'https://linkedin.com/in/janechen',
    location: 'San Francisco, CA',
    status: 'Open to opportunities',
    suggested_questions: ['Question 1', 'Question 2'],
    tags: ['ai', 'infrastructure', 'platform-engineering'],
    experience: [
      {
        company: 'Acme Corp',
        role: 'VP Engineering',
        period: '2022-Present',
        location: 'SF',
        tags: ['leadership'],
        highlights: ['Built platform team'],
        aiContext: {
          situation: 'Situation text',
          approach: 'Approach text',
          technicalWork: 'Technical work',
          lessonsLearned: 'Lessons learned',
        },
      },
    ],
    skills: {
      strong: ['Python', 'Kubernetes'],
      moderate: ['Rust'],
      gaps: ['Mobile'],
    },
    fit_assessment_examples: [
      {
        title: 'Strong Fit — VP Platform Engineering',
        fit_level: 'strong_fit',
        role: 'VP Platform Engineering',
        job_description: 'VP role at AI startup...',
        verdict: '⭐⭐⭐⭐⭐ Strong fit',
        key_matches: 'Platform expertise',
        gaps: 'None',
        recommendation: 'Excellent fit',
      },
    ],
  };

  beforeEach(() => {
    // Reset DOM for each test
    document.title = '';

    // Clear existing meta tags
    const metaTags = document.querySelectorAll('meta[name="description"], meta[property^="og:"], meta[name^="twitter:"]');
    metaTags.forEach(tag => tag.remove());

    // Add fresh meta tags
    const metaDescription = document.createElement('meta');
    metaDescription.setAttribute('name', 'description');
    metaDescription.setAttribute('content', '');
    document.head.appendChild(metaDescription);

    const ogTitle = document.createElement('meta');
    ogTitle.setAttribute('property', 'og:title');
    ogTitle.setAttribute('content', '');
    document.head.appendChild(ogTitle);

    const ogDescription = document.createElement('meta');
    ogDescription.setAttribute('property', 'og:description');
    ogDescription.setAttribute('content', '');
    document.head.appendChild(ogDescription);

    const twitterTitle = document.createElement('meta');
    twitterTitle.setAttribute('name', 'twitter:title');
    twitterTitle.setAttribute('content', '');
    document.head.appendChild(twitterTitle);

    const twitterDescription = document.createElement('meta');
    twitterDescription.setAttribute('name', 'twitter:description');
    twitterDescription.setAttribute('content', '');
    document.head.appendChild(twitterDescription);

    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should load profile successfully', async () => {
    vi.mocked(apiClient.getProfile).mockResolvedValueOnce(mockProfileData);

    const { result } = renderHook(() => useProfile());

    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.profile).toBeNull();
    expect(result.current.error).toBeNull();

    // Wait for profile to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Profile loaded successfully
    expect(result.current.profile).toBeDefined();
    expect(result.current.profile?.name).toBe('Jane Chen');
    expect(result.current.profile?.title).toBe('VP of Engineering');
    expect(result.current.profile?.initials).toBe('JC');
    expect(result.current.profile?.experience).toHaveLength(1);
    expect(result.current.profile?.skills).toEqual({
      strong: ['Python', 'Kubernetes'],
      moderate: ['Rust'],
      gaps: ['Mobile'],
    });
    expect(result.current.profile?.fit_assessment_examples).toHaveLength(1);
    expect(result.current.error).toBeNull();
  });

  it('should derive initials correctly from name', async () => {
    const testCases = [
      { name: 'Jane Chen', expected: 'JC' },
      { name: 'John Smith III', expected: 'JI' },  // First and LAST name
      { name: 'Alice', expected: 'A' },
      { name: 'Mary-Jane Watson', expected: 'MW' },
      { name: '', expected: '' },
    ];

    for (const testCase of testCases) {
      vi.mocked(apiClient.getProfile).mockResolvedValueOnce({
        ...mockProfileData,
        name: testCase.name,
      });

      const { result } = renderHook(() => useProfile());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.profile?.initials).toBe(testCase.expected);
    }
  });

  it('should handle missing optional fields gracefully', async () => {
    const minimalProfile = {
      name: 'Jane Chen',
      title: 'VP Engineering',
      email: 'jane@example.com',
      linkedin: 'https://linkedin.com/in/janechen',
      location: 'SF',
      status: 'Open',
      suggested_questions: [],
      tags: [],
    };

    vi.mocked(apiClient.getProfile).mockResolvedValueOnce(minimalProfile as any);

    const { result } = renderHook(() => useProfile());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.profile).toBeDefined();
    expect(result.current.profile?.experience).toEqual([]);
    expect(result.current.profile?.skills).toEqual({ strong: [], moderate: [], gaps: [] });
    expect(result.current.profile?.fit_assessment_examples).toEqual([]);
  });

  it('should handle API errors', async () => {
    const mockError = new Error('Failed to fetch profile');
    vi.mocked(apiClient.getProfile).mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useProfile());

    // Initially loading
    expect(result.current.loading).toBe(true);

    // Wait for error
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.profile).toBeNull();
    expect(result.current.error).toEqual(mockError);
  });

  it('should update document title when profile loads', async () => {
    vi.mocked(apiClient.getProfile).mockResolvedValueOnce(mockProfileData);

    renderHook(() => useProfile());

    await waitFor(() => {
      expect(document.title).toBe('Jane Chen — VP of Engineering');
    });
  });

  it('should update meta description when profile loads', async () => {
    vi.mocked(apiClient.getProfile).mockResolvedValueOnce(mockProfileData);

    renderHook(() => useProfile());

    await waitFor(() => {
      const metaDescription = document.querySelector('meta[name="description"]');
      expect(metaDescription?.getAttribute('content')).toContain('VP of Engineering');
      expect(metaDescription?.getAttribute('content')).toContain('ai, infrastructure, platform-engineering');
    });
  });

  it('should update Open Graph meta tags when profile loads', async () => {
    vi.mocked(apiClient.getProfile).mockResolvedValueOnce(mockProfileData);

    renderHook(() => useProfile());

    await waitFor(() => {
      const ogTitle = document.querySelector('meta[property="og:title"]');
      const ogDescription = document.querySelector('meta[property="og:description"]');

      expect(ogTitle?.getAttribute('content')).toBe('Jane Chen — VP of Engineering');
      expect(ogDescription?.getAttribute('content')).toBe(
        'Ask AI about my experience. Get honest, detailed answers about fit for your role.'
      );
    });
  });

  it('should update Twitter meta tags when profile loads', async () => {
    vi.mocked(apiClient.getProfile).mockResolvedValueOnce(mockProfileData);

    renderHook(() => useProfile());

    await waitFor(() => {
      const twitterTitle = document.querySelector('meta[name="twitter:title"]');
      const twitterDescription = document.querySelector('meta[name="twitter:description"]');

      expect(twitterTitle?.getAttribute('content')).toBe('Jane Chen — VP of Engineering');
      expect(twitterDescription?.getAttribute('content')).toBe(
        'AI-queryable professional portfolio. Ask questions, get honest answers.'
      );
    });
  });

  it('should not update meta tags if profile fails to load', async () => {
    const originalTitle = 'Original Title';
    document.title = originalTitle;

    vi.mocked(apiClient.getProfile).mockRejectedValueOnce(new Error('API Error'));

    renderHook(() => useProfile());

    await waitFor(() => {
      expect(document.title).toBe(originalTitle);
    });
  });

  it('should only fetch profile once on mount', async () => {
    vi.mocked(apiClient.getProfile).mockResolvedValueOnce(mockProfileData);

    const { rerender } = renderHook(() => useProfile());

    await waitFor(() => {
      expect(apiClient.getProfile).toHaveBeenCalledTimes(1);
    });

    // Rerender should not trigger another fetch
    rerender();

    expect(apiClient.getProfile).toHaveBeenCalledTimes(1);
  });
});

/**
 * Tests for API client functions
 * Critical for all frontend functionality
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { getProfile, getSuggestedQuestions, assessFit, checkHealth, ApiError } from '../api-client';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('api-client', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('checkHealth', () => {
    it('should return health data on success', async () => {
      const mockHealthData = {
        status: 'healthy',
        memvid_connected: true,
        memvid_frame_count: 15,
        active_sessions: 3,
        version: '1.0.0',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealthData,
      });

      const result = await checkHealth();

      expect(result).toEqual(mockHealthData);
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/health');
    });

    it('should throw ApiError on failure', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 503,
      });

      await expect(checkHealth()).rejects.toThrow(ApiError);
    });
  });

  describe('getProfile', () => {
    it('should return profile data with camelCase transformation', async () => {
      const mockApiResponse = {
        name: 'Jane Chen',
        title: 'VP of Engineering',
        email: 'jane@example.com',
        linkedin: 'https://linkedin.com/in/janechen',
        location: 'San Francisco, CA',
        status: 'Open to opportunities',
        suggested_questions: ['Question 1', 'Question 2'],
        tags: ['ai', 'infrastructure'],
        experience: [
          {
            company: 'Acme Corp',
            role: 'VP Engineering',
            period: '2022-Present',
            location: 'SF',
            tags: ['leadership'],
            highlights: ['Built platform team'],
            ai_context: {
              situation: 'Situation text',
              approach: 'Approach text',
              technical_work: 'Technical work',
              lessons_learned: 'Lessons learned',
            },
          },
        ],
        skills: {
          strong: ['Python', 'Kubernetes'],
          moderate: ['Rust'],
          gaps: ['Mobile'],
        },
        fit_assessment_examples: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockApiResponse,
      });

      const result = await getProfile();

      expect(result.name).toBe('Jane Chen');
      expect(result.experience).toHaveLength(1);
      // Check camelCase transformation
      expect(result.experience[0].aiContext).toBeDefined();
      expect(result.experience[0].aiContext?.technicalWork).toBe('Technical work');
      expect(result.experience[0].aiContext?.lessonsLearned).toBe('Lessons learned');
    });

    it('should throw ApiError on 404', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Profile not found' }),
      });

      await expect(getProfile()).rejects.toThrow(ApiError);
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(getProfile()).rejects.toThrow('Network error');
    });
  });

  describe('getSuggestedQuestions', () => {
    it('should return array of question strings', async () => {
      const mockResponse = {
        questions: [
          { question: 'What is your experience?', category: 'general' },
          { question: 'Tell me about leadership', category: 'leadership' },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await getSuggestedQuestions();

      expect(result).toEqual([
        'What is your experience?',
        'Tell me about leadership',
      ]);
    });

    it('should throw ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(getSuggestedQuestions()).rejects.toThrow(ApiError);
    });
  });

  describe('assessFit', () => {
    const validJobDescription = 'VP Engineering role at AI startup requiring Kubernetes and Python experience...';

    it('should return structured fit assessment', async () => {
      const mockResponse = {
        verdict: '⭐⭐⭐⭐ Strong fit',
        key_matches: [
          'Kubernetes expertise: 5+ years',
          'Python experience: 10+ years',
          'Leadership: VP-level experience',
        ],
        gaps: ['No mobile experience'],
        recommendation: 'Strong candidate for this role',
        chunks_retrieved: 10,
        tokens_used: 450,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await assessFit(validJobDescription);

      expect(result.verdict).toBe('⭐⭐⭐⭐ Strong fit');
      expect(result.key_matches).toHaveLength(3);
      expect(result.gaps).toHaveLength(1);
      expect(result.chunks_retrieved).toBe(10);
      expect(result.tokens_used).toBe(450);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/assess-fit',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({ job_description: validJobDescription }),
        })
      );
    });

    it('should throw ApiError when API key not configured', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({
          detail: 'AI service not configured. Set OPENROUTER_API_KEY to enable real-time fit assessment.',
        }),
      });

      await expect(assessFit(validJobDescription)).rejects.toThrow(ApiError);
    });

    it('should throw ApiError on validation failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({
          detail: 'Job description too short (minimum 50 characters)',
        }),
      });

      await expect(assessFit('short')).rejects.toThrow(ApiError);
    });

    it('should throw ApiError on LLM error', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => ({
          detail: 'AI service error: OpenRouter timeout',
        }),
      });

      await expect(assessFit(validJobDescription)).rejects.toThrow(ApiError);
    });
  });

  describe('ApiError', () => {
    it('should create error with message, status, and code', () => {
      const error = new ApiError('Test error', 404, 'NOT_FOUND');

      expect(error.message).toBe('Test error');
      expect(error.status).toBe(404);
      expect(error.code).toBe('NOT_FOUND');
      expect(error.name).toBe('ApiError');
    });

    it('should be instance of Error', () => {
      const error = new ApiError('Test', 500);

      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(ApiError);
    });
  });
});

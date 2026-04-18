import { useEffect, useState } from 'react';
import {
  getProfile,
  checkHealth,
  type Experience,
  type Skills,
  type FitAssessmentExample,
  type UIConfig,
} from '@/lib/api-client';
import { registerWebMcpTools } from '@/lib/webmcp';
import { getTracer } from '@/lib/otel';
import { SpanStatusCode } from '@opentelemetry/api';

export interface Profile {
  name: string;
  title: string;
  email: string;
  linkedin: string;
  location: string;
  status: string;
  suggested_questions: string[];
  tags: string[];
  experience: Experience[];
  skills: Skills;
  fit_assessment_examples: FitAssessmentExample[];
  config?: UIConfig;
  initials: string; // Derived from name
}

// Re-export types for convenience
export type {
  Experience,
  Skills,
  FitAssessmentExample,
  UIConfig,
} from '@/lib/api-client';
export type { AIContext } from '@/lib/api-client';

export interface UseProfileResult {
  profile: Profile | null;
  loading: boolean;
  isLoading: boolean; // Alias for compatibility
  error: Error | null;
  serviceStatus: 'checking' | 'healthy' | 'degraded' | 'unavailable';
}

/**
 * Hook to load profile data from the API.
 *
 * Profile data is loaded once on mount and cached.
 * Provides loading and error states.
 * Updates document title and meta tags dynamically.
 */
export function useProfile(): UseProfileResult {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [serviceStatus, setServiceStatus] = useState<
    'checking' | 'healthy' | 'degraded' | 'unavailable'
  >('checking');

  useEffect(() => {
    let mounted = true;

    async function loadProfile() {
      const span = getTracer().startSpan('profile.fetch');
      const start = performance.now();

      try {
        setIsLoading(true);
        const data = await getProfile();

        if (!mounted) return;

        // Derive initials from name
        const initials = deriveInitials(data.name);

        setProfile({
          ...data,
          initials,
          experience: data.experience || [],
          skills: data.skills || { strong: [], moderate: [], gaps: [] },
          fit_assessment_examples: data.fit_assessment_examples || [],
          config: data.config ?? undefined,
        });
        setError(null);

        span.setAttribute(
          'response_time_ms',
          Math.round(performance.now() - start),
        );
        span.setStatus({ code: SpanStatusCode.OK });

        // Register WebMCP tools once profile loads (Chrome 146+ only)
        registerWebMcpTools();
      } catch (err) {
        if (!mounted) return;

        setError(
          err instanceof Error ? err : new Error('Failed to load profile'),
        );
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: err instanceof Error ? err.message : 'unknown',
        });
      } finally {
        span.end();
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      mounted = false;
    };
  }, []);

  // Check backend service health on mount
  useEffect(() => {
    let mounted = true;

    async function checkServiceStatus() {
      try {
        const health = await checkHealth();
        if (!mounted) return;
        if (health.status === 'healthy' && health.memvid_connected) {
          setServiceStatus('healthy');
        } else {
          setServiceStatus('degraded');
        }
      } catch {
        if (!mounted) return;
        setServiceStatus('unavailable');
      }
    }

    checkServiceStatus();
    return () => {
      mounted = false;
    };
  }, []);

  // Update document title and meta tags when profile loads
  useEffect(() => {
    if (!profile) return;

    // Update document title
    document.title = `${profile.name} — ${profile.title}`;

    // Update meta description
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription) {
      metaDescription.setAttribute(
        'content',
        `${profile.title} specializing in ${profile.tags.slice(0, 3).join(', ')}. Ask AI about my experience, skills, and fit for your role.`,
      );
    }

    // Update Open Graph tags
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) {
      ogTitle.setAttribute('content', `${profile.name} — ${profile.title}`);
    }

    const ogDescription = document.querySelector(
      'meta[property="og:description"]',
    );
    if (ogDescription) {
      ogDescription.setAttribute(
        'content',
        'Ask AI about my experience. Get honest, detailed answers about fit for your role.',
      );
    }

    // Update Twitter Card tags
    const twitterTitle = document.querySelector('meta[name="twitter:title"]');
    if (twitterTitle) {
      twitterTitle.setAttribute(
        'content',
        `${profile.name} — ${profile.title}`,
      );
    }

    const twitterDescription = document.querySelector(
      'meta[name="twitter:description"]',
    );
    if (twitterDescription) {
      twitterDescription.setAttribute(
        'content',
        'AI-queryable professional portfolio. Ask questions, get honest answers.',
      );
    }
  }, [profile]);

  return { profile, loading: isLoading, isLoading, error, serviceStatus };
}

/**
 * Derive initials from full name.
 * Examples:
 * - "Frank Schwichtenberg" → "FS"
 * - "John Doe" → "JD"
 * - "Jane" → "J"
 */
function deriveInitials(name: string): string {
  if (!name) return '';

  const parts = name.trim().split(/\s+/);

  if (parts.length === 0) return '';
  if (parts.length === 1) return parts[0][0].toUpperCase();

  // Take first letter of first and last name
  const firstInitial = parts[0][0].toUpperCase();
  const lastInitial = parts[parts.length - 1][0].toUpperCase();

  return `${firstInitial}${lastInitial}`;
}

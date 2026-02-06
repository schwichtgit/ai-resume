/**
 * API client for the AI Resume backend service.
 * Handles chat requests, health checks, and configuration.
 */

// API base URL - in development, Vite proxies /api to the backend
const API_BASE_URL = '/api/v1';

/**
 * Chat request payload
 */
export interface ChatRequest {
  message: string;
  session_id?: string;
  stream?: boolean;
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: string;
  memvid_connected: boolean;
  memvid_status?: string;
  memvid_frame_count?: number;
  memvid_file?: string;
}

/**
 * Suggested question item
 */
export interface SuggestedQuestion {
  question: string;
  category?: string;
}

/**
 * Suggested questions response
 */
export interface SuggestedQuestionsResponse {
  questions: SuggestedQuestion[];
}

/**
 * AI Context for experience entries
 */
export interface AIContext {
  situation: string;
  approach: string;
  technicalWork: string;
  lessonsLearned: string;
}

/**
 * Experience entry
 */
export interface Experience {
  company: string;
  role: string;
  period: string;
  location: string;
  tags: string[];
  highlights: string[];
  aiContext?: AIContext;
}

/**
 * Skills categorization
 */
export interface Skills {
  strong: string[];
  moderate: string[];
  gaps: string[];
}

/**
 * Fit assessment example
 */
export interface FitAssessmentExample {
  title: string;
  fit_level: string;
  role: string;
  job_description: string;
  verdict: string;
  key_matches: string;
  gaps: string;
  recommendation: string;
}

/**
 * Profile response from /api/v1/profile
 */
export interface ProfileResponse {
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
}

/**
 * Stats from streaming response
 */
export interface StreamStats {
  chunks_retrieved?: number;
  tokens_used?: number;
  elapsed_seconds?: number;
}

/**
 * Fit assessment request
 */
export interface AssessFitRequest {
  job_description: string;
}

/**
 * Fit assessment response
 */
export interface AssessFitResponse {
  verdict: string;
  key_matches: string[];
  gaps: string[];
  recommendation: string;
  chunks_retrieved: number;
  tokens_used: number;
}

/**
 * Error thrown by API client
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Check if the backend is healthy
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new ApiError(
      'Health check failed',
      response.status
    );
  }

  return response.json();
}

/**
 * Snake_case AI context as returned by the API
 */
interface ApiAIContext {
  situation?: string;
  approach?: string;
  technical_work?: string;
  lessons_learned?: string;
}

/**
 * Snake_case experience entry as returned by the API
 */
interface ApiExperience {
  company: string;
  role: string;
  period: string;
  location: string;
  tags: string[];
  highlights: string[];
  ai_context?: ApiAIContext;
}

/**
 * Transform snake_case API response to camelCase for frontend
 */
function transformExperience(apiExp: ApiExperience): Experience {
  return {
    ...apiExp,
    aiContext: apiExp.ai_context ? {
      situation: apiExp.ai_context.situation || "",
      approach: apiExp.ai_context.approach || "",
      technicalWork: apiExp.ai_context.technical_work || "",
      lessonsLearned: apiExp.ai_context.lessons_learned || "",
    } : undefined
  };
}

/**
 * Get profile metadata from the backend
 */
export async function getProfile(): Promise<ProfileResponse> {
  const response = await fetch(`${API_BASE_URL}/profile`);

  if (!response.ok) {
    throw new ApiError(
      'Failed to get profile',
      response.status
    );
  }

  const data = await response.json();

  // Transform experience array from snake_case to camelCase
  if (data.experience) {
    data.experience = data.experience.map(transformExperience);
  }

  return data;
}

/**
 * Get suggested questions from the backend
 */
export async function getSuggestedQuestions(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/suggested-questions`);

  if (!response.ok) {
    throw new ApiError(
      'Failed to get suggested questions',
      response.status
    );
  }

  const data: SuggestedQuestionsResponse = await response.json();
  // Extract just the question strings from the response
  return data.questions.map((q) => q.question);
}

/**
 * SSE event data structure from the backend
 */
interface StreamEventData {
  type: 'retrieval' | 'token' | 'stats' | 'done' | 'error';
  content?: string | null;
  chunks?: number | null;
  tokens_used?: number | null;
  elapsed_seconds?: number | null;
  error?: string | null;
}

/**
 * Stream chat response using Server-Sent Events.
 *
 * @param request Chat request with message and optional session ID
 * @param onToken Callback for each token received
 * @param onStats Callback for stats event (chunks_retrieved, tokens_used, elapsed_seconds)
 * @param onError Callback for error events
 * @param signal AbortSignal for request cancellation
 * @returns Promise that resolves when stream completes
 */
export async function streamChat(
  request: ChatRequest,
  onToken: (token: string) => void,
  onStats?: (stats: StreamStats) => void,
  onError?: (error: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({
      ...request,
      stream: true,
    }),
    signal,
  });

  if (!response.ok) {
    let errorMessage = `Chat request failed: ${response.status}`;

    try {
      const errorBody = await response.json();
      errorMessage = errorBody.detail || errorBody.message || errorMessage;
    } catch {
      // Ignore JSON parse errors
    }

    throw new ApiError(errorMessage, response.status);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new ApiError('No response body', 500);
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete lines (SSE uses double newline as delimiter)
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.trim()) continue;

        // Handle SSE format: "data: {json}"
        if (line.startsWith('data:')) {
          const data = line.slice(5).trim();

          if (data === '[DONE]') {
            return; // Stream complete
          }

          try {
            const event: StreamEventData = JSON.parse(data);

            switch (event.type) {
              case 'token':
                if (event.content) {
                  onToken(event.content);
                }
                break;

              case 'retrieval':
                // Retrieval event - could track chunks_retrieved
                if (event.chunks) {
                  onStats?.({ chunks_retrieved: event.chunks });
                }
                break;

              case 'stats':
                onStats?.({
                  chunks_retrieved: event.chunks ?? undefined,
                  tokens_used: event.tokens_used ?? undefined,
                  elapsed_seconds: event.elapsed_seconds ?? undefined,
                });
                break;

              case 'done':
                return; // Stream complete

              case 'error':
                if (event.error) {
                  onError?.(event.error);
                }
                break;
            }
          } catch {
            // Not valid JSON - treat as plain token text
            onToken(data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Non-streaming chat request (for fallback or testing)
 */
export async function chat(request: ChatRequest): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...request,
      stream: false,
    }),
  });

  if (!response.ok) {
    let errorMessage = `Chat request failed: ${response.status}`;

    try {
      const errorBody = await response.json();
      errorMessage = errorBody.detail || errorBody.message || errorMessage;
    } catch {
      // Ignore JSON parse errors
    }

    throw new ApiError(errorMessage, response.status);
  }

  const data = await response.json();
  return data.content || data.response || '';
}

/**
 * Assess fit for a job description using AI
 */
export async function assessFit(jobDescription: string): Promise<AssessFitResponse> {
  const response = await fetch(`${API_BASE_URL}/assess-fit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      job_description: jobDescription,
    }),
  });

  if (!response.ok) {
    let errorMessage = `Fit assessment failed: ${response.status}`;

    try {
      const errorBody = await response.json();
      errorMessage = errorBody.detail || errorBody.message || errorMessage;
    } catch {
      // Ignore JSON parse errors
    }

    throw new ApiError(errorMessage, response.status);
  }

  return response.json();
}

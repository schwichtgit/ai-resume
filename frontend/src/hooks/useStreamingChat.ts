/**
 * React hook for streaming chat with the AI Resume backend.
 * Handles SSE parsing, message accumulation, and graceful disconnection.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  streamChat,
  StreamStats,
  ApiError,
  RateLimitError,
} from '@/lib/api-client';
import { getTracer, isOtelInitialized } from '@/lib/otel';
import { SpanStatusCode, type Span } from '@opentelemetry/api';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface UseStreamingChatOptions {
  /** Called when stream starts */
  onStreamStart?: () => void;
  /** Called when stream completes */
  onStreamComplete?: (stats?: StreamStats) => void;
  /** Called on error */
  onError?: (error: Error) => void;
}

export interface UseStreamingChatReturn {
  /** All messages in the conversation */
  messages: Message[];
  /** Current streaming content (while streaming) */
  streamingContent: string;
  /** Whether a response is currently streaming */
  isStreaming: boolean;
  /** Whether waiting for response to start */
  isLoading: boolean;
  /** Last error that occurred */
  error: Error | null;
  /** Stats from the last response */
  stats: StreamStats | null;
  /** Session ID for conversation continuity */
  sessionId: string | null;
  /** Timestamp (ms) when rate limit expires, or null if not rate limited */
  rateLimitedUntil: number | null;
  /** Whether currently rate limited */
  isRateLimited: boolean;
  /** Send a message and stream the response */
  sendMessage: (message: string) => Promise<void>;
  /** Cancel the current stream */
  cancelStream: () => void;
  /** Clear all messages and reset state */
  clearMessages: () => void;
  /** Retry the last failed message */
  retry: () => Promise<void>;
}

/**
 * Generate a cryptographically secure random session ID (UUID v4)
 *
 * SECURITY NOTE: This function uses the Web Crypto API's crypto.getRandomValues(),
 * which is cryptographically secure in browser environments. This is the recommended
 * method for generating secure random values in browsers (unlike Math.random()).
 *
 * Reference: https://developer.mozilla.org/en-US/docs/Web/API/Crypto/getRandomValues
 * "The values are generated using a cryptographically strong random number generator"
 */
function generateSessionId(): string {
  // Use Web Crypto API for cryptographically secure random generation
  // crypto.getRandomValues() is CSPRNG (Cryptographically Secure Pseudo-Random Number Generator)
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);

  // Set UUID version 4 bits (RFC 4122 section 4.4)
  array[6] = (array[6] & 0x0f) | 0x40; // Version 4
  array[8] = (array[8] & 0x3f) | 0x80; // Variant 10

  // Convert to UUID string format
  const hex = Array.from(array, (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * Hook for managing streaming chat with the AI Resume backend.
 */
export function useStreamingChat(
  options: UseStreamingChatOptions = {},
): UseStreamingChatReturn {
  const { onStreamStart, onStreamComplete, onError } = options;

  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [stats, setStats] = useState<StreamStats | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(() =>
    generateSessionId(),
  );
  const [rateLimitedUntil, setRateLimitedUntil] = useState<number | null>(null);
  const [isRateLimited, setIsRateLimited] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const lastMessageRef = useRef<string | null>(null);

  // Flip isRateLimited off when the window expires so the UI auto-updates
  // without requiring another render to notice wall-clock time has advanced.
  useEffect(() => {
    if (rateLimitedUntil === null) {
      setIsRateLimited(false);
      return;
    }
    const remaining = rateLimitedUntil - Date.now();
    if (remaining <= 0) {
      setIsRateLimited(false);
      return;
    }
    setIsRateLimited(true);
    const timer = setTimeout(() => setIsRateLimited(false), remaining);
    return () => clearTimeout(timer);
  }, [rateLimitedUntil]);

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setIsLoading(false);
  }, []);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!message.trim() || isStreaming || isLoading || isRateLimited) return;

      // Store for retry
      lastMessageRef.current = message;

      // Add user message
      setMessages((prev) => [...prev, { role: 'user', content: message }]);
      setError(null);
      setStats(null);
      setIsLoading(true);
      setStreamingContent('');

      // Create abort controller
      abortControllerRef.current = new AbortController();

      // OTel span for the full send-receive cycle (no-op when SDK absent)
      const otelActive = isOtelInitialized();
      const span: Span | null = otelActive
        ? getTracer().startSpan('chat.send_message')
        : null;
      const fetchResolvedAt = performance.now();
      let firstTokenTime: number | null = null;

      try {
        let fullContent = '';

        await streamChat(
          {
            message,
            session_id: sessionId || undefined,
          },
          // onToken
          (token) => {
            if (!isStreaming) {
              setIsLoading(false);
              setIsStreaming(true);
              onStreamStart?.();
              if (firstTokenTime === null) {
                firstTokenTime = performance.now();
                span?.setAttribute(
                  'chat.time_to_first_token_ms',
                  Math.round(firstTokenTime - fetchResolvedAt),
                );
              }
            }
            fullContent += token;
            setStreamingContent(fullContent);
          },
          // onStats
          (newStats) => {
            setStats(newStats);
            if (newStats.tokens_used != null) {
              span?.setAttribute('chat.total_tokens', newStats.tokens_used);
            }
          },
          // onError
          (errorMessage) => {
            const err = new Error(errorMessage);
            setError(err);
            onError?.(err);
          },
          abortControllerRef.current.signal,
        );

        // Stream complete - add assistant message
        if (fullContent) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: fullContent },
          ]);
        }

        if (firstTokenTime !== null) {
          span?.setAttribute(
            'chat.streaming_duration_ms',
            Math.round(performance.now() - firstTokenTime),
          );
        }
        span?.setStatus({ code: SpanStatusCode.OK });
        onStreamComplete?.(stats || undefined);
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          // User cancelled - don't treat as error
          // Keep any partial content as the message
          if (streamingContent) {
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: streamingContent + ' [cancelled]' },
            ]);
          }
          span?.setAttribute('chat.user_cancelled', true);
          if (firstTokenTime !== null) {
            span?.setAttribute(
              'chat.streaming_duration_ms',
              Math.round(performance.now() - firstTokenTime),
            );
          }
          span?.setStatus({ code: SpanStatusCode.UNSET });
        } else if (err instanceof RateLimitError) {
          setRateLimitedUntil(Date.now() + err.retryAfter * 1000);
          const error = err as Error;
          setError(error);
          onError?.(error);
          span?.setStatus({
            code: SpanStatusCode.ERROR,
            message: 'rate_limited',
          });
        } else {
          const error = err instanceof Error ? err : new Error('Unknown error');
          setError(error);
          onError?.(error);
          span?.setStatus({
            code: SpanStatusCode.ERROR,
            message: error.message,
          });
        }
      } finally {
        span?.end();
        setIsStreaming(false);
        setIsLoading(false);
        setStreamingContent('');
        abortControllerRef.current = null;
      }
    },
    [
      isStreaming,
      isLoading,
      isRateLimited,
      sessionId,
      streamingContent,
      stats,
      onStreamStart,
      onStreamComplete,
      onError,
    ],
  );

  const clearMessages = useCallback(() => {
    cancelStream();
    setMessages([]);
    setStreamingContent('');
    setError(null);
    setStats(null);
    // Generate new session ID for fresh conversation
    setSessionId(generateSessionId());
  }, [cancelStream]);

  const retry = useCallback(async () => {
    if (!lastMessageRef.current) return;

    // Remove the last user message (we'll re-add it)
    setMessages((prev) => {
      const newMessages = [...prev];
      // Remove last user message
      for (let i = newMessages.length - 1; i >= 0; i--) {
        if (newMessages[i].role === 'user') {
          newMessages.splice(i, 1);
          break;
        }
      }
      return newMessages;
    });

    await sendMessage(lastMessageRef.current);
  }, [sendMessage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    messages,
    streamingContent,
    isStreaming,
    isLoading,
    error,
    stats,
    sessionId,
    rateLimitedUntil,
    isRateLimited,
    sendMessage,
    cancelStream,
    clearMessages,
    retry,
  };
}

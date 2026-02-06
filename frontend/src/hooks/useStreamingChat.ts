/**
 * React hook for streaming chat with the AI Resume backend.
 * Handles SSE parsing, message accumulation, and graceful disconnection.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { streamChat, StreamStats, ApiError } from '@/lib/api-client';

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
 * Generate a cryptographically secure random session ID
 */
function generateSessionId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const array = new Uint8Array(1);
    crypto.getRandomValues(array);
    const r = array[0] % 16;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Hook for managing streaming chat with the AI Resume backend.
 */
export function useStreamingChat(options: UseStreamingChatOptions = {}): UseStreamingChatReturn {
  const { onStreamStart, onStreamComplete, onError } = options;

  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [stats, setStats] = useState<StreamStats | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const lastMessageRef = useRef<string | null>(null);

  // Initialize session ID on mount
  useEffect(() => {
    setSessionId(generateSessionId());
  }, []);

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setIsLoading(false);
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim() || isStreaming || isLoading) return;

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
          }
          fullContent += token;
          setStreamingContent(fullContent);
        },
        // onStats
        (newStats) => {
          setStats(newStats);
        },
        // onError
        (errorMessage) => {
          const err = new Error(errorMessage);
          setError(err);
          onError?.(err);
        },
        abortControllerRef.current.signal
      );

      // Stream complete - add assistant message
      if (fullContent) {
        setMessages((prev) => [...prev, { role: 'assistant', content: fullContent }]);
      }
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
      } else {
        const error = err instanceof Error ? err : new Error('Unknown error');
        setError(error);
        onError?.(error);
      }
    } finally {
      setIsStreaming(false);
      setIsLoading(false);
      setStreamingContent('');
      abortControllerRef.current = null;
    }
  }, [isStreaming, isLoading, sessionId, streamingContent, stats, onStreamStart, onStreamComplete, onError]);

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
    sendMessage,
    cancelStream,
    clearMessages,
    retry,
  };
}

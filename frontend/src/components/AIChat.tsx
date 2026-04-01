import { useState, useEffect, useRef, useCallback } from 'react';
import {
  X,
  Send,
  Sparkles,
  AlertCircle,
  RefreshCw,
  Loader2,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useStreamingChat } from '@/hooks/useStreamingChat';
import {
  getSuggestedQuestions,
  checkHealth,
  submitFeedback,
} from '@/lib/api-client';
import { useProfileContext } from '@/hooks/useProfileContext';
import { getTracer } from '@/lib/otel';
import { SpanStatusCode } from '@opentelemetry/api';

interface AIChatProps {
  isOpen: boolean;
  onClose: () => void;
}

const AIChat = ({ isOpen, onClose }: AIChatProps) => {
  const { profile } = useProfileContext();
  const [input, setInput] = useState('');
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [backendStatus, setBackendStatus] = useState<
    'checking' | 'healthy' | 'degraded' | 'unavailable'
  >('checking');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [countdown, setCountdown] = useState(0);

  // Track which assistant messages have received feedback: index -> "up" | "down"
  const [feedbackGiven, setFeedbackGiven] = useState<
    Record<number, 'up' | 'down'>
  >({});

  const {
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
  } = useStreamingChat({
    onError: (err) => {
      console.error('Chat error:', err);
    },
  });

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Rate limit countdown timer
  useEffect(() => {
    if (!rateLimitedUntil) return;

    const update = () => {
      const remaining = Math.max(
        0,
        Math.ceil((rateLimitedUntil - Date.now()) / 1000),
      );
      setCountdown(remaining);
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [rateLimitedUntil]);

  // Check backend health and load suggested questions on open
  useEffect(() => {
    if (!isOpen) return;

    // Check health
    checkHealth()
      .then((health) => {
        if (health.status === 'healthy' && health.memvid_connected) {
          setBackendStatus('healthy');
        } else if (
          health.status === 'healthy' ||
          health.status === 'degraded'
        ) {
          setBackendStatus('degraded');
        } else {
          setBackendStatus('unavailable');
        }
      })
      .catch(() => {
        setBackendStatus('unavailable');
      });

    // Load suggested questions
    const sqSpan = getTracer().startSpan('suggested_questions.fetch');
    const sqStart = performance.now();
    getSuggestedQuestions()
      .then((questions) => {
        if (questions.length > 0) {
          setSuggestedQuestions(questions);
        }
        sqSpan.setAttribute(
          'response_time_ms',
          Math.round(performance.now() - sqStart),
        );
        sqSpan.setStatus({ code: SpanStatusCode.OK });
      })
      .catch(() => {
        // Keep default questions on error
        sqSpan.setStatus({
          code: SpanStatusCode.ERROR,
          message: 'fetch_failed',
        });
      })
      .finally(() => {
        sqSpan.end();
      });
  }, [isOpen]);

  const handleSubmit = useCallback(
    (question: string) => {
      if (!question.trim() || isStreaming || isLoading || isRateLimited) return;
      setInput('');
      sendMessage(question);
    },
    [isStreaming, isLoading, isRateLimited, sendMessage],
  );

  const handleFormSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      handleSubmit(input);
    },
    [handleSubmit, input],
  );

  const handleFeedback = useCallback(
    (messageIndex: number, rating: 'up' | 'down') => {
      if (feedbackGiven[messageIndex]) return;
      setFeedbackGiven((prev) => ({ ...prev, [messageIndex]: rating }));
      // Fire-and-forget
      if (sessionId) {
        submitFeedback(sessionId, String(messageIndex), rating).catch(() => {
          // Silent failure -- feedback is best-effort
        });
      }
    },
    [feedbackGiven, sessionId],
  );

  // Reset feedback state when messages are cleared
  const handleClearMessages = useCallback(() => {
    setFeedbackGiven({});
    clearMessages();
  }, [clearMessages]);

  if (!isOpen) return null;

  const isWaiting = isLoading || isStreaming;

  return (
    <div
      data-testid="chat-dialog"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4 bg-background/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="w-full sm:max-w-2xl h-[100dvh] sm:h-[80vh] bg-card border-0 sm:border sm:border-border rounded-t-2xl sm:rounded-2xl flex flex-col overflow-hidden shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent to-primary flex items-center justify-center text-accent-foreground font-serif font-bold">
              {profile?.initials || 'AI'}
            </div>
            <div>
              <p className="text-foreground font-medium">
                Ask AI About {profile?.name?.split(' ')[0] || 'Me'}
              </p>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {backendStatus === 'checking' ? (
                  <>
                    <Loader2 className="w-2 h-2 animate-spin" />
                    Connecting...
                  </>
                ) : backendStatus === 'healthy' ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                    Ready to answer your questions
                  </>
                ) : backendStatus === 'degraded' ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                    Limited functionality (semantic search unavailable)
                  </>
                ) : (
                  <>
                    <span className="w-2 h-2 rounded-full bg-destructive" />
                    Backend unavailable
                  </>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={handleClearMessages}
                className="min-w-[44px] min-h-[44px] p-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-secondary text-sm flex items-center justify-center"
                title="Clear conversation"
                aria-label="Clear conversation"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="min-w-[44px] min-h-[44px] p-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-secondary flex items-center justify-center"
              aria-label="Close chat"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div
          className="flex-1 overflow-y-auto p-4 space-y-4"
          role="log"
          aria-label="Chat messages"
        >
          {/* Backend unavailable warning */}
          {backendStatus === 'unavailable' && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>
                Backend service is unavailable. Please try again later.
              </span>
            </div>
          )}

          {/* Empty state with suggested questions */}
          {messages.length === 0 && !isWaiting && (
            <div className="h-full flex flex-col items-center justify-center text-center px-6">
              <Sparkles className="w-12 h-12 text-accent mb-4" />
              <h3 className="text-xl font-serif text-foreground mb-2">
                What would you like to know?
              </h3>
              <p className="text-muted-foreground text-sm mb-6 max-w-md">
                Ask specific questions about{' '}
                {profile?.name?.split(' ')[0] ?? 'the candidate'}'s experience,
                skills, or fit for your role. Get honest, detailed answers.
              </p>
              <div className="w-full max-w-md space-y-2">
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(q)}
                    disabled={backendStatus === 'unavailable'}
                    className="w-full text-left p-3 min-h-[44px] bg-secondary rounded-xl text-sm text-foreground hover:bg-muted transition-colors border border-transparent hover:border-accent/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    "{q}"
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                'flex flex-col',
                msg.role === 'user' ? 'items-end' : 'items-start',
              )}
            >
              <div
                className={cn(
                  'max-w-[85%] rounded-2xl px-4 py-3',
                  msg.role === 'user'
                    ? 'bg-accent text-accent-foreground rounded-br-md'
                    : 'bg-secondary text-foreground rounded-bl-md',
                )}
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </p>
              </div>
              {msg.role === 'assistant' && (
                <div className="flex gap-1 mt-1 ml-1">
                  <button
                    onClick={() => handleFeedback(i, 'up')}
                    disabled={!!feedbackGiven[i]}
                    aria-label="Thumbs up"
                    className={cn(
                      'p-1 rounded transition-colors',
                      feedbackGiven[i] === 'up'
                        ? 'text-green-500'
                        : feedbackGiven[i]
                          ? 'text-muted-foreground/30 cursor-not-allowed'
                          : 'text-muted-foreground hover:text-green-500',
                    )}
                  >
                    <ThumbsUp
                      className="w-3.5 h-3.5"
                      fill={feedbackGiven[i] === 'up' ? 'currentColor' : 'none'}
                    />
                  </button>
                  <button
                    onClick={() => handleFeedback(i, 'down')}
                    disabled={!!feedbackGiven[i]}
                    aria-label="Thumbs down"
                    className={cn(
                      'p-1 rounded transition-colors',
                      feedbackGiven[i] === 'down'
                        ? 'text-red-500'
                        : feedbackGiven[i]
                          ? 'text-muted-foreground/30 cursor-not-allowed'
                          : 'text-muted-foreground hover:text-red-500',
                    )}
                  >
                    <ThumbsDown
                      className="w-3.5 h-3.5"
                      fill={
                        feedbackGiven[i] === 'down' ? 'currentColor' : 'none'
                      }
                    />
                  </button>
                </div>
              )}
            </div>
          ))}

          {/* Streaming response */}
          {(isLoading || streamingContent) && (
            <div className="flex justify-start" aria-live="polite">
              <div className="max-w-[85%] bg-secondary text-foreground rounded-2xl rounded-bl-md px-4 py-3">
                {isLoading && !streamingContent ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                ) : (
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">
                    {streamingContent}
                    <span className="inline-block w-2 h-4 bg-accent ml-1 animate-pulse" />
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Error message */}
          {error && !isWaiting && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1">{error.message}</span>
              <button
                onClick={retry}
                className="flex items-center gap-1 px-2 py-1 bg-destructive/20 hover:bg-destructive/30 rounded transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                Retry
              </button>
            </div>
          )}

          {/* Stats display */}
          {stats && !isWaiting && messages.length > 0 && (
            <div
              data-testid="chat-stats"
              className="text-xs text-muted-foreground text-center"
            >
              {stats.chunks_retrieved && (
                <span>{stats.chunks_retrieved} sources used</span>
              )}
              {stats.elapsed_seconds && (
                <span className="ml-2">
                  ({stats.elapsed_seconds.toFixed(1)}s)
                </span>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-3 sm:p-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:pb-4 border-t border-border">
          {countdown > 0 && (
            <div className="px-4 py-2 mb-2 text-sm text-warning bg-warning/10 rounded-md text-center">
              Rate limited. Try again in {countdown} seconds
            </div>
          )}
          <form onSubmit={handleFormSubmit} className="flex gap-2 sm:gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                isWaiting
                  ? 'Waiting for response...'
                  : 'Ask a follow-up question...'
              }
              disabled={
                isWaiting || isRateLimited || backendStatus === 'unavailable'
              }
              aria-label="Chat message input"
              className="flex-1 min-h-[44px] bg-secondary rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground border border-border focus:border-accent focus:outline-none transition-colors disabled:opacity-50"
            />
            {isStreaming ? (
              <button
                type="button"
                onClick={cancelStream}
                className="min-w-[44px] min-h-[44px] px-4 py-3 bg-destructive text-destructive-foreground rounded-xl font-medium hover:opacity-90 transition-opacity"
                title="Cancel"
                aria-label="Cancel streaming response"
              >
                <X className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={
                  !input.trim() ||
                  isWaiting ||
                  isRateLimited ||
                  backendStatus === 'unavailable'
                }
                aria-label="Send message"
                className="min-w-[44px] min-h-[44px] px-4 py-3 bg-accent text-accent-foreground rounded-xl font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

export default AIChat;

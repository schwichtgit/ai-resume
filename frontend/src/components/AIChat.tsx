import { useState, useEffect, useRef, useCallback } from "react";
import { X, Send, Sparkles, AlertCircle, RefreshCw, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useStreamingChat } from "@/hooks/useStreamingChat";
import { getSuggestedQuestions, checkHealth } from "@/lib/api-client";
import { useProfileContext } from "@/context/ProfileContext";

interface AIChatProps {
  isOpen: boolean;
  onClose: () => void;
}

const AIChat = ({ isOpen, onClose }: AIChatProps) => {
  const { profile } = useProfileContext();
  const [input, setInput] = useState("");
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    streamingContent,
    isStreaming,
    isLoading,
    error,
    stats,
    sendMessage,
    cancelStream,
    clearMessages,
    retry,
  } = useStreamingChat({
    onError: (err) => {
      console.error("Chat error:", err);
    },
  });

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Check backend health and load suggested questions on open
  useEffect(() => {
    if (!isOpen) return;

    // Check health
    checkHealth()
      .then((health) => {
        setIsBackendHealthy(health.status === "healthy");
      })
      .catch(() => {
        setIsBackendHealthy(false);
      });

    // Load suggested questions
    getSuggestedQuestions()
      .then((questions) => {
        if (questions.length > 0) {
          setSuggestedQuestions(questions);
        }
      })
      .catch(() => {
        // Keep default questions on error
      });
  }, [isOpen]);

  const handleSubmit = useCallback(
    (question: string) => {
      if (!question.trim() || isStreaming || isLoading) return;
      setInput("");
      sendMessage(question);
    },
    [isStreaming, isLoading, sendMessage]
  );

  const handleFormSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      handleSubmit(input);
    },
    [handleSubmit, input]
  );

  if (!isOpen) return null;

  const isWaiting = isLoading || isStreaming;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl h-[80vh] bg-card border border-border rounded-2xl flex flex-col overflow-hidden shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent to-primary flex items-center justify-center text-accent-foreground font-serif font-bold">
              {profile?.initials || "AI"}
            </div>
            <div>
              <p className="text-foreground font-medium">
                Ask AI About {profile?.name?.split(" ")[0] || "Me"}
              </p>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {isBackendHealthy === null ? (
                  <>
                    <Loader2 className="w-2 h-2 animate-spin" />
                    Connecting...
                  </>
                ) : isBackendHealthy ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                    Ready to answer your questions
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
                onClick={clearMessages}
                className="p-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-secondary text-sm"
                title="Clear conversation"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-secondary"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Backend unavailable warning */}
          {isBackendHealthy === false && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>Backend service is unavailable. Please try again later.</span>
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
                Ask specific questions about Frank's experience, skills, or fit for your role. Get honest, detailed answers.
              </p>
              <div className="w-full max-w-md space-y-2">
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(q)}
                    disabled={isBackendHealthy === false}
                    className="w-full text-left p-3 bg-secondary rounded-xl text-sm text-foreground hover:bg-muted transition-colors border border-transparent hover:border-accent/30 disabled:opacity-50 disabled:cursor-not-allowed"
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
                "flex",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-4 py-3",
                  msg.role === "user"
                    ? "bg-accent text-accent-foreground rounded-br-md"
                    : "bg-secondary text-foreground rounded-bl-md"
                )}
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}

          {/* Streaming response */}
          {(isLoading || streamingContent) && (
            <div className="flex justify-start">
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
            <div className="text-xs text-muted-foreground text-center">
              {stats.chunks_retrieved && (
                <span>{stats.chunks_retrieved} sources used</span>
              )}
              {stats.elapsed_seconds && (
                <span className="ml-2">({stats.elapsed_seconds.toFixed(1)}s)</span>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border">
          <form onSubmit={handleFormSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isWaiting ? "Waiting for response..." : "Ask a follow-up question..."}
              disabled={isWaiting || isBackendHealthy === false}
              className="flex-1 bg-secondary rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground border border-border focus:border-accent focus:outline-none transition-colors disabled:opacity-50"
            />
            {isStreaming ? (
              <button
                type="button"
                onClick={cancelStream}
                className="px-4 py-3 bg-destructive text-destructive-foreground rounded-xl font-medium hover:opacity-90 transition-opacity"
                title="Cancel"
              >
                <X className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || isWaiting || isBackendHealthy === false}
                className="px-4 py-3 bg-accent text-accent-foreground rounded-xl font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
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

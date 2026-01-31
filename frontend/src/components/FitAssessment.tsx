import { useState } from "react";
import { FileText, Check, AlertTriangle, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useProfile } from "@/hooks/useProfile";
import { assessFit, type AssessFitResponse } from "@/lib/api-client";

type TabType = "example1" | "example2" | "custom";

const FitAssessment = () => {
  const { profile, loading: profileLoading } = useProfile();
  const [activeTab, setActiveTab] = useState<TabType>("example1");
  const [customJD, setCustomJD] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [customResult, setCustomResult] = useState<AssessFitResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyzeCustom = async () => {
    if (!customJD.trim() || customJD.trim().length < 50) {
      setError("Please enter a job description (at least 50 characters)");
      return;
    }

    setAnalyzing(true);
    setError(null);
    setCustomResult(null);

    try {
      const result = await assessFit(customJD);
      setCustomResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assess fit");
    } finally {
      setAnalyzing(false);
    }
  };

  const examples = profile?.fit_assessment_examples || [];
  const example1 = examples[0];
  const example2 = examples[1];

  // Show loading state if profile is still loading
  if (profileLoading) {
    return (
      <section id="fit-assessment" className="py-24 px-6 bg-secondary/30">
        <div className="max-w-4xl mx-auto text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-muted-foreground" />
          <p className="text-muted-foreground mt-4">Loading fit assessment examples...</p>
        </div>
      </section>
    );
  }

  // Show message if no examples available
  if (!example1 && !example2) {
    return (
      <section id="fit-assessment" className="py-24 px-6 bg-secondary/30">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-muted-foreground">No fit assessment examples available</p>
        </div>
      </section>
    );
  }

  return (
    <section id="fit-assessment" className="py-24 px-6 bg-secondary/30">
      <div className="max-w-4xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-12">
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-4">
            Honest Fit Assessment
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            See pre-analyzed examples or paste your job description for a real-time AI assessment.
          </p>
        </div>

        {/* Tab buttons */}
        <div className="flex justify-center gap-4 mb-8 flex-wrap">
          {example1 && (
            <button
              onClick={() => setActiveTab("example1")}
              className={cn(
                "px-6 py-3 rounded-xl font-medium transition-all border",
                activeTab === "example1"
                  ? "bg-success-muted text-success border-success/30"
                  : "bg-card text-muted-foreground border-border hover:border-muted-foreground"
              )}
            >
              {example1.fit_level === "strong_fit" ? "Strong Fit" : "Example 1"}
            </button>
          )}
          {example2 && (
            <button
              onClick={() => setActiveTab("example2")}
              className={cn(
                "px-6 py-3 rounded-xl font-medium transition-all border",
                activeTab === "example2"
                  ? "bg-warning-muted text-warning border-warning/30"
                  : "bg-card text-muted-foreground border-border hover:border-muted-foreground"
              )}
            >
              {example2.fit_level === "weak_fit" ? "Weak Fit" : "Example 2"}
            </button>
          )}
          <button
            onClick={() => setActiveTab("custom")}
            className={cn(
              "px-6 py-3 rounded-xl font-medium transition-all border flex items-center gap-2",
              activeTab === "custom"
                ? "bg-accent-muted text-accent border-accent/30"
                : "bg-card text-muted-foreground border-border hover:border-muted-foreground"
            )}
          >
            <Sparkles className="w-4 h-4" />
            Paste Your JD
          </button>
        </div>

        {/* Main interface */}
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          {/* Example 1 Tab */}
          {activeTab === "example1" && example1 && (
            <div className="p-6">
              {/* Job Description */}
              <div className="mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-accent" />
                  </div>
                  <span className="text-muted-foreground text-sm">
                    {example1.role}
                  </span>
                </div>
                <div className="bg-secondary rounded-xl p-4 border border-border">
                  <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                    {example1.job_description}
                  </p>
                </div>
              </div>

              {/* Assessment */}
              <div className="animate-slide-up">
                {/* Verdict */}
                <div className="flex items-center gap-4 mb-6 p-4 rounded-xl border bg-success-muted border-success/20">
                  <div className="w-12 h-12 rounded-full flex items-center justify-center bg-success/20">
                    <Check className="w-6 h-6 text-success" />
                  </div>
                  <div>
                    <h3 className="text-xl font-serif text-success">
                      {example1.verdict}
                    </h3>
                  </div>
                </div>

                {/* Key Matches */}
                <div className="space-y-4 mb-6">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                    Key Matches
                  </h4>
                  <div className="p-4 bg-secondary rounded-xl border border-border">
                    <div className="flex items-start gap-3">
                      <span className="text-success mt-0.5">✓</span>
                      <p className="text-muted-foreground text-sm leading-relaxed whitespace-pre-wrap">
                        {example1.key_matches}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Gaps */}
                {example1.gaps && (
                  <div className="space-y-4 mb-6">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                      Gaps to Note
                    </h4>
                    <div className="p-4 bg-secondary rounded-xl border border-border">
                      <div className="flex items-start gap-3">
                        <span className="text-muted-foreground mt-0.5">○</span>
                        <p className="text-muted-foreground text-sm leading-relaxed whitespace-pre-wrap">
                          {example1.gaps}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Recommendation */}
                <div className="p-4 rounded-xl border bg-success-muted border-success/20">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
                    Recommendation
                  </h4>
                  <p className="leading-relaxed text-success">
                    {example1.recommendation}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Example 2 Tab */}
          {activeTab === "example2" && example2 && (
            <div className="p-6">
              {/* Job Description */}
              <div className="mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-accent" />
                  </div>
                  <span className="text-muted-foreground text-sm">
                    {example2.role}
                  </span>
                </div>
                <div className="bg-secondary rounded-xl p-4 border border-border">
                  <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                    {example2.job_description}
                  </p>
                </div>
              </div>

              {/* Assessment */}
              <div className="animate-slide-up">
                {/* Verdict */}
                <div className="flex items-center gap-4 mb-6 p-4 rounded-xl border bg-warning-muted border-warning/20">
                  <div className="w-12 h-12 rounded-full flex items-center justify-center bg-warning/20">
                    <AlertTriangle className="w-6 h-6 text-warning" />
                  </div>
                  <div>
                    <h3 className="text-xl font-serif text-warning">
                      {example2.verdict}
                    </h3>
                  </div>
                </div>

                {/* Key Matches */}
                {example2.key_matches && (
                  <div className="space-y-4 mb-6">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                      Key Matches
                    </h4>
                    <div className="p-4 bg-secondary rounded-xl border border-border">
                      <p className="text-muted-foreground text-sm leading-relaxed whitespace-pre-wrap">
                        {example2.key_matches}
                      </p>
                    </div>
                  </div>
                )}

                {/* Gaps */}
                <div className="space-y-4 mb-6">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                    Significant Gaps
                  </h4>
                  <div className="p-4 bg-secondary rounded-xl border border-border">
                    <div className="flex items-start gap-3">
                      <span className="text-warning mt-0.5">✗</span>
                      <p className="text-muted-foreground text-sm leading-relaxed whitespace-pre-wrap">
                        {example2.gaps}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Recommendation */}
                <div className="p-4 rounded-xl border bg-warning-muted border-warning/20">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
                    Recommendation
                  </h4>
                  <p className="leading-relaxed text-warning">
                    {example2.recommendation}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Custom JD Tab */}
          {activeTab === "custom" && (
            <div className="p-6">
              {/* Input section */}
              <div className="mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-accent" />
                  </div>
                  <span className="text-muted-foreground text-sm">
                    Paste your job description
                  </span>
                </div>
                <textarea
                  value={customJD}
                  onChange={(e) => setCustomJD(e.target.value)}
                  placeholder="Paste the full job description here (minimum 50 characters)..."
                  className="w-full h-48 p-4 bg-secondary rounded-xl border border-border text-sm text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-accent/50"
                />
                {error && (
                  <p className="text-destructive text-sm mt-2">{error}</p>
                )}
                <button
                  onClick={handleAnalyzeCustom}
                  disabled={analyzing || !customJD.trim()}
                  className="mt-4 px-6 py-3 bg-accent text-accent-foreground rounded-xl font-medium hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analyzing with AI...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Analyze Fit
                    </>
                  )}
                </button>
              </div>

              {/* Results section */}
              {customResult && !analyzing && (
                <div className="animate-slide-up">
                  {/* Verdict */}
                  <div className="flex items-center gap-4 mb-6 p-4 rounded-xl border bg-accent-muted border-accent/20">
                    <div className="w-12 h-12 rounded-full flex items-center justify-center bg-accent/20">
                      <Sparkles className="w-6 h-6 text-accent" />
                    </div>
                    <div>
                      <h3 className="text-xl font-serif text-accent">
                        {customResult.verdict}
                      </h3>
                      <p className="text-muted-foreground text-sm mt-1">
                        {customResult.chunks_retrieved} context chunks • {customResult.tokens_used} tokens
                      </p>
                    </div>
                  </div>

                  {/* Key Matches */}
                  <div className="space-y-4 mb-6">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                      Key Matches
                    </h4>
                    {customResult.key_matches.map((match, i) => (
                      <div
                        key={i}
                        className="p-4 bg-secondary rounded-xl border border-border"
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-success mt-0.5">✓</span>
                          <p className="text-muted-foreground text-sm leading-relaxed">
                            {match}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Gaps */}
                  <div className="space-y-4 mb-6">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                      Gaps to Note
                    </h4>
                    {customResult.gaps.map((gap, i) => (
                      <div
                        key={i}
                        className="p-4 bg-secondary rounded-xl border border-border"
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-muted-foreground mt-0.5">○</span>
                          <p className="text-muted-foreground text-sm leading-relaxed">
                            {gap}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Recommendation */}
                  <div className="p-4 rounded-xl border bg-accent-muted border-accent/20">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
                      Recommendation
                    </h4>
                    <p className="leading-relaxed text-accent">
                      {customResult.recommendation}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom insight */}
        <div className="mt-8 text-center">
          <div className="inline-block p-6 bg-card rounded-2xl border border-border max-w-2xl">
            <p className="text-muted-foreground leading-relaxed">
              This signals something completely different than "please consider my resume."
              <br />
              <br />
              <span className="text-foreground font-medium">
                You're qualifying them. Your time is valuable too.
              </span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FitAssessment;

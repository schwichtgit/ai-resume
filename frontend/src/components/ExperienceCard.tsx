import { useState } from "react";
import { ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIContext {
  situation?: string;
  approach?: string;
  technicalWork?: string;
  lessonsLearned?: string;
}

interface ExperienceCardProps {
  company: string;
  role: string;
  period: string;
  highlights: string[];
  aiContext?: AIContext;
  index: number;
}

const hasAIContext = (ctx?: AIContext): boolean => {
  if (!ctx) return false;
  // Check if at least one field has meaningful content
  return !!(ctx.situation || ctx.approach || ctx.technicalWork || ctx.lessonsLearned);
};

const ExperienceCard = ({
  company,
  role,
  period,
  highlights,
  aiContext,
  index,
}: ExperienceCardProps) => {
  const [expanded, setExpanded] = useState(false);
  const showAIContext = hasAIContext(aiContext);

  return (
    <div
      className={cn(
        "group relative p-6 md:p-8 bg-card border border-border rounded-2xl transition-all duration-300 hover:border-accent/50",
        "animate-slide-up opacity-0"
      )}
      style={{ animationDelay: `${index * 0.1 + 0.2}s`, animationFillMode: "forwards" }}
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-6">
        <div>
          <h3 className="text-2xl font-serif text-foreground mb-1">{company}</h3>
          <p className="text-primary">{role}</p>
        </div>
        <span className="text-sm font-mono text-muted-foreground">{period}</span>
      </div>

      {/* Highlights */}
      <ul className="space-y-3 mb-6">
        {highlights.map((highlight, i) => (
          <li key={i} className="flex items-start gap-3 text-muted-foreground">
            <span className="text-accent mt-1.5">→</span>
            <span>{highlight}</span>
          </li>
        ))}
      </ul>

      {/* AI Context Toggle - only show if there's content */}
      {showAIContext && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm text-accent hover:text-accent/80 transition-colors"
        >
          <Sparkles className="w-4 h-4" />
          <span>{expanded ? "Hide" : "View"} AI Context</span>
          {expanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>
      )}

      {/* Expanded AI Context - only render fields that have content */}
      {showAIContext && expanded && aiContext && (
        <div className="mt-4 p-4 bg-secondary rounded-xl border border-border animate-slide-down">
          <div className="grid gap-4 text-sm">
            {aiContext.situation && (
              <div>
                <span className="text-text-subtle font-mono text-xs uppercase tracking-wider">
                  Situation
                </span>
                <p className="text-foreground mt-1">{aiContext.situation}</p>
              </div>
            )}
            {aiContext.approach && (
              <div>
                <span className="text-text-subtle font-mono text-xs uppercase tracking-wider">
                  Approach
                </span>
                <p className="text-foreground mt-1">{aiContext.approach}</p>
              </div>
            )}
            {aiContext.technicalWork && (
              <div>
                <span className="text-text-subtle font-mono text-xs uppercase tracking-wider">
                  Technical Work
                </span>
                <p className="text-foreground mt-1">{aiContext.technicalWork}</p>
              </div>
            )}
            {aiContext.lessonsLearned && (
              <div>
                <span className="text-text-subtle font-mono text-xs uppercase tracking-wider">
                  Lessons Learned
                </span>
                <p className="text-text-highlight mt-1 italic">"{aiContext.lessonsLearned}"</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExperienceCard;

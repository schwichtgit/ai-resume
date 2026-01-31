import { MessageSquare } from "lucide-react";
import { useProfileContext } from "@/context/ProfileContext";

interface HeroProps {
  onOpenChat: () => void;
}

const Hero = ({ onOpenChat }: HeroProps) => {
  const { profile, isLoading } = useProfileContext();

  // Show skeleton while loading
  if (isLoading) {
    return (
      <section
        id="hero"
        className="min-h-screen flex flex-col justify-center px-6 pt-20"
      >
        <div className="max-w-4xl mx-auto w-full">
          <div className="h-10 w-64 bg-secondary rounded-full mb-8 animate-pulse" />
          <div className="h-24 w-full bg-secondary rounded-lg mb-6 animate-pulse" />
          <div className="h-12 w-3/4 bg-secondary rounded-lg mb-4 animate-pulse" />
          <div className="h-8 w-1/2 bg-secondary rounded-lg mb-8 animate-pulse" />
        </div>
      </section>
    );
  }

  if (!profile) {
    return null;
  }

  return (
    <section
      id="hero"
      className="min-h-screen flex flex-col justify-center px-6 pt-20"
    >
      <div className="max-w-4xl mx-auto w-full">
        {/* Status badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-secondary rounded-full mb-8 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-success animate-pulse-soft" />
          <span className="text-sm text-muted-foreground">{profile.status}</span>
        </div>

        {/* Main heading */}
        <h1 className="text-5xl md:text-7xl lg:text-8xl font-serif text-foreground mb-6 animate-slide-up">
          {profile.name}
        </h1>

        {/* Role */}
        <p className="text-2xl md:text-3xl text-primary font-serif mb-4 animate-slide-up stagger-1">
          {profile.title}
        </p>

        {/* Location */}
        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-8 animate-slide-up stagger-2">
          {profile.location}
        </p>

        {/* Tags as badges */}
        <div className="flex flex-wrap gap-3 mb-12 animate-slide-up stagger-3">
          {profile.tags.slice(0, 6).map((tag) => (
            <span
              key={tag}
              className="px-4 py-2 bg-card border border-border rounded-full text-sm text-foreground"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* CTA Button */}
        <button
          onClick={onOpenChat}
          className="group relative inline-flex items-center gap-3 px-8 py-4 bg-accent text-accent-foreground rounded-2xl font-medium transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-accent/20 animate-slide-up stagger-4"
        >
          <MessageSquare className="w-5 h-5" />
          <span>Ask AI About Me</span>
          <span className="absolute -top-2 -right-2 px-2 py-0.5 bg-success text-primary-foreground rounded-full text-xs font-medium">
            New
          </span>
        </button>

        {/* Scroll indicator */}
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-muted-foreground animate-fade-in opacity-0" style={{ animationDelay: "1.5s", animationFillMode: "forwards" }}>
          <span className="text-xs uppercase tracking-widest">Scroll to explore</span>
          <div className="w-px h-8 bg-gradient-to-b from-muted-foreground to-transparent" />
        </div>
      </div>
    </section>
  );
};

export default Hero;

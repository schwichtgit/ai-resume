import { MessageSquare } from 'lucide-react';
import { useProfileContext } from '@/hooks/useProfileContext';

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
        className="relative min-h-screen flex flex-col justify-start px-6 pt-[max(6rem,12vh)]"
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
      className="relative min-h-screen flex flex-col justify-start px-4 sm:px-6 pt-[max(6rem,12vh)]"
    >
      <div className="max-w-4xl mx-auto w-full">
        {/* Status badge */}
        <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-2 bg-secondary rounded-full mb-6 sm:mb-8 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-success animate-pulse-soft" />
          <span className="text-xs sm:text-sm text-muted-foreground">
            {profile.status}
          </span>
        </div>

        {/* Main heading */}
        <h1 className="text-3xl sm:text-5xl md:text-7xl lg:text-8xl font-serif text-foreground mb-4 sm:mb-6 animate-slide-up break-words">
          {profile.name}
        </h1>

        {/* Role */}
        <p
          data-testid="hero-subtitle"
          className="text-xl sm:text-2xl md:text-3xl text-primary font-serif mb-3 sm:mb-4 animate-slide-up stagger-1"
        >
          {profile.title}
        </p>

        {/* Location */}
        <p className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mb-6 sm:mb-8 animate-slide-up stagger-2">
          {profile.location}
        </p>

        {/* Tags as badges */}
        <div className="flex flex-wrap gap-2 sm:gap-3 mb-8 sm:mb-12 animate-slide-up stagger-3">
          {profile.tags.slice(0, 6).map((tag) => (
            <span
              key={tag}
              className="px-3 sm:px-4 py-1.5 sm:py-2 bg-card border border-border rounded-full text-xs sm:text-sm text-foreground"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* CTA Button */}
        <button
          data-testid="hero-cta"
          onClick={onOpenChat}
          className="group relative inline-flex items-center gap-2 sm:gap-3 px-6 sm:px-8 py-3 sm:py-4 min-h-[44px] bg-accent text-accent-foreground rounded-2xl font-medium transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-accent/20 animate-slide-up stagger-4"
        >
          <MessageSquare className="w-5 h-5" />
          <span>Ask AI About Me</span>
          <span className="absolute -top-2 -right-2 px-2 py-0.5 bg-success text-primary-foreground rounded-full text-xs font-medium">
            New
          </span>
        </button>

        {/* Scroll indicator */}
        <div
          className="hidden sm:flex absolute bottom-12 left-1/2 -translate-x-1/2 flex-col items-center gap-2 text-muted-foreground animate-fade-in opacity-0"
          style={{ animationDelay: '1.5s', animationFillMode: 'forwards' }}
        >
          <span className="text-xs uppercase tracking-widest">
            Scroll to explore
          </span>
          <div className="w-px h-8 bg-gradient-to-b from-muted-foreground to-transparent" />
        </div>
      </div>
    </section>
  );
};

export default Hero;

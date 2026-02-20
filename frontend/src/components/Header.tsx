import { useState, useEffect } from 'react';
import { Menu, X, Sun, Moon } from 'lucide-react';
import { useTheme } from 'next-themes';
import { cn } from '@/lib/utils';
import { useProfileContext } from '@/context/ProfileContext';

interface HeaderProps {
  onOpenChat?: () => void;
}

const Header = ({ onOpenChat }: HeaderProps) => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { profile, isLoading } = useProfileContext();
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleAskAI = () => {
    setMobileMenuOpen(false);
    if (onOpenChat) {
      onOpenChat();
    } else {
      scrollToSection('experience');
    }
  };

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-background/80 backdrop-blur-lg border-b border-border'
          : 'bg-transparent',
      )}
    >
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md"
      >
        Skip to content
      </a>
      <nav className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        {isLoading ? (
          <div className="h-7 w-10 bg-secondary rounded animate-pulse" />
        ) : (
          <button
            onClick={() => scrollToSection('hero')}
            className="font-serif text-xl text-foreground hover:text-primary transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            {profile?.initials || ''}
          </button>
        )}

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <button
            onClick={() => scrollToSection('experience')}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Experience
          </button>
          <button
            onClick={() => scrollToSection('fit-assessment')}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Fit Check
          </button>
          <button
            onClick={handleAskAI}
            className="text-sm px-4 py-2 bg-accent text-accent-foreground rounded-full hover:opacity-90 transition-opacity"
          >
            Ask AI
          </button>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-md hover:bg-accent/10 min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            aria-label={
              theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
            }
          >
            {theme === 'dark' ? (
              <Sun className="w-5 h-5" />
            ) : (
              <Moon className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileMenuOpen}
          className="md:hidden p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-muted-foreground hover:text-foreground"
        >
          {mobileMenuOpen ? (
            <X className="w-5 h-5" />
          ) : (
            <Menu className="w-5 h-5" />
          )}
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-card border-b border-border animate-slide-down">
          <div className="px-6 py-2 space-y-1">
            <button
              onClick={() => scrollToSection('experience')}
              className="block w-full text-left min-h-[44px] py-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              Experience
            </button>
            <button
              onClick={() => scrollToSection('fit-assessment')}
              className="block w-full text-left min-h-[44px] py-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              Fit Check
            </button>
            <button
              onClick={handleAskAI}
              className="block w-full text-left min-h-[44px] py-2 text-accent hover:opacity-80 transition-opacity"
            >
              Ask AI About Me
            </button>
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="flex w-full items-center gap-2 min-h-[44px] py-2 text-muted-foreground hover:text-foreground transition-colors"
              aria-label={
                theme === 'dark'
                  ? 'Switch to light mode'
                  : 'Switch to dark mode'
              }
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;

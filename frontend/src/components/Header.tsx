import { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useProfileContext } from "@/context/ProfileContext";

interface HeaderProps {
  onOpenChat?: () => void;
}

const Header = ({ onOpenChat }: HeaderProps) => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { profile } = useProfileContext();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  const handleAskAI = () => {
    setMobileMenuOpen(false);
    if (onOpenChat) {
      onOpenChat();
    } else {
      scrollToSection("experience");
    }
  };

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-background/80 backdrop-blur-lg border-b border-border"
          : "bg-transparent"
      )}
    >
      <nav className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <button
          onClick={() => scrollToSection("hero")}
          className="font-serif text-xl text-foreground hover:text-primary transition-colors"
        >
          {profile?.initials || ""}
        </button>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <button
            onClick={() => scrollToSection("experience")}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Experience
          </button>
          <button
            onClick={() => scrollToSection("fit-assessment")}
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
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 text-muted-foreground hover:text-foreground"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-card border-b border-border animate-slide-down">
          <div className="px-6 py-4 space-y-4">
            <button
              onClick={() => scrollToSection("experience")}
              className="block w-full text-left text-muted-foreground hover:text-foreground transition-colors"
            >
              Experience
            </button>
            <button
              onClick={() => scrollToSection("fit-assessment")}
              className="block w-full text-left text-muted-foreground hover:text-foreground transition-colors"
            >
              Fit Check
            </button>
            <button
              onClick={handleAskAI}
              className="block w-full text-left text-accent hover:opacity-80 transition-opacity"
            >
              Ask AI About Me
            </button>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;

import { Github, Linkedin, Mail } from 'lucide-react';
import { useProfileContext } from '@/context/ProfileContext';

const Footer = () => {
  const { profile, isLoading } = useProfileContext();

  // Don't render footer if profile is loading or not available
  if (isLoading || !profile) {
    return null;
  }

  return (
    <footer className="py-10 sm:py-16 px-4 sm:px-6 border-t border-border">
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 sm:gap-8">
          <div className="text-center md:text-left">
            <p className="text-xl sm:text-2xl font-serif text-foreground mb-2">
              {profile.name}
            </p>
            <p className="text-sm sm:text-base text-muted-foreground">
              {profile.title}
            </p>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="GitHub"
              className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center bg-secondary rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
            {profile.linkedin && (
              <a
                href={profile.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn"
                className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center bg-secondary rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <Linkedin className="w-5 h-5" />
              </a>
            )}
            <a
              href={`mailto:${profile.email}`}
              aria-label="Email"
              className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center bg-secondary rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Mail className="w-5 h-5" />
            </a>
          </div>
        </div>

        <div className="mt-8 sm:mt-12 pt-6 sm:pt-8 border-t border-border text-center">
          <p className="text-sm text-muted-foreground">
            This portfolio demonstrates AI-queryable professional presentation.
            <br />
            <span className="text-text-subtle">
              The interface is the proof.
            </span>
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

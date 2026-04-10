import { useState } from 'react';
import { Mail, BookOpen } from 'lucide-react';

const GitHubIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
  </svg>
);

const LinkedInIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
  </svg>
);

import { useProfileContext } from '@/hooks/useProfileContext';
import { useAppVersion } from '@/hooks/useAppVersion';
import { AboutDialog } from '@/components/AboutDialog';

const Footer = () => {
  const { profile, isLoading } = useProfileContext();
  const { version } = useAppVersion();
  const [aboutOpen, setAboutOpen] = useState(false);

  if (isLoading || !profile) return null;

  return (
    <footer className="border-t bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          {/* Left column: name, title, version */}
          <div className="text-center md:text-left space-y-1">
            <p className="font-serif text-lg font-semibold text-foreground">
              {profile.name}
            </p>
            <p className="text-sm text-muted-foreground">{profile.title}</p>
            {version && (
              <p className="text-xs text-muted-foreground/60 font-mono">
                v{version.version}
              </p>
            )}
          </div>

          {/* Right column: social icons + About */}
          <div className="flex items-center justify-center md:justify-end gap-2">
            <a
              href="https://github.com/schwichtgit/ai-resume"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="GitHub"
              className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center bg-secondary rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <GitHubIcon className="w-5 h-5" />
            </a>
            {profile.linkedin && (
              <a
                href={profile.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LinkedIn"
                className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center bg-secondary rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <LinkedInIcon className="w-5 h-5" />
              </a>
            )}
            <a
              href={`mailto:${profile.email}`}
              aria-label="Email"
              className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center bg-secondary rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Mail className="w-5 h-5" />
            </a>
            <a
              href="https://medium.com/@schwicht/list/the-information-latency-of-the-professional-history-27520369c074"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Medium"
              className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center bg-secondary rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <BookOpen className="w-5 h-5" />
            </a>
            <button
              onClick={() => setAboutOpen(true)}
              className="px-3 py-2 min-h-[44px] text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              About
            </button>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t text-center">
          <p className="text-xs text-muted-foreground/60">
            This portfolio demonstrates AI-queryable professional presentation.
            The interface is the proof.
          </p>
        </div>
      </div>

      <AboutDialog open={aboutOpen} onOpenChange={setAboutOpen} />
    </footer>
  );
};

export default Footer;

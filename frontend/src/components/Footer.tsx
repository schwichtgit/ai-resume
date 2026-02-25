import { useState } from 'react';
import { Github, Linkedin, Mail, BookOpen } from 'lucide-react';
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

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ExternalLink } from 'lucide-react';
import { useAppVersion } from '@/hooks/useAppVersion';

interface AboutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AboutDialog({ open, onOpenChange }: AboutDialogProps) {
  const { version, loading } = useAppVersion();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>About AI Resume</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Version</span>
            <span className="font-mono text-xs">
              {loading ? '...' : (version?.version ?? 'dev')}
            </span>
          </div>
          {version?.commit && version.commit !== 'unknown' && (
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Commit</span>
              <span className="font-mono text-xs">
                {version.commit.slice(0, 7)}
              </span>
            </div>
          )}
          <div className="border-t pt-4 space-y-3">
            <a
              href="https://github.com/schwichtgit/ai-resume"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Source Code
            </a>
            <a
              href="https://medium.com/@schwicht/list/the-information-latency-of-the-professional-history-27520369c074"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Blog
            </a>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

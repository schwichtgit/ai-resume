import { useState, useEffect } from 'react';

export interface VersionInfo {
  version: string;
  commit: string;
  /** Configured LLM model id. Optional: an older API build omits it. */
  model?: string;
}

export function useAppVersion() {
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    fetch('/api/v1/version')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: VersionInfo) => {
        if (mounted) {
          setVersion(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) {
          setVersion({ version: 'dev', commit: 'unknown' });
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  return { version, loading };
}

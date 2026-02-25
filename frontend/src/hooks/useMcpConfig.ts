import { useState, useCallback } from 'react';

export interface McpClient {
  id: string;
  label: string;
}

export interface McpConfigTemplate {
  label: string;
  instructions: string;
  config: Record<string, unknown>;
}

export function useMcpConfig() {
  const [clients, setClients] = useState<McpClient[]>([]);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [configs, setConfigs] = useState<
    Record<string, McpConfigTemplate | null>
  >({});
  const [configLoading, setConfigLoading] = useState<Record<string, boolean>>(
    {},
  );

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/mcp/clients');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: McpClient[] = await res.json();
      setClients(data);
      setAvailable(true);
    } catch {
      setClients([]);
      setAvailable(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchConfig = useCallback(
    async (clientId: string) => {
      if (configs[clientId]) return; // Already cached

      setConfigLoading((prev) => ({ ...prev, [clientId]: true }));
      try {
        const origin = encodeURIComponent(window.location.origin);
        const res = await fetch(
          `/api/v1/mcp/config/${clientId}?origin=${origin}`,
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: McpConfigTemplate = await res.json();
        setConfigs((prev) => ({ ...prev, [clientId]: data }));
      } catch {
        setConfigs((prev) => ({ ...prev, [clientId]: null }));
      } finally {
        setConfigLoading((prev) => ({ ...prev, [clientId]: false }));
      }
    },
    [configs],
  );

  return {
    clients,
    available,
    loading,
    configs,
    configLoading,
    fetchClients,
    fetchConfig,
  };
}

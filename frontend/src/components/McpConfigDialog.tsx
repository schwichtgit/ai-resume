import { useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { useMcpConfig, type McpClient } from '@/hooks/useMcpConfig';
import { useToast } from '@/hooks/use-toast';

interface McpConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function McpConfigDialog({ open, onOpenChange }: McpConfigDialogProps) {
  const { clients, configs, configLoading, fetchClients, fetchConfig } =
    useMcpConfig();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    if (open && clients.length === 0) {
      fetchClients();
    }
  }, [open, clients.length, fetchClients]);

  // Fetch config for the default (first) tab when clients are loaded
  useEffect(() => {
    if (open && clients.length > 0 && !configs[clients[0].id]) {
      fetchConfig(clients[0].id);
    }
  }, [open, clients, configs, fetchConfig]);

  const handleTabChange = (clientId: string) => {
    if (!configs[clientId]) {
      fetchConfig(clientId);
    }
  };

  const handleCopy = async (clientId: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(clientId);
      toast({ description: 'Copied to clipboard' });
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback: select the text for manual copy
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.body.removeChild(textarea);
      toast({ description: 'Select and copy the text manually' });
    }
  };

  const defaultTab = clients[0]?.id;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>MCP Configuration</DialogTitle>
        </DialogHeader>
        {clients.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Loading configurations...
          </p>
        ) : (
          <Tabs defaultValue={defaultTab} onValueChange={handleTabChange}>
            <TabsList className="w-full">
              {clients.map((client: McpClient) => (
                <TabsTrigger
                  key={client.id}
                  value={client.id}
                  className="flex-1"
                >
                  {client.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {clients.map((client: McpClient) => (
              <TabsContent key={client.id} value={client.id} className="mt-4">
                {configLoading[client.id] ? (
                  <p className="text-sm text-muted-foreground">Loading...</p>
                ) : configs[client.id] === null ? (
                  <p className="text-sm text-destructive">
                    MCP config for &apos;{client.label}&apos; is not available
                    at this time
                  </p>
                ) : configs[client.id] ? (
                  <div className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      {configs[client.id]!.instructions}
                    </p>
                    <div className="relative">
                      <pre className="rounded-lg bg-muted p-4 text-xs font-mono overflow-x-auto">
                        {JSON.stringify(configs[client.id]!.config, null, 2)}
                      </pre>
                      <button
                        onClick={() =>
                          handleCopy(
                            client.id,
                            JSON.stringify(configs[client.id]!.config, null, 2),
                          )
                        }
                        className="absolute top-2 right-2 p-1.5 rounded-md bg-background/80 hover:bg-background text-muted-foreground hover:text-foreground transition-colors"
                        aria-label="Copy to clipboard"
                      >
                        {copiedId === client.id ? (
                          <Check className="w-4 h-4" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                ) : null}
              </TabsContent>
            ))}
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}

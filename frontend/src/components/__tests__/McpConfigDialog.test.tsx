import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { McpConfigDialog } from '../McpConfigDialog';

// Mock useMcpConfig
vi.mock('@/hooks/useMcpConfig', () => ({
  useMcpConfig: () => ({
    clients: [
      { id: 'claude-desktop', label: 'Claude Desktop' },
      { id: 'cursor', label: 'Cursor' },
    ],
    configs: {
      'claude-desktop': {
        label: 'Claude Desktop',
        instructions: 'Add this config',
        config: { mcpServers: { 'test-resume': { url: '/mcp' } } },
      },
    },
    configLoading: {},
    fetchClients: vi.fn(),
    fetchConfig: vi.fn(),
    available: true,
    loading: false,
  }),
}));

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe('McpConfigDialog', () => {
  it('renders tabs when open', () => {
    render(<McpConfigDialog open={true} onOpenChange={() => {}} />);
    expect(screen.getByText('Claude Desktop')).toBeInTheDocument();
    expect(screen.getByText('Cursor')).toBeInTheDocument();
  });

  it('renders config content', () => {
    render(<McpConfigDialog open={true} onOpenChange={() => {}} />);
    expect(screen.getByText('Add this config')).toBeInTheDocument();
  });

  it('has copy-to-clipboard button', () => {
    render(<McpConfigDialog open={true} onOpenChange={() => {}} />);
    expect(screen.getByLabelText('Copy to clipboard')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<McpConfigDialog open={false} onOpenChange={() => {}} />);
    expect(screen.queryByText('MCP Configuration')).not.toBeInTheDocument();
  });
});

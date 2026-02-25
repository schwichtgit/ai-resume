/**
 * WebMCP browser tool registration for Chrome 146+.
 * Registers resume AI tools with the browser's navigator.modelContext API.
 * Silent no-op on unsupported browsers.
 */

interface McpContent {
  type: string;
  text: string;
}

interface McpToolResult {
  content: McpContent[];
}

interface McpToolArgs {
  [key: string]: unknown;
}

interface ModelContextToolDef {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  execute(args: McpToolArgs): Promise<McpToolResult>;
}

interface ModelContext {
  registerTool(tool: ModelContextToolDef): void;
}

declare global {
  interface Navigator {
    modelContext?: ModelContext;
    modelContextTesting?: ModelContext;
  }
}

export function registerWebMcpTools(): void {
  // Prefer stable API, fall back to testing API (Chrome flag: "WebMCP for testing")
  const ctx = navigator.modelContext ?? navigator.modelContextTesting;
  if (!ctx) {
    return; // Silent no-op on unsupported browsers
  }

  try {
    ctx.registerTool({
      name: 'ask_question',
      description:
        "Ask a question about the candidate's professional experience, skills, and background. Returns an AI-generated answer based on semantic search of the candidate's resume.",
      inputSchema: {
        type: 'object',
        properties: {
          question: {
            type: 'string',
            description: 'The question to ask about the candidate',
          },
        },
        required: ['question'],
      },
      async execute(args: McpToolArgs): Promise<McpToolResult> {
        try {
          const res = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: args.question as string,
              session_id: null,
              stream: false,
            }),
          });
          const data = await res.json();
          const text = data.message ?? data.detail ?? 'No response';
          return { content: [{ type: 'text', text }] };
        } catch {
          return { content: [{ type: 'text', text: 'Failed to reach API' }] };
        }
      },
    });

    ctx.registerTool({
      name: 'assess_fit',
      description:
        'Evaluate how well the candidate fits a job description. Provide the full job description text. Returns a structured assessment with verdict, key matches, gaps, and recommendation.',
      inputSchema: {
        type: 'object',
        properties: {
          job_description: {
            type: 'string',
            description: 'The full job description text to evaluate',
          },
        },
        required: ['job_description'],
      },
      async execute(args: McpToolArgs): Promise<McpToolResult> {
        try {
          const res = await fetch('/api/v1/assess-fit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              job_description: args.job_description as string,
            }),
          });
          const data = await res.json();
          const text = data.verdict
            ? `${data.verdict}\n\nKey Matches:\n${(data.key_matches || []).map((m: string) => `- ${m}`).join('\n')}\n\nGaps:\n${(data.gaps || []).map((g: string) => `- ${g}`).join('\n')}\n\nRecommendation:\n${data.recommendation}`
            : (data.detail ?? 'No response');
          return { content: [{ type: 'text', text }] };
        } catch {
          return { content: [{ type: 'text', text: 'Failed to reach API' }] };
        }
      },
    });
  } catch (error) {
    // Silent failure -- don't break the app if registration fails
    console.warn('WebMCP tool registration failed:', error);
  }
}

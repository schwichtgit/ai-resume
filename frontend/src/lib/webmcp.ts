/**
 * WebMCP browser tool registration for Chrome 146+.
 * Registers resume AI tools with the browser's navigator.modelContext API.
 * Silent no-op on unsupported browsers.
 */

interface ModelContextTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

interface ModelContext {
  addTool(tool: ModelContextTool): void;
}

declare global {
  interface Navigator {
    modelContext?: ModelContext;
  }
}

export function registerWebMcpTools(): void {
  if (!navigator.modelContext) {
    return; // Silent no-op on unsupported browsers
  }

  try {
    navigator.modelContext.addTool({
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
    });

    navigator.modelContext.addTool({
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
    });
  } catch (error) {
    // Silent failure -- don't break the app if registration fails
    console.warn('WebMCP tool registration failed:', error);
  }
}

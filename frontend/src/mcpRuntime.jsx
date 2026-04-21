import { AssistantRuntimeProvider, useLocalRuntime } from '@assistant-ui/react';

const CHAT_URL = import.meta.env.VITE_CHAT_URL || 'http://localhost:8001/chat';

/**
 * Custom MCP adapter that connects to Azure OpenAI via our backend
 * Implements streaming support using assistant-ui's LocalRuntime
 */
const MCPAdapter = {
  async *run({ messages, abortSignal }) {
    try {
      // Convert assistant-ui message format to our backend format
      const backendMessages = messages.map(m => ({
        role: m.role,
        content: m.content
          .filter(part => part.type === 'text')
          .map(part => part.text)
          .join('')
      }));

      // Call backend chat endpoint
      const response = await fetch(CHAT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: backendMessages
        }),
        signal: abortSignal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Build the message object
      const message = {
        content: [
          { type: 'text', text: data.content }
        ]
      };

      // Attach UI components as metadata if present
      if (data.ui) {
        message.metadata = { ui: data.ui };
      }

      // Yield the complete response (backend doesn't stream yet, but this is set up for future streaming)
      yield message;

    } catch (error) {
      if (error.name === 'AbortError') {
        // Request was cancelled
        return;
      }
      throw error;
    }
  }
};

/**
 * Runtime provider component that wraps the app
 */
export function MCPRuntimeProvider({ children }) {
  const runtime = useLocalRuntime(MCPAdapter);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}

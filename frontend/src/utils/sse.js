/**
 * Server-Sent Events (SSE) utilities
 */

/**
 * Parse SSE data line
 * @param {string} line - Raw SSE line
 * @returns {Object|null} - Parsed data or null if invalid
 */
export function parseSSELine(line) {
  if (!line.startsWith('data: ')) {
    return null;
  }

  try {
    return JSON.parse(line.slice(6));
  } catch (error) {
    console.error('Failed to parse SSE data:', error, 'Line:', line);
    return null;
  }
}

/**
 * Read SSE stream and process events
 * @param {ReadableStream} stream - Response body stream
 * @param {Object} handlers - Event handlers by type
 * @returns {Promise<void>}
 */
export async function processSSEStream(stream, handlers) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode chunk and append to buffer
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer

      // Process each complete line
      for (const line of lines) {
        const data = parseSSELine(line);
        if (!data) continue;

        // Call appropriate handler based on event type
        const handler = handlers[data.type];
        if (handler) {
          await handler(data);
        } else {
          console.warn('No handler for SSE event type:', data.type);
        }
      }
    }
  } catch (error) {
    console.error('Error processing SSE stream:', error);
    if (handlers.error) {
      handlers.error({ type: 'error', message: error.message });
    }
    throw error;
  }
}

/**
 * Create SSE event handlers for chat stream
 * @param {Function} updateMessages - Function to update messages state
 * @param {number} assistantMessageId - ID of the assistant message being updated
 * @returns {Object} - Event handlers
 */
export function createChatEventHandlers(updateMessages, assistantMessageId) {
  const toolCallsMap = {};
  let uiResources = null;

  return {
    tool_call_start: (data) => {
      const tool = data.tool;
      toolCallsMap[tool.id] = tool;

      updateMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === assistantMessageId) {
            return { ...msg, toolCalls: Object.values(toolCallsMap) };
          }
          return msg;
        })
      );
    },

    tool_result: (data) => {
      const { tool_id, result } = data;
      if (toolCallsMap[tool_id]) {
        toolCallsMap[tool_id].result = result;

        // Check if result contains UI components (MCP Apps)
        if (result && result.ui) {
          console.log('UI components found in tool result:', result.ui);
          uiResources = result.ui;
        }

        updateMessages((prev) =>
          prev.map((msg) => {
            if (msg.id === assistantMessageId) {
              const updatedMsg = { ...msg, toolCalls: Object.values(toolCallsMap) };

              // Attach UI components to message if present
              if (uiResources) {
                updatedMsg.ui = uiResources;
              }

              return updatedMsg;
            }
            return msg;
          })
        );
      }
    },

    content: (data) => {
      updateMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === assistantMessageId) {
            return {
              ...msg,
              content: msg.content + data.content,
              toolCalls: msg.toolCalls, // Preserve existing tool calls
            };
          }
          return msg;
        })
      );
    },

    done: async () => {
      // Stream complete
    },

    error: (data) => {
      console.error('SSE Error:', data.message);
      updateMessages((prev) =>
        prev.map((msg) => {
          if (msg.id === assistantMessageId) {
            return { ...msg, content: `Error: ${data.message}` };
          }
          return msg;
        })
      );
    },
  };
}

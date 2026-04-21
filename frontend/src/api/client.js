/**
 * API client for backend communication
 */
import { API_CONFIG } from '../config/constants';

/**
 * Send chat message and get streaming response
 * @param {Array} messages - Array of message objects
 * @returns {Promise<Response>} - Fetch response with streaming body
 */
export async function sendChatMessage(messages) {
  const response = await fetch(API_CONFIG.CHAT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response;
}

/**
 * Fetch MCP resource content by URI
 * @param {string} uri - Resource URI (e.g., "ui://tasks/list")
 * @returns {Promise<string|null>} - HTML content or null on error
 */
export async function fetchMCPResource(uri) {
  try {
    // Convert ui://tasks/list to /ui/tasks/list
    const httpPath = uri.replace('ui://', '/ui/');
    const url = `${API_CONFIG.BASE_URL}${httpPath}`;

    const response = await fetch(url);

    if (!response.ok) {
      console.error(`Failed to fetch resource ${uri}: HTTP ${response.status}`);
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const htmlContent = await response.text();
    return htmlContent;
  } catch (error) {
    console.error(`Failed to fetch MCP resource '${uri}':`, error);
    return null;
  }
}

/**
 * Convert HTML string to blob URL for iframe rendering
 * @param {string} html - HTML content
 * @returns {string} - Blob URL
 */
export function htmlToBlobURL(html) {
  const blob = new Blob([html], { type: 'text/html' });
  return URL.createObjectURL(blob);
}

/**
 * Render UI resources from URIs
 * @param {Array<string>} uiResources - Array of resource URIs
 * @returns {Promise<Array>} - Array of rendered resource objects
 */
export async function renderUIResources(uiResources) {
  const renderedResources = [];

  for (const resourceUri of uiResources) {
    const htmlContent = await fetchMCPResource(resourceUri);
    if (htmlContent) {
      const blobUrl = htmlToBlobURL(htmlContent);
      renderedResources.push({
        type: 'iframe',
        url: blobUrl,
        resourceUri,
        height: '500px',
      });
    }
  }

  return renderedResources;
}

/**
 * Cleanup blob URLs to prevent memory leaks
 * @param {Array} messages - Array of message objects
 */
export function cleanupBlobURLs(messages) {
  messages.forEach((msg) => {
    if (msg.ui && Array.isArray(msg.ui)) {
      msg.ui.forEach((uiComponent) => {
        if (uiComponent.type === 'iframe' && uiComponent.url) {
          URL.revokeObjectURL(uiComponent.url);
        }
      });
    }
  });
}

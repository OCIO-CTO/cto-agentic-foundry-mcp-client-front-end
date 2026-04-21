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


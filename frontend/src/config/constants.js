/**
 * Application constants and configuration
 */

// API Configuration
export const API_CONFIG = {
  CHAT_URL: import.meta.env.VITE_CHAT_URL || 'http://localhost:8001/chat',
  BASE_URL: import.meta.env.VITE_MCP_URL || 'http://localhost:8001',
};

// Placeholder questions for the input field
export const PLACEHOLDER_QUESTIONS = [
  "Ask me anything...",
  "What can you help me with?",
  "How can I use the available tools?",
];

// Typewriter animation settings
export const TYPEWRITER_CONFIG = {
  TYPING_SPEED: 50, // ms per character
  PAUSE_AFTER_TYPING: 2500, // ms to pause after typing completes
};

// Animation timing
export const ANIMATION_TIMING = {
  SETTLE_DELAY: 800, // ms before UI settles after first message
};

// Background images for SVG endpoint
export const BACKGROUND_IMAGES = [
  "abstract1.svg",
  "abstract2.svg",
  "abstract3.svg",
  "abstract4.svg"
];

// UI Component settings
export const UI_SETTINGS = {
  IFRAME_DEFAULT_HEIGHT: '500px',
  IFRAME_SANDBOX: "allow-scripts allow-forms allow-popups",
};

// Message roles
export const MESSAGE_ROLES = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system',
};

// Event types for SSE streaming
export const SSE_EVENT_TYPES = {
  TOOL_CALL_START: 'tool_call_start',
  TOOL_RESULT: 'tool_result',
  CONTENT: 'content',
  DONE: 'done',
  ERROR: 'error',
};

// Speech recognition language (auto-detected, but used for configuration)
export const SPEECH_LANGUAGE = 'es-US';

// Default voice for TTS
export const DEFAULT_VOICE = 'en-US-AriaNeural';

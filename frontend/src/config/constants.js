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
  "What is FSIS and what does it do?",
  "How does FSIS ensure food safety?",
  "What are FSIS inspection regulations?",
  "Tell me about FSIS recall procedures",
  "What foods does FSIS regulate?",
  "What are the requirements for meat processing facilities?",
  "How does FSIS handle food contamination incidents?",
  "What is the role of FSIS inspectors?",
  "How can I report a food safety concern to FSIS?",
  "What are FSIS guidelines for poultry inspection?",
  "What labeling requirements does FSIS enforce?",
  "How does FSIS work with international food safety standards?",
  "What are FSIS regulations for organic meat products?",
  "How does FSIS conduct pathogen testing?",
  "What training do FSIS inspectors receive?"
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
  "cows.svg",
  "field1.svg",
  "tractor1.svg",
  "plant1.svg"
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
  UI_RESOURCES: 'ui_resources',
  CONTENT: 'content',
  DONE: 'done',
  ERROR: 'error',
};

// Speech recognition languages
export const SPEECH_LANGUAGES = {
  ENGLISH_US: 'en-US',
  SPANISH: 'es-ES',
  FRENCH: 'fr-FR',
  GERMAN: 'de-DE',
};

// Default voice for TTS
export const DEFAULT_VOICE = 'en-US-AriaNeural';

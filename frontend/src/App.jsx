import { useState, useRef, useEffect } from 'react';
import './App.css';
import logoDark from './assets/logo_dark.png';
import { VoiceInput } from './components/VoiceInput';
import { Message } from './components/Message';
import { useTypewriter } from './hooks/useTypewriter';
import { sendChatMessage } from './api/client';
import { processSSEStream, createChatEventHandlers } from './utils/sse';
import {
  API_CONFIG,
  PLACEHOLDER_QUESTIONS,
  ANIMATION_TIMING,
  MESSAGE_ROLES,
  SPEECH_LANGUAGE,
  BACKGROUND_IMAGES,
} from './config/constants';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSettled, setIsSettled] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [uiConfig, setUiConfig] = useState(null);
  const messagesEndRef = useRef(null);

  // Use dynamic placeholders from MCP server or fall back to constants
  const placeholders = uiConfig?.placeholders?.questions || PLACEHOLDER_QUESTIONS;
  const backgroundImages = uiConfig?.backgrounds?.images || BACKGROUND_IMAGES;

  // Typewriter effect for placeholder (stops when input is focused)
  const typedPlaceholder = useTypewriter(placeholders, !isInputFocused);

  // Fetch UI configuration from MCP server on startup
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/api/config`);
        if (response.ok) {
          const config = await response.json();
          setUiConfig(config);
        }
      } catch (error) {
        console.error('Failed to fetch UI config:', error);
        // Will fall back to constants
      }
    };
    fetchConfig();
  }, []);

  // Set random background image from available options
  useEffect(() => {
    const randomBackground = backgroundImages[Math.floor(Math.random() * backgroundImages.length)];
    const backgroundUrl = `${API_CONFIG.BASE_URL}/static/${randomBackground}`;
    document.body.style.backgroundImage = `url('${backgroundUrl}')`;
    document.body.classList.add('custom-bg');
  }, [backgroundImages]);

  // Handle UI settling animation
  useEffect(() => {
    if (messages.length > 0 && !isSettled) {
      const timer = setTimeout(() => {
        setIsSettled(true);
      }, ANIMATION_TIMING.SETTLE_DELAY);
      return () => clearTimeout(timer);
    }
  }, [messages.length, isSettled]);


  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /**
   * Handle chat message submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // Create user message
    const userMessage = {
      id: Date.now(),
      role: MESSAGE_ROLES.USER,
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create assistant message placeholder
    const assistantMessageId = Date.now() + 1;
    const assistantMessage = {
      id: assistantMessageId,
      role: MESSAGE_ROLES.ASSISTANT,
      content: '',
      ui: null,
      toolCalls: null,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      // Send chat message
      const response = await sendChatMessage(messages.concat(userMessage));

      // Create event handlers for SSE stream
      const eventHandlers = createChatEventHandlers(setMessages, assistantMessageId);

      // Process SSE stream
      await processSSEStream(response.body, eventHandlers);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: `Error: ${error.message}` }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle voice input transcript
   */
  const handleVoiceTranscript = (transcript) => {
    setInput(transcript);
  };

  return (
    <div
      className={`app ${messages.length > 0 ? 'has-messages' : ''} ${
        isSettled ? 'settled' : ''
      }`}
    >
      {messages.length === 0 && (
        <div className="welcome-message">
          <img src={logoDark} alt="Logo" className="welcome-logo" />
        </div>
      )}

      <div className={`chat-container ${messages.length > 0 ? 'expanded' : ''}`}>
        <div
          className="messages-viewport"
          style={{ display: messages.length > 0 ? 'flex' : 'none' }}
        >
          {messages.map((message) => (
            <Message key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="message assistant-message">
              <div className="message-content typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="composer">
          <VoiceInput
            onTranscript={handleVoiceTranscript}
            disabled={isLoading}
            language={SPEECH_LANGUAGE}
          />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={() => {
              setIsInputFocused(true);
            }}
            onBlur={() => setIsInputFocused(false)}
            placeholder={typedPlaceholder}
            disabled={isLoading}
            className="composer-input"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="composer-send"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;

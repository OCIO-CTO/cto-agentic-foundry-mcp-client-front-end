import { useState, useRef, useEffect } from 'react';
import './App.css';
import logoDark from './assets/logo_dark.png';
import { VoiceInput } from './components/VoiceInput';
import { Message } from './components/Message';
import { useTypewriter } from './hooks/useTypewriter';
import { sendChatMessage, cleanupBlobURLs, renderUIResources } from './api/client';
import { processSSEStream, createChatEventHandlers } from './utils/sse';
import {
  API_CONFIG,
  PLACEHOLDER_QUESTIONS,
  ANIMATION_TIMING,
  MESSAGE_ROLES,
  SSE_EVENT_TYPES,
  SPEECH_LANGUAGES,
  BACKGROUND_IMAGES,
} from './config/constants';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSettled, setIsSettled] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const messagesEndRef = useRef(null);

  // Typewriter effect for placeholder (stops when input is focused)
  const typedPlaceholder = useTypewriter(PLACEHOLDER_QUESTIONS, !isInputFocused);

  // Set random background image from available options
  useEffect(() => {
    const randomBackground = BACKGROUND_IMAGES[Math.floor(Math.random() * BACKGROUND_IMAGES.length)];
    const backgroundUrl = `${API_CONFIG.BASE_URL}/static/${randomBackground}`;
    document.body.style.backgroundImage = `url('${backgroundUrl}')`;
    document.body.classList.add('custom-bg');
  }, []);

  // Handle UI settling animation
  useEffect(() => {
    if (messages.length > 0 && !isSettled) {
      const timer = setTimeout(() => {
        setIsSettled(true);
      }, ANIMATION_TIMING.SETTLE_DELAY);
      return () => clearTimeout(timer);
    }
  }, [messages.length, isSettled]);

  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      cleanupBlobURLs(messages);
    };
  }, [messages]);

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

      // Add custom handler for UI resources
      const originalDoneHandler = eventHandlers[SSE_EVENT_TYPES.DONE];
      let pendingUIResources = null;

      eventHandlers[SSE_EVENT_TYPES.UI_RESOURCES] = (data) => {
        pendingUIResources = data.resources;
      };

      eventHandlers[SSE_EVENT_TYPES.DONE] = async (data) => {
        // Render UI resources if available
        if (pendingUIResources && pendingUIResources.length > 0) {
          const uiComponents = await renderUIResources(pendingUIResources);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, ui: uiComponents } : msg
            )
          );
        }

        // Call original handler
        if (originalDoneHandler) {
          await originalDoneHandler(data);
        }
      };

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
            language={SPEECH_LANGUAGES.SPANISH}
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

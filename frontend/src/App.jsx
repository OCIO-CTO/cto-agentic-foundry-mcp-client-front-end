import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';
import logoDark from './assets/logo_dark.png';

const CHAT_URL = import.meta.env.VITE_CHAT_URL || 'http://localhost:8001/chat';
const MCP_BASE_URL = import.meta.env.VITE_MCP_URL || 'http://localhost:8001';
const BACKGROUND_IMAGE = import.meta.env.VITE_BACKGROUND_IMAGE || '';

// Tool Call Drawer Component
function ToolCallDrawer({ tool }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isExecuting = !tool.result;

  return (
    <div className="tool-call-drawer">
      <div
        className="tool-call-drawer-header"
        onClick={() => tool.result && setIsExpanded(!isExpanded)}
        style={{ cursor: tool.result ? 'pointer' : 'default' }}
      >
        <div className="tool-call-drawer-title">
          {tool.result && <span className="tool-call-drawer-icon">{isExpanded ? '▼' : '▶'}</span>}
          <span className="tool-name">
            {isExecuting ? `Using ${tool.name}...` : `Used ${tool.name}`}
          </span>
        </div>
      </div>
      {isExpanded && tool.result && (
        <div className="tool-call-drawer-content">
          <div className="tool-call-section">
            <div className="tool-section-label">ARGUMENTS</div>
            <div className="tool-arguments-expanded">
              {tool.arguments && Object.entries(tool.arguments).map(([key, value]) => (
                <div key={key} className="tool-arg">
                  <span className="arg-key">{key}:</span>
                  <span className="arg-value">{JSON.stringify(value)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="tool-call-section">
            <div className="tool-section-label">RESULT</div>
            <div className="tool-result">
              <pre>{JSON.stringify(tool.result, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSettled, setIsSettled] = useState(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [typedPlaceholder, setTypedPlaceholder] = useState('');
  const [isInputFocused, setIsInputFocused] = useState(false);
  const messagesEndRef = useRef(null);

  const placeholders = [
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

  // Set custom background image if provided
  useEffect(() => {
    if (BACKGROUND_IMAGE) {
      const randomParam = `?v=${Math.random()}`;
      document.body.style.backgroundImage = `url('${BACKGROUND_IMAGE}${randomParam}')`;
      document.body.classList.add('custom-bg');
    }
  }, []);

  // Add 'settled' class after expansion animation completes (800ms)
  useEffect(() => {
    if (messages.length > 0 && !isSettled) {
      const timer = setTimeout(() => {
        setIsSettled(true);
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [messages.length, isSettled]);

  // Cleanup blob URLs when component unmounts to prevent memory leaks
  useEffect(() => {
    return () => {
      messages.forEach(msg => {
        if (msg.ui && Array.isArray(msg.ui)) {
          msg.ui.forEach(uiComponent => {
            if (uiComponent.type === 'iframe' && uiComponent.url) {
              URL.revokeObjectURL(uiComponent.url);
            }
          });
        }
      });
    };
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Typewriter effect for placeholder (stops when input is focused)
  useEffect(() => {
    if (isInputFocused) return; // Stop typing when focused

    const currentText = placeholders[placeholderIndex];
    const typingSpeed = 50; // ms per character when typing
    const pauseAfterTyping = 2500; // pause after fully typed before clearing

    let timeout;

    if (typedPlaceholder.length < currentText.length) {
      // Typing
      timeout = setTimeout(() => {
        setTypedPlaceholder(currentText.slice(0, typedPlaceholder.length + 1));
      }, typingSpeed);
    } else if (typedPlaceholder.length === currentText.length) {
      // Pause after typing complete, then clear and move to next
      timeout = setTimeout(() => {
        setTypedPlaceholder('');
        setPlaceholderIndex((prev) => (prev + 1) % placeholders.length);
      }, pauseAfterTyping);
    }

    return () => clearTimeout(timeout);
  }, [typedPlaceholder, placeholderIndex, placeholders, isInputFocused]);

  /**
   * Fetch MCP resource content by URI
   * Converts ui:// URI to HTTP endpoint
   */
  const fetchMCPResource = async (uri) => {
    try {
      // Convert ui://tasks/list to /ui/tasks/list
      const httpPath = uri.replace('ui://', '/ui/');
      const url = `${MCP_BASE_URL}${httpPath}`;

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
  };

  /**
   * Convert HTML string to blob URL for iframe rendering
   */
  const htmlToBlobURL = (html) => {
    const blob = new Blob([html], { type: 'text/html' });
    return URL.createObjectURL(blob);
  };

  /**
   * Fetch and render UI resources from _meta
   */
  const renderUIResources = async (uiResources) => {
    const renderedResources = [];

    for (const resourceUri of uiResources) {
      const htmlContent = await fetchMCPResource(resourceUri);
      if (htmlContent) {
        const blobUrl = htmlToBlobURL(htmlContent);
        renderedResources.push({
          type: 'iframe',
          url: blobUrl,
          resourceUri,
          height: '500px'
        });
      }
    }

    return renderedResources;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create assistant message placeholder
    const assistantMessageId = Date.now() + 1;
    const assistantMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      ui: null,
      toolCalls: null
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      const response = await fetch(CHAT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messages.concat(userMessage).map(m => ({
            role: m.role,
            content: m.content
          }))
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let uiResources = null;
      let toolCallsMap = {}; // Track tool calls by ID

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode the chunk and append to buffer
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'tool_call_start') {
              // New tool call started - show immediately with "Using..."
              const tool = data.tool;
              // Backend now sends arguments as parsed object, no need to parse
              toolCallsMap[tool.id] = tool;

              // Update UI immediately to show "Using tool..."
              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantMessageId) {
                  return { ...msg, toolCalls: Object.values(toolCallsMap) };
                }
                return msg;
              }));
            } else if (data.type === 'tool_result') {
              // Tool result received - update the specific tool call
              const { tool_id, result } = data;
              if (toolCallsMap[tool_id]) {
                toolCallsMap[tool_id].result = result;

                // Update UI to show result and change to "Used tool"
                setMessages(prev => prev.map(msg => {
                  if (msg.id === assistantMessageId) {
                    return { ...msg, toolCalls: Object.values(toolCallsMap) };
                  }
                  return msg;
                }));
              }
            } else if (data.type === 'ui_resources') {
              uiResources = data.resources;
            } else if (data.type === 'content') {
              // Append content chunk to assistant message (streaming tokens)
              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantMessageId) {
                  return {
                    ...msg,
                    content: msg.content + data.content,
                    toolCalls: msg.toolCalls // Preserve existing tool calls
                  };
                }
                return msg;
              }));
            } else if (data.type === 'done') {
              // Stream complete, fetch and render UI if needed
              if (uiResources) {
                const uiComponents = await renderUIResources(uiResources);
                setMessages(prev => prev.map(msg =>
                  msg.id === assistantMessageId
                    ? { ...msg, ui: uiComponents }
                    : msg
                ));
              }
            }
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError, 'Line:', line);
          }
        }
      }
    } catch (error) {
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? { ...msg, content: `Error: ${error.message}` }
          : msg
      ));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`app ${messages.length > 0 ? 'has-messages' : ''} ${isSettled ? 'settled' : ''}`}>
      {messages.length === 0 && (
        <div className="welcome-message">
          <img src={logoDark} alt="Logo" className="welcome-logo" />
        </div>
      )}

      <div className={`chat-container ${messages.length > 0 ? 'expanded' : ''}`}>
        <div className="messages-viewport" style={{ display: messages.length > 0 ? 'flex' : 'none' }}>
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.role}-message`}>
              {message.toolCalls && message.toolCalls.length > 0 && (
                <div className="tool-calls-section">
                  <div className="tool-calls-header">Tool Execution</div>
                  {message.toolCalls.map((tool) => (
                    <ToolCallDrawer key={tool.id} tool={tool} />
                  ))}
                </div>
              )}

              <div className="message-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    a: ({ node, ...props }) => (
                      <a {...props} target="_blank" rel="noopener noreferrer" />
                    )
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>

              {message.ui && (
                <div className="message-ui">
                  {(Array.isArray(message.ui) ? message.ui : [message.ui]).map((uiComponent, idx) => (
                    uiComponent.type === 'iframe' && (
                      <iframe
                        key={idx}
                        src={uiComponent.url}
                        style={{
                          width: '100%',
                          height: uiComponent.height || '400px',
                          border: 'none',
                          borderRadius: '8px',
                          marginTop: idx === 0 ? '12px' : '8px',
                          marginBottom: '8px'
                        }}
                        title={`MCP UI Resource: ${uiComponent.resourceUri || idx + 1}`}
                        sandbox="allow-scripts allow-forms allow-popups"
                      />
                    )
                  ))}
                </div>
              )}
            </div>
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
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => {
                setIsInputFocused(true);
                setTypedPlaceholder('');
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

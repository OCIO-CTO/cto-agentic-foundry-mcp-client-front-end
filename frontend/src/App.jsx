import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

const CHAT_URL = import.meta.env.VITE_CHAT_URL || 'http://localhost:8001/chat';
const MCP_BASE_URL = import.meta.env.VITE_MCP_URL || 'http://localhost:8001';
const BACKGROUND_IMAGE = import.meta.env.VITE_BACKGROUND_IMAGE || '';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Random greeting messages
  const greetings = [
    "Hello! How can I help you today?",
    "Hi there! What can I assist you with?",
    "Good to see you! What would you like to do?",
    "Welcome! How may I assist you today?",
    "Hey! What can I help you with?",
    "Greetings! What brings you here today?",
    "Hi! Ready to tackle your tasks?",
    "Hello! What's on your mind?"
  ];

  const [greeting] = useState(() =>
    greetings[Math.floor(Math.random() * greetings.length)]
  );

  // Set custom background image if provided
  useEffect(() => {
    if (BACKGROUND_IMAGE) {
      document.body.style.backgroundImage = `url('${BACKGROUND_IMAGE}')`;
      document.body.classList.add('custom-bg');
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const htmlContent = await response.text();
      return htmlContent;
    } catch (error) {
      console.error('Failed to fetch MCP resource:', error);
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
      let toolCalls = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'tool_calls') {
              toolCalls = data.tools;
              console.log('Received tool calls:', toolCalls);
              // Display tool call information immediately
              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantMessageId) {
                  console.log('Updating message with toolCalls:', toolCalls);
                  return { ...msg, toolCalls: toolCalls };
                }
                return msg;
              }));
            } else if (data.type === 'ui_resources') {
              uiResources = data.resources;
            } else if (data.type === 'content') {
              // Append content chunk to assistant message
              setMessages(prev => prev.map(msg =>
                msg.id === assistantMessageId
                  ? { ...msg, content: msg.content + data.content }
                  : msg
              ));
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
    <div className="app">
      <div className={`chat-container ${messages.length > 0 ? 'expanded' : ''}`}>
        <div className="messages-viewport">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>{greeting}</h2>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`message ${message.role}-message`}>
              <div className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>

              {message.toolCalls && (
                <div className="tool-calls">
                  {message.toolCalls.map((tool, idx) => (
                    <div key={idx} className="tool-call">
                      <div className="tool-call-header">
                        <span className="tool-icon">🔧</span>
                        <span className="tool-name">{tool.name}</span>
                      </div>
                      {tool.arguments && Object.keys(tool.arguments).length > 0 && (
                        <div className="tool-arguments">
                          {Object.entries(tool.arguments).map(([key, value]) => (
                            <div key={key} className="tool-arg">
                              <span className="arg-key">{key}:</span>
                              <span className="arg-value">{JSON.stringify(value)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

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
                        sandbox="allow-scripts allow-same-origin"
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
            placeholder="Type your message..."
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

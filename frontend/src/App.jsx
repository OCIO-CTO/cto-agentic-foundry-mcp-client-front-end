import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

const CHAT_URL = import.meta.env.VITE_CHAT_URL || 'http://localhost:8001/chat';
const MCP_BASE_URL = import.meta.env.VITE_MCP_URL || 'http://localhost:8001';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

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

      const data = await response.json();

      // Check if there are UI resources in _meta (MCP Apps spec)
      let uiComponents = null;
      if (data._meta && data._meta.ui_resources) {
        // Fetch and render UI resources
        uiComponents = await renderUIResources(data._meta.ui_resources);
      }

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.content,
        ui: uiComponents
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `Error: ${error.message}`,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>MCP Task Manager</h1>
        <p className="subtitle">Powered by FastMCP 3.0 + Azure OpenAI GPT-4o</p>
      </header>

      <div className="chat-container">
        <div className="messages-viewport">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>Welcome to MCP Task Manager</h2>
              <p>Ask me to manage your tasks with natural language:</p>
              <ul>
                <li>"Add a task to buy groceries"</li>
                <li>"Show me all my tasks"</li>
                <li>"Give me a complete overview with charts"</li>
                <li>"Mark task 1 as complete"</li>
              </ul>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`message ${message.role}-message`}>
              <div className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
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

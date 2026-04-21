# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Proxy Server application that demonstrates Azure OpenAI integration with FastMCP 3.0. The backend proxies requests to any remote MCP server (configurable), implementing agentic loops for persistent tool usage and streaming responses to a React frontend. This is a generic proxy that works with any MCP server via environment configuration.

## Architecture

```
React Frontend (Port 3001)
    |
    | HTTP POST /chat (SSE streaming)
    | Azure Speech SDK (real-time STT/TTS)
    |
FastMCP Backend (Port 8001)
    |
    |-- FastMCP 3.0 Server (proxies to remote MCP server)
    |-- Azure OpenAI (GPT-4o) (agentic loop with tool calling)
    |-- Azure Speech Services (token generation for frontend)
    |-- Remote MCP Server (configurable via REMOTE_MCP_URL)
```

## Development Commands

### Backend

```bash
# Run backend locally
cd backend
pip install -r requirements.txt
python main.py

# Backend runs on port 8000 (maps to 8001 in Docker)
```

**Environment Setup:**
- Copy `backend/.env.example` to `backend/.env`
- Configure Azure OpenAI credentials (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT)
- Configure Azure Speech Services credentials (AZURE_SPEECH_KEY, AZURE_SPEECH_REGION)
- Set REMOTE_MCP_URL for the remote MCP server to proxy

### Frontend

```bash
# Install dependencies
cd frontend
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Frontend runs on port 3000 (maps to 3001 in Docker)
```

### Docker

```bash
# Build and run both services
docker-compose up --build

# Run in detached mode
docker-compose up --build -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Ports:**
- Frontend: http://localhost:3001
- Backend: http://localhost:8001

## Code Structure

### Backend Architecture (Modular Services)

The backend follows a modular architecture with separation of concerns:

**Core Modules:**
- [backend/config.py](backend/config.py) - Centralized configuration management with validation
- [backend/auth.py](backend/auth.py) - Authentication utilities and FastAPI dependencies
- [backend/exceptions.py](backend/exceptions.py) - Custom exception hierarchy with HTTP status codes
- [backend/mcp_service.py](backend/mcp_service.py) - MCP client operations (tool listing, execution, caching)
- [backend/chat_service.py](backend/chat_service.py) - Chat streaming and agentic loop logic
- [backend/speech_service.py](backend/speech_service.py) - Azure Speech Services integration
- [backend/main.py](backend/main.py) - FastAPI routes and application setup

**Key Improvements:**
- Single Responsibility Principle: Each module has one clear purpose
- Dependency Injection: Services use config module, endpoints use auth dependencies
- Custom Exceptions: Consistent error handling with proper HTTP status codes
- Testability: Services can be tested in isolation
- Reusability: Logic can be used across different contexts

### Frontend Architecture (Component-Based)

The frontend follows React best practices with modular components and hooks:

**Structure:**
```
frontend/src/
├── App.jsx                        # Main application component
├── config/
│   └── constants.js              # Configuration and constants
├── api/
│   └── client.js                 # API communication utilities
├── utils/
│   └── sse.js                    # SSE parsing and handling
├── hooks/
│   ├── useSpeechService.js       # Azure Speech SDK integration
│   └── useTypewriter.js          # Typewriter effect logic
└── components/
    ├── Message.jsx               # Message display component
    ├── ToolCallDrawer.jsx        # Tool execution display
    ├── VoiceInput.jsx            # Microphone input
    └── TextToSpeech.jsx          # Audio playback
```

**Key Improvements:**
- Extracted reusable logic into custom hooks
- Separated API logic from UI components
- PropTypes for type safety
- Better state management and data flow
- Reduced App.jsx from 447 to 214 lines (-52%)

## Key Architecture Patterns

### 1. FastMCP 3.0 Proxy Pattern with Custom HTTP Transport

[backend/main.py](backend/main.py:40-55)

The backend mounts a remote MCP server using `create_proxy()` with `StreamableHttpTransport`, making all remote tools available locally. The namespace prefix is configurable via `MCP_NAMESPACE` environment variable.

**Key Implementation Details:**
```python
from fastmcp.client.transports import StreamableHttpTransport

transport = StreamableHttpTransport(
    config.REMOTE_MCP_URL,
    headers={
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }
)
mcp.mount(create_proxy(transport), namespace=config.MCP_NAMESPACE)
```

**Why Custom Transport is Required:**
- FastMCP 3.0 HTTP servers require specific Accept headers: `application/json, text/event-stream`
- Default proxy client may not send both MIME types
- `StreamableHttpTransport` allows header customization for compatibility with strict MCP servers

**Namespace Configuration:**
- Set `MCP_NAMESPACE=""` for no prefix (tools named as-is from remote server)
- Set `MCP_NAMESPACE="myprefix"` for prefixed tools (e.g., `myprefix_tool_name`)
- Default: empty string (no prefix)

### 2. Agentic Loop with Tool Persistence

[backend/chat_service.py](backend/chat_service.py)

The `/chat` endpoint implements an agentic loop (MAX_TOOL_ITERATIONS=10) that:
1. Sends messages to Azure OpenAI
2. If tools are called, executes them via FastMCP client
3. Appends tool results to conversation history
4. Loops back to step 1 until final answer or max iterations

**Critical:** The system prompt instructs the LLM to be persistent and try multiple tool usage strategies before giving up.

### 3. Server-Sent Events (SSE) Streaming

[backend/chat_service.py](backend/chat_service.py) and [frontend/src/utils/sse.js](frontend/src/utils/sse.js)

Real-time streaming to frontend with event types:
- `tool_call_start`: Tool execution begins
- `tool_result`: Tool execution completes
- `content`: LLM response tokens
- `done`: Stream complete

### 4. System Prompt from FastMCP

[backend/main.py](backend/main.py)

System prompts are defined as FastMCP prompts (`@mcp.prompt`) and fetched dynamically at runtime, allowing prompt changes without code deployment.

### 5. Tool Caching

[backend/mcp_service.py](backend/mcp_service.py)

Tools from the remote MCP server are cached on startup to avoid repeated fetches. Cache is managed by the `MCPService` class.

### 6. Azure Speech Services Integration

The application integrates Azure Speech Services for real-time voice interaction:

**Backend Components:**
- [backend/speech_service.py](backend/speech_service.py) - Speech synthesis and token generation
- Backend endpoints at [backend/main.py](backend/main.py):
  - `GET /api/speech/token` - Generates short-lived tokens (10min) for frontend SDK
  - `POST /api/speech/synthesize` - Text-to-speech synthesis
  - `WS /api/speech/recognize` - WebSocket fallback for speech-to-text

**Frontend Components:**
- [frontend/src/hooks/useSpeechService.js](frontend/src/hooks/useSpeechService.js) - Speech SDK integration hook
- [frontend/src/components/VoiceInput.jsx](frontend/src/components/VoiceInput.jsx) - Microphone input component
- [frontend/src/components/TextToSpeech.jsx](frontend/src/components/TextToSpeech.jsx) - Audio playback component

**Speech-to-Text Flow:**
1. User clicks microphone button in UI
2. Browser requests microphone permission
3. Frontend fetches auth token from backend
4. Azure Speech SDK connects directly to Azure Speech Services with automatic language detection
5. Language is automatically detected within first 5 seconds (supports en-US and es-US)
6. Real-time transcription streams to input field as user speaks in detected language
7. **Important:** When microphone is turned off, the transcribed text remains in the input field ready for submission. User must click "Send" to submit the query.

**Automatic Language Detection:**
- Uses Azure's at-start language identification (LID)
- Candidate languages: English (en-US) and Spanish (es-US)
- Detection occurs within first 5 seconds of speech
- No user selection required - fully automatic
- Detected language is logged to browser console for debugging
- Each new microphone session performs fresh language detection

**Text-to-Speech Flow:**
1. User clicks speaker icon on assistant message
2. Frontend uses Azure Speech SDK to synthesize audio
3. Audio plays directly in browser

**Security:**
- Speech key never exposed to frontend
- Backend generates short-lived tokens (10min expiry)
- Token endpoint has rate limiting
- CORS restrictions on all speech endpoints

## State Management

[frontend/src/App.jsx](frontend/src/App.jsx)

Uses React hooks for local state (no Redux/Zustand for chat state):
- `messages`: Chat history
- `isLoading`: Request in progress
- `input`: User input text
- Tool calls are tracked per-message

## Configuration

### Environment Variables

**Backend (.env):**
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key (required)
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint (required)
- `AZURE_OPENAI_DEPLOYMENT`: Model deployment name (default: gpt-4o)
- `AZURE_SPEECH_KEY`: Azure Speech Services key (required for voice features)
- `AZURE_SPEECH_REGION`: Azure Speech Services region (e.g., usgovvirginia)
- `REMOTE_MCP_URL`: Remote MCP server URL (supports HTTP/HTTPS MCP endpoints)
- `MCP_NAMESPACE`: Tool prefix for remote tools (empty string for no prefix, default: "fsis")
- `MCP_SERVICE_NAME`: Display name for the proxy service (default: "MCP Proxy")
- `PORT`: Backend port (default: 8000)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)
- `API_KEY`: Optional API key for authentication
- `OPENAI_TIMEOUT`: OpenAI request timeout in seconds (default: 30)
- `MAX_TOOL_ITERATIONS`: Max agentic loop iterations (default: 10)
- `RATE_LIMIT`: Rate limiting (default: 10/minute)
- `MAX_REQUEST_SIZE`: Max request body size in bytes (default: 1048576)

**Frontend (environment variables):**
- `VITE_MCP_URL`: Backend base URL (default: http://localhost:8001)
- `VITE_CHAT_URL`: Chat endpoint URL (default: http://localhost:8001/chat)

### Docker Configuration

[docker-compose.yml](docker-compose.yml)

- Backend: 1 CPU / 1GB RAM limit
- Frontend: 0.5 CPU / 512MB RAM limit
- Health checks on backend
- Custom bridge network (`mcp-network`)

## Security Features

[backend/main.py](backend/main.py:12-14,38-39,176-191)

1. **Rate Limiting:** SlowAPI with configurable limits
2. **CORS:** Restricted origins
3. **API Key Authentication:** Optional X-API-Key header
4. **Request Size Limits:** Prevents DoS attacks
5. **Message Count Limits:** Max 100 messages per request
6. **Timeouts:** Configurable OpenAI timeout

## Connecting to Custom MCP Servers

This proxy is designed to work with any MCP server that implements the Model Context Protocol over HTTP+SSE. Here's how to connect to your own MCP server:

### Step 1: Configure Environment Variables

Update `backend/.env`:
```bash
# Your MCP server endpoint
REMOTE_MCP_URL=http://localhost:3000/mcp
# or from Docker:
REMOTE_MCP_URL=http://host.docker.internal:3000/mcp

# Tool prefix (empty for no prefix)
MCP_NAMESPACE=

# Service display name
MCP_SERVICE_NAME=My Custom MCP Proxy
```

### Step 2: Ensure MCP Server Compatibility

Your MCP server must:

1. **Implement standard MCP protocol** over HTTP with SSE responses
2. **Accept proper headers:**
   - `Accept: application/json, text/event-stream` (both MIME types required)
   - `Content-Type: application/json`
3. **Support standard MCP methods:**
   - `initialize` - Session initialization
   - `tools/list` - List available tools
   - `tools/call` - Execute tools
   - `prompts/list` - List available prompts (optional)

### Step 3: Configure Host Validation (Docker Only)

If running the backend in Docker and connecting to a localhost MCP server, your MCP server must accept `host.docker.internal` as a valid host:

**For FastMCP 3.0 servers:**
```python
# Add to your MCP server's allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*",
        "http://host.docker.internal:*"
    ]
)
```

**For custom servers:** Configure your server's host validation to accept `host.docker.internal`.

### Step 4: Test Connection

1. Rebuild and restart: `docker-compose down && docker-compose up --build`
2. Check backend logs: `docker-compose logs backend | grep "Fetched.*tools"`
3. Should see: `INFO:mcp_service:Fetched N tools from FastMCP server`
4. Open frontend at http://localhost:3001 and test tool functionality

### Troubleshooting Connection

See the **MCP Server Connection Issues** section in Troubleshooting below.

## MCP Apps Support (FastMCP 3.0)

This proxy fully supports **MCP Apps** - the interactive UI extension for Model Context Protocol that allows tools to return embedded HTML visualizations (maps, charts, tables, etc.) that render in the chat interface.

### How MCP Apps Work

MCP Apps allow MCP servers to return interactive UI components alongside text responses:

1. **Server returns embedded resources**: Tools return `EmbeddedResource` objects with HTML content
2. **Client extracts and fetches**: The proxy extracts UI resources and fetches content via `resources/read` if needed
3. **Frontend renders iframes**: UI components are rendered as sandboxed iframes in the chat

### Architecture Flow

```
MCP Server Tool Response
    |
    ├── TextContent (sent to LLM + displayed)
    └── EmbeddedResource (ui:// URI with HTML)
         |
         └── Proxy extracts & fetches HTML
              |
              └── Converts to data URL (base64)
                   |
                   └── Frontend renders in iframe
```

### Backend Implementation

**Key Files:**
- [backend/mcp_service.py](backend/mcp_service.py:169-225) - Detects and processes UI resources
- [backend/chat_service.py](backend/chat_service.py:128-141) - Separates UI from LLM content
- [frontend/src/utils/sse.js](frontend/src/utils/sse.js:92-119) - Extracts UI from tool results
- [frontend/src/components/Message.jsx](frontend/src/components/Message.jsx:46-67) - Renders iframes

**Resource Processing Flow:**

```python
# In mcp_service.py execute_tool()
if item.type == 'resource':
    resource_uri = str(resource.uri)

    # Check for embedded content
    if hasattr(resource, 'text'):
        # Encode HTML to base64 data URL
        encoded = base64.b64encode(resource.text.encode('utf-8')).decode('utf-8')
        ui_component['url'] = f"data:text/html;base64,{encoded}"

    elif resource_uri.startswith('ui://'):
        # Fetch via resources/read
        fetched = await client.read_resource(resource_uri)
        # Convert to data URL
```

**Critical: Separate UI from LLM Context**

Azure OpenAI cannot parse complex nested structures with UI resources. The proxy must:
1. Extract UI components from tool results
2. Send only text content to LLM (via `result['result']` field)
3. Forward full result with UI to frontend via SSE

```python
# In chat_service.py
# Send only text to LLM
if isinstance(result, dict) and 'result' in result:
    content = result['result']  # Text only
else:
    content = json.dumps(result)

full_messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "content": content  # No UI resources
})

# But send full result including UI to frontend
yield self._create_sse_event({
    'type': 'tool_result',
    'tool_id': tc.id,
    'result': result  # Includes 'ui' field
})
```

### Frontend Implementation

**SSE Event Handler:**
```javascript
// In utils/sse.js
tool_result: (data) => {
  const { tool_id, result } = data;

  // Check if result contains UI components
  if (result && result.ui) {
    uiResources = result.ui;
  }

  // Attach UI to message
  updateMessages((prev) =>
    prev.map((msg) => {
      if (msg.id === assistantMessageId) {
        return { ...msg, ui: uiResources };
      }
      return msg;
    })
  );
}
```

**Message Rendering:**
```jsx
// In components/Message.jsx
{ui && (
  <div className="message-ui">
    {(Array.isArray(ui) ? ui : [ui]).map((uiComponent, idx) =>
      uiComponent.type === 'iframe' ? (
        <iframe
          src={uiComponent.url}  // data:text/html;base64,...
          sandbox="allow-scripts allow-same-origin"
          style={{ width: '100%', height: '600px' }}
        />
      ) : null
    )}
  </div>
)}
```

### Server Requirements

For your MCP server to work with this proxy, tools should return:

```python
from fastmcp import FastMCP
from mcp.types import TextContent, EmbeddedResource, ResourceContents

@mcp.tool()
def my_visualization_tool(arg: str):
    html_content = "<html>...</html>"  # Your interactive HTML

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text="Summary for the LLM to read"
            ),
            EmbeddedResource(
                type="resource",
                resource=ResourceContents(
                    uri="ui://my-server/my-viz",
                    mimeType="text/html",
                    text=html_content  # Embedded HTML
                )
            )
        ]
    )
```

**Alternative: Register UI resources separately**
```python
@mcp.resource("ui://my-server/{viz_id}")
def get_ui_resource(viz_id: str):
    return ResourceContents(
        uri=f"ui://my-server/{viz_id}",
        mimeType="text/html",
        text="<html>...</html>"
    )

# Tool returns just the URI
return ToolResult(
    content=[
        TextContent(text="Summary"),
        EmbeddedResource(
            type="resource",
            resource=ResourceContents(
                uri="ui://my-server/my-viz",
                mimeType="text/html"
                # No text - will be fetched via resources/read
            )
        )
    ]
)
```

### Troubleshooting MCP Apps

**UI not rendering:**
- Check browser console for iframe errors
- Verify `ui` field is present in tool result: `console.log('UI components:', result.ui)`
- Check backend logs for "Found UI resource" messages
- Ensure HTML is properly base64 encoded

**"Output validation error" when calling tools:**
- LLM is receiving UI resources in tool content
- Verify chat_service.py only sends `result['result']` to LLM, not full dict
- Check that UI is stripped before calling Azure OpenAI

**"Failed to launch 'ui://' scheme" browser error:**
- UI resources weren't converted to data URLs
- Check mcp_service.py properly encodes HTML to base64
- Verify resources/read is being called for `ui://` URIs

**Empty iframes or blank UI:**
- HTML content might be malformed
- Check CSP (Content Security Policy) restrictions
- Verify external resources (JS/CSS CDNs) are loading in iframe
- Check browser console inside iframe (right-click iframe -> Inspect)

## Common Development Tasks

### Adding New MCP Tools

Tools are defined on the remote MCP server. This proxy automatically discovers and exposes them via [backend/mcp_service.py](backend/mcp_service.py).

### Adding New Configuration

Edit [backend/config.py](backend/config.py) to add new environment variables:
```python
class Config:
    NEW_SETTING: str = os.getenv("NEW_SETTING", "default")
```

### Adding New API Endpoint

Add routes to [backend/main.py](backend/main.py):
```python
@app.get("/api/new-endpoint")
async def new_endpoint(api_key: str = Depends(verify_api_key)):
    return {"status": "ok"}
```

### Adding Custom Exceptions

Add to [backend/exceptions.py](backend/exceptions.py):
```python
class CustomError(MCPProxyException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
```

### Modifying System Prompt

Edit the `@mcp.prompt` decorator function in [backend/main.py](backend/main.py).

### Adjusting Agentic Behavior

Modify `MAX_TOOL_ITERATIONS` in [backend/config.py](backend/config.py) or environment variable.

### Adding Frontend Components

Create new components in `frontend/src/components/` with PropTypes:
```jsx
import PropTypes from 'prop-types';

export function NewComponent({ prop1 }) {
  return <div>{prop1}</div>;
}

NewComponent.propTypes = {
  prop1: PropTypes.string.isRequired,
};
```

### Styling Changes

Edit [frontend/src/App.css](frontend/src/App.css).

## Important Notes

- **Remote Tool Namespace:** Configurable via `MCP_NAMESPACE` environment variable (default: `fsis`)
- **Python Version:** Uses Python 3.11 (verify compatibility with FastMCP)
- **FastMCP Version:** Uses FastMCP 3.0.0b1 (beta version)
- **Clean Codebase:** Legacy refactoring files have been removed to maintain code clarity
- **Docker Networking:** Use `host.docker.internal` in `REMOTE_MCP_URL` when connecting to localhost MCP servers from inside Docker containers

## Testing

No automated tests currently in the codebase. For manual testing:

1. Start services: `docker-compose up --build`
2. Open frontend: http://localhost:3001
3. Test queries using available MCP tools
4. Monitor backend logs: `docker-compose logs -f backend`
5. Check tool execution in UI drawers

## Troubleshooting

**Backend won't start:**
- Check `.env` file exists with valid Azure credentials
- Verify REMOTE_MCP_URL is accessible
- Check port 8001 is available

**Frontend won't connect:**
- Verify backend health: http://localhost:8001/
- Check CORS_ORIGINS includes frontend URL
- Ensure backend is healthy before frontend starts

**Tools not working:**
- Check remote MCP server is accessible
- View backend logs for tool execution errors
- Verify tool names match remote server prefix (configured via `MCP_NAMESPACE`)
- If connecting from Docker to localhost MCP server, use `http://host.docker.internal:PORT/mcp` in `REMOTE_MCP_URL`

**MCP Server Connection Issues (`421 Misdirected Request` or `406 Not Acceptable`):**
- **Host Header Issues:** Ensure your MCP server accepts `host.docker.internal` as a valid host when running backend in Docker
  - Solution: Configure your MCP server's CORS/host validation to accept `host.docker.internal`
- **Accept Header Issues:** FastMCP HTTP clients require servers to accept `Accept: application/json, text/event-stream`
  - Solution: The backend uses `StreamableHttpTransport` to send proper headers
  - If still failing, verify your MCP server accepts both MIME types in Accept header
- **Session Management:** Some MCP servers require session initialization before tool calls
  - The proxy handles this automatically via FastMCP's session management

**Rate limiting:**
- Adjust RATE_LIMIT environment variable
- Check client IP in backend logs

**Speech recognition not working:**
- Ensure browser has microphone permissions granted
- Check AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are set correctly
- Verify backend /api/speech/token endpoint is accessible
- HTTPS required for microphone access in production (localhost exempt)
- Check browser console for Azure Speech SDK errors
- Ensure microphone is not being used by another application
- Verify language detection is working: check console logs for "Detected language: en-US" or "es-US"
- If speaking languages other than English or Spanish, recognition may fail or be inaccurate

**Text-to-speech not playing:**
- Check browser console for audio playback errors
- Verify Azure Speech Services credentials in backend
- Check browser audio permissions and volume settings

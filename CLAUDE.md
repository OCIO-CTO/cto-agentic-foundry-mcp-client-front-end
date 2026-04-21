# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Proxy Server application that demonstrates Azure OpenAI integration with FastMCP 3.0. The backend proxies requests to a remote FSIS (Food Safety and Inspection Service) MCP server, implementing agentic loops for persistent tool usage and streaming responses to a React frontend.

## Architecture

```
React Frontend (Port 3001)
    |
    | HTTP POST /chat (SSE streaming)
    |
FastMCP Backend (Port 8001)
    |
    |-- FastMCP 3.0 Server (proxies to remote MCP server)
    |-- Azure OpenAI (GPT-4o) (agentic loop with tool calling)
    |-- Remote FSIS MCP Server (search and fetch tools)
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

## Key Architecture Patterns

### 1. FastMCP 3.0 Proxy Pattern

[backend/main.py](backend/main.py:43-45)

The backend mounts a remote MCP server using `create_proxy()`, making all remote tools available locally:

```python
mcp = FastMCP("FSIS Proxy")
mcp.mount(create_proxy(REMOTE_MCP_URL), namespace="fsis")
```

Remote tools are prefixed with `fsis_` (e.g., `fsis_search`, `fsis_fetch`).

### 2. Agentic Loop with Tool Persistence

[backend/main.py](backend/main.py:257-341)

The `/chat` endpoint implements an agentic loop (MAX_TOOL_ITERATIONS=10) that:
1. Sends messages to Azure OpenAI
2. If tools are called, executes them via FastMCP client
3. Appends tool results to conversation history
4. Loops back to step 1 until final answer or max iterations

**Critical:** The system prompt at [backend/main.py](backend/main.py:46-70) instructs the LLM to be persistent and try multiple search strategies before giving up.

### 3. Server-Sent Events (SSE) Streaming

[backend/main.py](backend/main.py:255-355)

Real-time streaming to frontend with event types:
- `tool_call_start`: Tool execution begins
- `tool_result`: Tool execution completes
- `content`: LLM response tokens
- `done`: Stream complete

Frontend handles these events at [frontend/src/App.jsx](frontend/src/App.jsx:263-320).

### 4. System Prompt from FastMCP

[backend/main.py](backend/main.py:77-95)

System prompts are defined as FastMCP prompts (`@mcp.prompt`) and fetched dynamically at runtime, allowing prompt changes without code deployment.

### 5. Tool Caching

[backend/main.py](backend/main.py:98-124)

Tools from the remote MCP server are cached on startup to avoid repeated fetches. Cache is global (`tools_cache`).

## Frontend Architecture

### State Management

[frontend/src/App.jsx](frontend/src/App.jsx:55-62)

Uses React hooks for local state (no Redux/Zustand for chat state):
- `messages`: Chat history
- `isLoading`: Request in progress
- `input`: User input text
- Tool calls are tracked per-message

### SSE Stream Handling

[frontend/src/App.jsx](frontend/src/App.jsx:243-321)

The frontend reads SSE streams using `ReadableStream` API and updates UI in real-time:
1. Parses `data:` lines as JSON
2. Updates tool call drawers as tools execute
3. Streams assistant response tokens
4. Renders UI components on completion

### Tool Call UI

[frontend/src/App.jsx](frontend/src/App.jsx:11-52)

`ToolCallDrawer` component shows:
- Tool name with "Using..." (executing) or "Used" (complete)
- Expandable drawer with arguments and results
- Real-time updates as tools execute

## Configuration

### Environment Variables

**Backend (.env):**
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key (required)
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint (required)
- `AZURE_OPENAI_DEPLOYMENT`: Model deployment name (default: gpt-4o)
- `REMOTE_MCP_URL`: Remote MCP server URL (default: FSIS server)
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
- `VITE_BACKGROUND_IMAGE`: Optional background image URL

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

## Common Development Tasks

### Adding New MCP Tools

Tools are defined on the remote MCP server. This proxy automatically discovers and exposes them.

### Modifying System Prompt

Edit the `@mcp.prompt` decorator function at [backend/main.py](backend/main.py:46-70).

### Adjusting Agentic Behavior

Modify `MAX_TOOL_ITERATIONS` in environment or code at [backend/main.py](backend/main.py:37).

### Styling Changes

Edit [frontend/src/App.css](frontend/src/App.css) (note: there's also an [App.css.backup](frontend/src/App.css.backup)).

## Important Notes

- **No Skills Directory:** This project doesn't use MCP skills (mentioned in SKILLS_GUIDE.md but not implemented here)
- **No Direct Task Storage:** Unlike the example in README.md, this proxy doesn't manage tasks directly
- **Remote Tool Namespace:** All remote tools are prefixed with `fsis_`
- **Python Version:** Uses Python 3.13.3 (verify compatibility with FastMCP)
- **FastMCP Beta:** Uses FastMCP 3.0.0b1 (beta version)

## Testing

No automated tests currently in the codebase. For manual testing:

1. Start services: `docker-compose up --build`
2. Open frontend: http://localhost:3001
3. Test FSIS queries (examples in placeholders)
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
- Verify tool names match remote server (use `fsis_` prefix)

**Rate limiting:**
- Adjust RATE_LIMIT environment variable
- Check client IP in backend logs

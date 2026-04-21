# CTO Agentic Foundry MCP Client Front End

A web-based MCP client that proxies requests to a remote MCP server and exposes them through a conversational interface backed by Azure OpenAI. Designed to connect to the **NASS (National Agricultural Statistics Service) MCP server**, but works with any MCP server that speaks HTTP + SSE.

## Architecture

```
React Frontend (Port 3001)
    |
    | HTTP POST /chat (SSE streaming)
    | Azure Speech SDK (real-time STT/TTS)
    |
FastMCP Backend (Port 8001)
    |
    |-- FastMCP 3.0 RC1 proxy (to remote MCP server)
    |-- Azure OpenAI GPT-4o (agentic loop with tool calling)
    |-- Azure Speech Services (token generation for frontend)
    |
    v
NASS MCP Server (configurable via REMOTE_MCP_URL)
```

## Features

- **Generic MCP proxy** — point at any MCP server via `REMOTE_MCP_URL`
- **Agentic tool loop** — the LLM can chain tool calls up to `MAX_TOOL_ITERATIONS` times per turn
- **Streaming responses** — Server-Sent Events push tokens, tool calls, and results to the UI as they happen
- **MCP Apps support** — tools can return interactive HTML that renders in the chat as sandboxed iframes
- **Voice input/output** — Azure Speech Services with automatic English/Spanish language detection
- **Dynamic UI config** — the remote MCP server can supply its own branding, placeholder questions, and background images via `ui://config/*` resources

## Quick Start

### Prerequisites
- Docker Desktop
- Azure OpenAI deployment (GPT-4o)
- Azure Speech Services resource (optional, for voice)
- A reachable MCP server (e.g. the NASS MCP server)

### Configure

Copy `backend/.env.example` to `backend/.env` and fill in:

```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o

AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=...

REMOTE_MCP_URL=https://your-nass-mcp-server/mcp
MCP_NAMESPACE=
MCP_SERVICE_NAME=NASS Assistant
```

### Run

```bash
docker-compose up --build
```

- Frontend: http://localhost:3001
- Backend:  http://localhost:8001

## Development

### Backend (local)

```bash
cd backend
pip install -r requirements.txt
python main.py   # runs on :8000
```

### Frontend (local)

```bash
cd frontend
npm install
npm run dev      # runs on :3000
```

## Project Structure

```
mcp-demo/
├── backend/
│   ├── main.py              # FastAPI routes + app setup
│   ├── config.py            # Centralized configuration
│   ├── mcp_service.py       # MCP client (proxy, tool exec, UI extraction)
│   ├── chat_service.py      # Agentic loop + SSE streaming
│   ├── speech_service.py    # Azure Speech integration
│   ├── auth.py              # API-key dependency
│   ├── exceptions.py        # Custom exception hierarchy
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/      # Message, ToolCallDrawer, VoiceInput, ...
│   │   ├── hooks/           # useSpeechService, useTypewriter
│   │   ├── api/             # Backend client
│   │   ├── utils/           # SSE parser
│   │   └── config/          # Constants
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Connecting to a Different MCP Server

Set `REMOTE_MCP_URL` to any MCP server that:

1. Speaks MCP over HTTP with SSE responses
2. Accepts `Accept: application/json, text/event-stream` headers
3. Implements the standard MCP methods (`initialize`, `tools/list`, `tools/call`)

For a server running on the Docker host, use `http://host.docker.internal:PORT/mcp`.


## Key Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI credential | required |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | required |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | `gpt-4o` |
| `AZURE_SPEECH_KEY` | Speech Services key | required for voice |
| `AZURE_SPEECH_REGION` | Speech Services region | required for voice |
| `REMOTE_MCP_URL` | Upstream MCP server URL | required |
| `MCP_NAMESPACE` | Tool name prefix | `""` (none) |
| `MCP_SERVICE_NAME` | Display name in UI | `MCP Proxy` |
| `MAX_TOOL_ITERATIONS` | Agentic loop cap | `10` |
| `RATE_LIMIT` | Per-IP request limit | `10/minute` |
| `CORS_ORIGINS` | Allowed origins | localhost dev |

## Technology Stack

- **Backend**: FastMCP 3.0 RC1, FastAPI, Azure OpenAI SDK, Azure Speech SDK, Python 3.11
- **Frontend**: React 18, Vite, Azure Speech SDK (browser)
- **Infra**: Docker Compose, nginx (frontend serving)

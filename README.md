# MCP Task Manager Demo

A demonstration of the Model Context Protocol (MCP) using FastMCP 3.0 for the backend and React for the frontend UI.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  React Frontend │────────>│  FastMCP Backend │
│   (Port 3000)   │  HTTP   │   (Port 8000)    │
│                 │ <────── │                  │
└─────────────────┘  JSON   └──────────────────┘
                    RPC MCP
```

## Components

### Backend (FastMCP 3.0)
- **Framework**: FastMCP 3.0 + FastAPI
- **Language**: Python 3.11
- **Port**: 8000
- **Endpoints**:
  - `/` - API info
  - `/mcp` - MCP JSON-RPC endpoint

### Frontend (React)
- **Framework**: React 18 + Vite
- **Port**: 3000
- **Features**: Chat-based task management interface

## MCP Tools Available

1. **add_task** - Create a new task
2. **list_tasks** - List all tasks (with optional filter)
3. **complete_task** - Mark a task as complete
4. **delete_task** - Remove a task
5. **get_statistics** - Get task statistics

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Ports 3000 and 8000 available

### Run with Docker Compose

```bash
cd mcp-demo
docker-compose up --build
```

### Access the Application

Open your browser to: http://localhost:3000

### Example Commands

Try these commands in the chat interface:

```
add task Buy groceries
add task Write documentation with description Complete the README file
list tasks
complete task 1
list completed
stats
delete task 2
help
```

## Project Structure

```
mcp-demo/
├── backend/
│   ├── main.py              # FastMCP server implementation
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── mcpClient.js     # MCP client implementation
│   │   ├── mcpRuntime.jsx   # Runtime adapter for chat
│   │   ├── App.jsx          # Main UI component
│   │   ├── App.css          # Styles
│   │   └── main.jsx         # Entry point
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Development

### Run Backend Locally

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

## How It Works

1. **User Input**: User types a command in the chat interface
2. **Command Parsing**: Frontend parses natural language into MCP tool calls
3. **JSON-RPC Request**: Frontend sends JSON-RPC request to backend
4. **Tool Execution**: Backend executes the MCP tool
5. **Response**: Backend returns result as JSON-RPC response
6. **Display**: Frontend displays the result in chat format

## Technology Stack

- **FastMCP 3.0**: Model Context Protocol server framework
- **FastAPI**: Web framework for Python
- **React**: UI library
- **Vite**: Build tool and dev server
- **Docker**: Containerization

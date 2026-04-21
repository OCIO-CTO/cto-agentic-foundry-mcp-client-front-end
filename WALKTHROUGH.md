# MCP Task Manager - Complete Code Walkthrough

## Overview

This application demonstrates the Model Context Protocol (MCP) by building a task management system with:
- **Backend**: FastMCP 3.0 server exposing task management tools
- **Frontend**: React chat interface that communicates with MCP server
- **Deployment**: Docker containers for easy deployment

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI applications to interact with tools and data sources. Think of it as an API specifically designed for AI agents and LLMs.

**Key Concepts:**
- **Tools**: Functions that can be called by AI agents (like "add_task", "list_tasks")
- **JSON-RPC**: Communication protocol used between client and server
- **Resources**: Data that can be accessed (not used in this demo)
- **Prompts**: Reusable prompt templates (not used in this demo)

## Architecture Deep Dive

```
User Input
    |
    v
React Frontend (Port 3001)
    |
    | HTTP POST (JSON-RPC)
    v
FastMCP Backend (Port 8001)
    |
    | Executes MCP Tool
    v
In-Memory Task Storage
    |
    | Returns Result
    v
React Frontend
    |
    v
Display to User
```

## Backend Walkthrough

### File: [backend/main.py](mcp-demo/backend/main.py)

#### 1. Import and Setup

```python
from fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

mcp = FastMCP("Task Manager MCP Server")
```

**What's happening:**
- `FastMCP` is the main class that handles MCP protocol
- `FastAPI` is used to create the HTTP server
- `CORSMiddleware` allows the frontend to communicate with backend
- `uvicorn` is the ASGI server that runs our application

#### 2. Data Storage

```python
tasks = []
task_id_counter = 1
```

**What's happening:**
- Simple in-memory storage (resets when server restarts)
- In production, you'd use a database like PostgreSQL or MongoDB
- `task_id_counter` ensures each task gets a unique ID

#### 3. Defining MCP Tools

```python
@mcp.tool
def add_task(title: str, description: str = "") -> dict:
    """
    Add a new task to the task list.

    Args:
        title: The title of the task
        description: Optional description of the task

    Returns:
        The created task with its ID
    """
    global task_id_counter
    task = {
        "id": task_id_counter,
        "title": title,
        "description": description,
        "completed": False
    }
    tasks.append(task)
    task_id_counter += 1
    return task
```

**What's happening:**
- `@mcp.tool` decorator registers this function as an MCP tool
- The docstring is IMPORTANT - MCP uses it to describe the tool to AI agents
- Type hints (`title: str`) help MCP validate inputs
- FastMCP automatically creates JSON schema from the function signature

**Why this matters:**
When an AI agent asks "what tools are available?", FastMCP sends:
```json
{
  "name": "add_task",
  "description": "Add a new task to the task list.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "description": {"type": "string"}
    },
    "required": ["title"]
  }
}
```

#### 4. Other Tools

**list_tasks**: Returns all tasks or filters by completion status
```python
@mcp.tool
def list_tasks(completed: bool = None) -> list:
    if completed is None:
        return tasks
    return [task for task in tasks if task["completed"] == completed]
```

**complete_task**: Marks a task as done
```python
@mcp.tool
def complete_task(task_id: int) -> dict:
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            return task
    raise ValueError(f"Task with ID {task_id} not found")
```

**delete_task**: Removes a task
**get_statistics**: Returns task counts

#### 5. FastAPI Integration

```python
app = FastAPI(title="MCP Task Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp.mount(app)
```

**What's happening:**
- Creates a FastAPI application
- CORS middleware allows frontend to make requests
- `mcp.mount(app)` adds MCP endpoints to FastAPI
- This creates a `/mcp` endpoint that handles JSON-RPC requests

#### 6. Running the Server

```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**What's happening:**
- Starts the server on all network interfaces (0.0.0.0)
- Listens on port 8000 (mapped to 8001 on host via Docker)

## Frontend Walkthrough

### File: [frontend/src/mcpClient.js](mcp-demo/frontend/src/mcpClient.js)

#### 1. MCP Client Class

```javascript
class MCPClient {
  constructor(baseUrl = MCP_BASE_URL) {
    this.baseUrl = baseUrl;
    this.requestId = 0;
  }
```

**What's happening:**
- Manages communication with MCP server
- Tracks request IDs (JSON-RPC requirement)
- Base URL points to backend MCP endpoint

#### 2. Making JSON-RPC Requests

```javascript
async request(method, params = {}) {
    this.requestId += 1;

    const body = {
      jsonrpc: '2.0',
      id: this.requestId,
      method: method,
      params: params
    };

    const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });

    const data = await response.json();
    return data.result;
}
```

**What's happening:**
- Constructs a JSON-RPC 2.0 request
- Sends it via HTTP POST to the MCP server
- Extracts the result from the response

**JSON-RPC Format:**
Request:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "add_task",
    "arguments": {"title": "Buy groceries"}
  }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": {"id": 1, "title": "Buy groceries", "completed": false}
    }]
  }
}
```

#### 3. Tool-Specific Methods

```javascript
async addTask(title, description = '') {
    return this.callTool('add_task', { title, description });
}
```

**What's happening:**
- Convenience methods that wrap `callTool`
- Makes code cleaner and more type-safe
- Each method maps to an MCP tool on the backend

### File: [frontend/src/mcpRuntime.jsx](mcp-demo/frontend/src/mcpRuntime.jsx)

#### 1. Custom Runtime Hook

```javascript
export function useMCPRuntime() {
  const [messages, setMessages] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
```

**What's happening:**
- React hook that manages chat state
- `messages`: Array of user and assistant messages
- `isRunning`: Loading state while processing

#### 2. Message Processing

```javascript
const handleUserMessage = async (content) => {
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: [{ type: 'text', text: content }],
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsRunning(true);

    try {
      const response = await processCommand(content);
      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: [{ type: 'text', text: response }],
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsRunning(false);
    }
}
```

**What's happening:**
1. User message is added to chat
2. Loading state is set
3. Command is processed (calls MCP tools)
4. Assistant response is added to chat
5. Loading state is cleared

#### 3. Command Parser

```javascript
const processCommand = async (input) => {
    const lower = input.toLowerCase();

    // Add task
    if (lower.includes('add') || lower.includes('create')) {
      const match = input.match(/(?:add|create)\s+(?:task\s+)?["']?(.+?)["']?$/i);
      if (match) {
        const title = match[1].trim();
        const result = await mcpClient.addTask(title, '');
        return `Task created: "${result.content[0].text.title}"`;
      }
    }
    // ... more command parsing
}
```

**What's happening:**
- Parses natural language into MCP tool calls
- Uses regex to extract parameters
- Calls appropriate MCP client method
- Formats response for display

**This is the AI-like behavior:**
Instead of a real LLM, we use simple pattern matching. In a real AI application, you'd use an LLM to:
1. Understand user intent
2. Decide which tool to call
3. Extract parameters
4. Format the response

### File: [frontend/src/App.jsx](mcp-demo/frontend/src/App.jsx)

#### 1. Main Component

```javascript
function App() {
  const { messages, isRunning, sendMessage } = useMCPRuntime();
  const [input, setInput] = useState('');
```

**What's happening:**
- Uses our custom MCP runtime hook
- Manages input field state
- Provides UI for chat interface

#### 2. Form Submission

```javascript
const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isRunning) {
      sendMessage(input);
      setInput('');
    }
};
```

**What's happening:**
- Prevents default form behavior
- Sends message only if not empty and not processing
- Clears input after sending

#### 3. Message Display

```javascript
{messages.map((message) => (
    <div key={message.id} className={`message ${message.role}`}>
      <div className="message-role">
        {message.role === 'user' ? 'You' : 'Assistant'}
      </div>
      <div className="message-content">
        {message.content[0].text.split('\n').map((line, i) => (
          <div key={i}>{line || '\u00A0'}</div>
        ))}
      </div>
    </div>
))}
```

**What's happening:**
- Maps over messages array
- Applies different styling for user vs assistant
- Handles multi-line text properly

## Docker Configuration

### File: [backend/Dockerfile](mcp-demo/backend/Dockerfile)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 8000
CMD ["python", "main.py"]
```

**What's happening:**
1. Start with lightweight Python image
2. Set working directory to /app
3. Copy and install dependencies first (Docker layer caching)
4. Copy application code
5. Expose port 8000
6. Run the application

### File: [frontend/Dockerfile](mcp-demo/frontend/Dockerfile)

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
```

**What's happening:**
1. Start with lightweight Node.js image
2. Copy package.json and install dependencies first
3. Copy all source files
4. Run Vite dev server

### File: [docker-compose.yml](mcp-demo/docker-compose.yml)

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8001:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"]
      interval: 10s
      timeout: 5s
      retries: 5

  frontend:
    build: ./frontend
    ports:
      - "3001:3000"
    depends_on:
      backend:
        condition: service_healthy
```

**What's happening:**
- **Backend**: Exposed on port 8001 (maps to 8000 inside container)
- **Healthcheck**: Ensures backend is ready before starting frontend
- **Frontend**: Waits for backend to be healthy
- **Networks**: Both containers on same network for communication

## How It All Works Together

### Example: Adding a Task

1. **User types**: "add task Buy groceries"

2. **Frontend (App.jsx)**:
   - Input captured and sent to `handleUserMessage`
   - User message added to chat

3. **Frontend (mcpRuntime.jsx)**:
   - `processCommand` parses the input
   - Detects "add" keyword
   - Extracts "Buy groceries" as title

4. **Frontend (mcpClient.js)**:
   - Calls `mcpClient.addTask("Buy groceries", "")`
   - Constructs JSON-RPC request:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "tools/call",
     "params": {
       "name": "add_task",
       "arguments": {"title": "Buy groceries", "description": ""}
     }
   }
   ```

5. **Backend (FastMCP)**:
   - Receives JSON-RPC request at `/mcp` endpoint
   - Validates request format
   - Finds `add_task` tool
   - Validates arguments against tool schema

6. **Backend (Tool Execution)**:
   - Calls `add_task("Buy groceries", "")`
   - Creates task object:
   ```python
   {
     "id": 1,
     "title": "Buy groceries",
     "description": "",
     "completed": False
   }
   ```
   - Adds to `tasks` list
   - Returns task object

7. **Backend (Response)**:
   - Wraps result in JSON-RPC response:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "content": [{
         "type": "text",
         "text": {"id": 1, "title": "Buy groceries", "completed": false}
       }]
     }
   }
   ```

8. **Frontend (mcpClient.js)**:
   - Receives response
   - Extracts result.content[0].text

9. **Frontend (mcpRuntime.jsx)**:
   - Formats response: "Task created: 'Buy groceries' (ID: 1)"
   - Creates assistant message
   - Adds to messages array

10. **Frontend (App.jsx)**:
    - Re-renders with new message
    - User sees confirmation in chat

## Key Learnings

### 1. MCP Protocol Benefits
- **Standardized**: Any MCP-compatible client can use our tools
- **Self-Documenting**: Tools describe themselves via schemas
- **Type-Safe**: Validation happens automatically
- **AI-Ready**: Designed for LLM integration

### 2. Separation of Concerns
- **Backend**: Handles business logic and data
- **Frontend**: Handles UI and user interaction
- **MCP**: Standardized communication layer

### 3. Docker Advantages
- **Consistency**: Same environment everywhere
- **Isolation**: Each service has its dependencies
- **Scalability**: Easy to add more services
- **Deployment**: One command to run everything

### 4. Real-World Extensions

To make this production-ready:

1. **Database**: Replace in-memory storage with PostgreSQL
   ```python
   from sqlalchemy import create_engine
   engine = create_engine('postgresql://user:pass@db/tasks')
   ```

2. **Authentication**: Add user authentication
   ```python
   from fastmcp.auth import require_auth

   @mcp.tool
   @require_auth
   def add_task(title: str, user_id: int):
       # Only allow users to manage their own tasks
   ```

3. **Real AI Integration**: Replace command parser with LLM
   ```javascript
   import OpenAI from 'openai';

   const completion = await openai.chat.completions.create({
     model: "gpt-4",
     messages: [{role: "user", content: input}],
     tools: mcpTools  // MCP tools converted to OpenAI format
   });
   ```

4. **Persistence**: Add database migrations
   ```python
   from alembic import command
   command.upgrade('head')
   ```

5. **Error Handling**: Comprehensive error handling
   ```python
   try:
       result = await tool.execute()
   except ValidationError as e:
       return {"error": "Invalid input"}
   except DatabaseError as e:
       return {"error": "Database error"}
   ```

## Testing Your Installation

### 1. Access the Application
Open your browser to: http://localhost:3001

### 2. Try These Commands

```
add task Buy groceries
add task Write documentation with description Complete the README file
list tasks
complete task 1
list completed
list pending
stats
delete task 2
help
```

### 3. Check Backend Logs
```bash
docker logs mcp-backend
```

### 4. Check Frontend Logs
```bash
docker logs mcp-frontend
```

### 5. Test MCP Endpoint Directly
```bash
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

## Troubleshooting

### Frontend Can't Connect to Backend
- Check if backend is healthy: `docker ps`
- Verify backend URL in frontend/.env
- Check CORS settings in backend/main.py

### Tasks Not Persisting
- This is expected - storage is in-memory
- Add a database for persistence

### Port Already in Use
- Change ports in docker-compose.yml
- Update VITE_MCP_URL in frontend .env file

## Next Steps

1. **Add More Tools**: Implement update_task, bulk_delete, etc.
2. **Add Resources**: Expose task statistics as MCP resources
3. **Add Prompts**: Create reusable prompt templates
4. **Integrate Real AI**: Use OpenAI or Anthropic API
5. **Add Database**: PostgreSQL for persistence
6. **Add Auth**: User authentication and authorization
7. **Deploy**: Deploy to cloud (AWS, GCP, Azure)

## Conclusion

This demo shows how MCP provides a clean, standardized way for AI applications to interact with tools and data. The key innovations are:

1. **Self-describing tools** - AI can discover and understand tools
2. **Type safety** - Automatic validation and schema generation
3. **Standardization** - Works with any MCP-compatible client
4. **Simplicity** - Decorators make tool creation easy

FastMCP 3.0 makes building MCP servers incredibly easy, while maintaining the flexibility to integrate with any frontend framework.

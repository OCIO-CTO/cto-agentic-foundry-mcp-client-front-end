"""
Consolidated MCP Proxy Server
Single-file implementation for simplicity
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from fastmcp import Client
from openai import AzureOpenAI
import httpx
import uvicorn
from dotenv import load_dotenv
import os
import json
import logging
from pathlib import Path
import random
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
REMOTE_MCP_URL = os.getenv("REMOTE_MCP_URL", "https://fsis-mcp-server-test1.azurewebsites.us/mcp")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3001").split(",")
PORT = int(os.getenv("PORT", "8000"))
API_KEY = os.getenv("API_KEY", "")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))

# Simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MCP client and cache
mcp_client: Optional[Client] = None
tools_cache: List[Dict[str, Any]] = []


# Helper to convert sync iterators to async
async def async_iter_wrapper(sync_iter):
    """Wrap synchronous iterator to async"""
    for item in sync_iter:
        yield item


# MCP Functions
async def get_mcp_client() -> Client:
    """Get or create MCP client"""
    global mcp_client
    if mcp_client is None:
        mcp_client = Client(REMOTE_MCP_URL)
        await mcp_client.__aenter__()
        logger.info(f"Connected to MCP server at {REMOTE_MCP_URL}")
    return mcp_client


async def list_mcp_tools() -> List[Dict[str, Any]]:
    """Fetch tools from remote MCP server"""
    global tools_cache
    if tools_cache:
        return tools_cache

    client = await get_mcp_client()
    tools = await client.list_tools()
    logger.info(f"Fetched {len(tools)} tools from MCP server")

    tools_cache = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Execute {tool.name}",
                "parameters": tool.inputSchema
            }
        }
        for tool in tools
    ]
    return tools_cache


async def execute_mcp_tool(tool_name: str, arguments: dict) -> Dict[str, Any]:
    """Execute a remote MCP tool"""
    client = await get_mcp_client()
    logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")

    result = await client.call_tool(tool_name, arguments)

    # Extract content from MCP response
    if hasattr(result, 'content') and isinstance(result.content, list):
        content_parts = []
        for item in result.content:
            if hasattr(item, 'type') and item.type == 'text' and hasattr(item, 'text'):
                content_parts.append(item.text)
            elif isinstance(item, dict) and 'text' in item:
                content_parts.append(item['text'])
            else:
                content_parts.append(str(item))
        return {"result": "\n".join(content_parts) if content_parts else str(result.content)}

    return {"result": str(result.content)} if hasattr(result, 'content') else {"result": str(result)}


async def close_mcp_client():
    """Cleanup MCP client"""
    global mcp_client
    if mcp_client:
        try:
            await mcp_client.__aexit__(None, None, None)
            logger.info("MCP client connection closed")
        except Exception as e:
            logger.error(f"Error closing MCP client: {e}")
        finally:
            mcp_client = None


# OpenAI Setup
http_client = httpx.Client(timeout=httpx.Timeout(timeout=OPENAI_TIMEOUT, connect=5.0))
azure_client = AzureOpenAI(
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_ENDPOINT,
    http_client=http_client
)


# FastAPI App Setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    logger.info("Starting MCP Proxy Server")
    try:
        tools = await list_mcp_tools()
        logger.info(f"Successfully cached {len(tools)} tools from MCP server")
    except Exception as e:
        logger.warning(f"MCP server unavailable on startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down MCP Proxy Server")
    await close_mcp_client()


app = FastAPI(
    title="MCP Proxy Server API",
    description="Proxy server for Model Context Protocol with Azure OpenAI integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# Optional API key authentication
async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header"""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key or "development"


# Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "MCP Proxy Server",
        "status": "running",
        "mcp_endpoint": "/mcp",
        "chat_endpoint": "/chat",
        "remote_mcp_url": REMOTE_MCP_URL
    }


@app.get("/static/cows.svg")
async def get_background_image(request: Request):
    """Serve a random background SVG image"""
    backgrounds = ["cows.svg", "field1.svg", "tractor1.svg", "plant1.svg"]
    selected = random.choice(backgrounds)
    svg_path = Path(__file__).parent / "assets" / selected

    if not svg_path.exists():
        raise HTTPException(status_code=404, detail="Background image not found")

    with open(svg_path, 'r') as f:
        svg_content = f.read()

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@app.post("/chat")
async def chat(
    request: Request,
    chat_request: dict,
    api_key: str = Header(None, alias="x-api-key")
):
    """Chat endpoint with streaming and MCP tool support"""
    # Verify API key if configured
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    messages = chat_request.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Messages required")

    logger.info(f"Chat request received with {len(messages)} messages")

    # Fetch tools from MCP server
    try:
        tools = await list_mcp_tools()
    except Exception as e:
        logger.warning(f"MCP server unavailable: {e}")
        tools = []

    # Build messages with system prompt
    system_message = {
        "role": "system",
        "content": "You are a helpful assistant with access to search tools. Use them when appropriate."
    }
    full_messages = [system_message] + messages

    async def generate_stream():
        """Generate Server-Sent Events stream"""
        try:
            # First, make a non-streaming call to check for tool calls
            initial_response = azure_client.chat.completions.create(
                model=AZURE_DEPLOYMENT,
                messages=full_messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                stream=False
            )

            response_message = initial_response.choices[0].message
            tool_calls = response_message.tool_calls

            # If there are tool calls, execute them ONCE and store results
            if tool_calls:
                tool_results = {}

                for tc in tool_calls:
                    # Parse arguments once
                    args = json.loads(tc.function.arguments)

                    # Send tool call start event with parsed arguments
                    yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': {'id': tc.id, 'name': tc.function.name, 'arguments': args}})}\n\n"

                    try:
                        logger.info(f"Executing tool: {tc.function.name}")
                        result = await execute_mcp_tool(tc.function.name, args)
                        tool_results[tc.id] = result
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool_id': tc.id, 'result': result})}\n\n"
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        error_result = {"error": str(e)}
                        tool_results[tc.id] = error_result
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool_id': tc.id, 'result': error_result})}\n\n"

                # Add assistant message with tool calls
                full_messages.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls
                    ]
                })

                # Reuse stored tool results
                for tc in tool_calls:
                    full_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_results[tc.id])
                    })

                # Stream final response
                stream = azure_client.chat.completions.create(
                    model=AZURE_DEPLOYMENT,
                    messages=full_messages,
                    stream=True
                )
            else:
                # No tool calls, just stream the response
                if response_message.content:
                    yield f"data: {json.dumps({'type': 'content', 'content': response_message.content})}\n\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

                # Stream if no content in initial response
                stream = azure_client.chat.completions.create(
                    model=AZURE_DEPLOYMENT,
                    messages=full_messages,
                    stream=True
                )

            # Stream the content
            async for chunk in async_iter_wrapper(stream):
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield f"data: {json.dumps({'type': 'content', 'content': delta.content})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.exception("Error in chat stream")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


if __name__ == "__main__":
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

"""
Consolidated MCP Proxy Server with FastMCP 3.0
Single-file implementation for simplicity
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from fastmcp import FastMCP, Client
from fastmcp.server import create_proxy
from openai import AzureOpenAI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
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
MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "5"))  # Prevent infinite loops
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")  # Rate limit per IP
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))  # 1MB default

# Simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server and mount remote FSIS server
mcp = FastMCP("FSIS Proxy")

# Mount the remote FSIS MCP server
logger.info(f"Mounting remote MCP server: {REMOTE_MCP_URL}")
mcp.mount(create_proxy(REMOTE_MCP_URL), namespace="fsis")

# Add system prompt
@mcp.prompt
def system() -> str:
    """System instructions for the LLM"""
    return """You are an FSIS assistant with access to search and fetch tools.

CRITICAL INSTRUCTION: You MUST NOT use your general knowledge or training data to answer questions. You are REQUIRED to use the search tool for every query to ensure accuracy and provide authoritative information from official FSIS sources.

TOOL USAGE WORKFLOW - BE PERSISTENT:
1. ALWAYS use fsis_search first to find relevant documents
2. If search results contain document IDs, use fsis_fetch to retrieve complete document content
3. If initial search results are insufficient, try alternative search queries with different keywords or phrasings
4. Continue searching and fetching until you have enough information to provide a comprehensive answer
5. ONLY after exhausting multiple search strategies (different keywords, broader/narrower terms) should you inform the user that information is not available
6. NEVER rely on your pre-trained knowledge - base answers ONLY on search and fetch results

SEARCH STRATEGY:
- First search: Use the user's exact query terms
- If insufficient: Try broader terms (e.g., "FSIS purpose" instead of "what is the purpose of FSIS")
- If still insufficient: Try related terms or acronym expansion (e.g., "Food Safety and Inspection Service")
- If still insufficient: Search for specific aspects mentioned in initial results
- Use fsis_fetch on ANY document IDs returned in search results to get full content

DO NOT give up after one search. You have multiple tool call iterations available - use them to thoroughly research the user's question before concluding information is unavailable.

Your role is to be a persistent, thorough conduit for official FSIS information."""

# Global cache
tools_cache: List[Dict[str, Any]] = []


# Helper to convert sync iterators to async
async def async_iter_wrapper(sync_iter):
    """Wrap synchronous iterator to async"""
    for item in sync_iter:
        yield item


# MCP Functions using FastMCP server
async def get_system_prompt() -> str:
    """Get system prompt from FastMCP server"""
    try:
        async with Client(mcp) as client:
            prompts = await client.list_prompts()
            logger.info(f"Fetched {len(prompts)} prompts from FastMCP server")

            # Look for the system prompt
            for prompt in prompts:
                if prompt.name == 'system':
                    logger.info(f"Found system prompt: {prompt.name}")
                    result = await client.get_prompt(prompt.name, {})
                    if result.messages and len(result.messages) > 0:
                        return result.messages[0].content.text if hasattr(result.messages[0].content, 'text') else str(result.messages[0].content)

            logger.info("No system prompt found, using default")
            return "You are a helpful assistant with access to search tools. Use them when appropriate."
    except Exception as e:
        logger.warning(f"Failed to fetch system prompt: {e}")
        return "You are a helpful assistant with access to search tools. Use them when appropriate."


async def list_mcp_tools() -> List[Dict[str, Any]]:
    """Fetch tools from FastMCP server (includes mounted remote tools)"""
    global tools_cache
    if tools_cache:
        return tools_cache

    try:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            logger.info(f"Fetched {len(tools)} tools from FastMCP server")

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
            logger.info(f"Successfully cached {len(tools_cache)} tools from FastMCP server")

            # Log tool details for debugging
            for tool in tools_cache:
                logger.info(f"Tool: {tool['function']['name']}")
                logger.info(f"  Description: {tool['function']['description']}")
                logger.info(f"  Parameters: {tool['function']['parameters']}")

            return tools_cache
    except Exception as e:
        logger.error(f"Failed to fetch tools: {e}")
        return []


async def execute_mcp_tool(tool_name: str, arguments: dict) -> Dict[str, Any]:
    """Execute a tool via FastMCP server"""
    try:
        async with Client(mcp) as client:
            logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")
            result = await client.call_tool(tool_name, arguments)

            # Log the raw result to see what we're getting
            logger.info(f"Tool result type: {type(result)}")
            logger.info(f"Tool result content: {result.content if hasattr(result, 'content') else result}")

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
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {"error": str(e)}


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
    logger.info("Starting MCP Proxy Server with FastMCP 3.0")
    try:
        tools = await list_mcp_tools()
        logger.info(f"Successfully cached {len(tools)} tools from FastMCP server")
    except Exception as e:
        logger.warning(f"FastMCP server unavailable on startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down MCP Proxy Server")


app = FastAPI(
    title="MCP Proxy Server API",
    description="Proxy server for Model Context Protocol with Azure OpenAI integration",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
    max_age=600  # Cache preflight requests for 10 minutes
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
@limiter.limit(RATE_LIMIT)
async def chat(
    request: Request,
    chat_request: dict,
    api_key: str = Header(None, alias="x-api-key")
):
    """Chat endpoint with streaming and MCP tool support"""
    # Verify API key if configured
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check request size
    body = await request.body()
    if len(body) > MAX_REQUEST_SIZE:
        raise HTTPException(status_code=413, detail=f"Request too large. Maximum size: {MAX_REQUEST_SIZE} bytes")

    messages = chat_request.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Messages required")

    # Validate message count
    if len(messages) > 100:
        raise HTTPException(status_code=400, detail="Too many messages. Maximum: 100")

    logger.info(f"Chat request received with {len(messages)} messages")

    # Fetch tools and system prompt from MCP server
    try:
        tools = await list_mcp_tools()
        system_prompt_content = await get_system_prompt()
    except Exception as e:
        logger.warning(f"MCP server unavailable: {e}")
        tools = []
        system_prompt_content = "You are a helpful assistant with access to search tools. Use them when appropriate."

    # Build messages with system prompt
    system_message = {
        "role": "system",
        "content": system_prompt_content
    }
    full_messages = [system_message] + messages

    async def generate_stream():
        """Generate Server-Sent Events stream with agentic loop"""
        try:
            iteration = 0

            # Agentic loop: Keep calling LLM until it stops requesting tools
            while iteration < MAX_TOOL_ITERATIONS:
                iteration += 1
                logger.info(f"Agentic loop iteration {iteration}/{MAX_TOOL_ITERATIONS}")

                # Call LLM with current conversation history
                response = azure_client.chat.completions.create(
                    model=AZURE_DEPLOYMENT,
                    messages=full_messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    stream=False
                )

                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

                # If LLM wants to call tools, execute them
                if tool_calls:
                    logger.info(f"LLM requested {len(tool_calls)} tool call(s)")
                    tool_results = {}

                    for tc in tool_calls:
                        # Parse arguments
                        args = json.loads(tc.function.arguments)

                        # Send tool call start event
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

                    # Add assistant message with tool calls to conversation history
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

                    # Add tool results to conversation history
                    for tc in tool_calls:
                        full_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_results[tc.id])
                        })

                    # Continue loop - LLM will analyze tool results and decide next action
                    continue

                # No tool calls - LLM has final answer, stream it to user
                else:
                    logger.info("LLM provided final answer, streaming response")

                    # If there's content in the non-streaming response, use it
                    if response_message.content:
                        yield f"data: {json.dumps({'type': 'content', 'content': response_message.content})}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return

                    # Otherwise, make a streaming call for the final response
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
                    return

            # Max iterations reached
            logger.warning(f"Max tool iterations ({MAX_TOOL_ITERATIONS}) reached")
            yield f"data: {json.dumps({'type': 'content', 'content': 'I apologize, but I reached the maximum number of tool calls while trying to answer your question. Please try rephrasing your question or asking something more specific.'})}\n\n"
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

"""
Refactored MCP Proxy Server with FastMCP 3.0
Modular implementation with separation of concerns
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from fastmcp import FastMCP
from fastmcp.server import create_proxy
from fastmcp.client.transports import StreamableHttpTransport
from openai import AzureOpenAI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
import uvicorn
import random
from typing import Optional, Dict, Any
from pathlib import Path
import logging

# Import refactored modules
from config import config
from auth import verify_api_key
from exceptions import (
    MCPProxyException,
    ValidationError,
    RequestTooLargeError,
    SpeechServiceError,
    log_error
)
from mcp_service import MCPService
from chat_service import ChatService
from speech_service import synthesize_speech, get_speech_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP and mount remote server
mcp = FastMCP(config.MCP_SERVICE_NAME)
logger.info(f"Mounting remote MCP server: {config.REMOTE_MCP_URL} with namespace: {config.MCP_NAMESPACE}")

# Create transport with proper headers for Hurricane Roof Leads MCP server
transport_headers = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json"
}
logger.info(f"Creating transport with headers: {transport_headers}")
transport = StreamableHttpTransport(
    config.REMOTE_MCP_URL,
    headers=transport_headers
)
logger.info(f"Transport created with URL: {config.REMOTE_MCP_URL}")
mcp.mount(create_proxy(transport), namespace=config.MCP_NAMESPACE)


@mcp.prompt
def system() -> str:
    """System instructions for the LLM"""
    return """You are a helpful assistant with access to various tools provided by an MCP server.

TOOL USAGE WORKFLOW:
1. Use available tools to find relevant information when answering user questions
2. If initial tool results are insufficient, try alternative approaches with different parameters or search terms
3. Be persistent - try multiple strategies before concluding information is not available
4. Always base your answers on tool results when available

SEARCH STRATEGY:
- First attempt: Use the user's exact query terms
- If insufficient: Try broader or more specific terms
- If insufficient: Try related terms or alternative phrasings
- Continue using tools iteratively until you have sufficient information

Your role is to be helpful, accurate, and make effective use of available tools to assist users."""


# Initialize services
http_client = httpx.Client(timeout=httpx.Timeout(timeout=config.OPENAI_TIMEOUT, connect=5.0))
azure_client = AzureOpenAI(
    api_key=config.AZURE_OPENAI_API_KEY,
    api_version=config.AZURE_OPENAI_API_VERSION,
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    http_client=http_client
)
mcp_service = MCPService(mcp)
chat_service = ChatService(azure_client, mcp_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting MCP Proxy Server with FastMCP 3.0")

    # Validate configuration
    if not config.validate_all():
        logger.error("Configuration validation failed")

    # Pre-cache tools
    try:
        tools = await mcp_service.list_tools()
        logger.info(f"Successfully cached {len(tools)} tools from FastMCP server")
    except Exception as e:
        logger.warning(f"FastMCP server unavailable on startup: {e}")

    yield

    logger.info("Shutting down MCP Proxy Server")
    http_client.close()


# Initialize FastAPI app
app = FastAPI(
    title="MCP Proxy Server API",
    description="Proxy server for Model Context Protocol with Azure OpenAI integration",
    version="1.0.0",
    lifespan=lifespan
)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
    max_age=600
)


# Exception handler for custom exceptions
@app.exception_handler(MCPProxyException)
async def mcp_exception_handler(request: Request, exc: MCPProxyException):
    """Handle custom MCP exceptions"""
    log_error(exc, f"Request failed: {request.url.path}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "MCP Proxy Server",
        "status": "running",
        "mcp_endpoint": "/mcp",
        "chat_endpoint": "/chat",
        "remote_mcp_url": config.REMOTE_MCP_URL
    }


@app.get("/api/config")
async def get_ui_config():
    """
    Get UI configuration from the connected MCP server.

    Returns configuration for:
    - Placeholder questions
    - Background images
    - Branding (service name, colors, etc.)

    Falls back to defaults if MCP server doesn't provide config.
    """
    ui_config = await mcp_service.get_ui_config()

    # Build response with defaults
    response = {
        "placeholders": ui_config.get("placeholders") or {
            "questions": [
                "Ask me anything...",
                "What can you help me with?",
                "How can I use the available tools?"
            ]
        },
        "backgrounds": ui_config.get("backgrounds") or {
            "images": [
                "abstract1.svg",
                "abstract2.svg",
                "abstract3.svg",
                "abstract4.svg"
            ]
        },
        "branding": ui_config.get("branding") or {
            "serviceName": config.MCP_SERVICE_NAME,
            "version": "1.0.0"
        }
    }

    return response


def serve_static_svg(filename: str):
    """Serve static SVG files with proper caching"""
    allowed_files = ["cows.svg", "field1.svg", "tractor1.svg", "plant1.svg"]

    if filename not in allowed_files:
        raise HTTPException(status_code=404, detail="File not found")

    svg_path = Path(__file__).parent / "assets" / filename

    if not svg_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    with open(svg_path, 'r') as f:
        svg_content = f.read()

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"}
    )


@app.get("/static/{filename}")
async def get_static_file(filename: str):
    """Serve static SVG files"""
    return serve_static_svg(filename)


@app.get("/api/backgrounds/{filename}")
async def get_background_file(filename: str):
    """Serve background SVG files (alias for /static/)"""
    return serve_static_svg(filename)


@app.post("/chat")
@limiter.limit(config.RATE_LIMIT)
async def chat(
    request: Request,
    chat_request: dict,
    api_key: str = Depends(verify_api_key)
):
    """
    Chat endpoint with agentic loop and SSE streaming

    Request body:
        {
            "messages": [
                {"role": "user", "content": "Your message"}
            ]
        }

    Returns:
        Server-Sent Events stream with tool calls and responses
    """
    # Validate request size
    body = await request.body()
    if len(body) > config.MAX_REQUEST_SIZE:
        raise RequestTooLargeError(config.MAX_REQUEST_SIZE)

    # Validate messages
    messages = chat_request.get("messages", [])
    if not messages:
        raise ValidationError("Messages required")

    if len(messages) > config.MAX_MESSAGES_PER_REQUEST:
        raise ValidationError(
            f"Too many messages. Maximum: {config.MAX_MESSAGES_PER_REQUEST}"
        )

    logger.info(f"Chat request received with {len(messages)} messages")

    # Get system prompt
    try:
        system_prompt = await mcp_service.get_system_prompt()
    except Exception as e:
        logger.warning(f"Failed to fetch system prompt: {e}")
        system_prompt = "You are a helpful assistant with access to search tools. Use them when appropriate."

    # Stream chat response
    async def generate():
        try:
            async for event in chat_service.process_chat_stream(messages, system_prompt):
                yield event
        except Exception as e:
            log_error(e, "Error in chat stream generation")
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@app.post("/api/speech/synthesize")
@limiter.limit(config.RATE_LIMIT)
async def synthesize_text_to_speech(
    request: Request,
    payload: dict,
    api_key: str = Depends(verify_api_key)
):
    """
    Convert text to speech audio

    Request body:
        {
            "text": "Text to convert to speech",
            "voice": "en-US-AriaNeural" (optional)
        }

    Returns:
        Audio bytes (MP3 format)
    """
    text = payload.get("text")
    if not text:
        raise ValidationError("Text is required")

    if len(text) > config.MAX_TEXT_LENGTH_FOR_TTS:
        raise ValidationError(
            f"Text too long. Maximum {config.MAX_TEXT_LENGTH_FOR_TTS} characters"
        )

    voice_name = payload.get("voice")

    try:
        logger.info(f"Synthesizing speech for text length: {len(text)}")
        audio_data = synthesize_speech(text, voice_name)

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "no-cache"
            }
        )
    except SpeechServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/speech/token")
@limiter.limit("30/minute")
async def get_speech_auth_token(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Get authentication token for Azure Speech Services
    Token is valid for 10 minutes

    Returns:
        {
            "token": "auth_token",
            "region": "usgovvirginia"
        }
    """
    try:
        logger.info("Generating speech authentication token")
        token_data = get_speech_token()
        return token_data
    except SpeechServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info(f"Starting server on port {config.PORT}")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)

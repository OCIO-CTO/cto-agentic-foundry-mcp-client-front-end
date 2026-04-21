from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import json
from pathlib import Path

# Load environment variables
load_dotenv()

# Import MCP client for remote server
from mcp_client import MCPClient

# Remote MCP server URL
REMOTE_MCP_URL = os.getenv("REMOTE_MCP_URL", "https://fsis-mcp-server-test1.azurewebsites.us/mcp")

# Create FastMCP instance
mcp = FastMCP("MCP Proxy Server")

# Skills support not available in FastMCP 3.0b1

# Initialize Azure OpenAI client
azure_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# All tools are provided by remote MCP server
# No local tools defined


async def get_remote_tools():
    """Fetch tools from remote MCP server asynchronously"""
    from fastmcp import Client
    tools = []

    try:
        client = Client(REMOTE_MCP_URL)
        async with client:
            remote_tools = await client.list_tools()
            for tool in remote_tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or f"Execute {tool.name}",
                        "parameters": tool.inputSchema
                    }
                })
    except Exception as e:
        print(f"Warning: Could not fetch remote MCP tools: {e}")

    return tools


def mcp_tools_to_openai_tools():
    """Convert MCP tools to OpenAI function calling format"""
    # Note: This function is deprecated - tools are now fetched async in the endpoint
    # Returning empty list as remote tools are fetched via get_remote_tools() in async context
    return []


async def execute_tool(tool_name: str, arguments: dict):
    """Execute a remote MCP tool"""
    # All tools come from remote MCP server
    from fastmcp import Client
    try:
        client = Client(REMOTE_MCP_URL)
        async with client:
            result = await client.call_tool(tool_name, arguments)
            # Extract content from MCP response
            if hasattr(result, 'content'):
                # Handle list of content items
                if isinstance(result.content, list):
                    content_parts = []
                    for item in result.content:
                        # Check for TextContent type
                        if hasattr(item, 'type') and item.type == 'text' and hasattr(item, 'text'):
                            content_parts.append(item.text)
                        elif isinstance(item, dict) and 'text' in item:
                            content_parts.append(item['text'])
                        else:
                            # For other content types, convert to string
                            content_parts.append(str(item))
                    return {"result": "\n".join(content_parts) if content_parts else str(result.content)}
                return {"result": str(result.content)}
            return result if isinstance(result, dict) else {"result": str(result)}
    except Exception as e:
        raise ValueError(f"Error executing tool '{tool_name}': {str(e)}")


def get_tool_ui_resource(tool_name: str) -> str | None:
    """Get the UI resource URI for a given tool"""
    # Remote tools don't have UI resources defined here
    return None


# Create the FastAPI app
app = FastAPI(title="MCP Proxy Server API", lifespan=mcp.lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP endpoints
app.mount("/mcp", mcp.get_asgi_app())


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "MCP Proxy Server",
        "version": "1.0.0",
        "mcp_endpoint": "/mcp",
        "chat_endpoint": "/chat",
        "remote_mcp_url": REMOTE_MCP_URL
    }


@app.get("/static/cows.svg")
async def get_background_image():
    """Serve the background SVG image"""
    svg_path = Path(__file__).parent / "cows.svg"
    if svg_path.exists():
        return FileResponse(svg_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Background image not found")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint that uses Azure OpenAI with remote MCP tools.
    The LLM can call remote MCP tools to perform operations.
    Returns a streaming response (SSE) for the final answer.
    """
    try:
        # Convert Pydantic models to dict for OpenAI
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Build system message
        system_message = {
            "role": "system",
            "content": """You are a helpful AI assistant with access to MCP tools.

Use the available tools to help users with their requests.

IMPORTANT: When you receive search results or other data from tools, present them clearly to the user with proper formatting and citations."""
        }
        messages.insert(0, system_message)

        # Get available tools in OpenAI format (including remote tools)
        remote_tools = await get_remote_tools()
        tools = mcp_tools_to_openai_tools()
        tools.extend(remote_tools)

        # Call Azure OpenAI with function calling (non-streaming)
        response = azure_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Collect UI resources from tool calls
        ui_resources = []
        tool_call_info = []

        # If the model wants to call tools
        if tool_calls:
            # Store tool call information for streaming
            for tc in tool_calls:
                # Use getattr to avoid type checking issues
                func = getattr(tc, 'function', None)
                if func:
                    tool_call_info.append({
                        'name': func.name,
                        'arguments': json.loads(func.arguments)
                    })

            # Add the assistant's response to messages
            messages.append({
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

            # Execute each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Collect UI resources
                ui_resource = get_tool_ui_resource(function_name)
                if ui_resource and ui_resource not in ui_resources:
                    ui_resources.append(ui_resource)

                # Execute the tool
                try:
                    function_response = await execute_tool(function_name, function_args)

                    # Add tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
                except Exception as e:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps({"error": str(e)})
                    })

            # Stream the final response
            async def generate_stream_with_tools():
                # Send tool call information first
                if tool_call_info:
                    yield f"data: {json.dumps({'type': 'tool_calls', 'tools': tool_call_info})}\n\n"

                # Send UI resources if any
                if ui_resources:
                    yield f"data: {json.dumps({'type': 'ui_resources', 'resources': ui_resources})}\n\n"

                # Get streaming response from the model
                stream = azure_client.chat.completions.create(
                    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                    messages=messages,
                    stream=True
                )

                for chunk in stream:
                    # Azure sends empty choices in first chunk, skip it
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield f"data: {json.dumps({'type': 'content', 'content': delta.content})}\n\n"

                # Signal end of stream
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            return StreamingResponse(generate_stream_with_tools(), media_type="text/event-stream")
        else:
            # No tool calls, stream the response directly
            async def generate_stream():
                stream = azure_client.chat.completions.create(
                    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                    messages=messages,
                    stream=True
                )

                for chunk in stream:
                    # Azure sends empty choices in first chunk, skip it
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield f"data: {json.dumps({'type': 'content', 'content': delta.content})}\n\n"

                # Signal end of stream
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            return StreamingResponse(generate_stream(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

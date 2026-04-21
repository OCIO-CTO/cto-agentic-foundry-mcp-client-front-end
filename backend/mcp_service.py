"""
MCP client service for tool management and execution.
Handles communication with the FastMCP server.
"""
from typing import List, Dict, Any, Optional
from fastmcp import Client
from exceptions import ToolExecutionError, log_error
from pydantic import AnyUrl
import logging
import base64

logger = logging.getLogger(__name__)


def _convert_resource_to_data_url(resource) -> Optional[str]:
    """
    Convert an MCP resource (text or blob) to a data URL.

    Args:
        resource: MCP resource object with text/blob and mimeType

    Returns:
        Data URL string or None if resource is invalid
    """
    mime_type = getattr(resource, 'mimeType', 'text/html')

    # Handle blob (already base64)
    if hasattr(resource, 'blob'):
        return f"data:{mime_type};base64,{resource.blob}"

    # Handle text (needs encoding)
    if hasattr(resource, 'text'):
        encoded = base64.b64encode(resource.text.encode('utf-8')).decode('utf-8')
        return f"data:{mime_type};base64,{encoded}"

    return None


async def _fetch_ui_resource(client, resource_uri: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a UI resource by URI and convert to iframe component.

    Args:
        client: MCP client instance
        resource_uri: URI of the resource (e.g., "ui://server/viz")

    Returns:
        UI component dict or None if fetch fails
    """
    try:
        fetched = await client.read_resource(resource_uri)
        # FastMCP client returns contents directly as a list
        contents = fetched if isinstance(fetched, list) else getattr(fetched, 'contents', [])

        if not contents:
            return None

        content = contents[0]
        url = _convert_resource_to_data_url(content)

        if url:
            return {
                'type': 'iframe',
                'resourceUri': resource_uri,
                'mimeType': getattr(content, 'mimeType', 'text/html'),
                'url': url
            }
    except Exception as e:
        logger.debug(f"Could not fetch UI resource {resource_uri}: {e}")

    return None


def serialize_for_json(obj: Any) -> Any:
    """
    Convert Pydantic models and special types to JSON-serializable format.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, AnyUrl):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif hasattr(obj, 'model_dump'):
        # Pydantic v2 model
        return serialize_for_json(obj.model_dump())
    elif hasattr(obj, 'dict'):
        # Pydantic v1 model
        return serialize_for_json(obj.dict())
    else:
        return obj


class MCPService:
    """Service for interacting with MCP server"""

    def __init__(self, mcp):
        """
        Initialize MCP service.

        Args:
            mcp: FastMCP server instance
        """
        self.mcp = mcp
        self._tools_cache: List[Dict[str, Any]] = []
        self._tools_metadata: Dict[str, Any] = {}  # Store full tool definitions with metadata
        self._system_prompt_cache: Optional[str] = None
        self._ui_config_cache: Optional[Dict[str, Any]] = None

    async def get_system_prompt(self) -> str:
        """
        Get system prompt from FastMCP server.

        Returns:
            System prompt string

        Uses cached value if available.
        """
        if self._system_prompt_cache:
            return self._system_prompt_cache

        try:
            async with Client(self.mcp) as client:
                prompts = await client.list_prompts()
                logger.info(f"Fetched {len(prompts)} prompts from FastMCP server")

                for prompt in prompts:
                    if prompt.name == 'system':
                        logger.info(f"Found system prompt: {prompt.name}")
                        result = await client.get_prompt(prompt.name, {})
                        if result.messages and len(result.messages) > 0:
                            prompt_text = (
                                result.messages[0].content.text
                                if hasattr(result.messages[0].content, 'text')
                                else str(result.messages[0].content)
                            )
                            self._system_prompt_cache = prompt_text
                            return prompt_text

                logger.info("No system prompt found, using default")
                return self._get_default_system_prompt()
        except Exception as e:
            log_error(e, "Failed to fetch system prompt")
            return self._get_default_system_prompt()

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt fallback"""
        return "You are a helpful assistant with access to search tools. Use them when appropriate."

    async def get_ui_config(self) -> Dict[str, Any]:
        """
        Get UI configuration from MCP server.

        Attempts to fetch UI configuration from MCP server resources:
        - ui://config/placeholders - Placeholder questions for input
        - ui://config/backgrounds - Background image names
        - ui://config/branding - Service name, colors, etc.

        Returns:
            Dictionary with UI configuration or defaults

        Uses cached value if available.
        """
        if self._ui_config_cache:
            return self._ui_config_cache

        config = {
            "placeholders": None,
            "backgrounds": None,
            "branding": None
        }

        try:
            async with Client(self.mcp) as client:
                # Try to fetch placeholder questions
                try:
                    result = await client.read_resource("ui://config/placeholders")
                    if result.contents and len(result.contents) > 0:
                        import json
                        content = result.contents[0]
                        if hasattr(content, 'text'):
                            config["placeholders"] = json.loads(content.text)
                            logger.info("Fetched placeholder questions from MCP server")
                except Exception as e:
                    logger.debug(f"No placeholders resource available: {e}")

                # Try to fetch background images
                try:
                    result = await client.read_resource("ui://config/backgrounds")
                    if result.contents and len(result.contents) > 0:
                        import json
                        content = result.contents[0]
                        if hasattr(content, 'text'):
                            config["backgrounds"] = json.loads(content.text)
                            logger.info("Fetched background images from MCP server")
                except Exception as e:
                    logger.debug(f"No backgrounds resource available: {e}")

                # Try to fetch branding config
                try:
                    result = await client.read_resource("ui://config/branding")
                    if result.contents and len(result.contents) > 0:
                        import json
                        content = result.contents[0]
                        if hasattr(content, 'text'):
                            config["branding"] = json.loads(content.text)
                            logger.info("Fetched branding config from MCP server")
                except Exception as e:
                    logger.debug(f"No branding resource available: {e}")

                self._ui_config_cache = config
                return config

        except Exception as e:
            log_error(e, "Failed to fetch UI configuration")
            return config

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Fetch tools from FastMCP server (includes mounted remote tools).

        Returns:
            List of tool definitions in OpenAI format

        Uses cached value if available.
        """
        if self._tools_cache:
            return self._tools_cache

        try:
            async with Client(self.mcp) as client:
                tools = await client.list_tools()
                logger.info(f"Fetched {len(tools)} tools from FastMCP server")

                self._tools_cache = [
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

                # Store full tool definitions for metadata access
                for tool in tools:
                    self._tools_metadata[tool.name] = tool

                logger.info(f"Cached {len(self._tools_cache)} tools")
                return self._tools_cache
        except Exception as e:
            log_error(e, "Failed to fetch tools")
            return []

    async def execute_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """
        Execute a tool via FastMCP server.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result as dict with optional 'ui' field for MCP Apps
        """
        try:
            async with Client(self.mcp) as client:
                logger.info(f"Executing tool: {tool_name}")
                result = await client.call_tool(tool_name, arguments)

                # Simple case: no content list
                if not hasattr(result, 'content') or not isinstance(result.content, list):
                    return {"result": str(getattr(result, 'content', result))}

                # Extract text and UI resources from content
                content_parts = []
                ui_components = []

                for item in result.content:
                    item_type = getattr(item, 'type', None)

                    # Text content
                    if item_type == 'text' and hasattr(item, 'text'):
                        content_parts.append(item.text)

                    # Resource content (UI components)
                    elif item_type == 'resource' and hasattr(item, 'resource'):
                        resource = item.resource
                        resource_uri = str(resource.uri) if hasattr(resource, 'uri') else None

                        # Try direct conversion (embedded content)
                        url = _convert_resource_to_data_url(resource)
                        if url:
                            ui_components.append(serialize_for_json({
                                'type': 'iframe',
                                'resourceUri': resource_uri,
                                'mimeType': getattr(resource, 'mimeType', 'text/html'),
                                'url': url
                            }))
                        # If no embedded content, try fetching by URI
                        elif resource_uri and resource_uri.startswith('ui://'):
                            ui_component = await _fetch_ui_resource(client, resource_uri)
                            if ui_component:
                                ui_components.append(serialize_for_json(ui_component))

                # Build response
                response = {
                    "result": "\n".join(content_parts) if content_parts else "Tool executed"
                }

                if ui_components:
                    response["ui"] = ui_components
                    logger.info(f"Returning {len(ui_components)} UI component(s)")

                return response

        except Exception as e:
            log_error(e, f"Tool execution failed for '{tool_name}'")
            return {"error": str(e)}

    def clear_cache(self) -> None:
        """Clear cached tools and system prompt"""
        self._tools_cache = []
        self._system_prompt_cache = None
        logger.info("MCP service cache cleared")

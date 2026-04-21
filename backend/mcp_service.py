"""
MCP client service for tool management and execution.
Handles communication with the FastMCP server.
"""
from typing import List, Dict, Any, Optional
from fastmcp import Client
from exceptions import ToolExecutionError, log_error
from pydantic import AnyUrl
import logging

logger = logging.getLogger(__name__)


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
                logger.info(f"Successfully cached {len(self._tools_cache)} tools")
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

        Raises:
            ToolExecutionError: If tool execution fails
        """
        try:
            async with Client(self.mcp) as client:
                logger.info(f"Executing tool: {tool_name}")
                result = await client.call_tool(tool_name, arguments)

                # Parse result content
                if hasattr(result, 'content') and isinstance(result.content, list):
                    content_parts = []
                    ui_components = []

                    for item in result.content:
                        # Handle text content
                        if hasattr(item, 'type') and item.type == 'text' and hasattr(item, 'text'):
                            content_parts.append(item.text)
                        elif isinstance(item, dict) and 'text' in item:
                            content_parts.append(item['text'])
                        # Handle resource content (MCP Apps - iframes, images, etc.)
                        elif hasattr(item, 'type') and item.type == 'resource':
                            if hasattr(item, 'resource'):
                                resource = item.resource
                                resource_uri = str(resource.uri) if hasattr(resource, 'uri') else None

                                ui_component = {
                                    'type': 'iframe',
                                    'resourceUri': resource_uri,
                                    'mimeType': resource.mimeType if hasattr(resource, 'mimeType') else None
                                }

                                # Check if resource has embedded content
                                if hasattr(resource, 'blob'):
                                    # Blob data already base64 encoded
                                    mime_type = resource.mimeType if hasattr(resource, 'mimeType') else 'text/html'
                                    ui_component['url'] = f"data:{mime_type};base64,{resource.blob}"
                                elif hasattr(resource, 'text'):
                                    # Text content needs encoding
                                    import base64
                                    mime_type = resource.mimeType if hasattr(resource, 'mimeType') else 'text/html'
                                    encoded = base64.b64encode(resource.text.encode('utf-8')).decode('utf-8')
                                    ui_component['url'] = f"data:{mime_type};base64,{encoded}"
                                elif resource_uri and resource_uri.startswith('ui://'):
                                    # URI-only resource - need to fetch via resources/read
                                    try:
                                        fetched = await client.read_resource(resource_uri)
                                        if hasattr(fetched, 'contents') and len(fetched.contents) > 0:
                                            content = fetched.contents[0]
                                            if hasattr(content, 'text'):
                                                import base64
                                                mime_type = content.mimeType if hasattr(content, 'mimeType') else 'text/html'
                                                encoded = base64.b64encode(content.text.encode('utf-8')).decode('utf-8')
                                                ui_component['url'] = f"data:{mime_type};base64,{encoded}"
                                            elif hasattr(content, 'blob'):
                                                mime_type = content.mimeType if hasattr(content, 'mimeType') else 'text/html'
                                                ui_component['url'] = f"data:{mime_type};base64,{content.blob}"
                                            else:
                                                logger.warning(f"Fetched resource has no text or blob: {resource_uri}")
                                                continue
                                        else:
                                            logger.warning(f"Fetched resource has no contents: {resource_uri}")
                                            continue
                                    except Exception as e:
                                        logger.error(f"Failed to fetch UI resource {resource_uri}: {e}")
                                        continue
                                else:
                                    continue

                                ui_components.append(serialize_for_json(ui_component))
                        else:
                            content_parts.append(str(item))

                    response = {
                        "result": "\n".join(content_parts) if content_parts else str(result.content)
                    }

                    # Add UI components if any were found
                    if ui_components:
                        response["ui"] = ui_components
                        logger.info(f"Returning {len(ui_components)} UI component(s)")

                    return response

                return {"result": str(result.content)} if hasattr(result, 'content') else {"result": str(result)}

        except Exception as e:
            log_error(e, f"Tool execution failed for '{tool_name}'")
            return {"error": str(e)}

    def clear_cache(self) -> None:
        """Clear cached tools and system prompt"""
        self._tools_cache = []
        self._system_prompt_cache = None
        logger.info("MCP service cache cleared")

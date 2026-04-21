"""
MCP client service for tool management and execution.
Handles communication with the FastMCP server.
"""
from typing import List, Dict, Any, Optional
from fastmcp import Client
from exceptions import ToolExecutionError, log_error
import logging

logger = logging.getLogger(__name__)


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
            Tool execution result as dict

        Raises:
            ToolExecutionError: If tool execution fails
        """
        try:
            async with Client(self.mcp) as client:
                logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")
                result = await client.call_tool(tool_name, arguments)

                # Parse result content
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
            log_error(e, f"Tool execution failed for '{tool_name}'")
            return {"error": str(e)}

    def clear_cache(self) -> None:
        """Clear cached tools and system prompt"""
        self._tools_cache = []
        self._system_prompt_cache = None
        logger.info("MCP service cache cleared")

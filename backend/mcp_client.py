"""
MCP Client wrapper for connecting to remote MCP servers via HTTP/SSE
Uses the official FastMCP Client library
"""
from fastmcp import Client
from typing import Any
import asyncio


class MCPClient:
    """Synchronous wrapper for FastMCP async client using a persistent event loop"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = Client(base_url)
        self.loop = None
        self._initialized = False

    def __enter__(self):
        """Synchronous context manager entry"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.client.__aenter__())
        self._initialized = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Synchronous context manager exit"""
        if self._initialized and self.loop:
            self.loop.run_until_complete(self.client.__aexit__(exc_type, exc_val, exc_tb))
            self.loop.close()
            self._initialized = False

    def list_tools(self) -> list:
        """List all available tools from the MCP server"""
        if not self.loop:
            raise RuntimeError("Client not initialized. Use 'with MCPClient(url) as client:'")

        result = self.loop.run_until_complete(self.client.list_tools())
        # Return the full result to see what we're getting
        if hasattr(result, 'tools'):
            return result.tools
        elif isinstance(result, dict) and 'tools' in result:
            return result['tools']
        else:
            # Return the raw result for debugging
            return result

    def call_tool(self, name: str, arguments: dict = None) -> Any:
        """Call a tool on the MCP server"""
        if not self.loop:
            raise RuntimeError("Client not initialized. Use 'with MCPClient(url) as client:'")

        result = self.loop.run_until_complete(self.client.call_tool(name, arguments or {}))
        return result

    def list_resources(self) -> list:
        """List all available resources from the MCP server"""
        if not self.loop:
            raise RuntimeError("Client not initialized. Use 'with MCPClient(url) as client:'")

        result = self.loop.run_until_complete(self.client.list_resources())
        return result.resources if hasattr(result, 'resources') else []

    def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server"""
        if not self.loop:
            raise RuntimeError("Client not initialized. Use 'with MCPClient(url) as client:'")

        result = self.loop.run_until_complete(self.client.read_resource(uri))
        return result

    def list_prompts(self) -> list:
        """List all available prompts from the MCP server"""
        if not self.loop:
            raise RuntimeError("Client not initialized. Use 'with MCPClient(url) as client:'")

        result = self.loop.run_until_complete(self.client.list_prompts())
        return result.prompts if hasattr(result, 'prompts') else []

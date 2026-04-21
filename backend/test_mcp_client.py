"""
Test script for MCP client
"""
from mcp_client import MCPClient
import json

# Test remote MCP server
REMOTE_MCP_URL = "https://fsis-mcp-server-test1.azurewebsites.us/mcp"

def main():
    print(f"Connecting to remote MCP server: {REMOTE_MCP_URL}")

    with MCPClient(REMOTE_MCP_URL) as client:
        # Client auto-initializes on first request
        print("\n1. Connected to remote MCP server")

        # List tools
        print("\n2. Listing tools...")
        tools = client.list_tools()
        print(f"Raw tools response type: {type(tools)}")
        print(f"Raw tools response: {tools}")

        if hasattr(tools, '__len__'):
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  Tool type: {type(tool)}")
                print(f"  Tool content: {tool}")
                if hasattr(tool, 'name'):
                    print(f"  - {tool.name}: {getattr(tool, 'description', 'No description')}")
                elif isinstance(tool, dict):
                    print(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")

        # List resources
        print("\n3. Listing resources...")
        try:
            resources = client.list_resources()
            print(f"Found {len(resources)} resources:")
            for resource in resources[:5]:  # Show first 5
                print(f"  - {resource.get('uri')}: {resource.get('name', 'No name')}")
        except Exception as e:
            print(f"Error listing resources: {e}")

        # List prompts
        print("\n4. Listing prompts...")
        try:
            prompts = client.list_prompts()
            print(f"Found {len(prompts)} prompts:")
            for prompt in prompts:
                print(f"  - {prompt.get('name')}: {prompt.get('description', 'No description')}")
        except Exception as e:
            print(f"Error listing prompts: {e}")

if __name__ == "__main__":
    main()

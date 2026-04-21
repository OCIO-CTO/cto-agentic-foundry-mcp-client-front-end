/**
 * MCP Client for communicating with the FastMCP backend
 * This uses fetch API to communicate with the MCP server
 */

const MCP_BASE_URL = import.meta.env.VITE_MCP_URL || 'http://localhost:8000/mcp';

class MCPClient {
  constructor(baseUrl = MCP_BASE_URL) {
    this.baseUrl = baseUrl;
    this.requestId = 0;
  }

  /**
   * Make a JSON-RPC request to the MCP server
   */
  async request(method, params = {}) {
    this.requestId += 1;

    const body = {
      jsonrpc: '2.0',
      id: this.requestId,
      method: method,
      params: params
    };

    try {
      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error.message || 'MCP request failed');
      }

      return data.result;
    } catch (error) {
      console.error('MCP request failed:', error);
      throw error;
    }
  }

  /**
   * List available tools from the MCP server
   */
  async listTools() {
    return this.request('tools/list');
  }

  /**
   * Call a tool on the MCP server
   */
  async callTool(name, arguments_) {
    return this.request('tools/call', {
      name: name,
      arguments: arguments_ || {}
    });
  }

  /**
   * Task management methods
   */
  async addTask(title, description = '') {
    return this.callTool('add_task', { title, description });
  }

  async listTasks(completed = null) {
    const args = completed !== null ? { completed } : {};
    return this.callTool('list_tasks', args);
  }

  async completeTask(taskId) {
    return this.callTool('complete_task', { task_id: taskId });
  }

  async deleteTask(taskId) {
    return this.callTool('delete_task', { task_id: taskId });
  }

  async getStatistics() {
    return this.callTool('get_statistics');
  }
}

export const mcpClient = new MCPClient();

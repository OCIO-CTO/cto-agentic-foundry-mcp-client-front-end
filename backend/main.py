from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Import MCP client for remote server
from mcp_client import MCPClient

# Remote MCP server URL
REMOTE_MCP_URL = os.getenv("REMOTE_MCP_URL", "https://fsis-mcp-server-test1.azurewebsites.us/mcp")

# Create FastMCP instance
mcp = FastMCP("Task Manager MCP Server")

# Add Skills Provider
from pathlib import Path
from fastmcp.server.providers.skills import SkillsDirectoryProvider

skills_path = Path(__file__).parent.parent / "skills"
if skills_path.exists():
    mcp.add_provider(SkillsDirectoryProvider(roots=skills_path))

# Initialize Azure OpenAI client
azure_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# In-memory task storage
tasks = []
task_id_counter = 1


@mcp.tool
def add_task(title: str, description: str = "") -> dict:
    """
    Add a new task to the task list.

    Args:
        title: The title of the task
        description: Optional description of the task

    Returns:
        The created task with its ID
    """
    global task_id_counter
    task = {
        "id": task_id_counter,
        "title": title,
        "description": description,
        "completed": False
    }
    tasks.append(task)
    task_id_counter += 1
    return task


@mcp.tool(
    meta={
        "ui/resourceUri": "ui://tasks/list"
    }
)
def list_tasks(completed: bool = None) -> list:
    """
    List all tasks, optionally filtered by completion status.

    Args:
        completed: If True, show only completed tasks. If False, show only incomplete tasks.
                  If None, show all tasks.

    Returns:
        List of tasks matching the filter
    """
    if completed is None:
        return tasks
    return [task for task in tasks if task["completed"] == completed]


@mcp.tool
def complete_task(task_id: int) -> dict:
    """
    Mark a task as completed.

    Args:
        task_id: The ID of the task to complete

    Returns:
        The updated task
    """
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            return task
    raise ValueError(f"Task with ID {task_id} not found")


@mcp.tool
def delete_task(task_id: int) -> dict:
    """
    Delete a task from the task list.

    Args:
        task_id: The ID of the task to delete

    Returns:
        Success message with deleted task info
    """
    global tasks
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            deleted_task = tasks.pop(i)
            return {"success": True, "deleted_task": deleted_task}
    raise ValueError(f"Task with ID {task_id} not found")


@mcp.tool(
    meta={
        "ui/resourceUri": "ui://tasks/chart"
    }
)
def get_statistics() -> dict:
    """
    Get statistics about the task list.

    Returns:
        Dictionary with total, completed, and pending task counts
    """
    total = len(tasks)
    completed = len([t for t in tasks if t["completed"]])
    pending = total - completed
    return {
        "total": total,
        "completed": completed,
        "pending": pending
    }


# MCP Apps UI Resources

@mcp.resource("ui://tasks/chart", mime_type="text/html+mcp")
def task_chart_ui() -> str:
    """Interactive data visualization chart component"""
    stats = get_statistics()
    total = stats['total']
    completed = stats['completed']
    pending = stats['pending']
    completion_rate = (completed / total * 100) if total > 0 else 0

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{
                color: #4facfe;
                margin-bottom: 20px;
                font-size: 24px;
            }}
            .charts-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 20px;
            }}
            .chart-container {{
                background: #f8f9fa;
                padding: 16px;
                border-radius: 8px;
                position: relative;
                height: 250px;
            }}
            .chart-container.full {{
                grid-column: 1 / -1;
            }}
            canvas {{
                max-height: 100%;
            }}
            .stat-highlight {{
                text-align: center;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .stat-highlight h2 {{
                font-size: 48px;
                margin-bottom: 8px;
            }}
            .stat-highlight p {{
                font-size: 16px;
                opacity: 0.9;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Task Analytics Dashboard</h1>

            <div class="stat-highlight">
                <h2>{completion_rate:.1f}%</h2>
                <p>Overall Completion Rate</p>
            </div>

            <div class="charts-grid">
                <div class="chart-container">
                    <canvas id="pieChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="barChart"></canvas>
                </div>
                <div class="chart-container full">
                    <canvas id="progressChart"></canvas>
                </div>
            </div>
        </div>

        <script>
            // Pie Chart - Completion Status
            new Chart(document.getElementById('pieChart'), {{
                type: 'doughnut',
                data: {{
                    labels: ['Completed', 'Pending'],
                    datasets: [{{
                        data: [{completed}, {pending}],
                        backgroundColor: ['#4caf50', '#ff9800'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }},
                        title: {{
                            display: true,
                            text: 'Task Status Distribution'
                        }}
                    }}
                }}
            }});

            // Bar Chart - Task Counts
            new Chart(document.getElementById('barChart'), {{
                type: 'bar',
                data: {{
                    labels: ['Total', 'Completed', 'Pending'],
                    datasets: [{{
                        label: 'Tasks',
                        data: [{total}, {completed}, {pending}],
                        backgroundColor: ['#667eea', '#4caf50', '#ff9800'],
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        title: {{
                            display: true,
                            text: 'Task Summary'
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1
                            }}
                        }}
                    }}
                }}
            }});

            // Progress Chart
            new Chart(document.getElementById('progressChart'), {{
                type: 'bar',
                data: {{
                    labels: ['Progress'],
                    datasets: [
                        {{
                            label: 'Completed',
                            data: [{completed}],
                            backgroundColor: '#4caf50',
                            barThickness: 40
                        }},
                        {{
                            label: 'Pending',
                            data: [{pending}],
                            backgroundColor: '#ff9800',
                            barThickness: 40
                        }}
                    ]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }},
                        title: {{
                            display: true,
                            text: 'Overall Progress'
                        }}
                    }},
                    scales: {{
                        x: {{
                            stacked: true,
                            beginAtZero: true
                        }},
                        y: {{
                            stacked: true
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html


@mcp.resource("ui://tasks/analytics", mime_type="text/html+mcp")
def task_analytics_ui() -> str:
    """Interactive analytics and insights component"""
    stats = get_statistics()
    tasks_list = list_tasks()

    total = stats['total']
    completed = stats['completed']
    pending = stats['pending']
    completion_rate = (completed / total * 100) if total > 0 else 0

    # Generate insights
    insights = []
    if completion_rate >= 75:
        insights.append(("Excellent Progress!", "You're crushing it! Keep up the great work.", "success"))
    elif completion_rate >= 50:
        insights.append(("Good Momentum", "You're making solid progress. Stay focused!", "info"))
    elif completion_rate > 0:
        insights.append(("Getting Started", "Every journey begins with a single step. Keep going!", "warning"))
    else:
        insights.append(("Ready to Begin", "Time to tackle those tasks! You've got this.", "info"))

    if pending > 5:
        insights.append(("High Task Load", f"You have {pending} pending tasks. Consider prioritizing the most important ones.", "warning"))
    elif pending > 0:
        insights.append(("Manageable Workload", f"You have {pending} tasks remaining. Great job keeping it under control!", "success"))

    if total == 0:
        insights.append(("No Tasks Yet", "Start by adding your first task to get organized!", "info"))

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 700px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{
                color: #f5576c;
                margin-bottom: 20px;
                font-size: 24px;
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }}
            .metric {{
                text-align: center;
                padding: 16px;
                background: #f8f9fa;
                border-radius: 8px;
                border-top: 3px solid #f5576c;
            }}
            .metric-value {{
                font-size: 32px;
                font-weight: bold;
                color: #f5576c;
                margin-bottom: 4px;
            }}
            .metric-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }}
            .insights {{
                margin-top: 20px;
            }}
            .insight {{
                padding: 16px;
                margin-bottom: 12px;
                border-radius: 8px;
                border-left: 4px solid;
            }}
            .insight.success {{
                background: #e8f5e9;
                border-left-color: #4caf50;
            }}
            .insight.warning {{
                background: #fff3e0;
                border-left-color: #ff9800;
            }}
            .insight.info {{
                background: #e3f2fd;
                border-left-color: #2196f3;
            }}
            .insight-title {{
                font-weight: 600;
                color: #333;
                margin-bottom: 4px;
                font-size: 16px;
            }}
            .insight-text {{
                color: #666;
                font-size: 14px;
                line-height: 1.5;
            }}
            .progress-bar {{
                width: 100%;
                height: 24px;
                background: #e0e0e0;
                border-radius: 12px;
                overflow: hidden;
                margin: 20px 0;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #4caf50 0%, #8bc34a 100%);
                transition: width 1s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Task Analytics & Insights</h1>

            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{total}</div>
                    <div class="metric-label">Total Tasks</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{completed}</div>
                    <div class="metric-label">Completed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{pending}</div>
                    <div class="metric-label">Pending</div>
                </div>
            </div>

            <div class="progress-bar">
                <div class="progress-fill" style="width: {completion_rate}%">
                    {completion_rate:.0f}%
                </div>
            </div>

            <div class="insights">
                <h2 style="color: #333; margin-bottom: 16px; font-size: 18px;">Insights & Recommendations</h2>
                {"".join([f'''
                <div class="insight {insight_type}">
                    <div class="insight-title">{title}</div>
                    <div class="insight-text">{text}</div>
                </div>
                ''' for title, text, insight_type in insights])}
            </div>
        </div>
    </body>
    </html>
    """
    return html


@mcp.resource("ui://tasks/list", mime_type="text/html+mcp")
def task_list_ui() -> str:
    """Interactive task list UI component"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{
                color: #667eea;
                margin-bottom: 20px;
                font-size: 24px;
            }}
            .stats {{
                display: flex;
                gap: 12px;
                margin-bottom: 24px;
            }}
            .stat {{
                flex: 1;
                padding: 12px;
                background: #f5f5f5;
                border-radius: 8px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 28px;
                font-weight: bold;
                color: #667eea;
            }}
            .stat-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                margin-top: 4px;
            }}
            .task-list {{
                list-style: none;
            }}
            .task-item {{
                padding: 16px;
                margin-bottom: 12px;
                background: #fafafa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                transition: all 0.3s ease;
            }}
            .task-item:hover {{
                transform: translateX(4px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .task-item.completed {{
                opacity: 0.7;
                border-left-color: #4caf50;
                background: #f0f8f0;
            }}
            .task-header {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .checkbox {{
                width: 20px;
                height: 20px;
                border: 2px solid #667eea;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }}
            .task-item.completed .checkbox {{
                background: #4caf50;
                border-color: #4caf50;
            }}
            .checkbox::after {{
                content: '✓';
                color: white;
                font-weight: bold;
                display: none;
            }}
            .task-item.completed .checkbox::after {{
                display: block;
            }}
            .task-content {{
                flex: 1;
            }}
            .task-title {{
                font-weight: 600;
                color: #333;
                margin-bottom: 4px;
            }}
            .task-item.completed .task-title {{
                text-decoration: line-through;
                color: #999;
            }}
            .task-description {{
                font-size: 14px;
                color: #666;
            }}
            .task-id {{
                font-size: 12px;
                color: #999;
                background: #e0e0e0;
                padding: 2px 8px;
                border-radius: 12px;
            }}
            .empty-state {{
                text-align: center;
                padding: 40px;
                color: #999;
            }}
            .empty-state svg {{
                width: 64px;
                height: 64px;
                margin-bottom: 16px;
                opacity: 0.5;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Task List</h1>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="total-count">{len(tasks)}</div>
                    <div class="stat-label">Total</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="pending-count">{len([t for t in tasks if not t['completed']])}</div>
                    <div class="stat-label">Pending</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="completed-count">{len([t for t in tasks if t['completed']])}</div>
                    <div class="stat-label">Completed</div>
                </div>
            </div>
            <ul class="task-list" id="task-list">
                {"".join([f'''
                <li class="task-item {'completed' if task['completed'] else ''}">
                    <div class="task-header">
                        <div class="checkbox"></div>
                        <div class="task-content">
                            <div class="task-title">{task['title']}</div>
                            {f'<div class="task-description">{task["description"]}</div>' if task.get('description') else ''}
                        </div>
                        <div class="task-id">#{task['id']}</div>
                    </div>
                </li>
                ''' for task in tasks]) if tasks else '''
                <div class="empty-state">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                    </svg>
                    <div>No tasks yet. Start by adding your first task!</div>
                </div>
                '''}
            </ul>
        </div>
    </body>
    </html>
    """
    return html


# Create MCP HTTP app first to get lifespan
mcp_app = mcp.http_app(path='/messages')

# Create FastAPI app with MCP lifespan
app = FastAPI(title="MCP Task Manager API", lifespan=mcp_app.lifespan)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "message": "MCP Task Manager Server",
        "version": "1.0.0",
        "mcp_endpoint": "/mcp",
        "chat_endpoint": "/chat",
        "ui_endpoint": "/ui/tasks/list"
    }


@app.get("/ui/tasks/list")
def get_task_list_ui():
    """Serve the interactive task list UI"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=task_list_ui())


@app.get("/ui/tasks/chart")
def get_task_chart_ui():
    """Serve the interactive data visualization chart UI"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=task_chart_ui())


@app.get("/ui/tasks/analytics")
def get_task_analytics_ui():
    """Serve the interactive analytics and insights UI"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=task_analytics_ui())


@app.get("/static/cows.svg")
def get_background_image():
    """Serve the background image"""
    from fastapi.responses import FileResponse
    import os
    svg_path = Path(__file__).parent / "cows.svg"
    if svg_path.exists():
        return FileResponse(svg_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Background image not found")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


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
    tools = []

    # Add remote MCP server tools (run async function in sync context)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, can't use asyncio.run()
            # Return empty for now, will be fetched in async endpoint
            pass
        else:
            remote_tools = asyncio.run(get_remote_tools())
            tools.extend(remote_tools)
    except Exception as e:
        print(f"Warning: Could not fetch remote MCP tools in sync context: {e}")

    # Manually define local tools in OpenAI format based on our MCP tools
    tools.append({
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a new task to the task list",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the task"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the task"
                    }
                },
                "required": ["title"]
            }
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all tasks, optionally filtered by completion status",
            "parameters": {
                "type": "object",
                "properties": {
                    "completed": {
                        "type": "boolean",
                        "description": "If true, show only completed tasks. If false, show only incomplete tasks. If not provided, show all tasks."
                    }
                },
                "required": []
            }
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task as completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "The ID of the task to complete"
                    }
                },
                "required": ["task_id"]
            }
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Delete a task from the task list",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "The ID of the task to delete"
                    }
                },
                "required": ["task_id"]
            }
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "get_statistics",
            "description": "Get statistics about the task list including total, completed, and pending counts",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })

    return tools


async def execute_tool(tool_name: str, arguments: dict):
    """Execute an MCP tool by name - either local or remote"""
    # Local tools
    if tool_name == "add_task":
        return add_task(**arguments)
    elif tool_name == "list_tasks":
        return list_tasks(**arguments)
    elif tool_name == "complete_task":
        return complete_task(**arguments)
    elif tool_name == "delete_task":
        return delete_task(**arguments)
    elif tool_name == "get_statistics":
        return get_statistics(**arguments)

    # Try remote MCP server
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
    tool_ui_map = {
        "list_tasks": "ui://tasks/list",
        "get_statistics": "ui://tasks/chart"
    }
    return tool_ui_map.get(tool_name)


def load_skills_content():
    """Load all skill content from the skills directory"""
    skills_content = {}
    skills_base = Path(__file__).parent.parent / "skills"

    if not skills_base.exists():
        return skills_content

    for skill_dir in skills_base.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills_content[skill_dir.name] = skill_file.read_text(encoding='utf-8')

    return skills_content


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint that uses Azure OpenAI with MCP tools.
    The LLM can call the MCP tools to perform task management operations.
    Skills are loaded from the MCP server and injected into the system prompt.
    Returns a streaming response (SSE) for the final answer.
    """
    try:
        # Convert Pydantic models to dict for OpenAI
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Load skills from MCP server
        skills = load_skills_content()

        # Build system message with actual skill content
        skills_text = "\n\n".join([
            f"# Skill: {name}\n\n{content}"
            for name, content in skills.items()
        ])

        system_message = {
            "role": "system",
            "content": f"""You are a helpful task management assistant with access to specialized MCP Skills.

{skills_text}

When listing tasks, remember that an INTERACTIVE UI COMPONENT will appear showing:
- Statistics dashboard with Total/Pending/Completed counts
- Beautiful task cards with checkmarks
- Color-coded completion status
- Task IDs for easy reference

IMPORTANT: Follow the instructions in the skills above. Use them to guide your responses."""
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

        # If the model wants to call tools
        if tool_calls:
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
                # Send UI resources first if any
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


# Mount MCP server after all routes are defined
app.mount("/mcp", mcp_app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

---
name: data-visualization
description: Create visual representations of task data with charts and graphs
version: 1.0.0
tags: [visualization, charts, analytics, ui-components]
---

# Data Visualization Skill

Transform task data into beautiful visual representations including charts, graphs, and interactive dashboards.

## When to Use This Skill

Use this skill when the user wants to:
- See visual charts of their task data
- Understand trends in task completion
- Compare different task metrics
- Get a visual overview of productivity

## Visual Components Available

### 1. Task Statistics Dashboard
- Pie chart showing completion ratio
- Bar chart comparing pending vs completed
- Progress gauge
- Trend lines over time (if historical data available)

### 2. Task Distribution Chart
- Tasks by category (if categories exist)
- Tasks by priority (if priorities exist)
- Completion rate visualization

### 3. Progress Tracker
- Visual progress bar
- Milestone markers
- Goal tracking display

## How to Create Visualizations

When the user asks for visual data:

1. **Gather the data** using `get_statistics` and `list_tasks`
2. **Describe what you'll show**: "I'll create a visual breakdown of your tasks"
3. **Present the visualization component**
4. **Provide insights**: Explain what the data shows

## Example Prompts

- "Show me a chart of my tasks"
- "Visualize my progress"
- "Create a graph of my task completion"
- "I want to see my productivity visually"

## Integration with MCP Apps

This skill can trigger custom visualization components that render:
- Chart.js or D3.js visualizations
- SVG-based graphics
- Canvas-rendered charts
- CSS-based progress indicators

## Best Practices

1. **Choose the right visualization** for the data type
2. **Use color effectively** (green for completed, blue for pending, red for overdue)
3. **Include labels and legends** for clarity
4. **Make it interactive** where possible
5. **Provide textual context** alongside visuals

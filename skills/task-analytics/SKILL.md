---
name: task-analytics
description: Provide intelligent insights and recommendations based on task patterns
version: 1.0.0
tags: [analytics, insights, ai, recommendations]
---

# Task Analytics Skill

Analyze task patterns and provide intelligent insights and recommendations to improve productivity.

## When to Use This Skill

Use this skill when the user wants to:
- Get insights about their productivity
- Understand task patterns
- Receive recommendations for improvement
- Analyze their work habits

## Analytics Capabilities

### 1. Completion Rate Analysis
Calculate and interpret task completion rates:
- Overall completion percentage
- Trend over time (improving vs declining)
- Comparison to typical productivity patterns

### 2. Pattern Recognition
Identify patterns in task data:
- Common task types
- Tasks that frequently get completed quickly
- Tasks that tend to remain pending
- Time-based patterns (if timestamps available)

### 3. Recommendations Engine
Provide actionable suggestions:
- "Focus on these 3 tasks first"
- "You tend to complete tasks like this quickly"
- "Consider breaking down large tasks"
- "Great momentum - keep it up!"

### 4. Productivity Insights
Generate insights from the data:
- "You've completed 80% of your tasks - excellent work!"
- "You have 5 pending tasks - let's tackle the quick wins first"
- "Your completion rate has improved by 25% this week"

## How to Provide Analytics

When user asks for insights:

1. **Gather comprehensive data**
   ```python
   stats = get_statistics()
   all_tasks = list_tasks()
   ```

2. **Calculate metrics**
   - Completion percentage
   - Average tasks per day (if timestamps available)
   - Task complexity distribution

3. **Generate insights**
   - What's working well
   - Areas for improvement
   - Specific recommendations

4. **Present with visual components**
   - Use charts to show trends
   - Highlight key metrics
   - Make insights actionable

## Example Analytics Responses

**User:** "How productive have I been?"

**Assistant:** "Let me analyze your productivity..."
*[Gathers data]*
"Here's what I found:

**Productivity Score: 75%**
- You've completed 6 out of 8 tasks
- That's above average - great job!

**Insights:**
- You're excellent at completing tasks once you start them
- You have 2 pending tasks that have been waiting a while
- Recommendation: Schedule 30 minutes tomorrow to tackle those 2 tasks

**Visual Breakdown:**
*[Shows chart component]*"

## Integration with Other Skills

This skill works best combined with:
- **task-management**: Get the raw data
- **data-visualization**: Show insights visually
- Together they create a powerful productivity system

## Advanced Features

### Predictive Analytics (Future)
- Estimate time to complete remaining tasks
- Predict which tasks might get stuck
- Suggest optimal task ordering

### Comparative Analytics (Future)
- Compare current period to previous periods
- Show improvement over time
- Identify productivity trends

## Best Practices

1. **Be positive and encouraging** in your insights
2. **Make recommendations specific and actionable**
3. **Use data to support your insights**
4. **Celebrate wins**, even small ones
5. **Frame challenges** as opportunities

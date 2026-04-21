"""
Chat service for managing agentic loops and streaming responses.
"""
from typing import List, Dict, Any, AsyncGenerator
from openai import AzureOpenAI
from mcp_service import MCPService
from config import config
from exceptions import log_error
import json
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions with agentic loops"""

    def __init__(self, azure_client: AzureOpenAI, mcp_service: MCPService):
        """
        Initialize chat service.

        Args:
            azure_client: Azure OpenAI client instance
            mcp_service: MCP service instance
        """
        self.azure_client = azure_client
        self.mcp_service = mcp_service

    async def process_chat_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str
    ) -> AsyncGenerator[str, None]:
        """
        Process chat messages with agentic loop and stream responses.

        Args:
            messages: List of conversation messages
            system_prompt: System prompt to use

        Yields:
            Server-Sent Event formatted strings
        """
        try:
            # Get tools from MCP service
            tools = await self.mcp_service.list_tools()

            # Prepare messages with system prompt
            system_message = {"role": "system", "content": system_prompt}
            full_messages = [system_message] + messages

            # Agentic loop
            iteration = 0
            while iteration < config.MAX_TOOL_ITERATIONS:
                iteration += 1
                logger.info(f"Agentic loop iteration {iteration}/{config.MAX_TOOL_ITERATIONS}")

                # Call Azure OpenAI
                response = self.azure_client.chat.completions.create(
                    model=config.AZURE_OPENAI_DEPLOYMENT,
                    messages=full_messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    stream=False
                )

                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

                # Handle tool calls
                if tool_calls:
                    logger.info(f"LLM requested {len(tool_calls)} tool call(s)")
                    tool_results = {}

                    for tc in tool_calls:
                        args = json.loads(tc.function.arguments)

                        # Emit tool call start event
                        yield self._create_sse_event({
                            'type': 'tool_call_start',
                            'tool': {
                                'id': tc.id,
                                'name': tc.function.name,
                                'arguments': args
                            }
                        })

                        # Execute tool
                        try:
                            logger.info(f"Executing tool: {tc.function.name}")
                            result = await self.mcp_service.execute_tool(tc.function.name, args)
                            tool_results[tc.id] = result

                            # Emit tool result event
                            yield self._create_sse_event({
                                'type': 'tool_result',
                                'tool_id': tc.id,
                                'result': result
                            })
                        except Exception as e:
                            log_error(e, f"Tool execution failed: {tc.function.name}")
                            error_result = {"error": str(e)}
                            tool_results[tc.id] = error_result

                            # Emit error result
                            yield self._create_sse_event({
                                'type': 'tool_result',
                                'tool_id': tc.id,
                                'result': error_result
                            })

                    # Append assistant message with tool calls
                    full_messages.append({
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

                    # Append tool results (send only text to LLM, strip UI resources)
                    for tc in tool_calls:
                        result = tool_results[tc.id]
                        # Extract only the 'result' text field for LLM, exclude UI components
                        if isinstance(result, dict) and 'result' in result:
                            content = result['result']
                        else:
                            content = json.dumps(result)

                        full_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": content
                        })

                    continue

                # No tool calls - final answer
                logger.info("LLM provided final answer, streaming response")

                if response_message.content:
                    # Emit content in one chunk
                    yield self._create_sse_event({
                        'type': 'content',
                        'content': response_message.content
                    })
                    yield self._create_sse_event({'type': 'done'})
                    return

                # If no content, create streaming response
                stream = self.azure_client.chat.completions.create(
                    model=config.AZURE_OPENAI_DEPLOYMENT,
                    messages=full_messages,
                    stream=True
                )

                # Stream response tokens
                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield self._create_sse_event({
                                'type': 'content',
                                'content': delta.content
                            })

                yield self._create_sse_event({'type': 'done'})
                return

            # Max iterations reached
            logger.warning(f"Max tool iterations ({config.MAX_TOOL_ITERATIONS}) reached")
            yield self._create_sse_event({
                'type': 'content',
                'content': 'I apologize, but I reached the maximum number of tool calls while trying to answer your question. Please try rephrasing your question or asking something more specific.'
            })
            yield self._create_sse_event({'type': 'done'})

        except Exception as e:
            log_error(e, "Error in chat stream")
            yield self._create_sse_event({
                'type': 'error',
                'message': str(e)
            })

    def _create_sse_event(self, data: Dict[str, Any]) -> str:
        """
        Create a Server-Sent Event formatted string.

        Args:
            data: Data to send in the event

        Returns:
            SSE formatted string
        """
        return f"data: {json.dumps(data)}\n\n"

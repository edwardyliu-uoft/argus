"""
Anthropic Claude LLM Provider

Implements the BaseLLMProvider interface for Anthropic's Claude models.
"""

import os
import json
import logging
from typing import List, Dict, Any
from anthropic import Anthropic

from argus.llm.provider import BaseLLMProvider

_logger = logging.get_logger("argus.console")


class AnthropicProvider(BaseLLMProvider):
    """LLM provider for Anthropic Claude models."""

    def initialize_client(self):
        """Initialize Anthropic client with API key from environment."""
        api_key_env = self.config.get("llm.anthropic.api_key", "ANTHROPIC_API_KEY")
        api_key = os.environ.get(api_key_env)

        if not api_key:
            raise ValueError(f"{api_key_env} environment variable not set")

        self.client = Anthropic(api_key=api_key)

    def convert_tools_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert tools to Anthropic format.

        Since our universal format IS the Anthropic format, no conversion needed.
        """
        return tools

    async def call_with_tools(
        self, prompt: str, tools: List[Dict[str, Any]], max_iterations: int = 10
    ) -> str:
        """
        Call Claude with tool use capability (multi-turn conversation).

        Args:
            prompt: User prompt
            tools: List of tool definitions
            max_iterations: Maximum tool use iterations

        Returns:
            Final text response
        """
        messages = [{"role": "user", "content": prompt}]
        converted_tools = self.convert_tools_format(tools)

        for _ in range(max_iterations):
            try:
                response = self.client.messages.create(
                    model=self.config.get("llm.anthropic.model"),
                    max_tokens=self.config.get("llm.anthropic.max_tokens", 4096),
                    tools=converted_tools,
                    messages=messages,
                )

                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
                    # Extract tool uses and text
                    text_parts = []
                    tool_uses = []

                    for block in response.content:
                        if block.type == "text":
                            text_parts.append(block.text)
                        elif block.type == "tool_use":
                            tool_uses.append(block)

                    # Execute tools
                    tool_results = []
                    for tool_use in tool_uses:
                        _logger.info(
                            "    [Tool] %s(%s...)",
                            tool_use.name,
                            json.dumps(tool_use.input, indent=2)[:100],
                        )
                        result = await self._execute_tool(tool_use.name, tool_use.input)

                        # Truncate large results to avoid token limits
                        max_length = self.config.get(
                            "llm.anthropic.max_tool_result_length", 50000
                        )
                        if len(result) > max_length:
                            original_length = len(result)
                            truncated = result[:max_length]
                            result = f"{truncated}\n\n[Result truncated due to size. Original length: {original_length} characters]"
                            _logger.warning(
                                "    Tool result truncated from %d to %d characters",
                                original_length,
                                max_length,
                            )

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": result,
                            }
                        )

                    # Add assistant response and tool results to messages
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

                    # Continue conversation
                    continue

                else:
                    # No more tool use, return final response
                    final_text = ""
                    for block in response.content:
                        if block.type == "text":
                            final_text += block.text

                    return final_text

            except Exception as e:
                _logger.error("    LLM call failed: %s", e)
                raise

        # Max iterations reached
        return "Max tool use iterations reached"

    def call_simple(self, prompt: str) -> str:
        """
        Call Claude without tools (simple text completion).

        Args:
            prompt: User prompt

        Returns:
            Text response
        """
        try:
            response = self.client.messages.create(
                model=self.config.get("llm.anthropic.model"),
                max_tokens=self.config.get("llm.anthropic.max_tokens", 4096),
                messages=[{"role": "user", "content": prompt}],
            )

            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

            return final_text

        except Exception as e:
            _logger.error("    LLM call failed: %s", e)
            raise

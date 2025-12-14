"""
Anthropic Claude LLM Provider

Implements the BaseLLMProvider interface for Anthropic's Claude models.
"""

from typing import List, Dict, Any
import os
import logging
import json

# pylint: disable=import-self
from anthropic import Anthropic

from argus.llm.provider import BaseLLMProvider

_logger = logging.getLogger("argus.console")


class AnthropicProvider(BaseLLMProvider):
    """LLM provider for Anthropic Claude models."""

    def initialize_client(self):
        """Initialize Anthropic client with API key from environment."""
        api_key_env = self.config.get("api_key", "ANTHROPIC_API_KEY")
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
                    model=self.config.get("model"),
                    max_tokens=self.config.get("max_tokens", 4096),
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
                            "\t[Tool] %s(%s...)",
                            tool_use.name,
                            json.dumps(tool_use.input, indent=2)[:100],
                        )
                        result = await self._execute_tool(tool_use.name, tool_use.input)

                        # Truncate large results to avoid token limits
                        max_length = self.config.get("max_tool_result_length", 50000)
                        if len(result) > max_length:
                            original_length = len(result)
                            truncated = result[:max_length]
                            result = (
                                f"{truncated}\n\n[Result truncated due to size. "
                                "Original length: {original_length} characters]"
                            )
                            _logger.warning(
                                "\tTool result truncated from %d to %d characters",
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
                _logger.error("\tLLM call failed: %s", e)
                raise

        # Max iterations reached
        return "Max tool use iterations reached"

    async def call_simple(self, prompt: str) -> str:
        """
        Call Claude without tools (simple text completion).
        Includes retry logic for connection failures.

        Args:
            prompt: User prompt

        Returns:
            Text response
        """
        from argus import utils
        import asyncio

        max_retries = utils.conf_get(self.config, "llm.max_retries", 3)
        retry_delay = utils.conf_get(self.config, "llm.retry_delay", 2.0)

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.config.get("model"),
                    max_tokens=self.config.get("max_tokens", 4096),
                    messages=[{"role": "user", "content": prompt}],
                )

                final_text = ""
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text

                return final_text

            except Exception as e:
                error_str = str(e).lower()

                # Check if this is a retryable error
                is_retryable = any(
                    keyword in error_str
                    for keyword in [
                        "disconnected",
                        "connection",
                        "timeout",
                        "remote protocol",
                        "broken pipe",
                        "reset by peer",
                        "server error",
                        "503",
                        "502",
                        "500",
                        "429",  # Rate limit
                        "overloaded",
                    ]
                )

                if is_retryable and attempt < max_retries - 1:
                    _logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt + 1,
                        max_retries,
                        e,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    # Non-retryable or final attempt
                    if attempt == max_retries - 1:
                        _logger.error(
                            "LLM call failed after %d attempts: %s", max_retries, e
                        )
                    _logger.error("\tLLM call failed: %s", e)
                    raise

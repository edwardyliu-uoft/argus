"""
Abstract base class for LLM providers.
Defines the interface that all providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import logging

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from argus import utils

_logger = logging.getLogger("argus.console")


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers (Anthropic, Gemini, etc.)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provider with configuration.

        Args:
            config: ArgusConfig instance
        """
        self.config = config
        self.client = None
        self.__mcp_session = None
        self.__mcp_context = None

    @abstractmethod
    def initialize_client(self):
        """
        Initialize the LLM API client.
        Should read API key from environment and create client instance.

        Raises:
            ValueError: If API key is not found in environment
        """

    @abstractmethod
    def convert_tools_format(self, tools: List[Dict[str, Any]]) -> Any:
        """
        Convert tools from universal format to provider-specific format.

        Universal format (Anthropic-style):
        {
            "name": "tool_name",
            "description": "description",
            "input_schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }

        Args:
            tools: List of tool definitions in universal format

        Returns:
            Provider-specific tool format
        """

    @abstractmethod
    async def call_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        max_iterations: int = 10,
    ) -> str:
        """
        Call LLM with tool use capability (multi-turn conversation).

        This method should:
        1. Send prompt with tool definitions
        2. Check if LLM wants to use tools
        3. Execute requested tools
        4. Send results back to LLM
        5. Repeat until LLM provides final answer

        Args:
            prompt: User prompt
            tools: List of available tools in universal format
            max_iterations: Maximum tool use iterations

        Returns:
            Final text response from LLM
        """

    @abstractmethod
    async def call_simple(self, prompt: str) -> str:
        """
        Call LLM without tools (simple text completion).

        Args:
            prompt: User prompt

        Returns:
            Text response from LLM
        """

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        Execute a tool by calling the MCP server via the MCP client.
        This is shared across all providers. Includes retry logic for connection failures.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Input parameters for the tool

        Returns:
            Tool result as JSON string

        Raises:
            RuntimeError: If MCP server call fails after all retries
        """
        max_retries = utils.conf_get(self.config, "server.max_retries", 3)
        retry_delay = utils.conf_get(self.config, "server.retry_delay", 1.0)

        for attempt in range(max_retries):
            try:
                # Initialize MCP session if not already done (lazy initialization)
                if self.__mcp_session is None:
                    await self._initialize_mcp_session()

                # Call the tool using the persistent session
                result = await self._call_mcp_tool(tool_name, tool_args)
                return json.dumps(result)

            except Exception as e:
                error_str = str(e).lower()

                # Check if this is a connection/network error that we can retry
                is_retryable = any(
                    keyword in error_str
                    for keyword in [
                        "disconnected",
                        "connection",
                        "timeout",
                        "remote protocol",
                        "broken pipe",
                        "reset by peer",
                    ]
                )

                if is_retryable and attempt < max_retries - 1:
                    _logger.warning(
                        "Tool execution failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt + 1,
                        max_retries,
                        e,
                        retry_delay,
                    )

                    # Clean up broken session before retry
                    await self._cleanup_broken_session()

                    # Wait before retrying
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    # Non-retryable error or final attempt
                    if attempt == max_retries - 1:
                        _logger.error(
                            "Tool execution failed after %d attempts: %s",
                            max_retries,
                            e,
                        )
                    raise RuntimeError(f"Tool execution error: {e}") from e

        # Should never reach here, but just in case
        raise RuntimeError("Tool execution failed: max retries exceeded")

    async def _initialize_mcp_session(self) -> None:
        """
        Initialize persistent MCP client session.
        Called lazily on first tool execution.
        """
        # Get MCP server endpoint from config
        mcp_host = utils.conf_get(self.config, "server.host", "127.0.0.1")
        mcp_port = utils.conf_get(self.config, "server.port", 8000)
        mount_path = utils.conf_get(self.config, "server.mount_path", "/mcp")
        mcp_url = f"http://{mcp_host}:{mcp_port}{mount_path}"

        # Create persistent connection context
        self.__mcp_context = streamablehttp_client(mcp_url)
        # pylint: disable=no-member, unnecessary-dunder-call
        read, write, _ = await self.__mcp_context.__aenter__()

        # Create and initialize session
        self.__mcp_session = ClientSession(read, write)
        await self.__mcp_session.__aenter__()
        await self.__mcp_session.initialize()

    async def _call_mcp_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Call MCP tool using the persistent session.

        Args:
            tool_name: Tool name to call
            tool_args: Tool input arguments

        Returns:
            Tool result dictionary
        """
        if self.__mcp_session is None:
            raise RuntimeError("MCP session not initialized")

        # Call the tool
        result = await self.__mcp_session.call_tool(tool_name, tool_args)

        # Extract content from result
        if hasattr(result, "content") and result.content:
            # MCP returns list of content blocks
            content_blocks = []
            for content in result.content:
                if hasattr(content, "text"):
                    content_blocks.append(content.text)

            return {"content": content_blocks, "raw": str(result)}
        else:
            return {"content": [str(result)], "raw": str(result)}

    async def _cleanup_broken_session(self) -> None:
        """
        Clean up a broken MCP session without raising errors.
        Used internally for retry logic.
        """
        if self.__mcp_session is not None:
            try:
                await self.__mcp_session.__aexit__(None, None, None)
            # pylint: disable=broad-except
            except Exception:
                pass  # Ignore errors during broken session cleanup
            finally:
                self.__mcp_session = None

        if self.__mcp_context is not None:
            try:
                # pylint: disable=no-member
                await self.__mcp_context.__aexit__(None, None, None)
            # pylint: disable=broad-except
            except Exception:
                pass  # Ignore errors during broken context cleanup
            finally:
                self.__mcp_context = None

    async def cleanup_mcp_session(self) -> None:
        """
        Close the MCP client session and cleanup resources.
        Should be called when tool calling is complete.
        """
        if self.__mcp_session is not None:
            try:
                await self.__mcp_session.__aexit__(None, None, None)

            # pylint: disable=broad-except
            except Exception as e:
                # Log but don't fail on cleanup errors
                _logger.warning("MCP session cleanup error: %s", e)
            finally:
                self.__mcp_session = None

        if self.__mcp_context is not None:
            try:
                # pylint: disable=no-member
                await self.__mcp_context.__aexit__(None, None, None)

            # pylint: disable=broad-except
            except Exception as e:
                # Log but don't fail on cleanup errors
                _logger.warning("MCP context cleanup error: %s", e)
            finally:
                self.__mcp_context = None

"""
Abstract base class for LLM providers.
Defines the interface that all providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from argus.core.config import conf


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers (Anthropic, Gemini, etc.)."""

    def __init__(self):
        """
        Initialize the provider with configuration.

        Args:
            config: ArgusConfig instance
        """
        self.config = conf
        self.client = None

    @abstractmethod
    def initialize_client(self):
        """
        Initialize the LLM API client.
        Should read API key from environment and create client instance.

        Raises:
            ValueError: If API key is not found in environment
        """
        pass

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
        pass

    @abstractmethod
    def call_with_tools(
        self, prompt: str, tools: List[Dict[str, Any]], max_iterations: int = 10
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
        pass

    @abstractmethod
    def call_simple(self, prompt: str) -> str:
        """
        Call LLM without tools (simple text completion).

        Args:
            prompt: User prompt

        Returns:
            Text response from LLM
        """
        pass

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool by calling the MCP server function.
        This is shared across all providers.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool result as JSON string
        """
        #TODO: implement this function when MCP server code is ready
        raise NotImplementedError("Unimplementated until new MCP server code is available.")
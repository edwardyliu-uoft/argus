"""MCP prompt plugin interface for Argus plugins."""

from typing import Callable, Dict

from .plugin import BasePlugin


class MCPPromptPlugin(BasePlugin):
    """
    Base class for MCP prompt plugins.

    Prompts are reusable prompt templates that can be invoked by name.
    """

    # Dict mapping prompt names to callable functions.
    #   Each function should return prompt content.
    # Example:
    #     {
    #         "analysis_prompt": analysis_prompt_function,
    #         "review_prompt": review_prompt_function
    #     }
    prompts: Dict[str, Callable]

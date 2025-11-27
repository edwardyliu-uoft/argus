"""
Google Gemini LLM Provider

Implements the BaseLLMProvider interface for Google's Gemini models.
"""

from typing import List, Dict, Any
import os
import logging

from google import genai
from google.genai import types

from argus.llm.provider import BaseLLMProvider

_logger = logging.getLogger("argus.console")


class GeminiProvider(BaseLLMProvider):
    """LLM provider for Google Gemini models."""

    def initialize_client(self):
        """Initialize Gemini client with API key from environment."""
        api_key_env = self.config.get("api_key", "GEMINI_API_KEY")
        api_key = os.environ.get(api_key_env)

        if not api_key:
            raise ValueError(f"{api_key_env} environment variable not set")

        self.client = genai.Client(api_key=api_key)

    def convert_tools_format(self, tools: List[Dict[str, Any]]) -> types.Tool:
        """
        Convert tools from Anthropic format to Gemini format.

        Anthropic format:
        {
            "name": "tool_name",
            "description": "description",
            "input_schema": {...}
        }

        Gemini format:
        types.Tool(function_declarations=[
            {
                "name": "tool_name",
                "description": "description",
                "parameters": {...}  # Note: "parameters" not "input_schema"
            }
        ])
        """
        gemini_functions = []
        for tool in tools:
            # Deep copy and fix the schema for Gemini
            parameters = self._fix_schema_for_gemini(tool["input_schema"])

            gemini_func = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": parameters,
            }
            gemini_functions.append(gemini_func)

        return types.Tool(function_declarations=gemini_functions)

    def _fix_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix JSON schema for Gemini compatibility.

        Gemini requires:
        - Array properties must have 'items' defined
        - Nested objects are properly structured
        """
        import copy

        fixed_schema = copy.deepcopy(schema)

        # Fix properties if they exist
        if "properties" in fixed_schema:
            for _, prop_def in fixed_schema["properties"].items():
                if prop_def.get("type") == "array" and "items" not in prop_def:
                    # Add default items schema for arrays
                    prop_def["items"] = {"type": "object"}
                elif prop_def.get("type") == "object" and "properties" in prop_def:
                    # Recursively fix nested objects
                    prop_def = self._fix_schema_for_gemini(prop_def)

        return fixed_schema

    async def call_with_tools(
        self, prompt: str, tools: List[Dict[str, Any]], max_iterations: int = 10
    ) -> str:
        """
        Call Gemini with function calling capability (multi-turn conversation).

        Args:
            prompt: User prompt
            tools: List of tool definitions
            max_iterations: Maximum function call iterations

        Returns:
            Final text response
        """
        gemini_tools = self.convert_tools_format(tools)
        config = types.GenerateContentConfig(
            tools=[gemini_tools], temperature=0, response_modalities=["TEXT"]
        )

        # Start with initial prompt
        contents = [prompt]

        for _ in range(max_iterations):
            try:
                response = self.client.models.generate_content(
                    model=self.config.get("model"),
                    contents=contents,
                    config=config,
                )

                # Check if response is valid
                if not response.candidates or len(response.candidates) == 0:
                    return "No response from Gemini"

                candidate = response.candidates[0]
                parts = candidate.content.parts

                # Check if any parts contain function calls
                has_function_call = any(
                    hasattr(part, "function_call") and part.function_call
                    for part in parts
                )

                if has_function_call:
                    # Extract and execute function calls
                    tool_results_parts = []

                    for part in parts:
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            _logger.info("    [Tool] %s(...)", fc.name)

                            # Execute the tool
                            result = await self._execute_tool(fc.name, dict(fc.args))

                            # Truncate large results to avoid token limits
                            max_length = self.config.get(
                                "max_tool_result_length", 50000
                            )
                            if len(result) > max_length:
                                original_length = len(result)
                                truncated = result[:max_length]
                                result = (
                                    f"{truncated}\n\n[Result truncated due to size. "
                                    "Original length: {original_length} characters]"
                                )
                                _logger.warning(
                                    "    Tool result truncated from %d to %d characters",
                                    original_length,
                                    max_length,
                                )

                            # Create function response part
                            tool_results_parts.append(
                                types.Part.from_function_response(
                                    name=fc.name, response={"result": result}
                                )
                            )

                    # Add model response to conversation
                    contents.append(candidate.content)

                    # Add function results
                    contents.append(
                        types.Content(role="user", parts=tool_results_parts)
                    )

                    # Continue conversation
                    continue

                else:
                    # No function calls, extract final text
                    final_text = ""
                    for part in parts:
                        if hasattr(part, "text") and part.text:
                            final_text += part.text

                    return final_text if final_text else "Empty response from Gemini"

            except Exception as e:
                _logger.error("    LLM call failed: %s", e)
                raise

        # Max iterations reached
        return "Max function call iterations reached"

    def call_simple(self, prompt: str) -> str:
        """
        Call Gemini without function calling (simple text completion).

        Args:
            prompt: User prompt

        Returns:
            Text response
        """
        try:
            config = types.GenerateContentConfig(
                temperature=0, response_modalities=["TEXT"]
            )

            response = self.client.models.generate_content(
                model=self.config.get("model"),
                contents=prompt,
                config=config,
            )

            # Extract text from response
            if not response.candidates or len(response.candidates) == 0:
                return "No response from Gemini"

            final_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

            return final_text if final_text else "Empty response from Gemini"

        except Exception as e:
            _logger.error("    LLM call failed: %s", e)
            raise

"""Inject tools into system prompts"""

import logging
from typing import Any

import tiktoken

from zikos.services.prompt.sections import ToolInstructionsSection

_logger = logging.getLogger(__name__)


class ToolInjector:
    """Handles injection of tools into system prompts"""

    def inject_if_needed(
        self,
        history: list[dict[str, Any]],
        tool_provider,
        tools: list,
        tool_schemas: list[dict[str, Any]],
        system_prompt_getter,
    ) -> bool:
        """Inject tools into system prompt if needed

        Args:
            history: Conversation history
            tool_provider: Tool provider instance
            tools: List of tool objects
            tool_schemas: List of tool schemas
            system_prompt_getter: Callable that returns the system prompt string

        Returns:
            True if tools were injected, False otherwise
        """
        if not tools or not tool_provider or not tool_provider.should_inject_tools_as_text():
            return False

        system_has_tools = False
        if history and history[0].get("role") == "system":
            system_content = history[0].get("content", "")
            if "<tools>" in system_content or "# Available Tools" in system_content:
                system_has_tools = True

        if system_has_tools:
            return False

        tools_section = ToolInstructionsSection(tool_provider, tools, tool_schemas)
        tools_text = tools_section.render()

        enc = tiktoken.get_encoding("cl100k_base")
        tools_tokens = len(enc.encode(tools_text))

        if history and history[0].get("role") == "system":
            original_system = history[0].get("content", "")
            original_tokens = len(enc.encode(original_system))
            history[0]["content"] = f"{original_system}\n\n{tools_text}"
            final_system = history[0]["content"]
        else:
            system_prompt = system_prompt_getter()
            original_tokens = len(enc.encode(system_prompt))
            final_system = f"{system_prompt}\n\n{tools_text}"
            history.insert(0, {"role": "system", "content": final_system})

        final_tokens = len(enc.encode(final_system))
        _logger.info(
            f"Tool injection complete: system prompt {original_tokens} -> {final_tokens} tokens "
            f"(tools section: {tools_tokens} tokens, {len(tools)} tools)"
        )

        return True

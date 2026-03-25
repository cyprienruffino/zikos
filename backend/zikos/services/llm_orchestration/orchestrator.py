"""Orchestrate LLM response generation, handling common logic"""

import json
import logging
from typing import Any

from zikos.constants import LLM
from zikos.mcp.server import MCPServer
from zikos.mcp.tool import ToolCategory
from zikos.services.llm_orchestration.audio_context_enricher import AudioContextEnricher
from zikos.services.llm_orchestration.conversation_manager import ConversationManager
from zikos.services.llm_orchestration.message_preparer import MessagePreparer
from zikos.services.llm_orchestration.response_validator import ResponseValidator
from zikos.services.llm_orchestration.thinking_extractor import ThinkingExtractor
from zikos.services.llm_orchestration.tool_call_parser import ToolCallParser
from zikos.services.llm_orchestration.tool_executor import ToolExecutor
from zikos.services.llm_orchestration.tool_injector import ToolInjector
from zikos.services.model_strategy import ModelStrategy, get_model_strategy

_conversation_logger = logging.getLogger("zikos.conversation")


class IterationState:
    """Tracks state during LLM iteration loop"""

    def __init__(self):
        self.iteration = 0
        self.max_iterations = LLM.MAX_ITERATIONS
        self.consecutive_tool_calls = 0
        self.max_consecutive_tool_calls = LLM.MAX_CONSECUTIVE_TOOL_CALLS
        self.recent_tool_calls: list[str] = []


class LLMOrchestrator:
    """Orchestrates LLM response generation, handling common setup and iteration logic"""

    def __init__(
        self,
        conversation_manager: ConversationManager,
        message_preparer: MessagePreparer,
        audio_context_enricher: AudioContextEnricher,
        tool_injector: ToolInjector,
        tool_call_parser: ToolCallParser,
        tool_executor: ToolExecutor,
        response_validator: ResponseValidator,
        thinking_extractor: ThinkingExtractor,
        system_prompt_getter,
    ):
        self.conversation_manager = conversation_manager
        self.message_preparer = message_preparer
        self.audio_context_enricher = audio_context_enricher
        self.tool_injector = tool_injector
        self.tool_call_parser = tool_call_parser
        self.tool_executor = tool_executor
        self.response_validator = response_validator
        self.thinking_extractor = thinking_extractor
        self._get_system_prompt = system_prompt_getter
        self.strategy: ModelStrategy | None = None

    def prepare_conversation(
        self, message: str, session_id: str, mcp_server: MCPServer
    ) -> tuple[list[dict[str, Any]], str, Any, list, list[dict[str, Any]], IterationState]:
        """Prepare conversation for LLM interaction

        Returns:
            Tuple of (history, original_message, tool_registry, tools, tool_schemas, iteration_state)
        """
        history = self.conversation_manager.get_history(session_id)

        original_message = message
        message, _ = self.audio_context_enricher.enrich_message(message, history)

        history.append({"role": "user", "content": message})
        _conversation_logger.info(
            f"Session: {session_id}\nUser Prompt:\n{original_message}\n{'=' * 80}"
        )

        tool_registry = mcp_server.get_tool_registry()
        tools = tool_registry.get_all_tools()
        tool_schemas = tool_registry.get_all_schemas()

        if not self.strategy:
            self.strategy = get_model_strategy()

        self.tool_injector.inject_if_needed(
            history, self.strategy.tool_provider, tools, tool_schemas, self._get_system_prompt
        )

        iteration_state = IterationState()

        return history, original_message, tool_registry, tools, tool_schemas, iteration_state

    def prepare_iteration_messages(
        self,
        history: list[dict[str, Any]],
        context_window: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Prepare messages for current iteration and validate token limit

        Args:
            history: Conversation history
            context_window: Actual context window size. If None, uses hardcoded constants.

        Returns:
            Tuple of (messages, token_error) where token_error is None if valid
        """
        current_messages = self.message_preparer.prepare(
            history,
            max_tokens=None,
            for_user=False,
            context_window=context_window,
        )

        token_error = self.response_validator.validate_token_limit(
            current_messages, context_window=context_window
        )

        return current_messages, token_error

    def process_llm_response(
        self,
        message_obj: dict[str, Any],
        history: list[dict[str, Any]],
        session_id: str,
    ) -> tuple[str, str, str]:
        """Process LLM response, extract thinking, validate content

        Returns:
            Tuple of (raw_content, cleaned_content, thinking_content)
        """
        raw_content = message_obj.get("content", "")

        content_error = self.response_validator.validate_response_content(raw_content)
        if content_error:
            return raw_content, "", ""

        cleaned_content, thinking_content = self.thinking_extractor.extract(raw_content)

        if thinking_content:
            thinking_msg = {"role": "thinking", "content": thinking_content}
            history.append(thinking_msg)

        message_obj["content"] = cleaned_content
        history.append(message_obj)

        return raw_content, cleaned_content, thinking_content

    async def process_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        iteration_state: IterationState,
        history: list[dict[str, Any]],
        tool_registry: Any,
        mcp_server: MCPServer,
        session_id: str,
        cleaned_content: str,
    ) -> tuple[bool, dict[str, Any] | None, list[dict[str, Any]]]:
        """Process tool calls, handle loops, execute tools

        Returns:
            Tuple of (should_continue, response_or_error, tool_call_infos)
            - should_continue: True if iteration should continue normally
            - response_or_error: Widget response or loop error dict, or None
            - tool_call_infos: Tool call info dicts for UI streaming
        """
        iteration_state.consecutive_tool_calls += 1

        current_tool_names = []
        tool_call_infos: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_name = (
                tool_call.get("function", {}).get("name", "")
                if isinstance(tool_call.get("function"), dict)
                else ""
            )
            current_tool_names.append(tool_name)

            # Build UI info, filtering out widget/recording tools
            if tool_name:
                tool = tool_registry.get_tool(tool_name)
                if tool and tool.category in (ToolCategory.WIDGET, ToolCategory.RECORDING):
                    continue

            tool_args_str = (
                tool_call.get("function", {}).get("arguments", "{}")
                if isinstance(tool_call.get("function"), dict)
                else "{}"
            )
            try:
                tool_args = (
                    json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                )
            except json.JSONDecodeError:
                tool_args = {}

            tool_call_infos.append(
                {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "tool_id": tool_call.get("id"),
                }
            )

        # Check for loops BEFORE adding current names to recent
        loop_error = self.response_validator.validate_tool_call_loops(
            iteration_state.consecutive_tool_calls,
            iteration_state.recent_tool_calls,
            iteration_state.max_consecutive_tool_calls,
        )
        if loop_error:
            return False, loop_error, tool_call_infos

        # Track recent tool calls
        iteration_state.recent_tool_calls.extend(current_tool_names)
        if len(iteration_state.recent_tool_calls) > LLM.RECENT_TOOL_CALLS_WINDOW:
            iteration_state.recent_tool_calls = iteration_state.recent_tool_calls[
                -LLM.RECENT_TOOL_CALLS_WINDOW :
            ]

        # Execute tools
        tool_results = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            widget_response = await self.tool_executor.execute_tool_call(
                tool_call,
                tool_registry,
                mcp_server,
                session_id,
                cleaned_content,
                self.tool_call_parser,
            )
            if widget_response:
                return False, widget_response, tool_call_infos

            tool_result = await self.tool_executor.execute_tool_and_get_result(
                tool_call, tool_registry, mcp_server, session_id
            )
            tool_results.append(tool_result)

        history.extend(tool_results)

        return True, None, tool_call_infos

    def finalize_response(
        self, cleaned_content: str, thinking_content: str, iteration_state: IterationState
    ) -> str:
        """Finalize response, reset counters

        Returns:
            Final response content
        """
        iteration_state.consecutive_tool_calls = 0
        iteration_state.recent_tool_calls.clear()

        return (
            cleaned_content
            or "I'm not sure how to help with that. Could you rephrase your request?"
        )

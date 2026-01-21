"""LLM service"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from zikos.config import settings
from zikos.constants import LLM
from zikos.mcp.server import MCPServer
from zikos.mcp.tool import ToolCategory
from zikos.services.audio import AudioService
from zikos.services.llm_backends import create_backend
from zikos.services.llm_orchestration.audio_context_enricher import AudioContextEnricher
from zikos.services.llm_orchestration.conversation_manager import ConversationManager
from zikos.services.llm_orchestration.message_preparer import MessagePreparer
from zikos.services.llm_orchestration.orchestrator import LLMOrchestrator
from zikos.services.llm_orchestration.response_validator import ResponseValidator
from zikos.services.llm_orchestration.thinking_extractor import ThinkingExtractor
from zikos.services.llm_orchestration.tool_call_parser import ToolCallParser
from zikos.services.llm_orchestration.tool_executor import ToolExecutor
from zikos.services.llm_orchestration.tool_injector import ToolInjector
from zikos.services.prompt import SystemPromptBuilder
from zikos.services.prompt.sections import (
    AudioAnalysisContextFormatter,
    CorePromptSection,
    ToolInstructionsSection,
)
from zikos.services.tool_providers import get_tool_provider
from zikos.utils.gpu import get_optimal_gpu_layers

# Setup logger for thinking/reasoning logs
_thinking_logger = logging.getLogger("zikos.thinking")
_thinking_logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
_logs_dir = Path("logs")
_logs_dir.mkdir(exist_ok=True)

# File handler for thinking logs
_thinking_handler = logging.FileHandler(_logs_dir / "thinking.log", encoding="utf-8")
_thinking_handler.setLevel(logging.DEBUG)  # Log DEBUG level to see when thinking is missing
_thinking_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
_thinking_handler.setFormatter(_thinking_formatter)
_thinking_logger.addHandler(_thinking_handler)
_thinking_logger.propagate = False

# Setup logger for LLM service
_logger = logging.getLogger("zikos.services.llm")


class LLMService:
    """Service for LLM interactions"""

    def __init__(self):
        self.backend = None
        self.audio_service = AudioService()
        self.tool_provider = None
        self.thinking_extractor = ThinkingExtractor()
        self.conversation_manager = ConversationManager(self._get_system_prompt)
        self.message_preparer = MessagePreparer()
        self.audio_context_enricher = AudioContextEnricher()
        self.tool_injector = ToolInjector()
        self.tool_call_parser = ToolCallParser()
        self.tool_executor = ToolExecutor()
        self.response_validator = ResponseValidator()
        self.orchestrator = LLMOrchestrator(
            self.conversation_manager,
            self.message_preparer,
            self.audio_context_enricher,
            self.tool_injector,
            self.tool_call_parser,
            self.tool_executor,
            self.response_validator,
            self.thinking_extractor,
            self._get_system_prompt,
        )
        self.conversations = self.conversation_manager.conversations
        self._initialize_llm()

    def __del__(self):
        """Cleanup LLM backend on deletion"""
        if self.backend is not None:
            try:
                self.backend.close()
            except Exception:
                pass

    def _initialize_llm(self):
        """Initialize LLM backend"""
        if not settings.llm_model_path:
            return

        model_path_str = settings.llm_model_path
        model_path = Path(model_path_str)

        if (
            not model_path.exists()
            and not model_path_str.startswith("Qwen/")
            and "/" not in model_path_str
        ):
            _logger.warning(f"Model file not found at {model_path}")
            _logger.warning("The application will start but LLM features will be unavailable.")
            _logger.info(
                f"To download a model, run: python scripts/download_model.py qwen2.5-7b-instruct-q4 -o {model_path.parent}"
            )
            _logger.info(
                "See MODEL_RECOMMENDATIONS.md for recommended models with better function calling support."
            )
            return

        try:
            backend_type = settings.llm_backend if settings.llm_backend != "auto" else None
            self.backend = create_backend(model_path_str, backend_type)

            if self.backend is None:
                _logger.warning("Could not create LLM backend")
                return

            n_gpu_layers = settings.llm_n_gpu_layers
            if n_gpu_layers == -1:
                n_gpu_layers = get_optimal_gpu_layers(model_path_str, backend_type or "auto")

            _logger.info(f"Initializing LLM backend: {type(self.backend).__name__}")
            _logger.info(f"Model path: {model_path_str}")
            _logger.info(f"Context window: {settings.llm_n_ctx} tokens")
            _logger.info(f"GPU layers: {n_gpu_layers}")

            self.backend.initialize(
                model_path=model_path_str,
                n_ctx=settings.llm_n_ctx,
                n_gpu_layers=n_gpu_layers,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )

            self.tool_provider = get_tool_provider(model_path_str)
            _logger.info(
                f"LLM initialized successfully with context window: {settings.llm_n_ctx} tokens"
            )
            _logger.info(f"Using tool provider: {type(self.tool_provider).__name__}")
        except Exception as e:
            _logger.error(f"Error initializing LLM: {e}", exc_info=True)
            _logger.warning("The application will start but LLM features will be unavailable.")
            self.backend = None
            self.tool_provider = get_tool_provider()

    def _get_conversation_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history for session"""
        result: list[dict[str, Any]] = self.conversation_manager.get_history(session_id)
        return result

    def get_thinking_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all thinking messages for a session (for debugging)

        Returns list of thinking messages with their context (adjacent messages)
        """
        result: list[dict[str, Any]] = self.conversation_manager.get_thinking_for_session(
            session_id
        )
        return result

    def _extract_thinking(self, content: str | None) -> tuple[str, str]:
        """Extract thinking content from <thinking> tags

        Returns:
            tuple: (cleaned_content, thinking_content)
        """
        result: tuple[str, str] = self.thinking_extractor.extract(content)
        return result

    def _prepare_messages(
        self, history: list[dict[str, Any]], max_tokens: int | None = None, for_user: bool = False
    ) -> list[dict[str, Any]]:
        """Prepare messages for LLM, ensuring system prompt is included

        For models that don't properly handle system messages (like Phi3),
        prepend the system prompt to the first user message and remove the system message.

        Also truncates conversation history if it exceeds max_tokens to prevent context overflow.
        IMPORTANT: Always preserves audio analysis messages even if they're older.

        Args:
            history: Conversation history
            max_tokens: Maximum tokens to include
            for_user: If True, filters out thinking messages for user display
        """
        result: list[dict[str, Any]] = self.message_preparer.prepare(history, max_tokens, for_user)
        return result

    async def generate_response(
        self,
        message: str,
        session_id: str,
        mcp_server: MCPServer,
    ) -> dict[str, Any]:
        """Generate LLM response, handling tool calls

        This method accumulates the stream from generate_response_stream and returns
        the final response. Streaming is the single source of truth for response generation.
        """
        final_response = None
        tool_call_response = None
        tool_registry = None

        async for chunk in self.generate_response_stream(message, session_id, mcp_server):
            chunk_type = chunk.get("type")

            # Keep tool_call chunks, but only return them if they're widgets
            if chunk_type == "tool_call":
                # Get tool registry to check if tool is a widget
                if tool_registry is None:
                    tool_registry = mcp_server.get_tool_registry()

                tool_name = chunk.get("tool_name")
                if tool_name:
                    tool = tool_registry.get_tool(tool_name)
                    # Only keep widget/recording tool calls (they pause the conversation)
                    if tool and tool.category in (ToolCategory.WIDGET, ToolCategory.RECORDING):
                        tool_call_response = chunk

            # Keep the last response or error chunk as the final result
            if chunk_type in ("response", "error"):
                final_response = chunk

        # If we got a widget tool_call, return it (pauses conversation)
        if tool_call_response:
            return dict(tool_call_response)

        # Return error responses as-is (standardized error handling)
        if final_response and final_response.get("type") == "error":
            return dict(final_response)

        if final_response:
            return dict(final_response)

        history = self._get_conversation_history(session_id)
        self._inject_error_system_message(
            history,
            "unexpected_error",
            "An unexpected error occurred while generating the response",
        )
        async for chunk in self.generate_response_stream("", session_id, mcp_server):
            if chunk.get("type") == "response":
                return dict(chunk)

        return {
            "type": "response",
            "message": "An unexpected error occurred while generating the response.",
        }

    def _yield_error(self, message: str) -> dict[str, Any]:
        """Create a standardized error response"""
        return {"type": "error", "message": message}

    def _inject_error_system_message(
        self, history: list[dict[str, Any]], error_type: str, error_details: str
    ) -> None:
        """Inject error information as a system message for the LLM to handle

        Args:
            history: Conversation history to modify
            error_type: Type of error (e.g., 'token_limit', 'streaming_error', 'tool_loop')
            error_details: Technical details about the error
        """
        error_message = f"ERROR: {error_type}: {error_details}"
        history.append({"role": "system", "content": error_message})

    async def generate_response_stream(
        self,
        message: str,
        session_id: str,
        mcp_server: MCPServer,
    ):
        """Generate LLM response with streaming, handling tool calls"""
        from collections.abc import AsyncGenerator

        if not self.backend or not self.backend.is_initialized():
            yield self._yield_error(
                "LLM not available. Please ensure the model file exists at the path specified by LLM_MODEL_PATH."
            )
            return

        history = self._get_conversation_history(session_id)
        original_message = message
        message, _ = self.audio_context_enricher.enrich_message(message, history)

        history.append({"role": "user", "content": message})
        _thinking_logger.info(
            f"Session: {session_id}\n" f"User Prompt:\n{original_message}\n" f"{'='*80}"
        )

        tool_registry = mcp_server.get_tool_registry()
        tools = tool_registry.get_all_tools()
        tool_schemas = tool_registry.get_all_schemas()

        if not self.tool_provider:
            self.tool_provider = get_tool_provider()

        self.tool_injector.inject_if_needed(
            history, self.tool_provider, tools, tool_schemas, self._get_system_prompt
        )

        max_iterations = LLM.MAX_ITERATIONS
        iteration = 0
        consecutive_tool_calls = 0
        max_consecutive_tool_calls = 5
        recent_tool_calls: list[str] = []
        accumulated_content = ""

        while iteration < max_iterations:
            iteration += 1
            current_messages = self._prepare_messages(
                history, max_tokens=LLM.MAX_TOKENS_PREPARE_MESSAGES, for_user=False
            )

            token_error = self.response_validator.validate_token_limit(current_messages)
            if token_error:
                self._inject_error_system_message(
                    history, token_error["error_type"], token_error["error_details"]
                )
                continue

            tools_param = None
            if tools and self.tool_provider and self.tool_provider.should_pass_tools_as_parameter():
                tools_param = tool_schemas

            try:
                stream = self.backend.stream_chat_completion(
                    messages=current_messages,
                    tools=tools_param,
                    temperature=settings.llm_temperature,
                    top_p=settings.llm_top_p,
                )

                accumulated_content = ""
                final_delta = {}
                final_finish_reason = None
                accumulated_tool_calls = []

                async for chunk in stream:
                    choice = chunk.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    finish_reason = choice.get("finish_reason")

                    if delta.get("content"):
                        token = delta.get("content", "")
                        accumulated_content += token
                        yield {"type": "token", "content": token}

                    # Handle tool calls in delta (for llama-cpp-python format)
                    if delta.get("tool_calls"):
                        accumulated_tool_calls.extend(delta.get("tool_calls", []))

                    if finish_reason:
                        final_delta = delta
                        final_finish_reason = finish_reason
                        # Tool calls might be in the final chunk
                        if choice.get("tool_calls"):
                            accumulated_tool_calls.extend(choice.get("tool_calls", []))
                        break

                message_obj = {
                    "role": "assistant",
                    "content": accumulated_content,
                    "tool_calls": (
                        accumulated_tool_calls
                        if accumulated_tool_calls
                        else (
                            final_delta.get("tool_calls")
                            if final_finish_reason == "tool_calls"
                            else None
                        )
                    ),
                }

            except Exception as e:
                self._inject_error_system_message(
                    history, "streaming_error", f"Error during streaming: {str(e)}"
                )
                continue

            content = message_obj.get("content", "")
            if not isinstance(content, str):
                content = str(content) if content else ""
            cleaned_content, thinking_content = self._extract_thinking(content)

            if thinking_content:
                history.append({"role": "thinking", "content": thinking_content})

            tool_calls = message_obj.get("tool_calls")
            if tool_calls and isinstance(tool_calls, list):
                # Yield tool call information
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue
                    tool_name = (
                        tool_call.get("function", {}).get("name", "")
                        if isinstance(tool_call.get("function"), dict)
                        else ""
                    )
                    tool_args_str = (
                        tool_call.get("function", {}).get("arguments", "{}")
                        if isinstance(tool_call.get("function"), dict)
                        else "{}"
                    )
                    try:
                        tool_args = (
                            json.loads(tool_args_str)
                            if isinstance(tool_args_str, str)
                            else tool_args_str
                        )
                    except json.JSONDecodeError:
                        tool_args = {}

                    yield {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "tool_id": tool_call.get("id") if isinstance(tool_call, dict) else None,
                    }

                consecutive_tool_calls += 1
                tool_call_names = [
                    (
                        tc.get("function", {}).get("name", "")
                        if isinstance(tc.get("function"), dict)
                        else ""
                    )
                    for tc in tool_calls
                    if isinstance(tc, dict)
                ]

                loop_error = self.response_validator.validate_tool_call_loops(
                    consecutive_tool_calls, recent_tool_calls, max_consecutive_tool_calls
                )
                if loop_error:
                    self._inject_error_system_message(
                        history, loop_error["error_type"], loop_error["error_details"]
                    )
                    max_iterations += 1
                    continue

                if len(set(tool_call_names)) == 1 and len(recent_tool_calls) >= 3:
                    if all(name == tool_call_names[0] for name in recent_tool_calls[-3:]):
                        self._inject_error_system_message(
                            history,
                            "repetitive_tool_calls",
                            f"Detected repetitive pattern calling tool '{tool_call_names[0]}' multiple times",
                        )
                        max_iterations += 1
                        continue

                recent_tool_calls.extend(tool_call_names)
                if len(recent_tool_calls) > 10:
                    recent_tool_calls = recent_tool_calls[-10:]

                tool_results = []
                widget_tool_found = False
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue

                    # Check if this is a widget/recording tool (should not be executed)
                    tool_name = (
                        tool_call.get("function", {}).get("name", "")
                        if isinstance(tool_call.get("function"), dict)
                        else ""
                    )
                    if tool_name:
                        tool = tool_registry.get_tool(tool_name)
                        if tool and tool.category in (ToolCategory.WIDGET, ToolCategory.RECORDING):
                            widget_tool_found = True
                            continue

                    tool_result = await self.tool_executor.execute_tool_and_get_result(
                        tool_call, tool_registry, mcp_server, session_id
                    )
                    tool_results.append(tool_result)

                # If we found a widget tool, don't add results to history and let the stream end
                # The generate_response method will catch the tool_call chunk and return it
                if widget_tool_found:
                    return

                history.extend(tool_results)
                continue

            consecutive_tool_calls = 0
            recent_tool_calls.clear()
            response_content = cleaned_content

            if thinking_content:
                _thinking_logger.info(
                    f"Session: {session_id}\n"
                    f"Final Response Thinking:\n{thinking_content}\n"
                    f"Response:\n{response_content}\n"
                    f"{'='*80}"
                )

            if not response_content:
                self._inject_error_system_message(
                    history, "empty_response", "Generated response is empty"
                )
                continue

            history.append({"role": "assistant", "content": response_content})

            yield {"type": "response", "message": response_content}
            return

        self._inject_error_system_message(
            history,
            "max_iterations",
            f"Reached maximum iterations ({max_iterations}). The model may be having trouble processing the request.",
        )

        current_messages = self._prepare_messages(
            history, max_tokens=LLM.MAX_TOKENS_PREPARE_MESSAGES, for_user=False
        )

        tools_param = None
        if tools and self.tool_provider and self.tool_provider.should_pass_tools_as_parameter():
            tools_param = tool_schemas

        try:
            stream = self.backend.stream_chat_completion(
                messages=current_messages,
                tools=tools_param,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )

            accumulated_content = ""
            async for chunk in stream:
                choice = chunk.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                finish_reason = choice.get("finish_reason")

                if delta.get("content"):
                    token = delta.get("content", "")
                    accumulated_content += token
                    yield {"type": "token", "content": token}

                if finish_reason:
                    break

            cleaned_content, _ = self._extract_thinking(accumulated_content)
            if cleaned_content:
                history.append({"role": "assistant", "content": cleaned_content})
                yield {"type": "response", "message": cleaned_content}
            else:
                yield self._yield_error("Maximum iterations reached.")
        except Exception as e:
            yield self._yield_error(f"Error after max iterations: {str(e)}")

    async def handle_audio_ready(
        self,
        audio_file_id: str,
        recording_id: str | None,
        session_id: str | None,
        mcp_server: MCPServer,
    ) -> dict[str, Any]:
        """Handle audio ready and generate response"""
        try:
            analysis = await self.audio_service.run_baseline_analysis(audio_file_id)
        except Exception as e:
            session_id = session_id or "default"
            history = self._get_conversation_history(session_id)
            self._inject_error_system_message(
                history,
                "audio_analysis_error",
                f"Error analyzing audio file {audio_file_id}: {str(e)}. The file may be corrupted or in an unsupported format.",
            )
            return await self.generate_response("", session_id, mcp_server)

        # Format analysis clearly for the LLM
        import json

        analysis_str = (
            json.dumps(analysis, indent=2) if isinstance(analysis, dict) else str(analysis)
        )

        message = AudioAnalysisContextFormatter.format_analysis_results(audio_file_id, analysis_str)

        return await self.generate_response(message, session_id or "default", mcp_server)

    def _get_system_prompt(self, prompt_file_path: Path | None = None) -> str:
        """Get system prompt using modular builder

        Args:
            prompt_file_path: Optional path to SYSTEM_PROMPT.md. If None, uses default location.
                Mainly for testing.
        """
        if prompt_file_path is None:
            from pathlib import Path

            prompt_file_path = Path(__file__).parent.parent.parent.parent / "SYSTEM_PROMPT.md"

        builder = SystemPromptBuilder()
        builder.add_section(CorePromptSection(prompt_file_path))

        result: str = builder.build()
        return result

    def _find_recent_audio_analysis(self, history: list[dict[str, Any]]) -> str | None:
        """Find the most recent audio analysis in conversation history"""
        result: str | None = self.audio_context_enricher.find_recent_audio_analysis(history)
        return result

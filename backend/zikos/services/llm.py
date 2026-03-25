"""LLM service"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from zikos.config import settings
from zikos.mcp.server import MCPServer
from zikos.mcp.tool import ToolCategory
from zikos.services.audio import AudioService
from zikos.services.llm_init import initialize_llm_backend
from zikos.services.llm_orchestration.audio_context_enricher import AudioContextEnricher
from zikos.services.llm_orchestration.conversation_manager import ConversationManager
from zikos.services.llm_orchestration.message_preparer import MessagePreparer
from zikos.services.llm_orchestration.orchestrator import LLMOrchestrator
from zikos.services.llm_orchestration.response_validator import ResponseValidator
from zikos.services.llm_orchestration.stream_processor import StreamProcessor, StreamResult
from zikos.services.llm_orchestration.thinking_extractor import ThinkingExtractor
from zikos.services.llm_orchestration.tool_call_parser import get_tool_call_parser
from zikos.services.llm_orchestration.tool_executor import ToolExecutor
from zikos.services.llm_orchestration.tool_injector import ToolInjector
from zikos.services.model_strategy import get_model_strategy
from zikos.services.prompt import SystemPromptBuilder
from zikos.services.prompt.sections import (
    AudioAnalysisContextFormatter,
    CorePromptSection,
    ToolInstructionsSection,
)

_conversation_logger = logging.getLogger("zikos.conversation")
_conversation_logger.setLevel(logging.DEBUG)
_conversation_logger.propagate = False

if settings.debug_tool_calls:
    _logs_dir = Path("logs")
    _logs_dir.mkdir(exist_ok=True)
    _conversation_handler = logging.FileHandler(_logs_dir / "conversation.log", encoding="utf-8")
    _conversation_handler.setLevel(logging.DEBUG)
    _conversation_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    _conversation_logger.addHandler(_conversation_handler)
else:
    _conversation_logger.addHandler(logging.NullHandler())

_logger = logging.getLogger("zikos.services.llm")


class LLMService:
    """Service for LLM interactions"""

    def __init__(self):
        self.audio_service = AudioService()
        self.thinking_extractor = ThinkingExtractor()
        self.conversation_manager = ConversationManager(self._get_system_prompt)
        self.message_preparer = MessagePreparer()
        self.audio_context_enricher = AudioContextEnricher()
        self.tool_injector = ToolInjector()
        self.tool_call_parser = get_tool_call_parser()
        self.tool_executor = ToolExecutor()
        self.response_validator = ResponseValidator()
        self.stream_processor = StreamProcessor()
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

        # Initialize LLM backend
        init = initialize_llm_backend()
        self.backend = init.backend
        self.initialization_error = init.error
        self.context_window = init.context_window
        self.strategy = init.strategy or get_model_strategy()
        self.tool_call_parser = init.tool_call_parser or self.tool_call_parser

        if init.backend:
            self.orchestrator.strategy = self.strategy
            self.orchestrator.tool_call_parser = self.tool_call_parser

    def __del__(self):
        if self.backend is not None:
            try:
                self.backend.close()
            except Exception:
                _logger.debug("Error closing LLM backend during cleanup", exc_info=True)

    def _get_conversation_history(self, session_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self.conversation_manager.get_history(session_id)
        return result

    def get_thinking_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all thinking messages for a session (for debugging)"""
        result: list[dict[str, Any]] = self.conversation_manager.get_thinking_for_session(
            session_id
        )
        return result

    def _extract_thinking(self, content: str | None) -> tuple[str, str]:
        result: tuple[str, str] = self.thinking_extractor.extract(content)
        return result

    def _prepare_messages(
        self,
        history: list[dict[str, Any]],
        max_tokens: int | None = None,
        for_user: bool = False,
        context_window: int | None = None,
    ) -> list[dict[str, Any]]:
        """Prepare messages for LLM, with truncation and system prompt."""
        if context_window is None:
            context_window = self.context_window
        result: list[dict[str, Any]] = self.message_preparer.prepare(
            history, max_tokens, for_user, context_window
        )
        return result

    async def generate_response(
        self,
        message: str,
        session_id: str,
        mcp_server: MCPServer,
    ) -> dict[str, Any]:
        """Generate LLM response by accumulating the stream."""
        final_response = None
        tool_call_response = None
        tool_registry = None

        async for chunk in self.generate_response_stream(message, session_id, mcp_server):
            chunk_type = chunk.get("type")

            if chunk_type == "tool_call":
                if tool_registry is None:
                    tool_registry = mcp_server.get_tool_registry()
                tool_name = chunk.get("tool_name")
                if tool_name:
                    tool = tool_registry.get_tool(tool_name)
                    if tool and tool.category in (ToolCategory.WIDGET, ToolCategory.RECORDING):
                        tool_call_response = chunk

            if chunk_type in ("response", "error"):
                final_response = chunk

        if tool_call_response:
            return dict(tool_call_response)
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
        return {"type": "error", "message": message}

    def _inject_error_system_message(
        self, history: list[dict[str, Any]], error_type: str, error_details: str
    ) -> None:
        history.append({"role": "system", "content": f"ERROR: {error_type}: {error_details}"})

    # --- Streaming generation ---

    def _get_max_thinking(self, nothink_retry: bool) -> int:
        if nothink_retry:
            return 0
        return int(
            self.strategy.thinking.max_tokens if self.strategy else settings.llm_max_thinking_tokens
        )

    def _create_stream(self, messages, tools, tool_schemas):
        tools_param = None
        if tools and self.strategy and self.strategy.tool_provider.should_pass_tools_as_parameter():
            tools_param = tool_schemas

        sampling = self.strategy.sampling if self.strategy else None
        return self.backend.stream_chat_completion(
            messages=messages,
            tools=tools_param,
            temperature=sampling.temperature if sampling else settings.llm_temperature,
            top_p=sampling.top_p if sampling else settings.llm_top_p,
            top_k=sampling.top_k if sampling else settings.llm_top_k,
        )

    def _handle_thinking_exceeded(
        self,
        history: list[dict[str, Any]],
        stream_result: StreamResult,
        session_id: str,
    ) -> None:
        """Handle thinking budget exceeded: add truncated thinking and swap to /nothink."""
        truncated = stream_result.accumulated_content.rstrip()
        if not truncated.endswith("</think>"):
            truncated += "\n</think>\n"
        history.append({"role": "assistant", "content": truncated})
        _conversation_logger.info(
            f"Session: {session_id}\n"
            f"Truncated thinking:\n"
            f"{stream_result.accumulated_content}\n"
            f"{'=' * 80}"
        )
        for msg in history:
            if msg["role"] == "system" and msg["content"].endswith("/think"):
                msg["content"] = msg["content"][:-6] + "/nothink"
                break

    def _finalize_response(
        self,
        history: list[dict[str, Any]],
        session_id: str,
        state,
        cleaned_content: str,
        thinking_content: str,
        nothink_retry: bool,
    ) -> list[dict[str, Any]] | None:
        """Finalize a successful response. Returns chunks to yield, or None if empty."""
        state.consecutive_tool_calls = 0
        state.recent_tool_calls.clear()

        if not cleaned_content:
            return None

        thinking_part = f"Thinking:\n{thinking_content}\n" if thinking_content else ""
        _conversation_logger.info(
            f"Session: {session_id}\n"
            f"Assistant Response:\n{thinking_part}"
            f"{cleaned_content}\n"
            f"{'=' * 80}"
        )

        if thinking_content:
            full_content = f"<think>\n{thinking_content}\n</think>\n\n{cleaned_content}"
        else:
            full_content = cleaned_content
        history.append({"role": "assistant", "content": full_content})

        # Restore /think if it was swapped to /nothink
        if nothink_retry:
            for msg in history:
                if msg["role"] == "system" and msg["content"].endswith("/nothink"):
                    msg["content"] = msg["content"][:-8] + "/think"
                    break

        chunks: list[dict[str, Any]] = []
        if thinking_content:
            chunks.append({"type": "thinking", "content": thinking_content})
        chunks.append({"type": "response", "message": cleaned_content})
        return chunks

    async def generate_response_stream(
        self,
        message: str,
        session_id: str,
        mcp_server: MCPServer,
    ):
        """Generate LLM response with streaming, handling tool calls."""
        if not self.backend or not self.backend.is_initialized():
            if self.initialization_error:
                error_msg = f"LLM not available: {self.initialization_error}"
            else:
                error_msg = "LLM not available. Please ensure the model file exists at the path specified by LLM_MODEL_PATH."
            yield self._yield_error(error_msg)
            return

        history, original_message, tool_registry, tools, tool_schemas, state = (
            self.orchestrator.prepare_conversation(message, session_id, mcp_server)
        )
        nothink_retry = False

        while state.iteration < state.max_iterations:
            state.iteration += 1

            current_messages, token_error = self.orchestrator.prepare_iteration_messages(
                history, self.context_window
            )
            if token_error:
                self._inject_error_system_message(
                    history, token_error["error_type"], token_error["error_details"]
                )
                continue

            # Stream LLM response
            try:
                stream = self._create_stream(current_messages, tools, tool_schemas)
                stream_result = StreamResult()
                max_thinking = self._get_max_thinking(nothink_retry)

                async for token_chunk in self.stream_processor.process(
                    stream,
                    stream_result,
                    nothink_retry=nothink_retry,
                    max_thinking=max_thinking,
                    session_id=session_id,
                ):
                    yield token_chunk

                if stream_result.thinking_budget_exceeded:
                    self._handle_thinking_exceeded(history, stream_result, session_id)
                    nothink_retry = True
                    continue

                message_obj = {
                    "role": "assistant",
                    "content": stream_result.accumulated_content,
                    "tool_calls": stream_result.tool_calls,
                }

            except Exception as e:
                self._inject_error_system_message(
                    history, "streaming_error", f"Error during streaming: {str(e)}"
                )
                continue

            # Post-streaming: extract thinking, parse tool calls
            content = message_obj.get("content", "")
            if not isinstance(content, str):
                content = str(content) if content else ""
            if nothink_retry:
                cleaned_content = re.sub(r"</?think(?:ing)?>", "", content).strip()
                thinking_content = ""
            else:
                cleaned_content, thinking_content = self._extract_thinking(content)

            tool_calls = message_obj.get("tool_calls")
            if not tool_calls or not isinstance(tool_calls, list):
                tool_calls = self.tool_call_parser.parse_tool_calls(message_obj, content)

            # Handle tool calls
            if tool_calls and isinstance(tool_calls, list):
                cleaned_content = self.tool_call_parser.strip_tool_call_tags(cleaned_content)

                should_continue, result, tool_call_infos = (
                    await self.orchestrator.process_tool_calls(
                        tool_calls,
                        state,
                        history,
                        tool_registry,
                        mcp_server,
                        session_id,
                        cleaned_content,
                    )
                )

                for info in tool_call_infos:
                    yield info

                if not should_continue:
                    if result and "error_type" in result:
                        self._inject_error_system_message(
                            history, result["error_type"], result["error_details"]
                        )
                        state.max_iterations += 1
                    elif result:
                        yield result
                        return
                continue

            # Check for malformed tool calls
            parse_error = self.tool_call_parser.detect_failed_tool_calls(content)
            if parse_error:
                history.append({"role": "assistant", "content": cleaned_content})
                self._inject_error_system_message(history, "malformed_tool_call", parse_error)
                continue

            # Finalize response
            chunks = self._finalize_response(
                history, session_id, state, cleaned_content, thinking_content, nothink_retry
            )
            if chunks is None:
                self._inject_error_system_message(
                    history, "empty_response", "Generated response is empty"
                )
                continue
            for chunk in chunks:
                yield chunk
            return

        # Max iterations fallback
        async for chunk in self._max_iterations_fallback(history, tools, tool_schemas, state):
            yield chunk

    async def _max_iterations_fallback(self, history, tools, tool_schemas, state):
        """Last-resort generation after max iterations exceeded."""
        self._inject_error_system_message(
            history,
            "max_iterations",
            f"Reached maximum iterations ({state.max_iterations}). The model may be having trouble processing the request.",
        )

        current_messages, _ = self.orchestrator.prepare_iteration_messages(
            history, self.context_window
        )

        try:
            stream = self._create_stream(current_messages, tools, tool_schemas)
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

    # --- Audio handling ---

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

        analysis_str = (
            json.dumps(analysis, indent=2) if isinstance(analysis, dict) else str(analysis)
        )
        message = AudioAnalysisContextFormatter.format_analysis_results(audio_file_id, analysis_str)
        return await self.generate_response(message, session_id or "default", mcp_server)

    # --- System prompt ---

    def _get_system_prompt(self, prompt_file_path: Path | None = None) -> str:
        """Get system prompt using modular builder."""
        if self.backend and prompt_file_path is None:
            cached_prompt: str | None = self.backend.get_cached_system_prompt()
            if cached_prompt:
                _logger.debug(
                    f"Using cached system prompt from KV cache sidecar ({len(cached_prompt)} chars)"
                )
                return cached_prompt

        if prompt_file_path is None:
            prompt_file_path = Path(__file__).parent.parent.parent.parent / "SYSTEM_PROMPT.md"

        builder = SystemPromptBuilder()
        builder.add_section(CorePromptSection(prompt_file_path))

        result: str = builder.build()

        if self.strategy and self.strategy.thinking.prompt_suffix:
            result = f"{result}\n\n{self.strategy.thinking.prompt_suffix}"

        return result

    def _find_recent_audio_analysis(self, history: list[dict[str, Any]]) -> str | None:
        result: str | None = self.audio_context_enricher.find_recent_audio_analysis(history)
        return result

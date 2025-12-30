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
    MusicFlamingoSection,
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
            print(f"Warning: Model file not found at {model_path}")
            print("The application will start but LLM features will be unavailable.")
            print(
                f"To download a model, run: python scripts/download_model.py qwen2.5-7b-instruct-q4 -o {model_path.parent}"
            )
            print(
                "See MODEL_RECOMMENDATIONS.md for recommended models with better function calling support."
            )
            return

        try:
            backend_type = settings.llm_backend if settings.llm_backend != "auto" else None
            self.backend = create_backend(model_path_str, backend_type)

            if self.backend is None:
                print("Warning: Could not create LLM backend")
                return

            n_gpu_layers = settings.llm_n_gpu_layers
            if n_gpu_layers == -1:
                n_gpu_layers = get_optimal_gpu_layers(model_path_str, backend_type or "auto")

            print(f"Initializing LLM backend: {type(self.backend).__name__}")
            print(f"Model path: {model_path_str}")
            print(f"Context window: {settings.llm_n_ctx} tokens")
            print(f"GPU layers: {n_gpu_layers}")

            self.backend.initialize(
                model_path=model_path_str,
                n_ctx=settings.llm_n_ctx,
                n_gpu_layers=n_gpu_layers,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )

            self.tool_provider = get_tool_provider(model_path_str)
            print(f"LLM initialized successfully with context window: {settings.llm_n_ctx} tokens")
            print(f"Using tool provider: {type(self.tool_provider).__name__}")
        except Exception as e:
            print(f"Error initializing LLM: {e}")
            import traceback

            traceback.print_exc()
            print("The application will start but LLM features will be unavailable.")
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
        """Generate LLM response, handling tool calls"""
        if not self.backend or not self.backend.is_initialized():
            return {
                "type": "response",
                "message": "LLM not available. Please ensure the model file exists at the path specified by LLM_MODEL_PATH.",
            }

        history, original_message, tool_registry, tools, tool_schemas, iteration_state = (
            self.orchestrator.prepare_conversation(message, session_id, mcp_server)
        )

        _thinking_logger.info(
            f"Session: {session_id}\n" f"User Prompt:\n{original_message}\n" f"{'='*80}"
        )

        if settings.debug_tool_calls:
            print(f"[DEBUG] Total tools available: {len(tools)}")
            if tools:
                print(f"[DEBUG] Sample tool: {tools[0].name} ({tools[0].category.value})")

        self.tool_provider = self.orchestrator.tool_provider

        max_iterations = LLM.MAX_ITERATIONS

        while iteration_state.iteration < max_iterations:
            iteration_state.iteration += 1
            current_messages, token_error = self.orchestrator.prepare_iteration_messages(history)

            if token_error:
                if settings.debug_tool_calls:
                    print("[TOKEN WARNING] Conversation exceeds token limit")
                return token_error

            if settings.debug_tool_calls:
                print(f"[DEBUG] Sending {len(tools)} tools to LLM")
                print(
                    f"[DEBUG] Tools list: {[t.get('function', {}).get('name', 'unknown') for t in tool_schemas[:5]]}..."
                )
                print(f"[DEBUG] Messages count: {len(current_messages)}")
                if current_messages:
                    print(
                        f"[DEBUG] First message role: {current_messages[0].get('role', 'unknown')}"
                    )
                    print(
                        f"[DEBUG] Last message role: {current_messages[-1].get('role', 'unknown')}"
                    )

            # Pass tools as parameter if provider supports it
            tools_param = None
            if tools and self.tool_provider and self.tool_provider.should_pass_tools_as_parameter():
                tools_param = tool_schemas

            response = self.backend.create_chat_completion(
                messages=current_messages,
                tools=tools_param,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )

            message_obj = response["choices"][0]["message"]

            if settings.debug_tool_calls:
                print("[LLM RESPONSE] Full response structure:")
                print(f"  Response keys: {list(response.keys())}")
                print(f"  Message object keys: {list(message_obj.keys())}")
                print(f"  Content: {str(message_obj.get('content', 'None'))[:200]}")
                print(f"  Tool calls: {message_obj.get('tool_calls', 'None')}")
                print(f"  Role: {message_obj.get('role', 'None')}")
                if "finish_reason" in response["choices"][0]:
                    print(f"  Finish reason: {response['choices'][0].get('finish_reason', 'None')}")
                if message_obj.get("content"):
                    content_preview = str(message_obj.get("content", ""))[:500]
                    if "<tool_call>" in content_preview:
                        print("  [FOUND] XML tool_call tag in content!")
                        print(f"  Content preview: {content_preview}")

            raw_content, cleaned_content, thinking_content = (
                self.orchestrator.process_llm_response(message_obj, history, session_id)
            )

            if not cleaned_content and raw_content:
                content_error = self.response_validator.validate_response_content(raw_content)
                if content_error:
                    return content_error

            if thinking_content:
                _thinking_logger.info(
                    f"Session: {session_id}\n"
                    f"Thinking (before tool calls):\n{thinking_content}\n"
                    f"{'='*80}"
                )
            else:
                if settings.debug_tool_calls:
                    content_to_log = raw_content if raw_content else "(empty content)"
                    _thinking_logger.debug(
                        f"Session: {session_id}\n"
                        f"No thinking found in response.\n"
                        f"Full content:\n{content_to_log}\n"
                        f"{'='*80}"
                    )
                else:
                    content_preview = raw_content[:300] if raw_content else "(empty content)"
                    _thinking_logger.debug(
                        f"Session: {session_id}\n"
                        f"No thinking found in response.\n"
                        f"Content preview: {content_preview}...\n"
                        f"{'='*80}"
                    )

            tool_calls = self.tool_call_parser.parse_tool_calls(message_obj, raw_content)

            if settings.debug_tool_calls:
                if tool_calls:
                    print(f"[TOOL CALLS FOUND] {len(tool_calls)} tool call(s)")
                elif raw_content and (
                    "<tool_call>" in raw_content
                    or ("name" in raw_content and "arguments" in raw_content)
                ):
                    print(
                        "[WARNING] Content contains tool-like content but no structured tool_calls field"
                    )
                    print(f"  Content snippet: {raw_content[:500]}")

            if tool_calls:
                should_continue, widget_response = await self.orchestrator.process_tool_calls(
                    tool_calls,
                    iteration_state,
                    history,
                    tool_registry,
                    mcp_server,
                    session_id,
                    cleaned_content,
                )

                if widget_response:
                    if isinstance(widget_response, dict) and widget_response.get("type") == "response":
                        _thinking_logger.warning(
                            f"Session: {session_id}\n"
                            f"Tool call loop detected: consecutive={iteration_state.consecutive_tool_calls}, recent={iteration_state.recent_tool_calls[-4:]}\n"
                            f"Response: {widget_response['message']}\n"
                            f"{'='*80}"
                        )
                    return widget_response

                if should_continue:
                    continue
                else:
                    return widget_response if widget_response else {
                        "type": "response",
                        "message": "An error occurred processing tool calls.",
                    }

            response_content = self.orchestrator.finalize_response(
                cleaned_content, thinking_content, iteration_state
            )

            # If we expected a tool call but didn't get one, log a warning
            # (This helps diagnose function calling issues)
            if iteration_state.iteration == 1 and not response_content:
                print("WARNING: Model returned empty response on first iteration")

            # Log final response thinking and full response
            if thinking_content:
                _thinking_logger.info(
                    f"Session: {session_id}\n"
                    f"Final Response Thinking:\n{thinking_content}\n"
                    f"Response:\n{response_content}\n"
                    f"{'='*80}"
                )
            else:
                _thinking_logger.info(
                    f"Session: {session_id}\n"
                    f"Response (no thinking):\n{response_content}\n"
                    f"{'='*80}"
                )

            # Show thinking in debug mode
            if settings.debug_tool_calls and thinking_content:
                print("[THINKING] Final response thinking:")
                print(f"  {thinking_content}")

            return {
                "type": "response",
                "message": response_content
                or "I'm not sure how to help with that. Could you rephrase your request?",
            }

        error_message = "Maximum iterations reached. The model may be having trouble processing your request. Please try rephrasing or breaking it into smaller parts."
        _thinking_logger.warning(
            f"Session: {session_id}\n"
            f"Maximum iterations reached\n"
            f"Response: {error_message}\n"
            f"{'='*80}"
        )
        return {
            "type": "response",
            "message": error_message,
        }

    async def generate_response_stream(
        self,
        message: str,
        session_id: str,
        mcp_server: MCPServer,
    ):
        """Generate LLM response with streaming, handling tool calls"""
        from collections.abc import AsyncGenerator

        if not self.backend or not self.backend.is_initialized():
            yield {
                "type": "error",
                "message": "LLM not available. Please ensure the model file exists at the path specified by LLM_MODEL_PATH.",
            }
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
                yield {
                    "type": "error",
                    "message": token_error["message"],
                }
                return

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
                    "tool_calls": accumulated_tool_calls
                    if accumulated_tool_calls
                    else (
                        final_delta.get("tool_calls")
                        if final_finish_reason == "tool_calls"
                        else None
                    ),
                }

            except Exception as e:
                yield {
                    "type": "error",
                    "message": f"Error during streaming: {str(e)}",
                }
                return

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
                if consecutive_tool_calls > max_consecutive_tool_calls:
                    yield {
                        "type": "response",
                        "message": "I seem to be stuck in a loop making tool calls. Let me try a different approach.",
                    }
                    return

                tool_call_names = [
                    tc.get("function", {}).get("name", "")
                    if isinstance(tc.get("function"), dict)
                    else ""
                    for tc in tool_calls
                    if isinstance(tc, dict)
                ]
                if len(set(tool_call_names)) == 1 and len(recent_tool_calls) >= 3:
                    if all(name == tool_call_names[0] for name in recent_tool_calls[-3:]):
                        yield {
                            "type": "response",
                            "message": f"I've called {tool_call_names[0]} multiple times. There may be an issue. Let me try a different approach.",
                        }
                        return

                recent_tool_calls.extend(tool_call_names)
                if len(recent_tool_calls) > 10:
                    recent_tool_calls = recent_tool_calls[-10:]

                tool_results = []
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue

                    tool_result = await self.tool_executor.execute_tool_and_get_result(
                        tool_call, tool_registry, mcp_server, session_id
                    )
                    tool_results.append(tool_result)

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

            history.append(
                {
                    "role": "assistant",
                    "content": response_content
                    or "I'm not sure how to help with that. Could you rephrase your request?",
                }
            )

            yield {
                "type": "response",
                "message": response_content
                or "I'm not sure how to help with that. Could you rephrase your request?",
            }
            return

        yield {
            "type": "error",
            "message": "Maximum iterations reached. The model may be having trouble processing your request. Please try rephrasing or breaking it into smaller parts.",
        }

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
            return {
                "type": "response",
                "message": f"Error analyzing audio: {str(e)}. The file may be corrupted or in an unsupported format.",
            }

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
        builder.add_section(MusicFlamingoSection())

        result: str = builder.build()
        return result

    def _find_recent_audio_analysis(self, history: list[dict[str, Any]]) -> str | None:
        """Find the most recent audio analysis in conversation history"""
        result: str | None = self.audio_context_enricher.find_recent_audio_analysis(history)
        return result

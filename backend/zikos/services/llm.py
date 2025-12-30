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
from zikos.services.llm_orchestration.thinking_extractor import ThinkingExtractor
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

        history = self._get_conversation_history(session_id)

        original_message = message
        message, _ = self.audio_context_enricher.enrich_message(message, history)

        history.append({"role": "user", "content": message})

        # Log user prompt
        _thinking_logger.info(
            f"Session: {session_id}\n" f"User Prompt:\n{original_message}\n" f"{'='*80}"
        )

        messages = self._prepare_messages(history)

        print(
            f"DEBUG: Conversation history has {len(history)} messages, prepared {len(messages)} messages"
        )
        if history and history[0].get("role") == "system":
            print(
                f"DEBUG: System message present, length: {len(history[0].get('content', ''))} chars"
            )

        tool_registry = mcp_server.get_tool_registry()
        tools = tool_registry.get_all_tools()
        tool_schemas = tool_registry.get_all_schemas()

        if settings.debug_tool_calls:
            print(f"[DEBUG] Total tools available: {len(tools)}")
            if tools:
                print(f"[DEBUG] Sample tool: {tools[0].name} ({tools[0].category.value})")

        # Use tool provider to format and inject tools
        if not self.tool_provider:
            self.tool_provider = get_tool_provider()

        if tools and self.tool_provider.should_inject_tools_as_text():
            # Check if tools are already in the system prompt (avoid duplicates)
            system_has_tools = False
            if history and history[0].get("role") == "system":
                system_content = history[0].get("content", "")
                if "<tools>" in system_content or "# Available Tools" in system_content:
                    system_has_tools = True

            if not system_has_tools:
                tools_section = ToolInstructionsSection(self.tool_provider, tools, tool_schemas)
                tools_text = tools_section.render()

                # Inject tools into the system prompt in the conversation history
                if history and history[0].get("role") == "system":
                    original_system = history[0].get("content", "")
                    history[0]["content"] = f"{original_system}\n\n{tools_text}"
                else:
                    # If no system message, add one with tools
                    system_prompt = self._get_system_prompt()
                    history.insert(
                        0, {"role": "system", "content": f"{system_prompt}\n\n{tools_text}"}
                    )

                if settings.debug_tool_calls:
                    print(
                        f"[DEBUG] Injected {len(tools)} tools into system prompt using {type(self.tool_provider).__name__}"
                    )

        max_iterations = LLM.MAX_ITERATIONS
        iteration = 0
        consecutive_tool_calls = 0
        max_consecutive_tool_calls = 5
        recent_tool_calls: list[str] = []

        while iteration < max_iterations:
            iteration += 1
            # Prepare messages for LLM (include thinking messages for context)
            current_messages = self._prepare_messages(
                history, max_tokens=LLM.MAX_TOKENS_PREPARE_MESSAGES, for_user=False
            )

            # Safety check: prevent context overflow
            try:
                import tiktoken

                enc = tiktoken.get_encoding("cl100k_base")
                total_tokens = sum(
                    len(enc.encode(str(msg.get("content", "")))) for msg in current_messages
                )
                if total_tokens > LLM.MAX_TOKENS_SAFETY_CHECK:
                    if settings.debug_tool_calls:
                        print(
                            f"[TOKEN WARNING] Conversation has {total_tokens} tokens, limit is {LLM.MAX_TOKENS_SAFETY_CHECK}"
                        )
                    return {
                        "type": "response",
                        "message": "The conversation is too long. Please start a new conversation or summarize what you need.",
                    }
            except Exception:
                pass  # If tiktoken fails, continue anyway

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

            # Safety check: detect gibberish/looping output
            # Note: we'll extract thinking later, so check raw content here
            raw_content_for_safety = message_obj.get("content", "")
            if raw_content_for_safety:
                words = raw_content_for_safety.split()
                # Check for very long responses (likely gibberish)
                if len(words) > LLM.MAX_WORDS_RESPONSE:
                    print(f"WARNING: Model generated unusually long response ({len(words)} words)")
                    return {
                        "type": "response",
                        "message": "The model generated an unusually long response. Please try rephrasing your question.",
                    }
                # Check for excessive repetition (gibberish pattern)
                if len(words) > 50:
                    unique_ratio = len(set(words)) / len(words) if words else 0
                    if unique_ratio < LLM.MIN_UNIQUE_WORD_RATIO:
                        print(
                            f"WARNING: Model generated repetitive output (unique ratio: {unique_ratio:.2f})"
                        )
                        return {
                            "type": "response",
                            "message": "The model seems to be repeating itself. Please try rephrasing your question.",
                        }
                    # Check for excessive single-character or number patterns (gibberish)
                    if (
                        len([w for w in words if len(w) == 1 or w.isdigit()])
                        > len(words) * LLM.MAX_SINGLE_CHAR_RATIO
                    ):
                        print(
                            "WARNING: Model generated suspicious pattern (too many single chars/numbers)"
                        )
                        return {
                            "type": "response",
                            "message": "The model generated an invalid response. Please try rephrasing your question.",
                        }

            # Extract thinking from content before processing
            raw_content = message_obj.get("content", "")
            cleaned_content, thinking_content = self._extract_thinking(raw_content)

            # Log whether thinking was found or not (for debugging)
            if thinking_content:
                thinking_msg = {"role": "thinking", "content": thinking_content}
                history.append(thinking_msg)

                # Log thinking to file
                _thinking_logger.info(
                    f"Session: {session_id}\n"
                    f"Thinking (before tool calls):\n{thinking_content}\n"
                    f"{'='*80}"
                )
            else:
                # Log when no thinking is found (helps debug why model isn't using it)
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

                if settings.debug_tool_calls:
                    print("[THINKING] Extracted thinking:")
                    print(f"  {thinking_content[:500]}...")

            # Update message_obj with cleaned content
            message_obj["content"] = cleaned_content
            history.append(message_obj)

            # Check for tool calls in response
            tool_calls = message_obj.get("tool_calls", [])

            # Qwen2.5 uses XML-based tool calling format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
            # Parse this if no structured tool_calls are present
            # Use raw_content (before thinking extraction) for tool call parsing
            if not tool_calls and raw_content and "<tool_call>" in raw_content:
                tool_calls = self._parse_qwen_tool_calls(raw_content)

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
                consecutive_tool_calls += 1

                # Track tool names to detect repetitive loops
                current_tool_names = []
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict) and "function" in tool_call:
                        tool_name = tool_call["function"]["name"]
                        current_tool_names.append(tool_name)

                recent_tool_calls.extend(current_tool_names)
                if len(recent_tool_calls) > 10:
                    recent_tool_calls = recent_tool_calls[-10:]

                # Check for repetitive tool calling pattern
                if len(recent_tool_calls) >= 4:
                    if len(set(recent_tool_calls[-4:])) == 1:
                        print(
                            f"WARNING: Detected repetitive tool calling pattern ({recent_tool_calls[-4:]}). "
                            "Breaking loop to prevent infinite recursion."
                        )
                        error_message = "The model appears to be stuck in a loop calling the same tool. Please try rephrasing your request."
                        _thinking_logger.warning(
                            f"Session: {session_id}\n"
                            f"Repetitive tool calling detected: {recent_tool_calls[-4:]}\n"
                            f"Response: {error_message}\n"
                            f"{'='*80}"
                        )
                        return {
                            "type": "response",
                            "message": error_message,
                        }

                if consecutive_tool_calls > max_consecutive_tool_calls:
                    print(
                        f"WARNING: Too many consecutive tool calls ({consecutive_tool_calls}). "
                        "Breaking loop to prevent infinite recursion."
                    )
                    error_message = "The model is making too many tool calls. Please try rephrasing your request or breaking it into smaller parts."
                    _thinking_logger.warning(
                        f"Session: {session_id}\n"
                        f"Too many consecutive tool calls: {consecutive_tool_calls}\n"
                        f"Response: {error_message}\n"
                        f"{'='*80}"
                    )
                    return {
                        "type": "response",
                        "message": error_message,
                    }

                tool_results = []

                for tool_call in tool_calls:
                    # Handle native tool calls from LLM
                    if isinstance(tool_call, dict) and "function" in tool_call:
                        tool_name = tool_call["function"]["name"]
                        tool_args_str = tool_call["function"].get("arguments", "{}")
                    else:
                        # Unexpected format - log and skip
                        print(f"WARNING: Unexpected tool_call format: {tool_call}")
                        continue

                    try:
                        tool_args = (
                            json.loads(tool_args_str)
                            if isinstance(tool_args_str, str)
                            else tool_args_str
                        )
                    except json.JSONDecodeError as e:
                        print(f"WARNING: Failed to parse tool arguments: {e}")
                        tool_args = {}

                    if settings.debug_tool_calls:
                        print(f"[TOOL CALL] {tool_name}")
                        print(f"  Tool ID: {tool_call.get('id', 'N/A')}")
                        print(f"  Arguments: {json.dumps(tool_args, indent=2)}")

                    tool = tool_registry.get_tool(tool_name)
                    is_widget = tool and tool.category in (
                        ToolCategory.WIDGET,
                        ToolCategory.RECORDING,
                    )

                    if is_widget:
                        if settings.debug_tool_calls:
                            print(
                                f"[WIDGET TOOL] Returning {tool_name} to frontend (pausing conversation)"
                            )
                        # Use cleaned_content (already has thinking stripped)
                        widget_content = (
                            self._strip_tool_call_tags(cleaned_content) if cleaned_content else ""
                        )
                        _thinking_logger.info(
                            f"Session: {session_id}\n"
                            f"Tool Call (Widget): {tool_name}\n"
                            f"Arguments: {json.dumps(tool_args, indent=2, default=str)}\n"
                            f"Message: {widget_content}\n"
                            f"{'='*80}"
                        )
                        return {
                            "type": "tool_call",
                            "message": widget_content,
                            "tool_name": tool_name,
                            "tool_id": tool_call.get("id"),
                            "arguments": tool_args,
                        }

                    # Log tool call
                    _thinking_logger.info(
                        f"Session: {session_id}\n"
                        f"Tool Call: {tool_name}\n"
                        f"Arguments: {json.dumps(tool_args, indent=2, default=str)}\n"
                        f"{'='*80}"
                    )

                    try:
                        result = await mcp_server.call_tool(tool_name, **tool_args)
                        if settings.debug_tool_calls:
                            print(f"[TOOL RESULT] {tool_name}")
                            print(f"  Result: {json.dumps(result, indent=2, default=str)}")

                        # Log tool result
                        _thinking_logger.info(
                            f"Session: {session_id}\n"
                            f"Tool Result: {tool_name}\n"
                            f"Result: {json.dumps(result, indent=2, default=str)}\n"
                            f"{'='*80}"
                        )
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": str(result),
                                "tool_call_id": tool_call.get("id"),
                            }
                        )
                    except FileNotFoundError as e:
                        error_msg = str(e)
                        if (
                            tool_name in ("midi_to_audio", "midi_to_notation")
                            and "not found" in error_msg.lower()
                        ):
                            enhanced_error = (
                                f"Error: {error_msg}\n\n"
                                "To fix this: First generate MIDI text in your response, then call 'validate_midi' "
                                "with that MIDI text. The validate_midi tool will return a midi_file_id that you "
                                "can use with midi_to_audio or midi_to_notation."
                            )
                        else:
                            enhanced_error = f"Error: {error_msg}"

                        if settings.debug_tool_calls:
                            print(f"[TOOL ERROR] {tool_name}")
                            print(f"  Error: {error_msg}")
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": enhanced_error,
                                "tool_call_id": tool_call.get("id"),
                            }
                        )
                    except Exception as e:
                        if settings.debug_tool_calls:
                            print(f"[TOOL ERROR] {tool_name}")
                            print(f"  Error: {str(e)}")
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": f"Error: {str(e)}",
                                "tool_call_id": tool_call.get("id"),
                            }
                        )

                history.extend(tool_results)

                # After tool results, allow model to reason about the results
                # This will be handled in the next iteration when the model generates a response
                continue

            # No tool calls - reset counters and return the response
            consecutive_tool_calls = 0
            recent_tool_calls.clear()
            response_content = cleaned_content

            # If we expected a tool call but didn't get one, log a warning
            # (This helps diagnose function calling issues)
            if iteration == 1 and not response_content:
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

        if tools and self.tool_provider.should_inject_tools_as_text():
            system_has_tools = False
            if history and history[0].get("role") == "system":
                system_content = history[0].get("content", "")
                if "<tools>" in system_content or "# Available Tools" in system_content:
                    system_has_tools = True

            if not system_has_tools:
                tools_section = ToolInstructionsSection(self.tool_provider, tools, tool_schemas)
                tools_text = tools_section.render()

                if history and history[0].get("role") == "system":
                    original_system = history[0].get("content", "")
                    history[0]["content"] = f"{original_system}\n\n{tools_text}"
                else:
                    system_prompt = self._get_system_prompt()
                    history.insert(
                        0, {"role": "system", "content": f"{system_prompt}\n\n{tools_text}"}
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

            try:
                import tiktoken

                enc = tiktoken.get_encoding("cl100k_base")
                total_tokens = sum(
                    len(enc.encode(str(msg.get("content", "")))) for msg in current_messages
                )
                if total_tokens > LLM.MAX_TOKENS_SAFETY_CHECK:
                    yield {
                        "type": "error",
                        "message": "The conversation is too long. Please start a new conversation or summarize what you need.",
                    }
                    return
            except Exception:
                pass

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

                    tool = tool_registry.get_tool(tool_name)
                    tool_call_id = tool_call.get("id") if isinstance(tool_call, dict) else None
                    if not tool:
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": f"Error: Tool '{tool_name}' not found",
                                "tool_call_id": tool_call_id,
                            }
                        )
                        continue

                    try:
                        result = await mcp_server.call_tool(tool_name, tool_args)
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": json.dumps(result)
                                if not isinstance(result, str)
                                else result,
                                "tool_call_id": tool_call_id,
                            }
                        )
                    except Exception as e:
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": f"Error: {str(e)}",
                                "tool_call_id": tool_call_id,
                            }
                        )

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

    def _parse_qwen_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """Parse Qwen2.5's XML-based tool call format

        Qwen2.5 wraps tool calls in <tool_call> tags:
        <tool_call>
        {"name": "tool_name", "arguments": {...}}
        </tool_call>
        """
        import re

        tool_calls: list[dict[str, Any]] = []

        # Find all <tool_call>...</tool_call> blocks
        pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            try:
                json_str = match.group(1).strip()
                tool_obj = json.loads(json_str)

                tool_name = tool_obj.get("name")
                tool_args = tool_obj.get("arguments", {})

                if tool_name:
                    tool_calls.append(
                        {
                            "id": f"call_qwen_{len(tool_calls)}",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args)
                                if isinstance(tool_args, dict)
                                else str(tool_args),
                            },
                        }
                    )

                    if settings.debug_tool_calls:
                        print(f"[PARSED QWEN TOOL CALL] {tool_name}")
                        print(f"  Arguments: {tool_args}")
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues
                json_str = match.group(1).strip()
                fixed_json = self._fix_json_string(json_str)

                if fixed_json != json_str:
                    try:
                        tool_obj = json.loads(fixed_json)
                        tool_name = tool_obj.get("name")
                        tool_args = tool_obj.get("arguments", {})

                        if tool_name:
                            tool_calls.append(
                                {
                                    "id": f"call_qwen_{len(tool_calls)}",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json.dumps(tool_args)
                                        if isinstance(tool_args, dict)
                                        else str(tool_args),
                                    },
                                }
                            )

                            if settings.debug_tool_calls:
                                print(f"[PARSED QWEN TOOL CALL] {tool_name} (after JSON fix)")
                                print(f"  Arguments: {tool_args}")
                            continue
                    except Exception:
                        pass

                if settings.debug_tool_calls:
                    print(f"[PARSE ERROR] Failed to parse Qwen tool call JSON: {e}")
                    print(f"  Content: {match.group(1)[:200]}")
                continue
            except Exception as e:
                if settings.debug_tool_calls:
                    print(f"[PARSE ERROR] Unexpected error parsing Qwen tool call: {e}")
                continue

        return tool_calls

    def _fix_json_string(self, json_str: str) -> str:
        """Attempt to fix common JSON issues like unescaped newlines in strings

        This handles cases where the model includes multi-line content
        (like MIDI text) directly in JSON strings without proper escaping.
        """
        fixed = json_str
        result = []
        i = 0
        in_string = False
        escape_next = False

        while i < len(fixed):
            char = fixed[i]

            if escape_next:
                result.append(char)
                escape_next = False
            elif char == "\\":
                result.append(char)
                escape_next = True
            elif char == '"' and not escape_next:
                in_string = not in_string
                result.append(char)
            elif in_string and char in ["\n", "\r", "\t"]:
                # Escape unescaped control characters in strings
                if char == "\n":
                    result.append("\\n")
                elif char == "\r":
                    result.append("\\r")
                elif char == "\t":
                    result.append("\\t")
            else:
                result.append(char)

            i += 1

        return "".join(result)

    def _strip_tool_call_tags(self, content: str) -> str:
        """Remove <tool_call> XML tags from content for display"""
        import re

        pattern = r"<tool_call>.*?</tool_call>"
        return re.sub(pattern, "", content, flags=re.DOTALL).strip()

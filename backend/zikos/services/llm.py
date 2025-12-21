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
        self.conversations: dict[str, list[dict[str, Any]]] = {}
        self.tool_provider = None
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
        if session_id not in self.conversations:
            system_prompt = self._get_system_prompt()
            self.conversations[session_id] = [{"role": "system", "content": system_prompt}]
        return self.conversations[session_id]

    def get_thinking_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all thinking messages for a session (for debugging)

        Returns list of thinking messages with their context (adjacent messages)
        """
        if session_id not in self.conversations:
            return []

        history = self.conversations[session_id]
        thinking_messages = []

        for i, msg in enumerate(history):
            if msg.get("role") == "thinking":
                context = {}
                # Get adjacent messages for context
                if i > 0:
                    prev_msg = history[i - 1]
                    context["before"] = {
                        "role": prev_msg.get("role"),
                        "content_preview": str(prev_msg.get("content", ""))[:200],
                    }
                if i < len(history) - 1:
                    next_msg = history[i + 1]
                    context["after"] = {
                        "role": next_msg.get("role"),
                        "content_preview": str(next_msg.get("content", ""))[:200],
                    }

                thinking_messages.append(
                    {
                        "thinking": msg.get("content", ""),
                        "context": context,
                        "position": i,
                    }
                )

        return thinking_messages

    def _extract_thinking(self, content: str | None) -> tuple[str, str]:
        """Extract thinking content from <thinking> tags

        Returns:
            tuple: (cleaned_content, thinking_content)
        """
        import re

        if content is None:
            return "", ""

        thinking_parts = []
        pattern = r"<thinking>(.*?)</thinking>"
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            thinking_parts.append(match.group(1).strip())

        cleaned_content = re.sub(pattern, "", content, flags=re.DOTALL).strip()

        thinking_content = "\n\n".join(thinking_parts) if thinking_parts else ""

        return cleaned_content, thinking_content

    def _prepare_messages(
        self, history: list[dict[str, Any]], max_tokens: int | None = None, for_user: bool = False
    ) -> list[dict[str, Any]]:
        if max_tokens is None:
            max_tokens = LLM.MAX_TOKENS_PREPARE_MESSAGES
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
        if not history:
            return history

        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")

        messages = []
        system_prompt = None
        system_prepended = False
        total_tokens = 0

        # First, find and preserve audio analysis messages (they're critical)
        audio_analysis_messages = []
        other_messages = []
        for msg in history:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
                continue
            # Filter thinking messages if preparing for user display
            if for_user and msg.get("role") == "thinking":
                continue
            content = str(msg.get("content", ""))
            # Check if this is an audio analysis message
            if any(
                marker in content
                for marker in ["[Audio Analysis", "Audio analysis complete", "audio_file_id"]
            ):
                audio_analysis_messages.append(msg)
            else:
                other_messages.append(msg)

        # Process other messages in reverse (keep most recent) to stay within token limit
        # Reserve more space for audio analysis (can be large)
        # Ensure we have at least some room for messages (handle case where max_tokens < reserve)
        available_tokens = max(max_tokens - LLM.TOKENS_RESERVE_AUDIO_ANALYSIS, max_tokens // 2)

        processed_messages: list[dict[str, Any]] = []
        first_message_added = False
        for msg in reversed(other_messages):
            msg_tokens = len(enc.encode(str(msg.get("content", ""))))
            if total_tokens + msg_tokens > available_tokens and first_message_added:
                break

            processed_messages.insert(0, msg)
            total_tokens += msg_tokens
            first_message_added = True

        # Always include audio analysis messages (they're essential)
        for msg in audio_analysis_messages:
            processed_messages.append(msg)

        # Now process in forward order
        for msg in processed_messages:
            if msg.get("role") == "user" and system_prompt and not system_prepended:
                combined_content = f"{system_prompt}\n\n{msg['content']}"
                messages.append({"role": "user", "content": combined_content})
                system_prepended = True
            elif msg.get("role") != "system":
                messages.append(msg)

        # Ensure at least one message is included (system prompt or first user message)
        if not messages and system_prompt:
            messages.append({"role": "user", "content": system_prompt})
        elif not messages and other_messages:
            first_msg = other_messages[0]
            if system_prompt:
                combined_content = f"{system_prompt}\n\n{first_msg.get('content', '')}"
                messages.append({"role": "user", "content": combined_content})
            else:
                messages.append(first_msg)

        return messages

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

        # Check if message already contains analysis (from handle_audio_ready)
        # If so, the LLM should use it directly - no need for keyword detection
        message_lower = message.lower()
        has_analysis_marker = (
            "[audio analysis results]" in message_lower or "audio analysis results" in message_lower
        )

        # Detect if user is asking about audio
        audio_keywords = ["sample", "audio", "recording", "sound", "playback", "performance"]
        is_asking_about_audio = any(keyword in message_lower for keyword in audio_keywords)

        # If asking about audio but no analysis marker, try to find recent audio analysis in history
        # This helps provide context when user asks follow-up questions about audio
        if not has_analysis_marker:
            recent_audio_analysis = self._find_recent_audio_analysis(history)
            if recent_audio_analysis:
                # Prepend the analysis context to help the LLM answer questions
                message = f"[Audio Analysis Context - Use this data to answer the user's question]\n{recent_audio_analysis}\n\n[User Question]\n{message}\n\nIMPORTANT: Answer based ONLY on the audio analysis data provided above. Do not make up or hallucinate information. If the analysis data doesn't contain the information needed, say so explicitly."
            elif is_asking_about_audio:
                # User is asking about audio but no analysis is available
                message = f"{message}\n\n[IMPORTANT: The user is asking about audio analysis, but no audio analysis data is available in the conversation history. Please inform them that you don't see any audio analysis available and suggest they record or upload audio first.]"

        history.append({"role": "user", "content": message})

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
                tool_instructions = self.tool_provider.format_tool_instructions()
                tool_summary = self.tool_provider.generate_tool_summary(tools)
                tool_schemas_text = self.tool_provider.format_tool_schemas(tools)
                tool_examples = self.tool_provider.get_tool_call_examples()

                tools_section = f"{tool_instructions}\n\n## Available Tools\n\n{tool_summary}\n\n{tool_schemas_text}\n\n{tool_examples}"

                # Inject tools into the system prompt in the conversation history
                if history and history[0].get("role") == "system":
                    original_system = history[0].get("content", "")
                    history[0]["content"] = f"{original_system}\n\n{tools_section}"
                else:
                    # If no system message, add one with tools
                    system_prompt = self._get_system_prompt()
                    history.insert(
                        0, {"role": "system", "content": f"{system_prompt}\n\n{tools_section}"}
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
                        return {
                            "type": "response",
                            "message": "The model appears to be stuck in a loop calling the same tool. Please try rephrasing your request.",
                        }

                if consecutive_tool_calls > max_consecutive_tool_calls:
                    print(
                        f"WARNING: Too many consecutive tool calls ({consecutive_tool_calls}). "
                        "Breaking loop to prevent infinite recursion."
                    )
                    return {
                        "type": "response",
                        "message": "The model is making too many tool calls. Please try rephrasing your request or breaking it into smaller parts.",
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
                        return {
                            "type": "tool_call",
                            "message": widget_content,
                            "tool_name": tool_name,
                            "tool_id": tool_call.get("id"),
                            "arguments": tool_args,
                        }

                    try:
                        result = await mcp_server.call_tool(tool_name, **tool_args)
                        if settings.debug_tool_calls:
                            print(f"[TOOL RESULT] {tool_name}")
                            print(f"  Result: {json.dumps(result, indent=2, default=str)}")
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": str(result),
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

            # Log final response thinking
            if thinking_content:
                _thinking_logger.info(
                    f"Session: {session_id}\n"
                    f"Final Response Thinking:\n{thinking_content}\n"
                    f"Response: {response_content[:200]}...\n"
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

        return {
            "type": "response",
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
        # Use [Audio Analysis Results] marker to prevent re-detection
        message = f"[Audio Analysis Results]\nAudio File: {audio_file_id}\n\n{analysis_str}\n\nPlease provide feedback on this musical performance based on the analysis above."

        return await self.generate_response(message, session_id or "default", mcp_server)

    def _get_system_prompt(self) -> str:
        """Get system prompt"""
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent.parent.parent / "SYSTEM_PROMPT.md"

        if prompt_path.exists():
            with open(prompt_path) as f:
                content = f.read()
                start = content.find("```")
                end = content.find("```", start + 3)
                if start != -1 and end != -1:
                    prompt = content[start + 3 : end].strip()
                    print(f"DEBUG: System prompt extracted, length: {len(prompt)} chars")
                    return prompt

        print("DEBUG: Using fallback system prompt")
        return "You are an expert music teacher AI assistant."

    def _find_recent_audio_analysis(self, history: list[dict[str, Any]]) -> str | None:
        """Find the most recent audio analysis in conversation history"""
        # Look for messages containing audio analysis (both user messages with analysis context and tool results)
        for msg in reversed(history):
            content = str(msg.get("content", ""))

            # Check for audio analysis markers (case insensitive)
            content_lower = content.lower()
            has_analysis_markers = any(
                keyword in content_lower
                for keyword in [
                    "[audio analysis",
                    "audio analysis",
                    "analysis complete",
                    "tempo",
                    "pitch",
                    "rhythm",
                    "bpm",
                    "intonation",
                    "timing accuracy",
                    "audio_file_id",
                ]
            )

            # Check if it contains structured data (JSON-like)
            has_structured_data = (
                "{" in content or "[" in content or '"tempo"' in content or '"pitch"' in content
            )

            if has_analysis_markers and has_structured_data:
                # Extract just the analysis portion if it's embedded in a longer message
                if "[Audio Analysis Context]" in content:
                    # Extract the analysis section
                    parts = content.split("[Audio Analysis Context]")
                    if len(parts) > 1:
                        analysis_part = parts[1].split("[User Question]")[0].strip()
                        return analysis_part
                return content
        return None

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

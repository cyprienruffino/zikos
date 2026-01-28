"""Transformers backend implementation for HuggingFace models"""

import json
import re
import threading
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
    from transformers.generation import GenerationConfig

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    torch = None  # type: ignore[assignment]
    AutoModelForCausalLM = None  # type: ignore[assignment,misc]
    AutoTokenizer = None  # type: ignore[assignment,misc]
    TextIteratorStreamer = None  # type: ignore[assignment,misc]

from zikos.services.llm_backends.base import LLMBackend


class TransformersBackend(LLMBackend):
    """Backend using HuggingFace Transformers for safetensors models"""

    def __init__(self):
        self.model: Any = None
        self.tokenizer: Any = None
        self.n_ctx: int = 32768
        self.device: str = "cpu"

    def initialize(
        self,
        model_path: str,
        n_ctx: int = 131072,
        n_gpu_layers: int = 0,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs: Any,
    ) -> None:
        """Initialize HuggingFace Transformers backend"""
        if not HAS_TRANSFORMERS:
            raise ImportError(
                "transformers is not installed. Install with: pip install transformers torch"
            )

        self.n_ctx = n_ctx

        if torch is not None and torch.cuda.is_available():
            self.device = "cuda"
            torch_dtype = kwargs.get("torch_dtype", torch.bfloat16)
        else:
            self.device = "cpu"
            torch_dtype = kwargs.get("torch_dtype", torch.float32)

        print(f"Loading Transformers model from {model_path} on {self.device}...")
        print(f"Using context window: {n_ctx} tokens")

        model_path_obj = Path(model_path)

        if model_path_obj.exists() and model_path_obj.is_dir():
            local_path = str(model_path_obj)
        else:
            local_path = model_path

        self.tokenizer = AutoTokenizer.from_pretrained(
            local_path,
            trust_remote_code=kwargs.get("trust_remote_code", True),
        )

        if self.device == "cuda":
            attn_impl = kwargs.get("attn_implementation", "flash_attention_2")
            try:
                import flash_attn

                model_kwargs: dict[str, Any] = {
                    "torch_dtype": torch_dtype,
                    "device_map": {"": "cuda:0"},
                    "trust_remote_code": kwargs.get("trust_remote_code", True),
                    "attn_implementation": attn_impl,
                }
            except ImportError:
                print("Warning: flash-attention not available, using default attention")
                model_kwargs = {
                    "torch_dtype": torch_dtype,
                    "device_map": {"": "cuda:0"},
                    "trust_remote_code": kwargs.get("trust_remote_code", True),
                    "attn_implementation": "sdpa",
                }
        else:
            model_kwargs = {
                "torch_dtype": torch_dtype,
                "device_map": None,
                "trust_remote_code": kwargs.get("trust_remote_code", True),
            }

        self.model = AutoModelForCausalLM.from_pretrained(
            local_path,
            **model_kwargs,
        )

        if self.device == "cpu":
            self.model = self.model.to(self.device)
        elif self.device == "cuda":
            if hasattr(self.model, "hf_device_map"):
                device_map = self.model.hf_device_map
                if device_map:
                    cpu_keys = [
                        k
                        for k, v in device_map.items()
                        if v == "cpu" or (isinstance(v, int) and v < 0)
                    ]
                    if cpu_keys:
                        print(f"Warning: Some model components on CPU: {cpu_keys[:5]}...")
                    gpu_keys = [k for k, v in device_map.items() if isinstance(v, int) and v >= 0]
                    if gpu_keys:
                        print(f"Model components on GPU: {len(gpu_keys)} components")
                    print(f"Device map summary: {len(device_map)} components")
                else:
                    if hasattr(self.model, "device"):
                        actual_device = str(self.model.device)
                        if "cuda" not in actual_device:
                            print(
                                f"Warning: Model on {actual_device}, expected CUDA. Moving to GPU..."
                            )
                            self.model = self.model.to(self.device)
                        else:
                            print(f"Model on device: {actual_device}")
            else:
                if hasattr(self.model, "device"):
                    actual_device = str(self.model.device)
                    if "cuda" not in actual_device:
                        print(f"Warning: Model on {actual_device}, expected CUDA. Moving to GPU...")
                        self.model = self.model.to(self.device)
                    else:
                        print(f"Model on device: {actual_device}")

        self.model.eval()

        if self.device == "cuda" and torch is not None:
            allocated = torch.cuda.memory_allocated(0) / (1024**3)
            reserved = torch.cuda.memory_reserved(0) / (1024**3)
            print(f"GPU memory allocated: {allocated:.2f} GB, reserved: {reserved:.2f} GB")

        print(f"Model loaded successfully on {self.device}")

    def create_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create chat completion using Transformers"""
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Backend not initialized. Call initialize() first.")

        text = self._format_messages(messages, tools)

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=self.n_ctx)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": kwargs.get("max_new_tokens", 2048),
            "do_sample": temperature is not None and temperature > 0,
        }

        if temperature is not None:
            generation_kwargs["temperature"] = temperature
        if top_p is not None:
            generation_kwargs["top_p"] = top_p

        with torch.no_grad():
            outputs = self.model.generate(**inputs, **generation_kwargs)

        generated_text = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )

        tool_calls = self._extract_tool_calls(generated_text)

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": generated_text,
                        "tool_calls": tool_calls if tool_calls else None,
                    },
                    "finish_reason": "stop",
                }
            ]
        }

    async def stream_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion using Transformers"""
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Backend not initialized. Call initialize() first.")

        if TextIteratorStreamer is None:
            # Fallback to base implementation if streamer not available
            async for chunk in super().stream_chat_completion(
                messages, tools, temperature, top_p, **kwargs
            ):
                yield chunk
            return

        text = self._format_messages(messages, tools)
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=self.n_ctx)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": kwargs.get("max_new_tokens", 2048),
            "do_sample": temperature is not None and temperature > 0,
        }

        if temperature is not None:
            generation_kwargs["temperature"] = temperature
        if top_p is not None:
            generation_kwargs["top_p"] = top_p

        if not hasattr(self.tokenizer, "decode") or not callable(self.tokenizer.decode):
            raise RuntimeError("Tokenizer does not support decoding")

        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
            timeout=60.0,
        )
        generation_kwargs["streamer"] = streamer

        def generate():
            try:
                with torch.no_grad():
                    self.model.generate(**inputs, **generation_kwargs)
            except Exception as e:
                import logging

                logging.error(f"Error in generation thread: {e}", exc_info=True)

        generation_thread = threading.Thread(target=generate, daemon=True)
        generation_thread.start()

        accumulated_text = ""
        consecutive_garbage_count = 0
        max_garbage_chunks = 10

        for new_text in streamer:
            if new_text is None:
                break
            if not isinstance(new_text, str):
                continue

            if not new_text or (not new_text.strip() and not accumulated_text):
                continue

            if len(new_text) > 0:
                printable_ratio = sum(1 for c in new_text if c.isprintable() or c.isspace()) / len(
                    new_text
                )
                if printable_ratio < 0.5:
                    consecutive_garbage_count += 1
                    if consecutive_garbage_count >= max_garbage_chunks:
                        import logging

                        logging.error(
                            f"Detected garbled output from model. "
                            f"Accumulated text length: {len(accumulated_text)}"
                        )
                        break
                else:
                    consecutive_garbage_count = 0

            accumulated_text += new_text
            yield {
                "choices": [
                    {
                        "delta": {
                            "content": new_text,
                            "role": "assistant",
                        },
                        "finish_reason": None,
                    }
                ]
            }

        generation_thread.join(timeout=30)

        tool_calls = self._extract_tool_calls(accumulated_text)
        finish_reason = "tool_calls" if tool_calls else "stop"

        yield {
            "choices": [
                {
                    "delta": {
                        "tool_calls": tool_calls if tool_calls else None,
                    },
                    "finish_reason": finish_reason,
                }
            ]
        }

    def _format_messages(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> str:
        """Format messages for Qwen models using chat template if available"""
        if (
            hasattr(self.tokenizer, "apply_chat_template")
            and self.tokenizer.chat_template is not None
        ):
            return self._format_with_chat_template(messages, tools)
        else:
            return self._format_simple(messages)

    def _format_with_chat_template(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> str:
        """Format messages using Qwen's chat template (preferred for Qwen3)"""
        formatted_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                formatted_messages.append({"role": "system", "content": content})
            elif role == "user":
                formatted_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                formatted_messages.append({"role": "assistant", "content": content})
            elif role == "thinking":
                # Treat thinking as assistant messages for context
                formatted_messages.append(
                    {"role": "assistant", "content": f"[Thinking: {content}]"}
                )
            elif role == "tool":
                tool_name = msg.get("name", "tool")
                tool_content = msg.get("content", "")
                formatted_messages.append(
                    {"role": "tool", "name": tool_name, "content": tool_content}
                )

        try:
            if tools:
                qwen_tools = self._convert_tools_for_qwen(tools)
                if hasattr(self.tokenizer, "apply_chat_template"):
                    text = self.tokenizer.apply_chat_template(
                        formatted_messages,
                        tools=qwen_tools,
                        tokenize=False,
                        add_generation_prompt=True,
                    )
                else:
                    print("Warning: Tokenizer doesn't support apply_chat_template, falling back")
                    return self._format_simple(messages)
            else:
                if hasattr(self.tokenizer, "apply_chat_template"):
                    text = self.tokenizer.apply_chat_template(
                        formatted_messages, tokenize=False, add_generation_prompt=True
                    )
                else:
                    return self._format_simple(messages)
            return str(text)
        except Exception as e:
            print(f"Warning: Failed to use chat template ({e}), falling back to simple formatting")
            import traceback

            traceback.print_exc()
            return self._format_simple(messages)

    def _convert_tools_for_qwen(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI-format tools to Qwen3 format for chat template

        Qwen3's chat template expects tools in this format:
        [
            {
                "type": "function",
                "function": {
                    "name": "...",
                    "description": "...",
                    "parameters": {...}
                }
            }
        ]
        """
        qwen_tools = []
        for tool in tools:
            if "function" in tool:
                func = tool["function"]
                qwen_tool = {
                    "type": "function",
                    "function": {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    },
                }
                qwen_tools.append(qwen_tool)
            elif "type" in tool and tool["type"] == "function":
                qwen_tools.append(tool)
            else:
                qwen_tools.append(tool)
        return qwen_tools

    def _format_simple(self, messages: list[dict[str, Any]]) -> str:
        """Fallback simple text formatting for models without chat template"""
        formatted_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                formatted_parts.append(f"System: {content}\n")
            elif role == "user":
                formatted_parts.append(f"User: {content}\n")
            elif role == "assistant":
                formatted_parts.append(f"Assistant: {content}\n")
            elif role == "thinking":
                formatted_parts.append(f"Assistant [Thinking]: {content}\n")
            elif role == "tool":
                tool_name = msg.get("name", "tool")
                tool_content = msg.get("content", "")
                formatted_parts.append(f"Tool ({tool_name}): {tool_content}\n")

        formatted_parts.append("Assistant:")

        return "\n".join(formatted_parts)

    def _extract_tool_calls(self, text: str) -> list[dict[str, Any]]:
        """Extract tool calls from Qwen XML format"""
        tool_calls = []

        pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        matches = re.finditer(pattern, text, re.DOTALL)

        for idx, match in enumerate(matches):
            try:
                json_str = match.group(1).strip()
                tool_obj = json.loads(json_str)

                tool_name = tool_obj.get("name")
                tool_args = tool_obj.get("arguments", {})

                if tool_name:
                    tool_calls.append(
                        {
                            "id": f"call_transformers_{idx}",
                            "function": {
                                "name": tool_name,
                                "arguments": (
                                    json.dumps(tool_args)
                                    if isinstance(tool_args, dict)
                                    else str(tool_args)
                                ),
                            },
                        }
                    )
            except json.JSONDecodeError:
                continue

        return tool_calls

    def supports_tools(self) -> bool:
        """Transformers backend supports tools via XML parsing"""
        return True

    def supports_system_messages(self) -> bool:
        """Transformers models (like Qwen) properly handle system messages via chat template"""
        return True

    def get_context_window(self) -> int:
        """Get configured context window"""
        return self.n_ctx

    def close(self) -> None:
        """Cleanup Transformers resources"""
        if self.model is not None:
            try:
                if hasattr(self.model, "cpu"):
                    self.model = self.model.cpu()
                del self.model
            except Exception:
                pass
            self.model = None

        if torch is not None:
            torch.cuda.empty_cache()

        self.tokenizer = None

    def is_initialized(self) -> bool:
        """Check if backend is initialized"""
        return self.model is not None and self.tokenizer is not None

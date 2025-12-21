"""Transformers backend implementation for HuggingFace models"""

import json
import re
from pathlib import Path
from typing import Any

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers.generation import GenerationConfig

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    AutoModelForCausalLM = None
    AutoTokenizer = None
    torch = None

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

        model_kwargs: dict[str, Any] = {
            "torch_dtype": torch_dtype,
            "device_map": "auto" if self.device == "cuda" else None,
            "trust_remote_code": kwargs.get("trust_remote_code", True),
        }

        if self.device == "cuda":
            attn_impl = kwargs.get("attn_implementation", "flash_attention_2")
            try:
                import flash_attn

                model_kwargs["attn_implementation"] = attn_impl
            except ImportError:
                print("Warning: flash-attention not available, using default attention")
                model_kwargs["attn_implementation"] = "sdpa"

        self.model = AutoModelForCausalLM.from_pretrained(
            local_path,
            **model_kwargs,
        )

        if self.device == "cpu":
            self.model = self.model.to(self.device)

        self.model.eval()

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
                                "arguments": json.dumps(tool_args)
                                if isinstance(tool_args, dict)
                                else str(tool_args),
                            },
                        }
                    )
            except json.JSONDecodeError:
                continue

        return tool_calls

    def supports_tools(self) -> bool:
        """Transformers backend supports tools via XML parsing"""
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

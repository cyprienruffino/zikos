"""LLM service"""

import json
from pathlib import Path
from typing import Any

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from zikos.config import settings
from zikos.mcp.server import MCPServer
from zikos.services.audio import AudioService


class LLMService:
    """Service for LLM interactions"""

    def __init__(self):
        self.llm = None
        self.audio_service = AudioService()
        self.conversations: dict[str, list[dict[str, Any]]] = {}
        self._initialize_llm()

    def _initialize_llm(self):
        """Initialize LLM"""
        if Llama is None:
            return
        if not settings.llm_model_path:
            return

        model_path = Path(settings.llm_model_path)
        if not model_path.exists():
            print(f"Warning: Model file not found at {model_path}")
            print("The application will start but LLM features will be unavailable.")
            print(
                f"To download a model, run: python scripts/download_model.py llama-3.1-8b-instruct-q4 -o {model_path.parent}"
            )
            return

        try:
            self.llm = Llama(
                model_path=str(model_path),
                n_ctx=settings.llm_n_ctx,
                n_gpu_layers=settings.llm_n_gpu_layers,
            )
        except Exception as e:
            print(f"Error initializing LLM: {e}")
            print("The application will start but LLM features will be unavailable.")
            self.llm = None

    def _get_conversation_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history for session"""
        if session_id not in self.conversations:
            self.conversations[session_id] = [
                {"role": "system", "content": self._get_system_prompt()}
            ]
        return self.conversations[session_id]

    async def generate_response(
        self,
        message: str,
        session_id: str,
        mcp_server: MCPServer,
    ) -> dict[str, Any]:
        """Generate LLM response, handling tool calls"""
        if not self.llm:
            return {
                "type": "response",
                "message": "LLM not available. Please ensure the model file exists at the path specified by LLM_MODEL_PATH.",
            }

        history = self._get_conversation_history(session_id)
        history.append({"role": "user", "content": message})

        tools = mcp_server.get_tools()
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            response = self.llm.create_chat_completion(
                messages=history,
                tools=tools,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )

            message_obj = response["choices"][0]["message"]
            history.append(message_obj)

            if "tool_calls" in message_obj and message_obj["tool_calls"]:
                tool_calls = message_obj["tool_calls"]
                tool_results = []

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"].get("arguments", "{}")

                    try:
                        tool_args = (
                            json.loads(tool_args_str)
                            if isinstance(tool_args_str, str)
                            else tool_args_str
                        )
                    except json.JSONDecodeError:
                        tool_args = {}

                    if tool_name == "request_audio_recording":
                        return {
                            "type": "tool_call",
                            "tool_name": tool_name,
                            "tool_id": tool_call.get("id"),
                            "arguments": tool_args,
                        }

                    if tool_name == "create_metronome":
                        return {
                            "type": "tool_call",
                            "tool_name": tool_name,
                            "tool_id": tool_call.get("id"),
                            "arguments": tool_args,
                        }

                    widget_tools = [
                        "create_tuner",
                        "create_chord_progression",
                        "create_tempo_trainer",
                        "create_ear_trainer",
                        "create_practice_timer",
                    ]
                    if tool_name in widget_tools:
                        return {
                            "type": "tool_call",
                            "tool_name": tool_name,
                            "tool_id": tool_call.get("id"),
                            "arguments": tool_args,
                        }

                    try:
                        result = await mcp_server.call_tool(tool_name, **tool_args)
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": str(result),
                                "tool_call_id": tool_call.get("id"),
                            }
                        )
                    except Exception as e:
                        tool_results.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": f"Error: {str(e)}",
                                "tool_call_id": tool_call.get("id"),
                            }
                        )

                history.extend(tool_results)
                continue

            return {
                "type": "response",
                "message": message_obj.get("content", ""),
            }

        return {
            "type": "response",
            "message": "Maximum iterations reached. Please try again.",
        }

    async def handle_audio_ready(
        self,
        audio_file_id: str,
        recording_id: str | None,
        session_id: str | None,
        mcp_server: MCPServer,
    ) -> dict[str, Any]:
        """Handle audio ready and generate response"""
        analysis = await self.audio_service.run_baseline_analysis(audio_file_id)

        message = f"Audio analysis complete for {audio_file_id}. Analysis: {analysis}"

        return await self.generate_response(message, session_id or "default", mcp_server)

    def _get_system_prompt(self) -> str:
        """Get system prompt"""
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent.parent / "SYSTEM_PROMPT.md"

        if prompt_path.exists():
            with open(prompt_path) as f:
                content = f.read()
                start = content.find("```")
                end = content.find("```", start + 3)
                if start != -1 and end != -1:
                    return content[start + 3 : end].strip()

        return "You are an expert music teacher AI assistant."

"""LLM service"""

import json
from typing import Any

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from src.zikos.config import settings
from src.zikos.mcp.server import MCPServer
from src.zikos.services.audio import AudioService


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
        if settings.llm_model_path:
            self.llm = Llama(
                model_path=settings.llm_model_path,
                n_ctx=settings.llm_n_ctx,
                n_gpu_layers=settings.llm_n_gpu_layers,
            )

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
                "message": "LLM not initialized. Please set LLM_MODEL_PATH in environment.",
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

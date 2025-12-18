"""LLM service"""

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None  # type: ignore

from src.zikos.config import settings
from src.zikos.mcp.server import MCPServer
from src.zikos.services.audio import AudioService


class LLMService:
    """Service for LLM interactions"""

    def __init__(self):
        self.llm = None
        self.audio_service = AudioService()
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

    async def generate_response(
        self,
        message: str,
        session_id: str,
        mcp_server: MCPServer,
    ) -> str:
        """Generate LLM response"""
        if not self.llm:
            return "LLM not initialized. Please set LLM_MODEL_PATH in environment."

        tools = mcp_server.get_tools()
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": message},
            ],
            tools=tools,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
        )

        return response["choices"][0]["message"]["content"]

    async def handle_audio_ready(
        self,
        audio_file_id: str,
        recording_id: str | None,
        session_id: str | None,
        mcp_server: MCPServer,
    ) -> str:
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

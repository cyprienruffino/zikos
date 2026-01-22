"""Practice timer tools"""

import uuid
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class PracticeTimerTools(ToolCollection):
    """Practice timer MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="create_practice_timer",
                description="Create a practice timer widget to track practice sessions. Helps build consistent practice habits with optional goals and break reminders.",
                category=ToolCategory.WIDGET,
                schema={
                    "type": "function",
                    "function": {
                        "name": "create_practice_timer",
                        "description": "Create a practice timer widget to track practice sessions. Helps build consistent practice habits with optional goals and break reminders.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "duration_minutes": {
                                    "type": "number",
                                    "description": "Target practice duration in minutes",
                                },
                                "goal": {
                                    "type": "string",
                                    "description": "Optional practice goal or focus (e.g., 'Work on scales', 'Practice piece X')",
                                },
                                "break_interval_minutes": {
                                    "type": "number",
                                    "description": "Optional break reminder interval in minutes (e.g., 25 for Pomodoro technique)",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional instruction or context for the user",
                                },
                            },
                            "required": [],
                        },
                    },
                },
            ),
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "create_practice_timer":
            return await self.create_practice_timer(
                kwargs.get("duration_minutes"),
                kwargs.get("goal"),
                kwargs.get("break_interval_minutes"),
                kwargs.get("description"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def create_practice_timer(
        self,
        duration_minutes: float | None,
        goal: str | None,
        break_interval_minutes: float | None,
        description: str | None,
    ) -> dict[str, Any]:
        """Create practice timer widget"""
        timer_id = str(uuid.uuid4())

        return {
            "status": "practice_timer_created",
            "timer_id": timer_id,
            "duration_minutes": duration_minutes,
            "goal": goal,
            "break_interval_minutes": break_interval_minutes,
            "description": description,
        }

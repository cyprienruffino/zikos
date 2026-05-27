"""Update-settings tool — lets the LLM persist user profile information."""

from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection
from zikos.services.user_settings import VALID_FIELDS, UserSettingsService


def get_update_settings_tool() -> Tool:
    return Tool(
        name="update_settings",
        description=(
            "Save a piece of user profile information (language, instruments, level, "
            "preferences, or free-form notes). Call this whenever the user tells you "
            "something about themselves that should persist across sessions."
        ),
        category=ToolCategory.OTHER,
        parameters={
            "field": {
                "type": "string",
                "enum": sorted(VALID_FIELDS),
                "description": (
                    "Which setting to update. "
                    "'language': response language (e.g. 'French'). "
                    "'instruments': list of instruments played. "
                    "'level': skill level (beginner/intermediate/advanced/expert). "
                    "'preferences': musical genres or styles. "
                    "'notes': anything else worth remembering."
                ),
            },
            "value": {
                "type": "string",
                "description": (
                    "New value. For list fields (instruments, preferences) use "
                    "comma-separated values, e.g. 'bass guitar, piano'."
                ),
            },
        },
        required=["field", "value"],
    )


class SettingsTools(ToolCollection):
    def __init__(self, user_settings_service: UserSettingsService):
        self._service = user_settings_service

    def get_tools(self) -> list[Tool]:
        return [get_update_settings_tool()]

    async def call_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        if tool_name != "update_settings":
            raise ValueError(f"Unknown tool: {tool_name}")

        field = kwargs.get("field", "")
        raw_value = kwargs.get("value", "")

        list_fields = {"instruments", "preferences"}
        if field in list_fields:
            value: Any = [v.strip() for v in raw_value.split(",") if v.strip()]
        else:
            value = raw_value

        try:
            updated = self._service.update(field, value)
            return {
                "success": True,
                "message": f"Saved {field}: {raw_value}",
                "current_settings": updated.model_dump(),
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}

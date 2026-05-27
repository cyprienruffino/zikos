"""Tests for user settings service, prompt section, and MCP tool."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from zikos.mcp.tools.settings.settings_tools import SettingsTools
from zikos.services.prompt.sections.user_profile import UserProfileSection
from zikos.services.user_settings import VALID_FIELDS, UserSettings, UserSettingsService

# ── UserSettingsService ───────────────────────────────────────────────────────


class TestUserSettingsService:
    def test_load_returns_defaults_when_no_file(self, tmp_path):
        service = UserSettingsService(tmp_path / "settings.json")
        s = service.load()
        assert s.language == "auto"
        assert s.instruments == []
        assert s.level == ""

    def test_update_persists_to_disk(self, tmp_path):
        path = tmp_path / "settings.json"
        service = UserSettingsService(path)
        service.update("language", "French")

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["language"] == "French"

    def test_update_string_field(self, tmp_path):
        service = UserSettingsService(tmp_path / "s.json")
        updated = service.update("level", "intermediate")
        assert updated.level == "intermediate"

    def test_update_list_field(self, tmp_path):
        service = UserSettingsService(tmp_path / "s.json")
        updated = service.update("instruments", ["bass guitar", "piano"])
        assert updated.instruments == ["bass guitar", "piano"]

    def test_update_unknown_field_raises(self, tmp_path):
        service = UserSettingsService(tmp_path / "s.json")
        with pytest.raises(ValueError, match="Unknown settings field"):
            service.update("nonexistent", "value")

    def test_load_from_existing_file(self, tmp_path):
        path = tmp_path / "s.json"
        path.write_text(json.dumps({"language": "Spanish", "level": "advanced"}))
        service = UserSettingsService(path)
        s = service.load()
        assert s.language == "Spanish"
        assert s.level == "advanced"

    def test_load_is_cached(self, tmp_path):
        service = UserSettingsService(tmp_path / "s.json")
        s1 = service.load()
        s2 = service.load()
        assert s1 is s2

    def test_corrupt_file_falls_back_to_defaults(self, tmp_path):
        path = tmp_path / "s.json"
        path.write_text("not valid json {{{")
        service = UserSettingsService(path)
        s = service.load()
        assert s.language == "auto"

    def test_update_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "settings.json"
        service = UserSettingsService(path)
        service.update("level", "beginner")
        assert path.exists()

    def test_multiple_updates_accumulate(self, tmp_path):
        service = UserSettingsService(tmp_path / "s.json")
        service.update("language", "French")
        service.update("level", "beginner")
        s = service.load()
        assert s.language == "French"
        assert s.level == "beginner"


# ── UserProfileSection ────────────────────────────────────────────────────────


class TestUserProfileSection:
    def test_empty_profile_shows_nudge(self):
        section = UserProfileSection(UserSettings())
        text = section.render()
        assert "No profile" in text
        assert "update_settings" in text

    def test_language_auto_not_shown(self):
        section = UserProfileSection(UserSettings(language="auto"))
        text = section.render()
        assert "Language" not in text

    def test_filled_profile_shows_fields(self):
        s = UserSettings(
            language="French",
            instruments=["bass guitar"],
            level="intermediate",
            preferences=["jazz", "funk"],
            notes="Victor Wooten slap technique",
        )
        text = UserProfileSection(s).render()
        assert "French" in text
        assert "bass guitar" in text
        assert "intermediate" in text
        assert "jazz" in text
        assert "Victor Wooten" in text

    def test_language_includes_instruction(self):
        s = UserSettings(language="German")
        text = UserProfileSection(s).render()
        assert "German" in text
        assert "respond in this language" in text

    def test_partial_profile_only_shows_set_fields(self):
        s = UserSettings(level="advanced")
        text = UserProfileSection(s).render()
        assert "advanced" in text
        assert "Instruments" not in text
        assert "Preferences" not in text


# ── SettingsTools ─────────────────────────────────────────────────────────────


class TestSettingsTools:
    @pytest.fixture
    def service(self, tmp_path):
        return UserSettingsService(tmp_path / "s.json")

    @pytest.fixture
    def tools(self, service):
        return SettingsTools(service)

    def test_exposes_update_settings_tool(self, tools):
        names = [t.name for t in tools.get_tools()]
        assert "update_settings" in names

    @pytest.mark.asyncio
    async def test_update_string_field(self, tools, service):
        result = await tools.call_tool("update_settings", field="language", value="French")
        assert result["success"] is True
        assert service.load().language == "French"

    @pytest.mark.asyncio
    async def test_update_list_field_comma_separated(self, tools, service):
        result = await tools.call_tool(
            "update_settings", field="instruments", value="bass guitar, piano"
        )
        assert result["success"] is True
        assert service.load().instruments == ["bass guitar", "piano"]

    @pytest.mark.asyncio
    async def test_update_unknown_field_returns_error(self, tools):
        result = await tools.call_tool("update_settings", field="bad_field", value="x")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_result_includes_current_settings(self, tools):
        result = await tools.call_tool("update_settings", field="level", value="beginner")
        assert "current_settings" in result
        assert result["current_settings"]["level"] == "beginner"

    @pytest.mark.asyncio
    async def test_unknown_tool_name_raises(self, tools):
        with pytest.raises((ValueError, NotImplementedError)):
            await tools.call_tool("nonexistent_tool")


# ── MCPServer integration ─────────────────────────────────────────────────────


class TestMCPServerSettingsIntegration:
    def test_update_settings_registered_in_mcp_server(self):
        from zikos.mcp.server import MCPServer

        server = MCPServer()
        tool_names = [t.name for t in server.get_tool_registry().get_all_tools()]
        assert "update_settings" in tool_names

    @pytest.mark.asyncio
    async def test_update_settings_callable_via_server(self, tmp_path):
        from zikos.mcp.server import MCPServer

        service = UserSettingsService(tmp_path / "s.json")
        server = MCPServer(user_settings_service=service)
        result = await server.call_tool("update_settings", field="language", value="Italian")
        assert result["success"] is True
        assert service.load().language == "Italian"

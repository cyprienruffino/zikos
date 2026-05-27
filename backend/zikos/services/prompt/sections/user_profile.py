"""User profile prompt section"""

from zikos.services.prompt.sections.base import PromptSection
from zikos.services.user_settings import UserSettings


class UserProfileSection(PromptSection):
    """Injects the user's saved profile into the system prompt."""

    def __init__(self, user_settings: UserSettings):
        self._settings = user_settings

    def render(self) -> str:
        s = self._settings
        has_profile = any(
            [
                s.language not in ("", "auto"),
                s.instruments,
                s.level,
                s.preferences,
                s.notes,
            ]
        )

        if not has_profile:
            return (
                "## User Profile\n"
                "No profile saved yet. When the user tells you anything about themselves "
                "(language preference, instrument, level, musical goals), "
                "call update_settings to persist it for future sessions."
            )

        lines = ["## User Profile"]
        if s.language not in ("", "auto"):
            lines.append(f"Language: {s.language} — always respond in this language")
        if s.instruments:
            lines.append(f"Instruments: {', '.join(s.instruments)}")
        if s.level:
            lines.append(f"Level: {s.level}")
        if s.preferences:
            lines.append(f"Preferences: {', '.join(s.preferences)}")
        if s.notes:
            lines.append(f"Notes: {s.notes}")
        return "\n".join(lines)

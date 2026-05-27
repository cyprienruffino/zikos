"""User settings — persistent profile loaded into the system prompt each session."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

_logger = logging.getLogger(__name__)

VALID_FIELDS = {"language", "instruments", "level", "preferences", "notes"}


class UserSettings(BaseModel):
    language: str = "auto"
    instruments: list[str] = []
    level: str = ""
    preferences: list[str] = []
    notes: str = ""


class UserSettingsService:
    def __init__(self, path: Path):
        self._path = path
        self._cache: UserSettings | None = None

    def load(self) -> UserSettings:
        if self._cache is not None:
            return self._cache
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._cache = UserSettings(**data)
            except Exception as e:
                _logger.warning(f"Could not load user settings from {self._path}: {e}")
                self._cache = UserSettings()
        else:
            self._cache = UserSettings()
        return self._cache

    def update(self, field: str, value: Any) -> UserSettings:
        if field not in VALID_FIELDS:
            raise ValueError(
                f"Unknown settings field: {field!r}. Valid fields: {sorted(VALID_FIELDS)}"
            )
        current = self.load()
        updated = UserSettings(**{**current.model_dump(), field: value})
        self._cache = updated
        self._persist(updated)
        return updated

    def _persist(self, s: UserSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(s.model_dump_json(indent=2), encoding="utf-8")

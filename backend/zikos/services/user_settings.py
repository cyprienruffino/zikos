"""User settings — persistent profile loaded into the system prompt each session."""

import json
import logging
import os
import tempfile
import threading
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
        self._lock = threading.Lock()

    def load(self) -> UserSettings:
        with self._lock:
            return self._load_locked()

    def _load_locked(self) -> UserSettings:
        if self._cache is not None:
            return self._cache
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._cache = UserSettings(**data)
            except Exception:
                # Do not silently destroy the profile: back up the corrupt
                # file so it can be recovered, and log loudly.
                backup_path = self._path.with_suffix(self._path.suffix + ".corrupt")
                _logger.error(
                    "User settings file %s is corrupt and could not be loaded. "
                    "Backing it up to %s and starting with defaults.",
                    self._path,
                    backup_path,
                    exc_info=True,
                )
                try:
                    os.replace(self._path, backup_path)
                except OSError:
                    _logger.exception("Could not back up corrupt settings file %s", self._path)
                self._cache = UserSettings()
        else:
            self._cache = UserSettings()
        return self._cache

    def update(self, field: str, value: Any) -> UserSettings:
        if field not in VALID_FIELDS:
            raise ValueError(
                f"Unknown settings field: {field!r}. Valid fields: {sorted(VALID_FIELDS)}"
            )
        with self._lock:
            current = self._load_locked()
            updated = UserSettings(**{**current.model_dump(), field: value})
            self._persist(updated)
            self._cache = updated
            return updated

    def _persist(self, s: UserSettings) -> None:
        """Atomically write settings: temp file in the same dir + os.replace."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=self._path.parent, prefix=self._path.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(s.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, self._path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

"""Remembering answers for a while, so we don't ask the internet every time.

Weather doesn't change much in 15 minutes, and a town doesn't move at all.
Asking again would be slow and unkind to a free service. A cache is like
writing the answer on a sticky note with a "use until" time on it.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .exceptions import StorageError
from .files import write_safely

Clock = Callable[[], datetime]


class Cache(ABC):
    @abstractmethod
    def get(self, key: str, allow_expired: bool = False) -> Any | None:
        """The saved value, or None if there isn't one or it's out of date.
        allow_expired=True returns old values too, for when going online fails."""

    @abstractmethod
    def set(self, key: str, value: Any, keep_for: timedelta) -> None:
        """Save a value. It must be something JSON can hold."""

    @abstractmethod
    def clear(self) -> int:
        """Forget everything. Returns how many entries there were."""


class MemoryCache(Cache):
    """Forgets everything when the program closes. Good for tests."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or datetime.now
        self._entries: dict[str, tuple[datetime, Any]] = {}

    def get(self, key: str, allow_expired: bool = False) -> Any | None:
        entry = self._entries.get(key)
        if entry is None or (entry[0] <= self._clock() and not allow_expired):
            return None
        return entry[1]

    def set(self, key: str, value: Any, keep_for: timedelta) -> None:
        self._entries[key] = (self._clock() + keep_for, value)

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count


class FileCache(Cache):
    """Keeps entries in a JSON file, so they last between runs.

    If the file gets damaged, it's treated as empty instead of crashing. The
    worst that happens is the weather gets fetched again.
    """

    def __init__(self, path: str | Path, clock: Clock | None = None) -> None:
        self._path = Path(path)
        self._clock = clock or datetime.now

    @property
    def path(self) -> Path:
        return self._path

    def get(self, key: str, allow_expired: bool = False) -> Any | None:
        entry = self._load().get(key)
        if not isinstance(entry, dict) or "value" not in entry:
            return None
        try:
            expired = datetime.fromisoformat(entry["expires"]) <= self._clock()
        except (KeyError, TypeError, ValueError):
            return None
        return None if expired and not allow_expired else entry["value"]

    def set(self, key: str, value: Any, keep_for: timedelta) -> None:
        entries = self._load()
        entries[key] = {"expires": (self._clock() + keep_for).isoformat(), "value": value}
        self._save(entries)

    def clear(self) -> int:
        count = len(self._load())
        self._save({})
        return count

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, entries: dict[str, Any]) -> None:
        try:
            write_safely(self._path, json.dumps(entries, ensure_ascii=False))
        except OSError as error:
            raise StorageError(f"Could not save the cache to {self._path}: {error}") from error


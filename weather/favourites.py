"""Favourite places, saved in a JSON file so they're remembered between runs."""

from __future__ import annotations

import json
from pathlib import Path

from .exceptions import PlaceNotFoundError, StorageError, ValidationError
from .files import write_safely
from .models import Location
from .serialise import location_from_dict, location_to_dict


class Favourites:
    """A short list of places. The first one is the home place, used when
    no place is named."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def all(self) -> list[Location]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as error:
            raise StorageError(f"Could not read {self._path}: {error}") from error
        try:
            return [location_from_dict(item) for item in data]
        except (KeyError, TypeError, ValidationError) as error:
            raise StorageError(f"{self._path} is damaged: {error}") from error

    def add(self, place: Location) -> bool:
        """Save a place. Returns False if it was already saved."""
        places = self.all()
        if any(p.key == place.key for p in places):
            return False
        self._save([*places, place])
        return True

    def remove(self, name: str) -> Location:
        place = self.find(name)
        self._save([p for p in self.all() if p.key != place.key])
        return place

    def find(self, name: str) -> Location:
        """A saved place by name. Case doesn't matter."""
        wanted = str(name).strip().lower()
        for place in self.all():
            if place.name.lower() == wanted:
                return place
        raise PlaceNotFoundError(f"{name!r} isn't one of your saved places.")

    @property
    def home(self) -> Location | None:
        places = self.all()
        return places[0] if places else None

    def set_home(self, name: str) -> Location:
        """Move a saved place to the top of the list."""
        place = self.find(name)
        self._save([place, *[p for p in self.all() if p.key != place.key]])
        return place

    def _save(self, places: list[Location]) -> None:
        try:
            write_safely(self._path, json.dumps([location_to_dict(p) for p in places],
                                                 indent=2, ensure_ascii=False))
        except OSError as error:
            raise StorageError(f"Could not save {self._path}: {error}") from error

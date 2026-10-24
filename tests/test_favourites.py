"""Tests for favourite places."""

from __future__ import annotations

import pytest

from weather import Favourites, Location, PlaceNotFoundError, StorageError

from .conftest import BROMLEY

PARIS = Location("Paris", 48.85, 2.35, "France", "Ile-de-France", "Europe/Paris")
HARARE = Location("Harare", -17.83, 31.05, "Zimbabwe", "Harare", "Africa/Harare")


@pytest.fixture
def favourites(tmp_path) -> Favourites:
    return Favourites(tmp_path / "places.json")


def test_starts_empty(favourites):
    assert favourites.all() == []
    assert favourites.home is None


def test_add_and_keep_order(favourites):
    assert favourites.add(BROMLEY)
    assert favourites.add(PARIS)
    assert favourites.all() == [BROMLEY, PARIS]
    assert favourites.home == BROMLEY


def test_same_place_twice(favourites):
    favourites.add(BROMLEY)
    assert not favourites.add(BROMLEY)
    assert len(favourites.all()) == 1


def test_find_and_remove_ignore_case(favourites):
    favourites.add(BROMLEY)
    favourites.add(PARIS)
    assert favourites.find("PARIS") == PARIS
    assert favourites.remove(" bromley ") == BROMLEY
    assert favourites.all() == [PARIS]


def test_unknown_place(favourites):
    with pytest.raises(PlaceNotFoundError, match="saved places"):
        favourites.remove("Atlantis")


def test_set_home_moves_it_to_the_top(favourites):
    for place in (BROMLEY, PARIS, HARARE):
        favourites.add(place)
    favourites.set_home("Harare")
    assert favourites.all() == [HARARE, BROMLEY, PARIS]


def test_saved_between_runs(tmp_path):
    Favourites(tmp_path / "p.json").add(HARARE)
    assert Favourites(tmp_path / "p.json").home == HARARE


@pytest.mark.parametrize("text, message", [
    ("not json", "Could not read"),
    ('[{"name": "X"}]', "damaged"),
    ('[{"name": "X", "latitude": 500, "longitude": 0}]', "damaged"),
])
def test_damaged_file(tmp_path, text, message):
    path = tmp_path / "p.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(StorageError, match=message):
        Favourites(path).all()


def test_cannot_save(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(StorageError, match="Could not"):
        Favourites(blocker / "p.json").add(BROMLEY)


def test_cannot_save_into_a_read_only_spot(tmp_path, monkeypatch):
    import os

    def broken(*args):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", broken)
    with pytest.raises(StorageError, match="Could not save"):
        Favourites(tmp_path / "p.json").add(BROMLEY)


def test_path(favourites):
    assert favourites.path.name == "places.json"

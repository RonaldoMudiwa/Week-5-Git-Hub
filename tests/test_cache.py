"""Tests for the caches. Both kinds must behave the same way."""

from __future__ import annotations

import os
from datetime import timedelta

import pytest

from weather import FileCache, MemoryCache, StorageError

TEN_MINUTES = timedelta(minutes=10)


@pytest.fixture(params=["memory", "file"])
def cache(request, clock, tmp_path):
    if request.param == "memory":
        return MemoryCache(clock)
    return FileCache(tmp_path / "cache.json", clock)


class TestEveryCache:
    def test_empty(self, cache):
        assert cache.get("missing") is None

    def test_set_and_get(self, cache):
        cache.set("a", {"temp": 12.5, "days": [1, 2]}, TEN_MINUTES)
        assert cache.get("a") == {"temp": 12.5, "days": [1, 2]}

    def test_entries_run_out(self, cache, clock):
        cache.set("a", 1, TEN_MINUTES)
        clock.advance(minutes=9, seconds=59)
        assert cache.get("a") == 1
        clock.advance(seconds=1)
        assert cache.get("a") is None

    def test_old_entries_can_still_be_asked_for(self, cache, clock):
        cache.set("a", 1, TEN_MINUTES)
        clock.advance(days=1)
        assert cache.get("a", allow_expired=True) == 1

    def test_setting_again_replaces(self, cache):
        cache.set("a", 1, TEN_MINUTES)
        cache.set("a", 2, TEN_MINUTES)
        assert cache.get("a") == 2

    def test_clear(self, cache):
        cache.set("a", 1, TEN_MINUTES)
        cache.set("b", 2, TEN_MINUTES)
        assert cache.clear() == 2
        assert cache.get("a") is None
        assert cache.clear() == 0


class TestFileCache:
    def test_lasts_between_runs(self, tmp_path, clock):
        FileCache(tmp_path / "c.json", clock).set("a", "hello", TEN_MINUTES)
        assert FileCache(tmp_path / "c.json", clock).get("a") == "hello"

    @pytest.mark.parametrize("text", ["not json", "[1, 2]", '{"a": "no expiry"}',
                                      '{"a": {"expires": "soon", "value": 1}}',
                                      '{"a": {"value": 1}}'])
    def test_damaged_file_counts_as_empty(self, tmp_path, clock, text):
        path = tmp_path / "c.json"
        path.write_text(text, encoding="utf-8")
        cache = FileCache(path, clock)
        assert cache.get("a") is None
        cache.set("b", 1, TEN_MINUTES)    # and it can be used again
        assert cache.get("b") == 1

    def test_cannot_save(self, tmp_path, clock):
        blocker = tmp_path / "file"
        blocker.write_text("in the way", encoding="utf-8")
        with pytest.raises(StorageError, match="Could not save"):
            FileCache(blocker / "c.json", clock).set("a", 1, TEN_MINUTES)

    def test_failed_save_leaves_no_temp_file(self, tmp_path, clock, monkeypatch):
        cache = FileCache(tmp_path / "c.json", clock)

        def broken(*args):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", broken)
        with pytest.raises(StorageError):
            cache.set("a", 1, TEN_MINUTES)
        assert list(tmp_path.iterdir()) == []

    def test_path(self, tmp_path):
        assert FileCache(tmp_path / "c.json").path.name == "c.json"


def test_default_clocks_work():
    MemoryCache().set("a", 1, TEN_MINUTES)

"""Tests for the provider that remembers answers."""

from __future__ import annotations

from datetime import timedelta

import pytest

from weather import CachedProvider, MemoryCache, NetworkError, OpenMeteoProvider, WeatherProvider

from .conftest import BROMLEY
from .sample_data import GEOCODING, FakeHttpClient, forecast_json

GEO = OpenMeteoProvider.GEOCODING_URL
FORECAST = OpenMeteoProvider.FORECAST_URL


@pytest.fixture
def http():
    return FakeHttpClient({GEO: GEOCODING, FORECAST: forecast_json()})


@pytest.fixture
def cached(http, clock) -> CachedProvider:
    return CachedProvider(OpenMeteoProvider(http, clock), MemoryCache(clock))


def forecast_calls(http) -> int:
    return sum(1 for url, _ in http.calls if url == FORECAST)


def test_it_is_still_a_provider(cached):
    assert isinstance(cached, WeatherProvider)


def test_second_forecast_comes_from_the_cache(cached, http):
    first = cached.forecast(BROMLEY)
    second = cached.forecast(BROMLEY)
    assert first == second
    assert forecast_calls(http) == 1


def test_forecast_is_fetched_again_after_15_minutes(cached, http, clock):
    cached.forecast(BROMLEY)
    clock.advance(minutes=15)
    cached.forecast(BROMLEY)
    assert forecast_calls(http) == 2


def test_different_places_and_lengths_are_kept_apart(cached, http):
    from weather import Location

    cached.forecast(BROMLEY, 7)
    cached.forecast(BROMLEY, 3)
    cached.forecast(Location("Paris", 48.85, 2.35))
    assert forecast_calls(http) == 3


def test_place_searches_are_kept_for_30_days(cached, http, clock):
    first = cached.find_places("Bromley")
    clock.advance(days=29)
    assert cached.find_places(" BROMLEY ") == first
    assert len([c for c in http.calls if c[0] == GEO]) == 1
    assert cached.find_place("Bromley") == first[0]   # limit 1 is a separate search


def test_empty_searches_are_remembered_too(clock):
    http = FakeHttpClient({GEO: {}})
    cached = CachedProvider(OpenMeteoProvider(http, clock), MemoryCache(clock))
    assert cached.find_places("Zzzz") == []
    assert cached.find_places("Zzzz") == []
    assert len(http.calls) == 1


def test_offline_falls_back_to_an_old_forecast(cached, http, clock):
    fresh = cached.forecast(BROMLEY)
    clock.advance(hours=3)
    http.answers[FORECAST] = NetworkError("offline")
    old = cached.forecast(BROMLEY)
    assert old == fresh
    assert clock.now - old.fetched_at >= timedelta(hours=3)


def test_offline_with_nothing_saved_still_fails(cached, http):
    http.answers[FORECAST] = NetworkError("offline")
    with pytest.raises(NetworkError):
        cached.forecast(BROMLEY)


def test_custom_lifetimes(http, clock):
    cached = CachedProvider(OpenMeteoProvider(http, clock), MemoryCache(clock),
                            forecast_lifetime=timedelta(minutes=1))
    cached.forecast(BROMLEY)
    clock.advance(minutes=1)
    cached.forecast(BROMLEY)
    assert forecast_calls(http) == 2

"""Saved answers from Open-Meteo, so tests never need the internet.

They have the same shape as the real thing, cut down to three days.
"""

from __future__ import annotations

import copy

from weather import HttpClient

GEOCODING = {
    "results": [
        {"id": 2654971, "name": "Bromley", "latitude": 51.40606, "longitude": 0.01519,
         "elevation": 59.0, "feature_code": "PPLA2", "country_code": "GB",
         "timezone": "Europe/London", "country": "United Kingdom", "admin1": "England",
         "admin2": "Greater London"},
        {"id": 2172797, "name": "Bromley", "latitude": -27.5, "longitude": 153.0,
         "country": "Australia", "admin1": "Queensland", "timezone": "Australia/Brisbane"},
    ],
    "generationtime_ms": 0.7,
}

NO_PLACES = {"generationtime_ms": 0.4}

FORECAST = {
    "latitude": 51.4, "longitude": 0.02, "timezone": "Europe/London", "elevation": 59.0,
    "current_units": {"time": "iso8601", "temperature_2m": "°C"},
    "current": {
        "time": "2026-10-22T09:00", "interval": 900, "temperature_2m": 12.3,
        "apparent_temperature": 10.9, "relative_humidity_2m": 81, "precipitation": 0.0,
        "weather_code": 3, "wind_speed_10m": 14.2, "wind_direction_10m": 225,
    },
    "daily_units": {"time": "iso8601", "temperature_2m_max": "°C"},
    "daily": {
        "time": ["2026-10-22", "2026-10-23", "2026-10-24"],
        "weather_code": [3, 63, 1],
        "temperature_2m_max": [14.1, 12.8, 15.6],
        "temperature_2m_min": [7.2, 8.9, 5.4],
        "precipitation_sum": [0.0, 8.4, None],
        "precipitation_probability_max": [10, 90, None],
        "wind_speed_10m_max": [18.0, 32.5, 12.1],
        "sunrise": ["2026-10-22T07:33", "2026-10-23T07:35", "2026-10-24T07:36"],
        "sunset": ["2026-10-22T17:50", "2026-10-23T17:48", "2026-10-24T17:46"],
    },
}


def forecast_json() -> dict:
    """A fresh copy, so a test that edits it can't spoil the next test."""
    return copy.deepcopy(FORECAST)


class FakeHttpClient(HttpClient):
    """Hands back saved answers instead of going online, and remembers
    every request so tests can check what was asked for."""

    def __init__(self, answers: dict | None = None) -> None:
        # Maps a url to an answer, or to an exception to raise.
        self.answers = answers or {}
        self.calls: list[tuple[str, dict]] = []

    def get_json(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        answer = self.answers[url]
        if isinstance(answer, Exception):
            raise answer
        return copy.deepcopy(answer)

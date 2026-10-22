"""Turning weather code numbers into words.

Weather services describe the sky with a number from the World
Meteorological Organization (WMO) list. 0 means clear sky, 61 means light
rain, 95 means thunderstorm, and so on. This file turns those numbers into
something a person can read.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique


@unique
class Condition(Enum):
    """The broad kind of weather, used for grouping and for alerts."""

    CLEAR = "clear"
    CLOUDY = "cloudy"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    SNOW = "snow"
    STORM = "storm"
    UNKNOWN = "unknown"

    @property
    def is_wet(self) -> bool:
        return self in (Condition.DRIZZLE, Condition.RAIN, Condition.SNOW, Condition.STORM)


@dataclass(frozen=True)
class WeatherCode:
    code: int
    description: str
    condition: Condition

    def __str__(self) -> str:
        return self.description


_C = Condition
_TABLE: dict[int, tuple[str, Condition]] = {
    0: ("Clear sky", _C.CLEAR),
    1: ("Mainly clear", _C.CLEAR),
    2: ("Partly cloudy", _C.CLOUDY),
    3: ("Overcast", _C.CLOUDY),
    45: ("Fog", _C.FOG),
    48: ("Freezing fog", _C.FOG),
    51: ("Light drizzle", _C.DRIZZLE),
    53: ("Drizzle", _C.DRIZZLE),
    55: ("Heavy drizzle", _C.DRIZZLE),
    56: ("Light freezing drizzle", _C.DRIZZLE),
    57: ("Freezing drizzle", _C.DRIZZLE),
    61: ("Light rain", _C.RAIN),
    63: ("Rain", _C.RAIN),
    65: ("Heavy rain", _C.RAIN),
    66: ("Light freezing rain", _C.RAIN),
    67: ("Freezing rain", _C.RAIN),
    71: ("Light snow", _C.SNOW),
    73: ("Snow", _C.SNOW),
    75: ("Heavy snow", _C.SNOW),
    77: ("Snow grains", _C.SNOW),
    80: ("Light showers", _C.RAIN),
    81: ("Showers", _C.RAIN),
    82: ("Violent showers", _C.RAIN),
    85: ("Light snow showers", _C.SNOW),
    86: ("Heavy snow showers", _C.SNOW),
    95: ("Thunderstorm", _C.STORM),
    96: ("Thunderstorm with hail", _C.STORM),
    99: ("Thunderstorm with heavy hail", _C.STORM),
}


def describe(code: int) -> WeatherCode:
    """Look up a WMO code. A code we don't know gives "Unknown" instead of
    crashing, so a new code from the service never breaks the dashboard."""
    if isinstance(code, bool) or not isinstance(code, int):
        return WeatherCode(-1, "Unknown", Condition.UNKNOWN)
    description, condition = _TABLE.get(code, ("Unknown", Condition.UNKNOWN))
    return WeatherCode(code, description, condition)


def known_codes() -> tuple[int, ...]:
    return tuple(_TABLE)

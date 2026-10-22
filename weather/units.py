"""Showing numbers in metric or imperial units.

Everything is stored in metric (Celsius, km/h, millimetres) and only changed
when it's shown. That way there's one set of numbers to get right, and the
units are just a choice of how to print them, like choosing a language.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .exceptions import ValidationError


def celsius_to_fahrenheit(celsius: float) -> float:
    return celsius * 9 / 5 + 32


def kmh_to_mph(kmh: float) -> float:
    return kmh / 1.609344


def mm_to_inches(mm: float) -> float:
    return mm / 25.4


class UnitSystem(ABC):
    """How to show temperatures, speeds and rain amounts."""

    name = ""

    @abstractmethod
    def temperature(self, celsius: float) -> str:
        """e.g. "12°C" """

    @abstractmethod
    def speed(self, kmh: float) -> str:
        """e.g. "14 km/h" """

    @abstractmethod
    def rain(self, mm: float) -> str:
        """e.g. "2.5 mm" """

    @abstractmethod
    def temperature_value(self, celsius: float) -> float:
        """The number on its own, for charts."""


class Metric(UnitSystem):
    name = "metric"

    def temperature(self, celsius: float) -> str:
        return f"{round(celsius)}°C"

    def speed(self, kmh: float) -> str:
        return f"{round(kmh)} km/h"

    def rain(self, mm: float) -> str:
        return f"{mm:.1f} mm"

    def temperature_value(self, celsius: float) -> float:
        return celsius


class Imperial(UnitSystem):
    name = "imperial"

    def temperature(self, celsius: float) -> str:
        return f"{round(celsius_to_fahrenheit(celsius))}°F"

    def speed(self, kmh: float) -> str:
        return f"{round(kmh_to_mph(kmh))} mph"

    def rain(self, mm: float) -> str:
        return f"{mm_to_inches(mm):.2f} in"

    def temperature_value(self, celsius: float) -> float:
        return celsius_to_fahrenheit(celsius)


_SYSTEMS = {cls.name: cls for cls in (Metric, Imperial)}


def unit_system(name: str) -> UnitSystem:
    """Pick units by name: "metric" or "imperial"."""
    try:
        return _SYSTEMS[str(name).strip().lower()]()
    except KeyError:
        raise ValidationError(f"Unknown units {name!r}. Choose metric or imperial.") from None


def compass(degrees: float) -> str:
    """Turn a wind direction in degrees into N, NE, E and so on.

    Weather services give the direction the wind comes FROM, so 225 is a
    south westerly, "SW".
    """
    points = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return points[round((degrees % 360) / 45) % 8]

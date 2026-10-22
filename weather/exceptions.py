"""All the errors this package can raise.

Everything inherits from WeatherError, so one except clause catches the lot.
"""

from __future__ import annotations


class WeatherError(Exception):
    """Base class for every error in this package. Never raised directly."""


class ValidationError(WeatherError):
    """A value isn't allowed, e.g. a latitude of 200."""

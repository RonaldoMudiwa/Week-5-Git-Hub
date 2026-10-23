"""All the errors this package can raise.

Everything inherits from WeatherError, so one except clause catches the lot.
"""

from __future__ import annotations


class WeatherError(Exception):
    """Base class for every error in this package. Never raised directly."""


class ValidationError(WeatherError):
    """A value isn't allowed, e.g. a latitude of 200."""


class NetworkError(WeatherError):
    """The weather service couldn't be reached, e.g. no internet."""


class ApiError(WeatherError):
    """The weather service answered, but with an error or something we can't read."""

    def __init__(self, message: str, status: int | None = None) -> None:
        self.status = status
        super().__init__(message)


class PlaceNotFoundError(WeatherError):
    """No place matches that name."""

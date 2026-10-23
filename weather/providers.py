"""Where forecasts come from.

WeatherProvider is the plug. OpenMeteoProvider is the one we use, but a
different service could be added as another class without changing the
dashboard at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Callable

from .codes import describe
from .exceptions import ApiError, PlaceNotFoundError, ValidationError
from .http import HttpClient, UrllibHttpClient
from .models import CurrentWeather, DailyForecast, Forecast, Location

MAX_DAYS = 16  # the most Open-Meteo forecasts ahead


class WeatherProvider(ABC):
    @abstractmethod
    def find_places(self, name: str, limit: int = 5) -> list[Location]:
        """Places matching a name, best match first. Empty if none."""

    @abstractmethod
    def forecast(self, location: Location, days: int = 7) -> Forecast:
        """The current weather and the next few days for a place."""

    def find_place(self, name: str) -> Location:
        """The best match for a name. Raises PlaceNotFoundError if there's none."""
        places = self.find_places(name, limit=1)
        if not places:
            raise PlaceNotFoundError(f"Couldn't find a place called {name!r}.")
        return places[0]


class OpenMeteoProvider(WeatherProvider):
    """Forecasts from open-meteo.com. Free, with no key needed."""

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    CURRENT_FIELDS = ("temperature_2m", "apparent_temperature", "relative_humidity_2m",
                      "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m")
    DAILY_FIELDS = ("weather_code", "temperature_2m_max", "temperature_2m_min",
                    "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max",
                    "sunrise", "sunset")

    def __init__(self, http: HttpClient | None = None,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._http = http or UrllibHttpClient()
        self._clock = clock or datetime.now

    def find_places(self, name: str, limit: int = 5) -> list[Location]:
        if not isinstance(name, str) or len(name.strip()) < 2:
            raise ValidationError("Type at least 2 letters of a place name.")
        data = self._http.get_json(self.GEOCODING_URL, {
            "name": name.strip(), "count": limit, "language": "en", "format": "json"})
        # No matches means the "results" key is missing altogether.
        results = (data.get("results") or []) if isinstance(data, dict) else []
        try:
            return [Location(r["name"], r["latitude"], r["longitude"], r.get("country", ""),
                             r.get("admin1", ""), r.get("timezone", "auto")) for r in results]
        except (KeyError, TypeError, ValidationError) as error:
            raise ApiError(f"The place search sent something unexpected: {error}") from None

    def forecast(self, location: Location, days: int = 7) -> Forecast:
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= MAX_DAYS:
            raise ValidationError(f"Days must be between 1 and {MAX_DAYS}.")
        data = self._http.get_json(self.FORECAST_URL, {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": list(self.CURRENT_FIELDS),
            "daily": list(self.DAILY_FIELDS),
            "timezone": location.timezone or "auto",
            "forecast_days": days,
        })
        try:
            return parse_forecast(data, location, self._clock())
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise ApiError(f"The forecast had something unexpected in it: {error!r}") from None


def parse_forecast(data: dict[str, Any], location: Location, fetched_at: datetime) -> Forecast:
    """Turn Open-Meteo's JSON into a Forecast.

    The daily part comes as one list per field, like columns in a
    spreadsheet: all the dates, then all the highs, and so on. zip() reads
    across them a row (one day) at a time.
    """
    now = data["current"]
    current = CurrentWeather(
        time=datetime.fromisoformat(now["time"]),
        code=describe(now["weather_code"]),
        temperature=now["temperature_2m"],
        feels_like=now["apparent_temperature"],
        humidity=now["relative_humidity_2m"],
        wind_speed=now["wind_speed_10m"],
        wind_direction=now["wind_direction_10m"],
        precipitation=now.get("precipitation") or 0.0,
    )

    daily = data["daily"]
    columns = zip(daily["time"], daily["weather_code"], daily["temperature_2m_max"],
                  daily["temperature_2m_min"], daily["precipitation_probability_max"],
                  daily["precipitation_sum"], daily["wind_speed_10m_max"],
                  daily["sunrise"], daily["sunset"])
    days = []
    for day, code, high, low, chance, rain, wind, sunrise, sunset in columns:
        days.append(DailyForecast(
            day=date.fromisoformat(day),
            code=describe(code),
            high=high,
            low=low,
            # Missing values come back as null, so treat them as zero.
            rain_chance=chance or 0,
            rain_total=rain or 0.0,
            wind_max=wind or 0.0,
            sunrise=datetime.fromisoformat(sunrise) if sunrise else None,
            sunset=datetime.fromisoformat(sunset) if sunset else None,
        ))
    return Forecast(location, current, days, fetched_at)

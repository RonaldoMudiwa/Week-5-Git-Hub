"""The weather data itself: places, current conditions and forecasts.

Every class here is frozen, like a printed weather report. Once made it
can't be changed, so the dashboard can never show half updated numbers.
All values are metric. units.py decides how they're shown.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .codes import WeatherCode
from .exceptions import ValidationError


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {value!r}.")
    return float(value)


@dataclass(frozen=True)
class Location:
    """A place on the map."""

    name: str
    latitude: float
    longitude: float
    country: str = ""
    region: str = ""
    timezone: str = "auto"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("A place needs a name.")
        object.__setattr__(self, "name", self.name.strip())
        latitude = _number(self.latitude, "Latitude")
        longitude = _number(self.longitude, "Longitude")
        if not -90 <= latitude <= 90:
            raise ValidationError(f"Latitude must be between -90 and 90, got {latitude}.")
        if not -180 <= longitude <= 180:
            raise ValidationError(f"Longitude must be between -180 and 180, got {longitude}.")
        object.__setattr__(self, "latitude", latitude)
        object.__setattr__(self, "longitude", longitude)

    @property
    def label(self) -> str:
        """e.g. "Bromley, England, United Kingdom". Repeats are skipped."""
        parts = [self.name]
        for part in (self.region, self.country):
            if part and part not in parts:
                parts.append(part)
        return ", ".join(parts)

    @property
    def key(self) -> str:
        """A short id for the place, e.g. "51.41,0.02". About 1 km accuracy,
        which is plenty for weather."""
        return f"{self.latitude:.2f},{self.longitude:.2f}"

    def __str__(self) -> str:
        return self.label


@dataclass(frozen=True)
class CurrentWeather:
    """What it's like outside right now."""

    time: datetime
    code: WeatherCode
    temperature: float          # °C
    feels_like: float           # °C
    humidity: int               # %
    wind_speed: float           # km/h
    wind_direction: float       # degrees the wind comes from
    precipitation: float = 0.0  # mm in the last hour

    def __post_init__(self) -> None:
        if not isinstance(self.time, datetime):
            raise ValidationError("time must be a datetime.")
        for name in ("temperature", "feels_like", "wind_speed", "wind_direction", "precipitation"):
            object.__setattr__(self, name, _number(getattr(self, name), name))
        if not 0 <= _number(self.humidity, "humidity") <= 100:
            raise ValidationError("Humidity must be between 0 and 100.")
        if self.wind_speed < 0 or self.precipitation < 0:
            raise ValidationError("Wind and rain can't be negative.")


@dataclass(frozen=True)
class DailyForecast:
    """The forecast for one day."""

    day: date
    code: WeatherCode
    high: float                 # °C
    low: float                  # °C
    rain_chance: int            # % chance of rain
    rain_total: float           # mm expected
    wind_max: float             # km/h
    sunrise: datetime | None = None
    sunset: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.day, date) or isinstance(self.day, datetime):
            raise ValidationError("day must be a date.")
        for name in ("high", "low", "rain_total", "wind_max"):
            object.__setattr__(self, name, _number(getattr(self, name), name))
        if self.low > self.high:
            raise ValidationError(f"Low {self.low} is above high {self.high} on {self.day}.")
        if not 0 <= _number(self.rain_chance, "rain_chance") <= 100:
            raise ValidationError("Rain chance must be between 0 and 100.")

    @property
    def daylight_hours(self) -> float | None:
        if self.sunrise is None or self.sunset is None:
            return None
        return round((self.sunset - self.sunrise).total_seconds() / 3600, 1)


@dataclass(frozen=True)
class Forecast:
    """Everything known about one place: now, and the days ahead."""

    location: Location
    current: CurrentWeather
    days: tuple[DailyForecast, ...]
    fetched_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "days", tuple(self.days))
        if not self.days:
            raise ValidationError("A forecast needs at least one day.")
        dates = [d.day for d in self.days]
        if dates != sorted(set(dates)):
            raise ValidationError("Forecast days must be in order with no repeats.")

    @property
    def today(self) -> DailyForecast:
        return self.days[0]

    @property
    def warmest(self) -> DailyForecast:
        return max(self.days, key=lambda d: d.high)

    @property
    def coldest(self) -> DailyForecast:
        return min(self.days, key=lambda d: d.low)

    @property
    def wettest(self) -> DailyForecast:
        return max(self.days, key=lambda d: (d.rain_total, d.rain_chance))

    @property
    def total_rain(self) -> float:
        return round(sum(d.rain_total for d in self.days), 1)

    def dry_days(self, max_chance: int = 30) -> list[DailyForecast]:
        """Days with a low chance of rain. Handy for planning a day out."""
        return [d for d in self.days if d.rain_chance <= max_chance]

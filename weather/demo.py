"""A made up week of weather, for trying the dashboard without the internet."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .codes import describe
from .models import CurrentWeather, DailyForecast, Forecast, Location

DEMO_PLACE = Location("Bromley", 51.406, 0.015, "United Kingdom", "England", "Europe/London")

# code, high, low, rain chance, rain mm, wind km/h
_WEEK = [
    (3, 14.1, 7.2, 20, 0.0, 18.0),
    (63, 12.8, 8.9, 90, 12.4, 55.0),
    (1, 15.6, -1.0, 0, 0.0, 12.1),
    (95, 17.9, 9.3, 70, 3.0, 30.4),
    (2, 11.2, 4.1, 30, 0.5, 21.0),
    (0, 9.4, 1.8, 10, 0.0, 14.6),
    (61, 12.0, 6.2, 60, 2.1, 25.3),
]


def demo_forecast(now: datetime | None = None) -> Forecast:
    """A seven day forecast starting today, so the day names look right."""
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    today = now.date()
    days = [_day(today + timedelta(days=n), *values) for n, values in enumerate(_WEEK)]
    current = CurrentWeather(now, describe(3), 12.3, 10.9, 81, 14.2, 225.0, 0.0)
    return Forecast(DEMO_PLACE, current, days, now)


def _day(day: date, code: int, high: float, low: float, chance: int, rain: float,
         wind: float) -> DailyForecast:
    morning = datetime.combine(day, datetime.min.time())
    return DailyForecast(day, describe(code), high, low, chance, rain, wind,
                         morning + timedelta(hours=7, minutes=33),
                         morning + timedelta(hours=16, minutes=50))

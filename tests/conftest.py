"""Shared test helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from weather import CurrentWeather, DailyForecast, Forecast, Location, describe

BROMLEY = Location("Bromley", 51.406, 0.015, "United Kingdom", "England", "Europe/London")


def make_day(day: date, high: float = 14, low: float = 7, code: int = 3, rain_chance: int = 20,
             rain_total: float = 0.0, wind_max: float = 18) -> DailyForecast:
    return DailyForecast(day, describe(code), high, low, rain_chance, rain_total, wind_max,
                         datetime.combine(day, datetime.min.time()) + timedelta(hours=7, minutes=30),
                         datetime.combine(day, datetime.min.time()) + timedelta(hours=17, minutes=45))


def make_forecast(days=None, location=BROMLEY, temperature=12.0, code=3) -> Forecast:
    start = date(2026, 10, 22)
    days = days or [make_day(start + timedelta(days=n)) for n in range(7)]
    current = CurrentWeather(datetime(2026, 10, 22, 9, 0), describe(code), temperature,
                             temperature - 2, 80, 14.0, 225.0, 0.0)
    return Forecast(location, current, days, datetime(2026, 10, 22, 9, 5))


@pytest.fixture
def forecast() -> Forecast:
    return make_forecast()


class FakeClock:
    """A clock the tests control, so cache expiry can be tested without waiting."""

    def __init__(self, start: datetime = datetime(2026, 10, 22, 9, 0)) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()

"""Tests for places, current weather and forecasts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta

import pytest

from weather import CurrentWeather, DailyForecast, Forecast, Location, ValidationError, describe

from .conftest import BROMLEY, make_day, make_forecast

OCT_22 = date(2026, 10, 22)


class TestLocation:
    def test_label_skips_repeats_and_blanks(self):
        assert BROMLEY.label == "Bromley, England, United Kingdom"
        assert Location("Singapore", 1.29, 103.85, "Singapore").label == "Singapore"
        assert Location("Somewhere", 0, 0).label == "Somewhere"
        assert str(BROMLEY) == BROMLEY.label

    def test_key(self):
        assert BROMLEY.key == "51.41,0.01"

    @pytest.mark.parametrize("kwargs", [
        {"name": "", "latitude": 0, "longitude": 0},
        {"name": "X", "latitude": 91, "longitude": 0},
        {"name": "X", "latitude": 0, "longitude": -181},
        {"name": "X", "latitude": "51", "longitude": 0},
        {"name": "X", "latitude": True, "longitude": 0},
    ])
    def test_bad_places(self, kwargs):
        with pytest.raises(ValidationError):
            Location(**kwargs)

    def test_frozen(self):
        with pytest.raises(FrozenInstanceError):
            BROMLEY.name = "Elsewhere"


class TestCurrentWeather:
    def make(self, **changes):
        details = {"time": datetime(2026, 10, 22, 9), "code": describe(3), "temperature": 12,
                   "feels_like": 10, "humidity": 80, "wind_speed": 14, "wind_direction": 225}
        details.update(changes)
        return CurrentWeather(**details)

    def test_whole_numbers_become_floats(self):
        assert self.make().temperature == 12.0

    @pytest.mark.parametrize("changes", [
        {"humidity": 120}, {"humidity": -1}, {"wind_speed": -2}, {"precipitation": -0.1},
        {"time": "2026-10-22"}, {"temperature": "warm"},
    ])
    def test_bad_values(self, changes):
        with pytest.raises(ValidationError):
            self.make(**changes)


class TestDailyForecast:
    def test_daylight(self):
        assert make_day(OCT_22).daylight_hours == 10.2
        assert DailyForecast(OCT_22, describe(0), 10, 5, 0, 0, 5).daylight_hours is None

    @pytest.mark.parametrize("changes", [
        {"low": 20}, {"rain_chance": 101}, {"rain_chance": -5},
        {"day": datetime(2026, 10, 22)}, {"day": "2026-10-22"}, {"wind_max": None},
    ])
    def test_bad_values(self, changes):
        details = {"day": OCT_22, "code": describe(3), "high": 14, "low": 7, "rain_chance": 20,
                   "rain_total": 0, "wind_max": 10}
        details.update(changes)
        with pytest.raises(ValidationError):
            DailyForecast(**details)


class TestForecast:
    def days(self):
        return [
            make_day(OCT_22, high=14, low=7, rain_chance=10),
            make_day(OCT_22 + timedelta(days=1), high=17, low=9, rain_chance=80, rain_total=6.5),
            make_day(OCT_22 + timedelta(days=2), high=11, low=2, rain_chance=40, rain_total=1.2),
        ]

    def test_summary_numbers(self):
        forecast = make_forecast(self.days())
        assert forecast.today.day == OCT_22
        assert forecast.warmest.high == 17
        assert forecast.coldest.low == 2
        assert forecast.wettest.rain_total == 6.5
        assert forecast.total_rain == 7.7
        assert [d.day.day for d in forecast.dry_days()] == [22]
        assert len(forecast.dry_days(max_chance=50)) == 2

    def test_days_must_be_in_order_without_repeats(self):
        days = self.days()
        with pytest.raises(ValidationError):
            make_forecast([days[1], days[0]])
        with pytest.raises(ValidationError):
            make_forecast([days[0], days[0]])

    def test_needs_a_day(self, forecast):
        with pytest.raises(ValidationError):
            Forecast(BROMLEY, forecast.current, [], forecast.fetched_at)

    def test_days_become_a_tuple(self, forecast):
        assert isinstance(forecast.days, tuple)
        assert len(forecast.days) == 7

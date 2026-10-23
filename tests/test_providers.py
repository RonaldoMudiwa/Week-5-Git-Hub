"""Tests for getting places and forecasts from Open-Meteo, using saved answers."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from weather import (
    ApiError,
    Condition,
    Location,
    NetworkError,
    OpenMeteoProvider,
    PlaceNotFoundError,
    ValidationError,
    WeatherProvider,
)

from .conftest import BROMLEY
from .sample_data import GEOCODING, NO_PLACES, FakeHttpClient, forecast_json

GEO = OpenMeteoProvider.GEOCODING_URL
FORECAST = OpenMeteoProvider.FORECAST_URL


def provider(clock=None, **answers) -> tuple[OpenMeteoProvider, FakeHttpClient]:
    http = FakeHttpClient({GEO: answers.get("geo", GEOCODING),
                           FORECAST: answers.get("forecast", forecast_json())})
    return OpenMeteoProvider(http, clock), http


class TestFindingPlaces:
    def test_results_become_locations(self):
        weather, http = provider()
        places = weather.find_places("Bromley")
        assert [p.label for p in places] == ["Bromley, England, United Kingdom",
                                             "Bromley, Queensland, Australia"]
        assert places[0].timezone == "Europe/London"
        assert http.calls == [(GEO, {"name": "Bromley", "count": 5, "language": "en",
                                     "format": "json"})]

    def test_find_place_takes_the_best_match(self):
        weather, http = provider()
        assert weather.find_place(" bromley ").country == "United Kingdom"
        assert http.calls[0][1]["count"] == 1

    def test_no_matches(self):
        weather, _ = provider(geo=NO_PLACES)
        assert weather.find_places("Zzzzz") == []
        with pytest.raises(PlaceNotFoundError, match="Zzzzz"):
            weather.find_place("Zzzzz")

    @pytest.mark.parametrize("name", ["", " x ", None])
    def test_name_too_short(self, name):
        weather, http = provider()
        with pytest.raises(ValidationError):
            weather.find_places(name)
        assert http.calls == []

    @pytest.mark.parametrize("answer", [
        {"results": [{"name": "Nowhere"}]},
        {"results": [{"name": "Bad", "latitude": 400, "longitude": 0}]},
        {"results": ["not a dict"]},
    ])
    def test_strange_answers(self, answer):
        weather, _ = provider(geo=answer)
        with pytest.raises(ApiError):
            weather.find_places("Bromley")

    def test_answer_that_is_not_an_object(self):
        weather, _ = provider(geo=["unexpected"])
        assert weather.find_places("Bromley") == []


class TestForecast:
    def test_current_weather(self, clock):
        weather, _ = provider(clock)
        now = weather.forecast(BROMLEY).current
        assert now.time == datetime(2026, 10, 22, 9, 0)
        assert (now.temperature, now.feels_like, now.humidity) == (12.3, 10.9, 81)
        assert now.code.description == "Overcast"
        assert now.wind_direction == 225

    def test_daily_columns_become_days(self):
        weather, _ = provider()
        days = weather.forecast(BROMLEY).days
        assert [d.day for d in days] == [date(2026, 10, 22), date(2026, 10, 23), date(2026, 10, 24)]
        rainy = days[1]
        assert (rainy.high, rainy.low, rainy.rain_chance, rainy.rain_total) == (12.8, 8.9, 90, 8.4)
        assert rainy.code.condition is Condition.RAIN
        assert rainy.sunrise == datetime(2026, 10, 23, 7, 35)

    def test_missing_values_count_as_zero(self):
        weather, _ = provider()
        last = weather.forecast(BROMLEY).days[2]
        assert (last.rain_chance, last.rain_total) == (0, 0.0)

    def test_missing_sunrise(self):
        data = forecast_json()
        data["daily"]["sunrise"][0] = None
        weather, _ = provider(forecast=data)
        assert weather.forecast(BROMLEY).today.daylight_hours is None

    def test_fetched_at_uses_the_clock(self, clock):
        weather, _ = provider(clock)
        assert weather.forecast(BROMLEY).fetched_at == clock.now

    def test_request_asks_for_the_right_things(self):
        weather, http = provider()
        weather.forecast(BROMLEY, days=3)
        url, params = http.calls[0]
        assert url == FORECAST
        assert (params["latitude"], params["longitude"]) == (51.406, 0.015)
        assert params["forecast_days"] == 3
        assert params["timezone"] == "Europe/London"
        assert "temperature_2m_max" in params["daily"]

    @pytest.mark.parametrize("days", [0, 17, "7", True])
    def test_days_must_be_sensible(self, days):
        weather, http = provider()
        with pytest.raises(ValidationError):
            weather.forecast(BROMLEY, days)
        assert http.calls == []

    @pytest.mark.parametrize("damage", [
        lambda d: d.pop("current"),
        lambda d: d["daily"].pop("temperature_2m_max"),
        lambda d: d["current"].update(time="yesterday"),
        lambda d: d["daily"].update(time=None),
    ])
    def test_damaged_answers_become_api_errors(self, damage):
        data = forecast_json()
        damage(data)
        weather, _ = provider(forecast=data)
        with pytest.raises(ApiError, match="unexpected"):
            weather.forecast(BROMLEY)

    def test_network_errors_pass_through(self):
        weather, _ = provider(forecast=NetworkError("offline"))
        with pytest.raises(NetworkError):
            weather.forecast(BROMLEY)


def test_a_new_provider_only_needs_two_methods():
    class StubProvider(WeatherProvider):
        def find_places(self, name, limit=5):
            return [Location("Testville", 1, 2)]

        def forecast(self, location, days=7):
            raise NotImplementedError

    assert StubProvider().find_place("anything").name == "Testville"


def test_default_setup():
    assert isinstance(OpenMeteoProvider(), WeatherProvider)

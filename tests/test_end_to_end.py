"""Whole program tests: every part working together, from the saved API
answers all the way to the finished dashboard."""

from __future__ import annotations

import io
from datetime import datetime

import pytest

from weather import (
    AlertChecker,
    CachedProvider,
    FileCache,
    HtmlDashboard,
    Imperial,
    NetworkError,
    OpenMeteoProvider,
    TextDashboard,
    forecast_from_dict,
    forecast_to_dict,
)
from weather.cli import main

from .conftest import FakeClock
from .sample_data import GEOCODING, FakeHttpClient, forecast_json

GEO = OpenMeteoProvider.GEOCODING_URL
FORECAST = OpenMeteoProvider.FORECAST_URL


@pytest.fixture
def http() -> FakeHttpClient:
    return FakeHttpClient({GEO: GEOCODING, FORECAST: forecast_json()})


def run_cli(tmp_path, http, clock, *argv) -> tuple[int, str]:
    out = io.StringIO()
    code = main(["--data", str(tmp_path), *argv], out=out,
                provider=OpenMeteoProvider(http, clock=clock), clock=clock)
    return code, out.getvalue()


def test_offline_shows_the_last_saved_forecast(tmp_path, http, clock):
    # Online at 9am, then the internet goes down and two hours pass.
    assert run_cli(tmp_path, http, clock, "forecast", "Bromley")[0] == 0
    http.answers[FORECAST] = NetworkError("No internet.")
    clock.advance(hours=2)

    code, text = run_cli(tmp_path, http, clock, "forecast", "Bromley")

    assert code == 0
    assert "Updated 2 hours ago (saved copy, may be out of date)" in text
    assert "Bromley, England, United Kingdom" in text


def test_offline_with_nothing_saved_is_one_clear_line(tmp_path, http, clock):
    http.answers[FORECAST] = NetworkError("No internet.")
    code, text = run_cli(tmp_path, http, clock, "now", "Bromley")
    assert code == 1
    assert text.strip() == "Error: No internet."


def test_saved_forecast_draws_exactly_the_same(tmp_path, http, clock):
    # A forecast that went through the cache file must look no different.
    provider = OpenMeteoProvider(http, clock=clock)
    fresh = provider.forecast(provider.find_place("Bromley"), days=3)
    cached = CachedProvider(provider, FileCache(tmp_path / "cache.json", clock=clock))
    cached.forecast(fresh.location, days=3)
    from_file = cached.forecast(fresh.location, days=3)

    dashboard = TextDashboard(clock=clock)
    alerts = AlertChecker()
    assert from_file == fresh
    assert (dashboard.render(from_file, alerts.check(from_file))
            == dashboard.render(fresh, alerts.check(fresh)))
    assert forecast_from_dict(forecast_to_dict(fresh)) == fresh


def test_text_and_html_show_the_same_alerts(http, clock):
    stormy = forecast_json()
    stormy["daily"]["precipitation_sum"][1] = 14.0
    stormy["daily"]["temperature_2m_min"][2] = -2.0
    http.answers[FORECAST] = stormy
    provider = OpenMeteoProvider(http, clock=clock)
    forecast = provider.forecast(provider.find_place("Bromley"), days=3)
    alerts = AlertChecker().check(forecast)
    assert [a.title for a in alerts] == ["Heavy rain", "Frost"]

    text = TextDashboard(clock=clock).render(forecast, alerts)
    html = HtmlDashboard(clock=clock).render(forecast, alerts)
    for alert in alerts:
        assert alert.title in text and alert.title in html


@pytest.mark.parametrize("units", [None, Imperial()])
def test_both_dashboards_work_in_both_units(http, clock, units):
    provider = OpenMeteoProvider(http, clock=clock)
    forecast = provider.forecast(provider.find_place("Bromley"), days=3)
    text = TextDashboard(clock=clock).render(forecast, units=units)
    html = HtmlDashboard(clock=clock).render(forecast, units=units)
    symbol = "°F" if units else "°C"
    assert symbol in text and symbol in html


def test_a_whole_session(tmp_path, http):
    # The kind of thing a person would actually type, one after another.
    clock = FakeClock(datetime(2026, 10, 22, 9, 0))
    steps = [
        (("places",), "No saved places yet"),
        (("save", "Bromley"), "Saved Bromley"),
        (("now",), "Bromley, England, United Kingdom: 12°C"),
        (("--units", "imperial", "now"), "54°F"),
        (("forecast", "--days", "3"), "-- This week"),
        (("html",), "Saved"),
        # The place search, plus forecasts for 1, 3 and 7 days.
        (("clear-cache",), "Cleared 4 saved answers."),
        (("remove", "bromley"), "Removed Bromley"),
        (("now",), "no home place saved yet"),
    ]
    for argv, expected in steps:
        clock.advance(minutes=1)
        code, text = run_cli(tmp_path, http, clock, *argv)
        assert expected in text, argv
    assert (tmp_path / "bromley.html").exists()

"""Tests for the text dashboard."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from weather import Alert, AlertChecker, DashboardRenderer, Imperial, Severity, TextDashboard
from weather.dashboard import age_text, day_name, temperature_bar

from .conftest import make_day, make_forecast

DAY = date(2026, 10, 22)


def dashboard(minutes_later: int = 5) -> TextDashboard:
    return TextDashboard(clock=lambda: datetime(2026, 10, 22, 9, 5) + timedelta(minutes=minutes_later))


def week():
    return [
        make_day(DAY, high=14, low=7, rain_chance=20),
        make_day(DAY + timedelta(days=1), high=12.8, low=8.9, code=63, rain_chance=90,
                 rain_total=12.4, wind_max=55),
        make_day(DAY + timedelta(days=2), high=15.6, low=-1, code=1, rain_chance=0),
    ]


@pytest.fixture
def text() -> str:
    forecast = make_forecast(week())
    return dashboard().render(forecast, AlertChecker().check(forecast))


def test_it_is_a_renderer():
    assert isinstance(TextDashboard(), DashboardRenderer)


def test_header(text):
    assert "Bromley, England, United Kingdom" in text
    assert "Updated 5 min ago" in text


def test_right_now(text):
    assert "12°C    Overcast" in text
    assert "Feels like 10°C" in text
    assert "Wind 14 km/h from the SW" in text
    assert "Rain in the last hour" not in text


def test_rain_in_the_last_hour_is_shown_when_there_was_some():
    from dataclasses import replace

    forecast = make_forecast(week())
    forecast = replace(forecast, current=replace(forecast.current, precipitation=1.2))
    assert "Rain in the last hour: 1.2 mm" in dashboard().render(forecast)


def test_days_table(text):
    assert "Today" in text and "Tomorrow" in text and "Sat 24" in text
    assert "90% 12.4 mm" in text


def test_chart_has_a_line_per_day(text):
    chart = text.split("-- Temperature")[1].split("-- Alerts")[0]
    assert chart.count("#") > 0
    assert len([line for line in chart.splitlines() if "#" in line]) == 3


def test_alerts_and_summary(text):
    assert "[Warning] Tomorrow: Heavy rain." in text
    assert "[Warning] Sat 24: Frost." in text
    assert "Warmest: Sat 24 at 16°C" in text
    assert "Wettest: Tomorrow with 12.4 mm" in text
    assert "Dry days: Today, Sat 24" in text


def test_no_alerts_and_no_dry_days():
    forecast = make_forecast([make_day(DAY, rain_chance=50)])
    text = dashboard().render(forecast)
    assert "No weather alerts." in text
    assert "none, keep a coat handy" in text


def test_old_forecast_is_flagged():
    text = dashboard(minutes_later=125).render(make_forecast(week()))
    assert "Updated 2 hours ago (saved copy, may be out of date)" in text


def test_imperial():
    text = dashboard().render(make_forecast(week()), units=Imperial())
    assert "54°F" in text and "mph" in text and " in " in text
    assert "°C" not in text


def test_every_line_fits_the_width(text):
    table_lines = text.split("-- Alerts")[0].splitlines()
    assert all(len(line) <= 72 for line in table_lines)


def test_minimum_width():
    assert TextDashboard(width=10).width == 60


def test_alert_on_a_later_day():
    forecast = make_forecast(week())
    alert = Alert(DAY + timedelta(days=2), "Test", "Just a test.", Severity.DANGER)
    assert "[Danger] Sat 24: Test. Just a test." in dashboard().render(forecast, [alert])


@pytest.mark.parametrize("day, name", [
    (DAY, "Today"), (DAY + timedelta(days=1), "Tomorrow"), (DAY + timedelta(days=4), "Mon 26"),
])
def test_day_name(day, name):
    assert day_name(day, DAY) == name


@pytest.mark.parametrize("minutes, words", [
    (0, "just now"), (-3, "just now"), (1, "1 min ago"), (59, "59 min ago"),
    (60, "1 hour ago"), (150, "2 hours ago"),
])
def test_age_text(minutes, words):
    fetched = datetime(2026, 10, 22, 9, 0)
    assert age_text(fetched, fetched + timedelta(minutes=minutes)) == words


def test_temperature_bar():
    assert temperature_bar(5, 10, 0, 20, 20) == ".....#####.........."
    assert temperature_bar(0, 20, 0, 20, 10) == "##########"
    assert temperature_bar(20, 20, 0, 20, 10) == ".........#"   # always at least one block
    assert temperature_bar(7, 7, 7, 7, 5) == "#...."           # every day the same


def test_default_clock():
    assert "Updated" in TextDashboard().render(make_forecast(week()))

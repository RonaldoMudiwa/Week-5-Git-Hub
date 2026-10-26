"""Tests for the HTML dashboard and its chart."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from html.parser import HTMLParser

import pytest

from weather import (
    Alert,
    AlertChecker,
    ChartSize,
    DashboardRenderer,
    HtmlDashboard,
    Imperial,
    Location,
    Severity,
    TemperatureChart,
)

from .conftest import make_day, make_forecast

DAY = date(2026, 10, 22)


def page(minutes_later: int = 5) -> HtmlDashboard:
    return HtmlDashboard(clock=lambda: datetime(2026, 10, 22, 9, 5) + timedelta(minutes=minutes_later))


def week():
    return [
        make_day(DAY, high=14, low=7, rain_chance=20),
        make_day(DAY + timedelta(days=1), high=12.8, low=8.9, code=63, rain_chance=90,
                 rain_total=12.4, wind_max=55),
        make_day(DAY + timedelta(days=2), high=15.6, low=-1, code=1, rain_chance=0),
    ]


@pytest.fixture
def html() -> str:
    forecast = make_forecast(week())
    return page().render(forecast, AlertChecker().check(forecast))


class TagCounter(HTMLParser):
    """Counts opening and closing tags, to check the page is well formed."""

    VOID = {"meta", "br", "img", "input", "link"}

    def __init__(self) -> None:
        super().__init__()
        self.open: list[str] = []
        self.counts: dict[str, int] = {}
        self.problems: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.counts[tag] = self.counts.get(tag, 0) + 1
        if tag not in self.VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.counts[tag] = self.counts.get(tag, 0) + 1

    def handle_endtag(self, tag):
        if not self.open or self.open.pop() != tag:
            self.problems.append(tag)


def parse(text: str) -> TagCounter:
    counter = TagCounter()
    counter.feed(text)
    return counter


def test_it_is_a_renderer():
    assert isinstance(HtmlDashboard(), DashboardRenderer)


def test_page_is_well_formed(html):
    counter = parse(html)
    assert html.startswith("<!DOCTYPE html>")
    assert counter.problems == []
    assert counter.open == []


def test_page_needs_nothing_from_the_internet(html):
    # Styles and chart are inside the page, so it opens offline.
    assert "<script" not in html
    assert '<link rel="stylesheet"' not in html
    assert "<style>" in html and "<svg" in html


def test_header_and_title(html):
    assert "<title>Weather for Bromley</title>" in html
    assert "<h1>Bromley, England, United Kingdom</h1>" in html
    assert "Updated 5 min ago" in html


def test_right_now(html):
    assert '<span class="temp">12°C</span>' in html
    assert "Overcast" in html
    assert "Wind 14 km/h from the SW" in html
    assert "Rain in the last hour" not in html


def test_rain_in_the_last_hour_is_shown_when_there_was_some():
    forecast = make_forecast(week())
    forecast = replace(forecast, current=replace(forecast.current, precipitation=1.2))
    assert "Rain in the last hour 1.2 mm" in page().render(forecast)


def test_days_table(html):
    assert parse(html).counts["tr"] == 4  # a heading row and three days
    assert "<td>Tomorrow</td>" in html
    assert '<td class="num">90% 12.4 mm</td>' in html


def test_alerts_get_a_colour_by_severity(html):
    assert '<li class="warning"><strong>Warning · Tomorrow: Heavy rain.</strong>' in html
    assert '<li class="warning"><strong>Warning · Sat 24: Frost.</strong>' in html


def test_danger_and_info_alerts():
    alerts = [Alert(DAY, "Umbrella", "Take one.", Severity.INFO),
              Alert(DAY, "Gale", "Stay in.", Severity.DANGER)]
    html = page().render(make_forecast(week()), alerts)
    assert 'class="info"' in html and 'class="danger"' in html


def test_no_alerts_and_no_dry_days():
    html = page().render(make_forecast([make_day(DAY, rain_chance=50)]))
    assert "No weather alerts." in html
    assert "none, keep a coat handy" in html


def test_summary(html):
    assert "Warmest: Sat 24 at 16°C" in html
    assert "Wettest: Tomorrow with 12.4 mm" in html
    assert "Dry days: Today, Sat 24" in html


def test_old_forecast_is_flagged():
    html = page(minutes_later=125).render(make_forecast(week()))
    assert '<p class="old">Updated 2 hours ago (saved copy, may be out of date)</p>' in html


def test_imperial():
    html = page().render(make_forecast(week()), units=Imperial())
    assert "54°F" in html and "mph" in html
    assert "°C" not in html


def test_place_names_are_escaped():
    # A name with < and & must not be able to break or inject into the page.
    sneaky = Location("<script>alert(1)</script> & Co", 51.4, 0.0)
    html = page().render(make_forecast(week(), location=sneaky))
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; Co" in html


def test_save_writes_the_file(tmp_path):
    path = page().save(tmp_path / "out" / "bromley.html", make_forecast(week()))
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_default_clock():
    assert "Updated" in HtmlDashboard().render(make_forecast(week()))


# ----------------------------------------------------------------------
# The chart
# ----------------------------------------------------------------------

def chart_of(days, units=None, size=None) -> str:
    from weather import Metric

    return TemperatureChart(size).draw(make_forecast(days), units or Metric())


def test_chart_has_two_lines_and_a_bar_per_day():
    svg = chart_of(week())
    assert svg.count("<polyline") == 2
    assert svg.count('<rect class="rain"') == 3
    assert svg.count("<circle") == 6


def test_chart_puts_the_warmest_point_at_the_top():
    size = ChartSize(width=400, height=200, margin=20)
    svg = chart_of(week(), size=size)
    high_line = svg.split('class="high" points="')[1].split('"')[0]
    low_line = svg.split('class="low" points="')[1].split('"')[0]
    high_y = [float(point.split(",")[1]) for point in high_line.split()]
    low_y = [float(point.split(",")[1]) for point in low_line.split()]
    assert min(high_y) == 20          # 15.6°C is the top of the chart
    assert max(low_y) == 152          # -1°C is the bottom, above the day names
    assert all(h <= l for h, l in zip(high_y, low_y))


def test_rain_bars_grow_with_the_chance():
    svg = chart_of(week(), size=ChartSize(width=400, height=200, margin=20))
    heights = [float(part.split('height="')[1].split('"')[0])
               for part in svg.split('<rect class="rain"')[1:]]
    assert heights == [26.4, 118.8, 0.0]   # 20%, 90% and 0% of 132


def test_chart_with_one_day_and_flat_temperatures():
    svg = chart_of([make_day(DAY, high=10, low=10)])
    assert "<polyline" in svg   # no divide by zero
    assert "Today" in svg


def test_chart_labels_use_the_units():
    svg = chart_of(week(), units=Imperial())
    assert "°F" in svg and "°C" not in svg
